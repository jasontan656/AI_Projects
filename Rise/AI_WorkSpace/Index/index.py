from __future__ import annotations

import ast
import importlib.util
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

try:
    import yaml
except ImportError as exc:  # pragma: no cover - PyYAML is required for output
    raise SystemExit("PyYAML is required to generate index.yaml") from exc


CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = CURRENT_DIR.parent
RISE_ROOT = WORKSPACE_DIR.parent
UP_ROOT = RISE_ROOT.parent / "Up"

IGNORE_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    ".idea",
    ".pytest_cache",
    "dist",
    "build",
}

JS_IMPORT_RE = re.compile(r"^\s*import\s+[^;]*?\s+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE)
JS_SIDE_EFFECT_IMPORT_RE = re.compile(r"^\s*import\s+['\"]([^'\"]+)['\"]", re.MULTILINE)
JS_EXPORT_FROM_RE = re.compile(r"^\s*export\s+[^;]*?\s+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE)
JS_REQUIRE_RE = re.compile(r"require\(\s*['\"]([^'\"]+)['\"]\s*\)")

JS_EXT_CANDIDATES = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".json")


@dataclass(frozen=True)
class StructureRule:
    layer: str
    path: str
    max_files: int = 2


@dataclass(frozen=True)
class ProjectConfig:
    name: str
    root: Path
    language: str
    source_root: str
    config_files: Sequence[str]
    entry_globs: Sequence[str]
    dependency_source: str
    structure_rules: Sequence[StructureRule]
    graph_exts: Sequence[str]


@dataclass(frozen=True)
class SymbolRecord:
    project: str
    layer: str
    path: str
    name: str
    kind: str
    signature: str
    lines: int
    doc: str
    preview: str
    extra: str = ""


@dataclass(frozen=True)
class ApiRecord:
    project: str
    category: str  # backend / frontend
    layer: str
    path: str
    method: str
    handler: str
    file_path: str
    doc: str
    preview: str


@dataclass(frozen=True)
class EventRecord:
    project: str
    file_path: str
    layer: str
    name: str
    value: str
    kind: str  # event / queue / topic
    context: str


@dataclass(frozen=True)
class ConfigRecord:
    source: str  # env / python
    key: str
    location: str
    note: str


@dataclass(frozen=True)
class StorageRecord:
    backend: str  # mongo / redis / rabbit
    name: str
    file_path: str
    layer: str
    context: str



PROJECTS: Dict[str, ProjectConfig] = {
    "rise": ProjectConfig(
        name="rise-project-utility",
        root=RISE_ROOT,
        language="python",
        source_root="src",
        config_files=("pyproject.toml", "requirements.lock"),
        entry_globs=("app.py", "src/interface_entry/bootstrap/app.py"),
        dependency_source="requirements.lock",
        structure_rules=(
            StructureRule("Project Utility Layer", "src/project_utility"),
            StructureRule("One-off Utility Layer", "src/one_off"),
            StructureRule("Foundational Service Layer", "src/foundational_service"),
            StructureRule("Interface / Entry Layer", "src/interface_entry"),
            StructureRule("Business Service Layer", "src/business_service"),
            StructureRule("Business Logic Layer", "src/business_logic"),
        ),
        graph_exts=(".py",),
    ),
    "up": ProjectConfig(
        name="up",
        root=UP_ROOT,
        language="javascript",
        source_root="src",
        config_files=("package.json", "vite.config.js"),
        entry_globs=("src/main.js", "src/App.vue"),
        dependency_source="package.json",
        structure_rules=(
            StructureRule("Project Utility Layer", "src/utils"),
            StructureRule("Foundational Service Layer", "src/services"),
            StructureRule("Business Service Layer", "src/stores"),
            StructureRule("Interface / Entry Layer", "src/components"),
            StructureRule("Interface / Entry Layer", "src/views"),
        ),
        graph_exts=(".js", ".ts", ".vue"),
    ),
}

SCHEMA_BASE_SUFFIXES = {
    "BaseModel",
    "BaseSettings",
    "TypedDict",
    "DocumentModel",
    "Dataclass",
}

SYMBOL_CATEGORIES = ("functions", "classes", "schemas")

MD_TARGETS = {
    "functions": WORKSPACE_DIR / "functions_index.md",
    "classes": WORKSPACE_DIR / "classes_index.md",
    "schemas": WORKSPACE_DIR / "schemas_index.md",
}

SYMBOL_LIMIT_PER_LAYER = 6

API_INDEX_PATH = WORKSPACE_DIR / "api_index.md"
EVENT_INDEX_PATH = WORKSPACE_DIR / "events_index.md"
CONFIG_INDEX_PATH = WORKSPACE_DIR / "config_index.md"
STORAGE_INDEX_PATH = WORKSPACE_DIR / "storage_index.md"

EXPORT_FUNCTION_RE = re.compile(r"export\s+(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)", re.MULTILINE)
EXPORT_CONST_FUNC_RE = re.compile(r"export\s+const\s+(\w+)\s*=\s*(?:async\s*)?\(([^)]*)\s*=>", re.MULTILINE)
DEFINE_STORE_RE = re.compile(r"defineStore\(\s*['\"]([^'\"]+)['\"]")
CLASS_DECL_RE = re.compile(r"export\s+class\s+(\w+)")
DEFINE_COMPONENT_RE = re.compile(r"defineComponent\(\s*{", re.MULTILINE)

HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}

