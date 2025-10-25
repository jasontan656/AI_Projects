from __future__ import annotations

import os
import re
import sys
import io
import subprocess
import shlex
from typing import List, Tuple


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
KOBE_DIR = os.path.join(REPO_ROOT, "Kobe")
OUTPUT_YAML = os.path.join(REPO_ROOT, "CodexFeatured", "Common", "CodebaseStructure.yaml")

DEFAULT_IGNORED_DIR_NAMES = {
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".mypy_cache",
    ".pytest_cache",
    ".idea",
    ".vscode",
    "node_modules",
    "dist",
    "build",
}
DEFAULT_IGNORED_FILE_GLOBS = {
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.log",
    "*.tmp",
    "Thumbs.db",
    ".DS_Store",
}


def read_text_safely(path: str, max_bytes: int = 8192) -> str:
    try:
        with open(path, "rb") as f:
            blob = f.read(max_bytes)
        # Try utf-8 first, then fallback to gbk
        for enc in ("utf-8", "utf-8-sig", "gbk", "latin-1"):
            try:
                return blob.decode(enc, errors="ignore")
            except Exception:
                continue
        return ""
    except Exception:
        return ""


def tokenize_filename(name: str) -> List[str]:
    base = os.path.splitext(name)[0]
    # split by underscores, hyphens and camel case
    parts = re.sub(r"([a-z])([A-Z])", r"\1 \2", base)
    tokens = re.split(r"[\s_\-]+", parts)
    return [t for t in tokens if t]


