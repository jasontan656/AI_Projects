#!/usr/bin/env python
"""WorkPlan 文档一致性检查（忽略文件头）。

解析 WorkPlan 目录下的 Markdown 文档，抽取关键段落与契约定义，分析是否存在
重复或冲突的描述，并输出结构化报告。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

WORKPLAN_DIR = Path("WorkPlan")
SECTION_PATTERN = re.compile(r"^\s*([A-Za-z0-9\u4e00-\u9fa5&/ _-]{1,64}):\s*$")
PROMPT_ID_PATTERN = re.compile(r"prompt_id\s*=\s*([A-Za-z0-9_\-\.]+)")
PROMPT_HEADER_PATTERN = re.compile(r"^\s*-\s*([A-Za-z0-9_\-\.]+)\s*（")
SCHEMA_ID_PATTERN = re.compile(r'"[$]?id"\s*:\s*"([^"]+)"')
BEHAVIOR_PATTERN = re.compile(r"def\s+(behavior_[A-Za-z0-9_]+)\s*\(")
TOOLCALL_PATTERN = re.compile(r"def\s+(call_[A-Za-z0-9_]+)\s*\(")


@dataclass
class Artifact:
    kind: str
    key: str
    doc: Path
    snippet: str


def iter_workplan_files(files: Optional[Sequence[str]] = None) -> Iterable[Path]:
    root = WORKPLAN_DIR.resolve()
    if files:
        for item in files:
            path = (root / item).resolve()
            if not path.exists():
                raise FileNotFoundError(f"WorkPlan 文档不存在: {item}")
            yield path
    else:
        for path in root.glob("*.md"):
            if path.is_file():
                yield path


def load_body_lines(path: Path) -> List[str]:
    """忽略文件头，只读取第一个 ``` 代码块内的正文。"""
    lines = path.read_text(encoding="utf-8").splitlines()
    body: List[str] = []
    in_body = False
    for line in lines:
        if line.strip().startswith("```"):
            if not in_body:
                in_body = True
                continue
            break
        if in_body:
            body.append(line.rstrip("\n"))
    return body


def parse_sections(body_lines: Sequence[str]) -> Dict[str, str]:
    sections: Dict[str, List[str]] = {}
    current: Optional[str] = None
    for line in body_lines:
        match = SECTION_PATTERN.match(line)
        if match:
            current = match.group(1).strip()
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(line)
    return {key: "\n".join(value).strip() for key, value in sections.items()}


def normalize_snippet(lines: Sequence[str]) -> str:
    chunk = "\n".join(line.rstrip() for line in lines if line.strip())
    return re.sub(r"\s+", " ", chunk).strip()


def extract_block(lines: Sequence[str], start_idx: int) -> str:
    """尝试从 start_idx 开始获取结构化片段（例如 JSON 块）。"""
    collected: List[str] = []
    depth = 0
    for idx in range(start_idx, len(lines)):
        line = lines[idx]
        collected.append(line)
        depth += line.count("{") - line.count("}")
        depth += line.count("[") - line.count("]")
        if depth <= 0 and idx > start_idx:
            break
        if depth == 0 and line.strip() == "":
            break
    return normalize_snippet(collected)


def extract_artifacts(path: Path, body_lines: Sequence[str]) -> List[Artifact]:
    artifacts: List[Artifact] = []
    for idx, line in enumerate(body_lines):
        for match in PROMPT_ID_PATTERN.finditer(line):
            key = match.group(1)
            snippet = extract_block(body_lines, idx)
            artifacts.append(Artifact("prompt", key, path, snippet))
        header_match = PROMPT_HEADER_PATTERN.match(line)
        if header_match:
            key = header_match.group(1)
            snippet = normalize_snippet([line])
            artifacts.append(Artifact("prompt_header", key, path, snippet))
        for match in SCHEMA_ID_PATTERN.finditer(line):
            key = match.group(1)
            snippet = extract_block(body_lines, idx)
            artifacts.append(Artifact("schema", key, path, snippet))
        for match in BEHAVIOR_PATTERN.finditer(line):
            key = match.group(1)
            snippet = extract_block(body_lines, idx)
            artifacts.append(Artifact("behavior", key, path, snippet))
        for match in TOOLCALL_PATTERN.finditer(line):
            key = match.group(1)
            snippet = extract_block(body_lines, idx)
            artifacts.append(Artifact("toolcall", key, path, snippet))
    return artifacts