REQUEST_JSON_PATTERN = re.compile(r"requestJson\s*\(", re.MULTILINE)
EVENT_CONST_RE = re.compile(r"([A-Z0-9_]*EVENT[A-Z0-9_]*)\s*=\s*['\"]([^'\"]+)['\"]")
QUEUE_CONST_RE = re.compile(r"([A-Z0-9_]*(QUEUE|EXCHANGE|TOPIC)[A-Z0-9_]*)\s*=\s*['\"]([^'\"]+)")
MONGO_COLLECTION_RE = re.compile(r"db\[\s*['\"]([^'\"]+)['\"]\s*\]")
UPPERCASE_ASSIGN_RE = re.compile(r"^([A-Z_][A-Z0-9_]*)\s*=\s*.+", re.MULTILINE)


def main() -> None:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    index_data = {
        "generated_at": generated_at,
        "projects": {},
    }
    symbol_buckets: Dict[str, List[SymbolRecord]] = {kind: [] for kind in SYMBOL_CATEGORIES}
    api_records: List[ApiRecord] = []
    event_records: List[EventRecord] = []
    config_records: List[ConfigRecord] = []
    storage_records: List[StorageRecord] = []
    for key, config in PROJECTS.items():
        if not config.root.exists():
            continue
        project_data = build_project_index(config)
        index_data["projects"][key] = project_data
        symbol_data = collect_symbol_index(key, config)
        for kind in SYMBOL_CATEGORIES:
            symbol_buckets[kind].extend(symbol_data[kind])
        api_records.extend(collect_api_records(key, config))
        event_records.extend(collect_event_records(key, config))
        storage_records.extend(collect_storage_records(key, config))
    config_records.extend(collect_config_records())
    write_yaml_index(index_data)
    write_markdown_indexes(symbol_buckets, generated_at)
    write_api_index(api_records, generated_at)
    write_event_index(event_records, generated_at)
    write_config_index(config_records, generated_at)
    write_storage_index(storage_records, generated_at)


def build_project_index(config: ProjectConfig) -> Dict[str, object]:
    meta = collect_meta(config)
    structure = collect_structure(config)
    graph = collect_dependency_graph(config, structure)
    return {"meta": meta, "structure": structure, "graph": graph}


def write_yaml_index(data: Dict[str, object]) -> None:
    output_path = WORKSPACE_DIR / "index.yaml"
    with output_path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, allow_unicode=False, sort_keys=False)


def write_markdown_indexes(symbol_buckets: Dict[str, List[SymbolRecord]], generated_at: str) -> None:
    for kind, path in MD_TARGETS.items():
        records = select_symbols(symbol_buckets[kind])
        content = render_markdown(kind, records, generated_at)
        with path.open("w", encoding="utf-8") as fh:
            fh.write(content)


def write_api_index(api_records: List[ApiRecord], generated_at: str) -> None:
    backend = [record for record in api_records if record.category == "backend"]
    frontend = [record for record in api_records if record.category == "frontend"]
    lines = [
        "# API 索引",
        "",
        f"_生成时间：{generated_at}_",
        "",
    ]
    lines.append("## 后端接口（FastAPI）")
    lines.append("")
    if backend:
        for record in backend:
            lines.extend(format_api_entry(record))
            lines.append("")
    else:
        lines.append("（暂无 FastAPI 路由记录）\n")
    lines.append("## 前端服务请求（Up）")
    lines.append("")
    if frontend:
        for record in frontend:
            lines.extend(format_api_entry(record))
            lines.append("")
    else:
        lines.append("（暂无前端请求记录）\n")
    API_INDEX_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_event_index(records: List[EventRecord], generated_at: str) -> None:
    lines = [
        "# 事件 / 队列索引",
        "",
        f"_生成时间：{generated_at}_",
        "",
    ]
    if not records:
        lines.append("（暂无事件/队列记录）\n")
    else:
        grouped: Dict[str, List[EventRecord]] = defaultdict(list)
        for record in records:
            grouped[record.project].append(record)
        for project, items in grouped.items():
            lines.append(f"## {project}")
            lines.append("")
            for item in items:
                lines.extend(format_event_entry(item))
                lines.append("")
    EVENT_INDEX_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_config_index(records: List[ConfigRecord], generated_at: str) -> None:
    lines = [
        "# 配置 / Flag 索引",
        "",
        f"_生成时间：{generated_at}_",
        "",
    ]
    if not records:
        lines.append("（暂无配置记录）\n")
    else:
        env = [r for r in records if r.source == "env"]
        py = [r for r in records if r.source == "python"]
        if env:
            lines.append("## .env 变量")
            lines.append("")
            for entry in env:
                lines.append(f"- `{entry.key}` · {entry.location} · {entry.note}")
            lines.append("")
        if py:
            lines.append("## Python 配置常量")
            lines.append("")
            for entry in py:
                lines.append(f"- `{entry.key}` · {entry.location} · {entry.note}")
            lines.append("")
    CONFIG_INDEX_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_storage_index(records: List[StorageRecord], generated_at: str) -> None:
    lines = [
        "# 数据持久化索引",
        "",
        f"_生成时间：{generated_at}_",
        "",
    ]
    if not records:
        lines.append("（暂无存储映射记录）\n")
    else:
        grouped: Dict[str, List[StorageRecord]] = defaultdict(list)
        for record in records:
            grouped[record.backend].append(record)
        for backend, items in grouped.items():
            lines.append(f"## {backend.upper()}")
            lines.append("")
            for item in items:
                lines.append(
                    f"- `{item.name}` · {item.file_path} · {item.layer} · {item.context}"
                )
            lines.append("")
    STORAGE_INDEX_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def collect_meta(config: ProjectConfig) -> Dict[str, object]:
    meta: Dict[str, object] = {
        "root": rel_posix(config.root),
        "language": config.language,
        "config": [cfg for cfg in config.config_files if (config.root / cfg).exists()],
        "entrypoints": gather_entrypoints(config),
        "dependencies": collect_dependencies(config),
    }
    return meta