def summarize_content(ext: str, filename: str, text: str) -> str:
    ext = ext.lower()
    tokens = tokenize_filename(filename)
    token_cn = "、".join(tokens[:5]) if tokens else "通用"

    def clamp_100_200(s: str) -> str:
        s = re.sub(r"\s+", " ", s).strip()
        length = len(s)
        if length < 100:
            # pad with structured, non-fabricated context
            pad = (
                "。文档聚焦于文件职责、主要入口与对外接口的简要描述，"
                "并提示关键依赖、上下游交互以及在整体目录中的定位，"
                "便于快速理解与检索。"
            )
            s = s + pad
        if len(s) > 200:
            s = s[:200].rstrip("，。；,; ") + "。"
        if len(s) < 100:
            # ensure lower bound
            s = s + "该说明遵循简洁准确、可维护与可溯源的原则，避免冗余。"
        return s

    head = text[:400].strip() if text else ""

    if ext in {".py"}:
        # Try to get module docstring or leading comments
        doc_match = re.search(r'"""([\s\S]*?)"""', head) or re.search(r"'''([\s\S]*?)'''", head)
        if doc_match:
            gist = re.sub(r"\s+", " ", doc_match.group(1)).strip()[:140]
            desc = f"Python 模块，提供与 {token_cn} 相关的核心实现与接口。模块说明：{gist}。包含主要函数/类定义，关注输入输出与异常边界，便于复用与测试。"
        else:
            fn_defs = ", ".join(re.findall(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\(", head)[:4])
            cls_defs = ", ".join(re.findall(r"class\s+([A-Za-z_][A-Za-z0-9_]*)\(", head)[:3])
            extra = []
            if fn_defs:
                extra.append(f"函数：{fn_defs}")
            if cls_defs:
                extra.append(f"类：{cls_defs}")
            extra_str = ("；".join(extra) + "；") if extra else ""
            desc = (
                f"Python 源码，实现 {token_cn} 的业务或工具逻辑，强调清晰边界、可测试性与日志可观测性。"
                f"{extra_str}适用于被其他模块调用或直接作为脚本入口运行。"
            )
        return clamp_100_200(desc)

    if ext in {".md", ".markdown"}:
        title = re.search(r"^#\s+(.+)$", head, re.MULTILINE)
        t = title.group(1).strip() if title else token_cn
        desc = (
            f"Markdown 说明文档，主题为“{t}”。用于记录 {token_cn} 相关的背景信息、设计思路与使用指南，"
            "帮助读者快速建立上下文并作为日后维护与协作的依据。"
        )
        return clamp_100_200(desc)

    if ext in {".json", ".yaml", ".yml", ".toml", ".ini"}:
        desc = (
            f"配置/数据文件，描述 {token_cn} 的参数、元数据或样例。建议在修改前备份并通过校验工具验证格式，"
            "以确保上下游兼容性与环境一致性。"
        )
        return clamp_100_200(desc)

    if ext in {".sql"}:
        is_create = bool(re.search(r"\bCREATE\b", head, re.IGNORECASE))
        is_query = bool(re.search(r"\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b", head, re.IGNORECASE))
        aspect = "建表/迁移脚本" if is_create else ("查询/变更脚本" if is_query else "数据库脚本")
        desc = (
            f"{aspect}，围绕 {token_cn} 进行结构定义或数据操作。建议在受控环境中执行并做好回滚方案，"
            "确保事务一致性与性能指标符合预期。"
        )
        return clamp_100_200(desc)

    if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"}:
        desc = (
            f"图片资源（{ext.upper()}），多用于展示 {token_cn} 的示例、流程或界面元素。"
            "请保持尺寸与压缩比适中，并在需要时提供可无损导出的源文件，以便后续调整。"
        )
        return clamp_100_200(desc)

    if ext in {".pdf", ".doc", ".docx", ".ppt", ".pptx"}:
        desc = (
            f"文档/资料文件，聚焦 {token_cn} 相关的说明、方案或报告。建议同步维护来源与版本信息，"
            "便于审阅与归档。"
        )
        return clamp_100_200(desc)

    if ext in {".ps1", ".sh", ".bat"}:
        desc = (
            f"脚本文件，用于自动化与运维场景，围绕 {token_cn} 执行批处理或环境操作。"
            "请在安全环境中测试并记录依赖与参数示例。"
        )
        return clamp_100_200(desc)

    # Fallback
    desc = (
        f"通用文件（{ext or '无扩展'}），名称体现 {token_cn}。此文件在目录中承担特定职责，"
        "建议结合上下文查阅相邻文档与代码以获得完整理解，并关注版本更新记录。"
    )
    return clamp_100_200(desc)


def run_git_list_files(repo_root: str) -> List[str]:
    """Return repo-relative file paths that are not ignored, using git."""
    try:
        cmd = f"git -C {shlex.quote(repo_root)} ls-files --cached --others --exclude-standard"
        completed = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8", check=True)
        lines = [ln.strip().replace("/", os.sep) for ln in completed.stdout.splitlines() if ln.strip()]
        return lines
    except Exception:
        return []


def read_gitignore_patterns(repo_root: str) -> List[str]:
    gitignore_path = os.path.join(repo_root, ".gitignore")
    try:
        with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
            patterns = []
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                patterns.append(s)
            return patterns
    except Exception:
        return []


def path_is_ignored(repo_rel_path: str, patterns: List[str]) -> bool:
    """A lightweight matcher for common .gitignore patterns. Not 100% feature-complete, but practical.
    - Supports folder patterns like node_modules/ and simple globs like *.log, **/build/**.
    - Treats patterns starting with '!' as negation (basic support).
    """
    # Normalize to posix-like for matching
    norm = repo_rel_path.replace(os.sep, "/")

    def match_one(pat: str, target: str) -> bool:
        # crude ** support
        if pat.startswith("**/"):
            pat = pat[3:]
        if pat.endswith("/**"):
            if target.startswith(pat[:-3]):
                return True
        # directory suffix pattern
        if pat.endswith("/") and target.startswith(pat):
            return True
        # path contains segment pattern
        if "/**/" in pat:
            parts = pat.split("/**/")
            # ensure order of parts
            idx = 0
            for seg in parts:
                found = target.find(seg, idx)
                if found == -1:
                    return False
                idx = found + len(seg)
            return True
        # basic fnmatch
        from fnmatch import fnmatch
        return fnmatch(target, pat) or fnmatch(target, pat.lstrip("/"))

    ignored = False
    for raw_pat in patterns:
        neg = raw_pat.startswith("!")
        pat = raw_pat[1:] if neg else raw_pat
        if match_one(pat, norm):
            ignored = not neg
    return ignored


def list_unignored_files_under_kobe(repo_root: str, kobe_dir: str) -> List[str]:
    repo_files = run_git_list_files(repo_root)
    if repo_files:
        prefix = "Kobe" + os.sep
        return [p for p in repo_files if p.startswith(prefix)]

    # Fallback: os.walk with naive .gitignore filtering
    patterns = read_gitignore_patterns(repo_root)
    results: List[str] = []
    for current_root, dirs, files in os.walk(kobe_dir):
        rel_root = os.path.relpath(current_root, repo_root)
        rel_root_posix = rel_root.replace(os.sep, "/")
        # filter ignored directories in place
        keep_dirs = []
        for d in sorted(dirs):
            dir_rel = f"{rel_root}/{d}" if rel_root != "." else d
            if not path_is_ignored(dir_rel + "/", patterns):
                keep_dirs.append(d)
        dirs[:] = keep_dirs

        for fname in sorted(files):
            file_rel = f"{rel_root}/{fname}" if rel_root != "." else fname
            if not path_is_ignored(file_rel, patterns):
                results.append(file_rel)
    # Keep only Kobe/*
    return [p for p in results if p.split(os.sep, 1)[0] == "Kobe"]


def walk_kobe_with_default_ignores(repo_root: str, kobe_dir: str) -> List[str]:
    from fnmatch import fnmatch
    results: List[str] = []
    for current_root, dirs, files in os.walk(kobe_dir):
        # Filter directories by common ignore names
        keep_dirs = []
        for d in sorted(dirs):
            if d in DEFAULT_IGNORED_DIR_NAMES or d.startswith(".") and d not in {".github"}:
                continue
            keep_dirs.append(d)
        dirs[:] = keep_dirs

        for fname in sorted(files):
            # file globs ignore
            if any(fnmatch(fname, pat) for pat in DEFAULT_IGNORED_FILE_GLOBS):
                continue
            rel_root = os.path.relpath(current_root, repo_root)
            file_rel = f"{rel_root}/{fname}" if rel_root != "." else fname
            results.append(file_rel)
    return [p for p in results if p.split(os.sep, 1)[0] == "Kobe"]


def build_tree_from_file_list(root: str, file_repo_paths: List[str]) -> List[Tuple[int, str, bool]]:
    """Build tree items (indent level, display text, is_dir) without annotations.
    Order: for each directory, list its files first, then recursively list subdirectories.
    """
    # Normalize to paths relative to Kobe root
    rel_paths_under_root = [os.path.relpath(os.path.join(REPO_ROOT, p), root) for p in file_repo_paths]
    rel_paths_under_root = [p for p in rel_paths_under_root if not p.startswith(os.pardir)]

    # Build a nested tree structure
    class Node:
        __slots__ = ("dirs", "files")
        def __init__(self):
            self.dirs: dict[str, "Node"] = {}
            self.files: List[str] = []

    root_node = Node()

    def get_dir_node(path_parts: List[str]) -> Node:
        node = root_node
        for part in path_parts:
            if part not in node.dirs:
                node.dirs[part] = Node()
            node = node.dirs[part]
        return node

    for rp in rel_paths_under_root:
        parts = rp.split(os.sep)
        dir_parts, file_name = parts[:-1], parts[-1]
        node = get_dir_node([p for p in dir_parts if p])
        node.files.append(file_name)

    def depth(rel_path: str) -> int:
        return 0 if rel_path in ("", ".") else len(rel_path.split(os.sep))

    items: List[Tuple[int, str, bool]] = []

    # Add files directly under root first (level = 0)
    for file_name in sorted(root_node.files):
        items.append((0, file_name, False))

    def walk(dir_path: str, node: Node):
        # For deterministic output
        for name in sorted(node.dirs.keys()):
            child = node.dirs[name]
            current_path = name if not dir_path else f"{dir_path}{os.sep}{name}"
            lvl = depth(current_path) - 1
            items.append((lvl, name + "/", True))
            # files inside this directory
            for file_name in sorted(child.files):
                items.append((lvl + 1, file_name, False))
            # recurse into subdirectories
            walk(current_path, child)

    walk("", root_node)
    return items


def write_yaml(root: str, items: List[Tuple[int, str, bool]], out_path: str) -> None:
    buf = io.StringIO()
    root_name = os.path.basename(root.rstrip(os.sep))
    buf.write("---\n")
    buf.write("content: |-\n")
    buf.write("  # **必读且遵守**：`Kobe\\`为代码库根目录，该目录及其子目录为唯一代码库工作目录，禁止跨越该代码库访问其他路径或者工作\n")
    buf.write("\n")

    def write_line(level: int, text: str, is_dir: bool):
        indent = "  " * level
        prefix = "- "
        buf.write(f"  {indent}{prefix}{text}\n")

    write_line(0, root_name + "/", True)
    for level, display, is_dir in items:
        write_line(level + 1, display, is_dir)

    content = buf.getvalue()
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def main() -> int:
    if not os.path.isdir(KOBE_DIR):
        print(f"Kobe directory not found: {KOBE_DIR}", file=sys.stderr)
        return 1

    file_repo_paths = list_unignored_files_under_kobe(REPO_ROOT, KOBE_DIR)
    if not file_repo_paths:
        # Fallback to safe defaults if git/.gitignore filtering yields nothing
        file_repo_paths = walk_kobe_with_default_ignores(REPO_ROOT, KOBE_DIR)

    items = build_tree_from_file_list(KOBE_DIR, file_repo_paths)
    os.makedirs(os.path.dirname(OUTPUT_YAML), exist_ok=True)
    write_yaml(KOBE_DIR, items, OUTPUT_YAML)
    print(f"Written: {OUTPUT_YAML}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