def build_artifact_index(docs: Iterable[Path]) -> Tuple[Dict[str, Dict[str, List[Artifact]]], Dict[Path, Dict[str, str]]]:
    artifact_index: Dict[str, Dict[str, List[Artifact]]] = defaultdict(lambda: defaultdict(list))
    section_index: Dict[Path, Dict[str, str]] = {}

    for doc_path in docs:
        body = load_body_lines(doc_path)
        sections = parse_sections(body)
        section_index[doc_path] = sections
        for art in extract_artifacts(doc_path, body):
            artifact_index[art.kind][art.key].append(art)
    return artifact_index, section_index


def detect_conflicts(artifact_index: Dict[str, Dict[str, List[Artifact]]]) -> Dict[str, List[Dict[str, str]]]:
    conflicts: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    duplicates: Dict[str, List[Dict[str, str]]] = defaultdict(list)

    for kind, items in artifact_index.items():
        for key, artifacts in items.items():
            if len(artifacts) <= 1:
                continue
            normalized_snippets = {art.snippet for art in artifacts}
            if len(normalized_snippets) > 1:
                conflicts[kind].append(
                    {
                        "key": key,
                        "docs": ", ".join(str(art.doc.name) for art in artifacts),
                        "snippets": "\n---\n".join(art.snippet for art in artifacts),
                    }
                )
            else:
                duplicates[kind].append(
                    {
                        "key": key,
                        "docs": ", ".join(str(art.doc.name) for art in artifacts),
                        "snippet": artifacts[0].snippet,
                    }
                )
    return {"conflicts": conflicts, "duplicates": duplicates}


def detect_section_duplicates(section_index: Dict[Path, Dict[str, str]]) -> List[Dict[str, str]]:
    registry: Dict[str, List[Tuple[Path, str]]] = defaultdict(list)
    for doc, sections in section_index.items():
        for name, content in sections.items():
            if not content:
                continue
            normalized = re.sub(r"\s+", " ", content).strip()
            if normalized:
                registry[(name, normalized)].append((doc, content))

    duplicates: List[Dict[str, str]] = []
    for (name, _), entries in registry.items():
        if len(entries) > 1:
            docs = ", ".join(str(doc.name) for doc, _ in entries)
            duplicates.append({"section": name, "docs": docs})
    return duplicates


def run(files: Optional[Sequence[str]] = None) -> Dict[str, object]:
    docs = list(iter_workplan_files(files))
    if not docs:
        raise SystemExit("未找到任何 WorkPlan 文档。")
    artifact_index, section_index = build_artifact_index(docs)
    artifact_report = detect_conflicts(artifact_index)
    section_report = detect_section_duplicates(section_index)
    return {
        "checked_docs": [str(doc.name) for doc in docs],
        "artifact_conflicts": artifact_report["conflicts"],
        "artifact_duplicates": artifact_report["duplicates"],
        "section_duplicates": section_report,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="WorkPlan 文档一致性检测")
    parser.add_argument(
        "--doc",
        dest="docs",
        action="append",
        help="指定单个 WorkPlan 文档（可重复使用）。默认检查全部。",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="如指定，则把报告写入该路径（JSON 格式）。",
    )
    args = parser.parse_args(argv)

    report = run(args.docs)
    payload = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload)
    # 若存在冲突，返回非零状态码以便 CI 阻断
    has_conflict = any(report["artifact_conflicts"].get(kind) for kind in report["artifact_conflicts"])
    return 1 if has_conflict else 0


if __name__ == "__main__":
    sys.exit(main())