def gather_entrypoints(config: ProjectConfig) -> List[str]:
    entries: List[str] = []
    for pattern in config.entry_globs:
        for path in config.root.glob(pattern):
            if path.is_file():
                entries.append(rel_posix(path, config.root))
    return sorted(dict.fromkeys(entries))


def collect_dependencies(config: ProjectConfig, limit: int = 10) -> List[str]:
    source = config.root / config.dependency_source
    if not source.exists():
        return []
    if source.name.endswith(".lock"):
        return parse_requirements(source, limit)
    if source.suffix == ".json":
        return parse_package_json(source, limit)
    return []


def parse_requirements(path: Path, limit: int) -> List[str]:
    items: List[str] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            value = line.strip()
            if not value or value.startswith("#"):
                continue
            items.append(value)
            if len(items) >= limit:
                break
    return items


def parse_package_json(path: Path, limit: int) -> List[str]:
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    deps = payload.get("dependencies", {})
    dev = payload.get("devDependencies", {})
    merged = [f"{k}@{v}" for k, v in {**deps, **dev}.items()]
    return merged[:limit]


def collect_structure(config: ProjectConfig) -> List[Dict[str, object]]:
    summaries: List[Dict[str, object]] = []
    for rule in config.structure_rules:
        dir_path = config.root / rule.path
        if not dir_path.exists():
            continue
        summary = summarize_directory(dir_path, config.root, rule)
        if summary:
            summaries.append(summary)
    return summaries


def summarize_directory(dir_path: Path, project_root: Path, rule: StructureRule) -> Optional[Dict[str, object]]:
    file_records: List[Tuple[int, Path]] = []
    ext_counter: Counter[str] = Counter()

    for path in dir_path.rglob("*"):
        if not path.is_file():
            continue
        if should_ignore(path):
            continue
        rel = path.relative_to(project_root)
        ext = path.suffix.lstrip(".").lower() or "noext"
        ext_counter[ext] += 1
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        file_records.append((size, rel))

    if not file_records:
        return None

    file_records.sort(reverse=True, key=lambda item: item[0])
    key_files = [
        rel_posix(path)
        for _, path in file_records[: rule.max_files]
    ]
    ext_summary = [
        f"{ext}({count})"
        for ext, count in ext_counter.most_common(2)
    ]

    return {
        "layer": rule.layer,
        "path": rel_posix(dir_path, project_root),
        "ext": ext_summary,
        "files": key_files,
    }


def should_ignore(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)


def collect_dependency_graph(
    config: ProjectConfig,
    structure: List[Dict[str, object]],
) -> Dict[str, Dict[str, List[str]]]:
    target_files: Set[str] = set()
    for entry in structure:
        for rel_path in entry.get("files", []):
            target_files.add(rel_path)

    src_root = config.root / config.source_root
    python_index = {}
    if ".py" in config.graph_exts and src_root.exists():
        python_index = build_python_index(src_root)

    graph: Dict[str, Dict[str, List[str]]] = {}
    for rel_path in sorted(target_files):
        file_path = config.root / rel_path
        if not file_path.exists():
            continue
        ext = file_path.suffix.lower()
        local: Set[str] = set()
        external: Set[str] = set()
        if ext == ".py":
            local, external = analyze_python_file(file_path, src_root, config.root, python_index)
        elif ext in {".js", ".ts", ".vue", ".mjs", ".jsx", ".tsx"}:
            local, external = analyze_js_file(file_path, src_root, config.root)
        graph[rel_path] = {
            "local": sorted(local)[:5],
            "external": sorted(external)[:5],
        }
    return graph


def collect_symbol_index(project_key: str, config: ProjectConfig) -> Dict[str, List[SymbolRecord]]:
    if config.language == "python":
        return collect_python_symbols(project_key, config)
    return collect_js_symbols(project_key, config)


def collect_python_symbols(project_key: str, config: ProjectConfig) -> Dict[str, List[SymbolRecord]]:
    buckets: Dict[str, List[SymbolRecord]] = {kind: [] for kind in SYMBOL_CATEGORIES}
    src_root = config.root / config.source_root
    if not src_root.exists():
        return buckets
    for file_path in src_root.rglob("*.py"):
        if should_ignore(file_path):
            continue
        if "tests" in {part.lower() for part in file_path.parts}:
            continue
        text = file_path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, filename=str(file_path))
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                record = build_class_record(project_key, config, file_path, text, node)
                if not record:
                    continue
                buckets[record.kind].append(record)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                record = build_function_record(project_key, config, file_path, text, node)
                if record:
                    buckets["functions"].append(record)
    return buckets


def collect_api_records(project_key: str, config: ProjectConfig) -> List[ApiRecord]:
    if project_key == "rise":
        return collect_backend_api_records(project_key, config)
    if project_key == "up":
        return collect_frontend_api_records(project_key, config)
    return []


def collect_backend_api_records(project_key: str, config: ProjectConfig) -> List[ApiRecord]:
    api_records: List[ApiRecord] = []
    target_dir = config.root / "src" / "interface_entry"
    if not target_dir.exists():
        return api_records
    for file_path in target_dir.rglob("*.py"):
        if should_ignore(file_path):
            continue
        text = file_path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, filename=str(file_path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            doc = format_docstring(ast.get_docstring(node))
            preview = extract_source_preview(text, node)
            rel_path = rel_posix(file_path, config.root)
            layer = infer_layer(file_path, config)
            for decorator in node.decorator_list:
                method, path = parse_router_decorator(decorator)
                if method and path:
                    api_records.append(
                        ApiRecord(
                            project=project_key,
                            category="backend",
                            layer=layer,
                            path=path,
                            method=method,
                            handler=node.name,
                            file_path=rel_path,
                            doc=doc,
                            preview=preview,
                        )
                    )
    return api_records


def parse_router_decorator(decorator: ast.AST) -> Tuple[Optional[str], Optional[str]]:
    if not isinstance(decorator, ast.Call):
        return None, None
    func = decorator.func
    method = None
    if isinstance(func, ast.Attribute):
        attr = func.attr.lower()
        if attr in HTTP_METHODS:
            method = attr.upper()
    elif isinstance(func, ast.Name):
        # decorator like @get("/path")
        attr = func.id.lower()
        if attr in HTTP_METHODS:
            method = attr.upper()
    if not method:
        return None, None
    if not decorator.args:
        return method, None
    first = decorator.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return method, first.value
    return method, None


def collect_frontend_api_records(project_key: str, config: ProjectConfig) -> List[ApiRecord]:
    api_records: List[ApiRecord] = []
    src_root = config.root / config.source_root
    if not src_root.exists():
        return api_records
    for file_path in src_root.rglob("*.js"):
        if should_ignore(file_path):
            continue
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        rel_path = rel_posix(file_path, config.root)
        layer = infer_layer(file_path, config)
        functions = list(find_js_functions(text))
        for match in REQUEST_JSON_PATTERN.finditer(text):
            call_start = match.end()
            call_text, call_end = extract_balanced_segment(text, call_start - 1)
            if not call_text:
                continue
            path_literal = parse_js_string_literal(call_text)
            method = parse_js_method(call_text)
            handler = resolve_enclosing_js_function(functions, match.start())
            doc = handler or "requestJson 调用"
            preview = truncate_text(call_text.strip(), 160)
            api_records.append(
                ApiRecord(
                    project=project_key,
                    category="frontend",
                    layer=layer,
                    path=path_literal or "(动态路径)",
                    method=method or "GET",
                    handler=handler or "(匿名)",
                    file_path=rel_path,
                    doc=doc,
                    preview=preview,
                )
            )
    return api_records


def collect_event_records(project_key: str, config: ProjectConfig) -> List[EventRecord]:
    if project_key != "rise":
        return []
    event_records: List[EventRecord] = []
    target_dirs = [
        config.root / "src" / "foundational_service" / "messaging",
        config.root / "src" / "business_service",
        config.root / "src" / "interface_entry" / "runtime",
    ]
    for directory in target_dirs:
        if not directory.exists():
            continue
        for file_path in directory.rglob("*.py"):
            if should_ignore(file_path):
                continue
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            layer = infer_layer(file_path, config)
            rel_path = rel_posix(file_path, config.root)
            for match in EVENT_CONST_RE.finditer(text):
                context = extract_line_around(text, match.start())
                event_records.append(
                    EventRecord(
                        project=project_key,
                        file_path=rel_path,
                        layer=layer,
                        name=match.group(1),
                        value=match.group(2),
                        kind="event",
                        context=context,
                    )
                )
            for match in QUEUE_CONST_RE.finditer(text):
                context = extract_line_around(text, match.start())
                kind = match.group(2).lower()
                event_records.append(
                    EventRecord(
                        project=project_key,
                        file_path=rel_path,
                        layer=layer,
                        name=match.group(1),
                        value=match.group(3),
                        kind=kind,
                        context=context,
                    )
                )
    return event_records


def collect_config_records() -> List[ConfigRecord]:
    records: List[ConfigRecord] = []
    env_file = RISE_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, _ = stripped.split("=", 1)
            records.append(
                ConfigRecord(
                    source="env",
                    key=key.strip(),
                    location=".env",
                    note="存在值（未导出具体内容）",
                )
            )
    config_dir = RISE_ROOT / "src" / "project_utility" / "config"
    if config_dir.exists():
        for file_path in config_dir.rglob("*.py"):
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            for match in UPPERCASE_ASSIGN_RE.finditer(text):
                key = match.group(1)
                if key.startswith("_"):
                    continue
                records.append(
                    ConfigRecord(
                        source="python",
                        key=key,
                        location=rel_posix(file_path, RISE_ROOT),
                        note="模块常量",
                    )
                )
    return records


def collect_storage_records(project_key: str, config: ProjectConfig) -> List[StorageRecord]:
    if project_key != "rise":
        return []
    records: List[StorageRecord] = []
    target_dirs = [
        config.root / "src" / "business_service",
        config.root / "src" / "foundational_service" / "persist",
    ]
    for directory in target_dirs:
        if not directory.exists():
            continue
        for file_path in directory.rglob("*.py"):
            if should_ignore(file_path):
                continue
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            layer = infer_layer(file_path, config)
            rel_path = rel_posix(file_path, config.root)
            for match in MONGO_COLLECTION_RE.finditer(text):
                records.append(
                    StorageRecord(
                        backend="mongo",
                        name=match.group(1),
                        file_path=rel_path,
                        layer=layer,
                        context=extract_line_around(text, match.start()),
                    )
                )
            for match in QUEUE_CONST_RE.finditer(text):
                records.append(
                    StorageRecord(
                        backend="rabbit",
                        name=match.group(3),
                        file_path=rel_path,
                        layer=layer,
                        context=extract_line_around(text, match.start()),
                    )
                )
            if "redis" in text.lower():
                records.append(
                    StorageRecord(
                        backend="redis",
                        name=Path(rel_path).stem,
                        file_path=rel_path,
                        layer=layer,
                        context="包含 redis 关键字",
                    )
                )
    return records


def build_class_record(
    project_key: str,
    config: ProjectConfig,
    file_path: Path,
    text: str,
    node: ast.ClassDef,
) -> Optional[SymbolRecord]:
    if not node.name or node.name.startswith("_"):
        return None
    rel_path = rel_posix(file_path, config.root)
    layer = infer_layer(file_path, config)
    lines = max(1, (node.end_lineno or node.lineno) - node.lineno + 1)
    doc = format_docstring(ast.get_docstring(node))
    bases = resolve_base_names(node)
    decorators = [resolve_name(deco) for deco in node.decorator_list if resolve_name(deco)]
    category = "schemas" if is_schema_class(bases, decorators) else "classes"
    signature = format_class_signature(node.name, bases)
    preview = extract_source_preview(text, node)
    extra_bits: List[str] = []
    if bases:
        extra_bits.append("基类: " + ", ".join(bases))
    if decorators:
        extra_bits.append("装饰器: " + ", ".join(decorators))
    extra = "; ".join(extra_bits)
    return SymbolRecord(
        project=project_key,
        layer=layer,
        path=rel_path,
        name=node.name,
        kind=category,
        signature=signature,
        lines=lines,
        doc=doc,
        preview=preview,
        extra=extra,
    )


def build_function_record(
    project_key: str,
    config: ProjectConfig,
    file_path: Path,
    text: str,
    node: ast.AST,
) -> Optional[SymbolRecord]:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return None
    if not node.name or node.name.startswith("_"):
        return None
    rel_path = rel_posix(file_path, config.root)
    layer = infer_layer(file_path, config)
    lines = max(1, (node.end_lineno or node.lineno) - node.lineno + 1)
    doc = format_docstring(ast.get_docstring(node))
    signature = format_function_signature(node)
    preview = extract_source_preview(text, node)
    extra = "async" if isinstance(node, ast.AsyncFunctionDef) else ""
    return SymbolRecord(
        project=project_key,
        layer=layer,
        path=rel_path,
        name=node.name,
        kind="functions",
        signature=signature,
        lines=lines,
        doc=doc,
        preview=preview,
        extra=extra,
    )


def collect_js_symbols(project_key: str, config: ProjectConfig) -> Dict[str, List[SymbolRecord]]:
    buckets: Dict[str, List[SymbolRecord]] = {kind: [] for kind in SYMBOL_CATEGORIES}
    src_root = config.root / config.source_root
    if not src_root.exists():
        return buckets
    for file_path in src_root.rglob("*"):
        suffix = file_path.suffix.lower()
        if suffix not in {".js", ".ts", ".vue"}:
            continue
        if should_ignore(file_path):
            continue
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        rel_path = rel_posix(file_path, config.root)
        layer = infer_layer(file_path, config)
        component_added = False
        for match in EXPORT_FUNCTION_RE.finditer(text):
            record = build_js_record(
                project_key,
                rel_path,
                layer,
                kind="functions",
                name=match.group(1),
                signature=f"{match.group(1)}({match.group(2).strip()})",
                text=text,
                start=match.start(),
            )
            buckets["functions"].append(record)
        for match in EXPORT_CONST_FUNC_RE.finditer(text):
            record = build_js_record(
                project_key,
                rel_path,
                layer,
                kind="functions",
                name=match.group(1),
                signature=f"{match.group(1)}({match.group(2).strip()} =>)",
                text=text,
                start=match.start(),
            )
            buckets["functions"].append(record)
        for match in CLASS_DECL_RE.finditer(text):
            record = build_js_record(
                project_key,
                rel_path,
                layer,
                kind="classes",
                name=match.group(1),
                signature=f"class {match.group(1)}",
                text=text,
                start=match.start(),
            )
            buckets["classes"].append(record)
        for match in DEFINE_STORE_RE.finditer(text):
            store_name = match.group(1)
            record = build_js_record(
                project_key,
                rel_path,
                layer,
                kind="schemas",
                name=store_name,
                signature=f"defineStore('{store_name}')",
                text=text,
                start=match.start(),
            )
            buckets["schemas"].append(record)
        component_match = DEFINE_COMPONENT_RE.search(text)
        if component_match:
            comp_name = file_path.stem
            record = build_js_record(
                project_key,
                rel_path,
                layer,
                kind="classes",
                name=comp_name,
                signature=f"defineComponent({comp_name})",
                text=text,
                start=component_match.start(),
            )
            buckets["classes"].append(record)
            component_added = True
        if suffix == ".vue" and not component_added:
            record = build_vue_component_record(project_key, rel_path, layer, text, file_path.stem)
            buckets["classes"].append(record)
    return buckets


def build_js_record(
    project_key: str,
    rel_path: str,
    layer: str,
    kind: str,
    name: str,
    signature: str,
    text: str,
    start: int,
) -> SymbolRecord:
    preview, approx_lines = extract_js_preview(text, start)
    doc = extract_js_doc(text, start)
    return SymbolRecord(
        project=project_key,
        layer=layer,
        path=rel_path,
        name=name,
        kind=kind,
        signature=signature,
        lines=approx_lines,
        doc=doc,
        preview=preview,
        extra="",
    )


def build_python_index(src_root: Path) -> Dict[str, Path]:
    module_index: Dict[str, Path] = {}
    for path in src_root.rglob("*.py"):
        if should_ignore(path):
            continue
        rel = path.relative_to(src_root)
        module_name = ".".join(rel.with_suffix("").parts)
        module_index[module_name] = path
    return module_index


def analyze_python_file(
    file_path: Path,
    src_root: Path,
    project_root: Path,
    module_index: Dict[str, Path],
) -> Tuple[Set[str], Set[str]]:
    text = file_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text, filename=str(file_path))
    except SyntaxError:
        return set(), set()

    local_deps: Set[str] = set()
    external_deps: Set[str] = set()
    package = ".".join(file_path.relative_to(src_root).with_suffix("").parts)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                track_python_dependency(alias.name, package, module_index, project_root, local_deps, external_deps)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            for alias in node.names:
                target = build_import_from_target(base, alias.name, node.level)
                track_python_dependency(target, package, module_index, project_root, local_deps, external_deps)

    self_rel = rel_posix(file_path, project_root)
    local_deps.discard(self_rel)
    return local_deps, external_deps


def build_import_from_target(base: str, name: str, level: int) -> str:
    prefix = "." * level
    if name == "*":
        return f"{prefix}{base}"
    if base:
        return f"{prefix}{base}.{name}"
    return f"{prefix}{name}" if prefix else name


def track_python_dependency(
    module_name: str,
    package: str,
    module_index: Dict[str, Path],
    project_root: Path,
    local_deps: Set[str],
    external_deps: Set[str],
) -> None:
    target = resolve_python_module(module_name, package, module_index)
    if target:
        local_deps.add(rel_posix(target, project_root))
    elif module_name:
        external_deps.add(module_name.split(".")[0])


def resolve_python_module(module_name: str, package: str, module_index: Dict[str, Path]) -> Optional[Path]:
    if not module_name:
        return None
    if module_name.startswith("."):
        try:
            module_name = importlib.util.resolve_name(module_name, package)
        except ImportError:
            return None
    parts = module_name.split(".")
    while parts:
        candidate = ".".join(parts)
        if candidate in module_index:
            return module_index[candidate]
        parts.pop()
    return None


def analyze_js_file(
    file_path: Path,
    src_root: Path,
    project_root: Path,
) -> Tuple[Set[str], Set[str]]:
    text = file_path.read_text(encoding="utf-8")
    imports: Set[str] = set()
    for pattern in (JS_IMPORT_RE, JS_SIDE_EFFECT_IMPORT_RE, JS_EXPORT_FROM_RE, JS_REQUIRE_RE):
        imports.update(pattern.findall(text))

    local_deps: Set[str] = set()
    external_deps: Set[str] = set()
    for spec in imports:
        resolved = resolve_js_specifier(spec, file_path, src_root)
        if resolved:
            local_deps.add(rel_posix(resolved, project_root))
        else:
            external_deps.add(spec.split("/")[0])

    self_rel = rel_posix(file_path, project_root)
    local_deps.discard(self_rel)
    return local_deps, external_deps


def resolve_js_specifier(spec: str, file_path: Path, src_root: Path) -> Optional[Path]:
    base = file_path.parent
    candidate: Optional[Path] = None
    if spec.startswith("./") or spec.startswith("../"):
        candidate = (base / spec).resolve()
    elif spec.startswith("@/"):
        relative = spec[2:]
        candidate = (src_root / relative).resolve()
    else:
        return None

    if candidate.is_file():
        return candidate
    if candidate.is_dir():
        for suffix in ("index.ts", "index.tsx", "index.js", "index.jsx", "index.vue"):
            next_candidate = candidate / suffix
            if next_candidate.exists():
                return next_candidate
        return None

    for ext in JS_EXT_CANDIDATES:
        with_ext = candidate.with_suffix(ext)
        if with_ext.exists():
            return with_ext
    return None


def infer_layer(file_path: Path, config: ProjectConfig) -> str:
    abs_path = file_path.resolve()
    for rule in config.structure_rules:
        base = (config.root / rule.path).resolve()
        try:
            abs_path.relative_to(base)
            return rule.layer
        except ValueError:
            continue
    return "Unmapped"


def format_docstring(doc: Optional[str]) -> str:
    if not doc:
        return ""
    first_line = doc.strip().splitlines()[0]
    return truncate_text(first_line, 160)


def resolve_base_names(node: ast.ClassDef) -> List[str]:
    names: List[str] = []
    for base in node.bases:
        value = resolve_name(base)
        if value:
            names.append(value)
    return names


def resolve_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = resolve_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Subscript):
        return resolve_name(node.value)
    if isinstance(node, ast.Call):
        return resolve_name(node.func)
    return ""


def is_schema_class(bases: List[str], decorators: List[str]) -> bool:
    base_suffixes = {name.split(".")[-1] for name in bases}
    deco_suffixes = {name.split(".")[-1] for name in decorators}
    if deco_suffixes.intersection({"dataclass", "pydantic_dataclass"}):
        return True
    if base_suffixes.intersection(SCHEMA_BASE_SUFFIXES):
        return True
    return False


def format_class_signature(name: str, bases: List[str]) -> str:
    if bases:
        return f"class {name}({', '.join(bases)})"
    return f"class {name}"


def extract_source_preview(text: str, node: ast.AST, max_lines: int = 3) -> str:
    segment = ast.get_source_segment(text, node) or ""
    lines = [line.rstrip() for line in segment.strip().splitlines()[:max_lines]]
    return truncate_text(" ".join(lines), 200)


def format_function_signature(node: ast.AST) -> str:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return ""
    params = render_arguments(node.args)
    prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
    returns = f" -> {ast.unparse(node.returns)}" if getattr(node, "returns", None) else ""
    return f"{prefix}def {node.name}({params}){returns}"


def render_arguments(args: ast.arguments) -> str:
    parts: List[str] = []
    posonly_total = len(args.posonlyargs)
    regular = args.args
    all_positional = args.posonlyargs + regular
    total_positional = len(all_positional)
    defaults = list(args.defaults)
    default_start = total_positional - len(defaults)
    for idx, arg in enumerate(all_positional):
        default = defaults[idx - default_start] if idx >= default_start and defaults else None
        parts.append(format_single_argument(arg, default))
        if posonly_total and idx + 1 == posonly_total:
            parts.append("/")
    if args.vararg:
        parts.append("*" + args.vararg.arg)
    elif args.kwonlyargs:
        parts.append("*")
    for kwarg, default in zip(args.kwonlyargs, args.kw_defaults):
        parts.append(format_single_argument(kwarg, default))
    if args.kwarg:
        parts.append("**" + args.kwarg.arg)
    return ", ".join(part for part in parts if part)


def format_single_argument(arg: ast.arg, default: Optional[ast.AST]) -> str:
    name = arg.arg
    if arg.annotation:
        name += f": {ast.unparse(arg.annotation)}"
    if default is not None:
        name += f"={ast.unparse(default)}"
    return name


def extract_js_preview(text: str, start: int, max_chars: int = 320) -> Tuple[str, int]:
    end = text.find("\n\n", start)
    if end == -1 or end - start > max_chars:
        end = min(len(text), start + max_chars)
    segment = text[start:end]
    preview = truncate_text(" ".join(segment.strip().splitlines()[:3]), 200)
    lines = max(1, segment.count("\n") + 1)
    return preview, lines


def extract_js_doc(text: str, start: int) -> str:
    window_start = max(0, start - 200)
    window = text[window_start:start]
    comments = [
        line.strip().lstrip("/").strip()
        for line in window.splitlines()
        if line.strip().startswith("//")
    ]
    if comments:
        return truncate_text(comments[-1], 160)
    return ""


def build_vue_component_record(
    project_key: str,
    rel_path: str,
    layer: str,
    text: str,
    name: str,
) -> SymbolRecord:
    doc = extract_vue_doc(text)
    preview = extract_vue_preview(text)
    lines = text.count("\n") + 1
    signature = f"VueComponent<{name}>"
    return SymbolRecord(
        project=project_key,
        layer=layer,
        path=rel_path,
        name=name,
        kind="classes",
        signature=signature,
        lines=lines,
        doc=doc,
        preview=preview,
        extra="",
    )


def extract_vue_doc(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("<!") or stripped.startswith("<template"):
            continue
        if stripped.startswith("<!--") and "-->" in stripped:
            return truncate_text(stripped.strip("<!-> ").strip(), 160)
        if not stripped.startswith("<template"):
            return truncate_text(stripped, 160)
    return ""


def extract_vue_preview(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            lines.append(stripped)
        if len(lines) >= 3:
            break
    return truncate_text(" ".join(lines), 200)


def find_js_functions(text: str) -> List[Tuple[str, int]]:
    patterns = [
        re.compile(r"export\s+(?:async\s+)?function\s+(\w+)\s*\(", re.MULTILINE),
        re.compile(r"export\s+const\s+(\w+)\s*=\s*(?:async\s*)?\(", re.MULTILINE),
        re.compile(r"export\s+function\s+(\w+)\s*=", re.MULTILINE),
    ]
    matches: List[Tuple[str, int]] = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            matches.append((match.group(1), match.start()))
    matches.sort(key=lambda item: item[1])
    return matches


def extract_balanced_segment(text: str, open_paren_index: int) -> Tuple[str, int]:
    if open_paren_index >= len(text) or text[open_paren_index] != "(":
        return "", open_paren_index
    depth = 0
    idx = open_paren_index
    start_content = open_paren_index + 1
    while idx < len(text):
        char = text[idx]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[start_content:idx], idx + 1
        elif char in "`'\"":
            idx = skip_js_string(text, idx)
        idx += 1
    return text[start_content:], len(text)


def skip_js_string(text: str, start: int) -> int:
    quote = text[start]
    idx = start + 1
    if quote == "`":
        brace_depth = 0
        while idx < len(text):
            char = text[idx]
            if char == "\\":
                idx += 2
                continue
            if char == "{" and brace_depth >= 0:
                brace_depth += 1
                idx += 1
                continue
            if char == "}" and brace_depth > 0:
                brace_depth -= 1
                idx += 1
                continue
            if char == "`" and brace_depth == 0:
                return idx
            idx += 1
        return len(text) - 1
    while idx < len(text):
        char = text[idx]
        if char == "\\":
            idx += 2
            continue
        if char == quote:
            return idx
        idx += 1
    return len(text) - 1


def parse_js_string_literal(args_text: str) -> Optional[str]:
    idx = 0
    length = len(args_text)
    while idx < length and args_text[idx].isspace():
        idx += 1
    if idx >= length:
        return None
    quote = args_text[idx]
    if quote in {'"', "'", "`"}:
        end = skip_js_string(args_text, idx)
        literal = args_text[idx : end + 1]
        return literal.strip()
    # fallback: read until comma
    end = args_text.find(",")
    if end == -1:
        end = length
    return args_text[idx:end].strip()


def parse_js_method(args_text: str) -> Optional[str]:
    method_match = re.search(r"method\s*:\s*['\"]([A-Z]+)['\"]", args_text)
    if method_match:
        return method_match.group(1).upper()
    return None


def resolve_enclosing_js_function(functions: List[Tuple[str, int]], position: int) -> Optional[str]:
    latest = None
    for name, start in functions:
        if start <= position:
            latest = name
        else:
            break
    return latest


def format_api_entry(record: ApiRecord) -> List[str]:
    scope = "Rise" if record.category == "backend" else "Up"
    doc = record.doc or "（无说明）"
    preview = record.preview or ""
    return [
        f"- `{record.method} {record.path}` · `{record.handler}` · {scope} · {record.file_path}",
        f"  - 说明：{doc}",
        f"  - 片段：{truncate_text(preview, 200)}",
    ]


def format_event_entry(record: EventRecord) -> List[str]:
    return [
        f"- `{record.name}` = `{record.value}` · {record.kind} · {record.file_path}",
        f"  - 层级：{record.layer}",
        f"  - 片段：{record.context}",
    ]


def truncate_text(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    return value[: max_len - 1] + "…"


def extract_line_around(text: str, index: int, window: int = 120) -> str:
    start = max(0, index - window)
    end = min(len(text), index + window)
    segment = text[start:end]
    line = segment.splitlines()
    if line:
        return truncate_text(line[0].strip(), 160)
    return ""


def infer_related_module(text: str) -> str:
    module_match = re.search(r"from\s+src\.([a-zA-Z0-9_\.]+)", text)
    if module_match:
        return module_match.group(1)
    module_match = re.search(r"import\s+src\.([a-zA-Z0-9_\.]+)", text)
    if module_match:
        return module_match.group(1)
    vue_match = re.search(r"from\s+'@/(.+?)'", text)
    if vue_match:
        return vue_match.group(1)
    return ""


def select_symbols(records: List[SymbolRecord]) -> Dict[Tuple[str, str], List[SymbolRecord]]:
    grouped: Dict[Tuple[str, str], List[SymbolRecord]] = defaultdict(list)
    sorted_records = sorted(
        records,
        key=lambda r: (r.project, r.layer, -r.lines, r.path, r.name),
    )
    for record in sorted_records:
        bucket = grouped[(record.project, record.layer)]
        if len(bucket) >= SYMBOL_LIMIT_PER_LAYER:
            continue
        bucket.append(record)
    return grouped


def render_markdown(kind: str, grouped: Dict[Tuple[str, str], List[SymbolRecord]], generated_at: str) -> str:
    title_map = {
        "functions": "函数索引",
        "classes": "类索引",
        "schemas": "Schema 索引",
    }
    lines = [
        f"# {title_map.get(kind, kind)}",
        "",
        f"_生成时间：{generated_at}_",
        "",
    ]
    for project_key, config in PROJECTS.items():
        project_layers = [rule.layer for rule in config.structure_rules] + ["Unmapped"]
        has_content = any((project_key, layer) in grouped for layer in project_layers)
        if not has_content:
            continue
        lines.append(f"## {config.name}（{project_key}）")
        lines.append("")
        for layer in project_layers:
            bucket = grouped.get((project_key, layer))
            if not bucket:
                continue
            lines.append(f"### {layer}")
            lines.append("")
            for record in bucket:
                lines.extend(format_symbol_entry(record))
            lines.append("")
    if len(lines) == 4:
        lines.append("（暂未扫描到相关符号）")
    return "\n".join(lines).rstrip() + "\n"


def format_symbol_entry(record: SymbolRecord) -> List[str]:
    doc_line = record.doc or "（无 docstring，参考片段）"
    preview = record.preview or record.signature
    meta_bits = [f"{record.lines} 行"]
    if record.extra:
        meta_bits.append(record.extra)
    meta = " · ".join(meta_bits)
    formatted = [
        f"- `{record.path}` · `{record.signature}` · {meta}",
        f"  - 说明：{doc_line}",
        f"  - 片段：{preview}",
    ]
    return formatted


def rel_posix(path: Path, base: Optional[Path] = None) -> str:
    target = path if base is None else path.relative_to(base)
    return str(PurePosixPath(target))


if __name__ == "__main__":
    main()
