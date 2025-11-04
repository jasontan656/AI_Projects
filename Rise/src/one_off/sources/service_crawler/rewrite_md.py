from __future__ import annotations

import concurrent.futures
import os
import traceback
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console

from .config_loader import resolve_path, get_llm_config

BASE_DIR = Path(__file__).resolve().parent
ROOT = resolve_path("workspace_root")
TEMPLATE_PATH = resolve_path("md_template")
PRICE_PATH = resolve_path("price_doc")
ENV_PATH = resolve_path("env_file")
OUTPUT_SUFFIX = "_rewritten.md"
MAX_WORKERS = 10

SYSTEM_PROMPT_FALLBACK = """
role: "PROWRITER"
description: "你是一名政务与业务文档结构化专家，任务是理解、迁移并增强指定业务说明文档，使其完全符合统一模板结构。你的目标是：吸收 BASE_DOC、PDF_SUMMARY、PRICE_DOC、TEMPLATE 四个来源中的信息，理解后用中文重写为完整、结构化、信息充分的业务说明 Markdown。"

(省略其余提示词内容...)
"""

try:
    LLM_CONFIG = get_llm_config("rewrite_md")
except KeyError as exc:
    raise RuntimeError("config.yaml 缺少 llm.rewrite_md 配置。") from exc

MODEL = LLM_CONFIG.get("model")
SYSTEM_PROMPT = LLM_CONFIG.get("system_prompt")

if not MODEL or not SYSTEM_PROMPT:
    raise RuntimeError("llm.rewrite_md 需要同时提供 model 与 system_prompt。")

console = Console()


def load_env() -> None:
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH)
    else:
        load_dotenv()


def find_base_doc(directory: Path) -> Path | None:
    preferred = directory / f"{directory.name}.md"
    if preferred.exists():
        return preferred
    for candidate in sorted(directory.glob("*.md")):
        if candidate.name == "PDFSUM.md" or candidate.name.endswith(OUTPUT_SUFFIX):
            continue
        return candidate
    return None


def gather_tasks() -> List[Tuple[Path, Path | None, Path]]:
    directories = sorted(p for p in ROOT.iterdir() if p.is_dir())

    tasks: List[Tuple[Path, Path | None, Path]] = []
    for directory in directories:
        rewritten_exists = any(
            child.is_file() and "rewritten" in child.stem.lower()
            for child in directory.iterdir()
        )
        if rewritten_exists:
            console.print(
                f"[yellow]Skip (already rewritten):[/yellow] {directory.relative_to(ROOT)}"
            )
            continue

        base_doc = find_base_doc(directory)
        if not base_doc:
            continue
        pdf_path = directory / "PDFSUM.md"
        pdf_path = pdf_path if pdf_path.exists() else None
        output_path = directory / f"{base_doc.stem}{OUTPUT_SUFFIX}"
        tasks.append((base_doc, pdf_path, output_path))
    return tasks


def read_required_files() -> Tuple[str, str]:
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE_PATH}")
    if not PRICE_PATH.exists():
        raise FileNotFoundError(f"Price document not found: {PRICE_PATH}")
    template_text = TEMPLATE_PATH.read_text(encoding="utf-8")
    price_text = PRICE_PATH.read_text(encoding="utf-8")
    return template_text, price_text


def call_llm(base_doc: str, pdf_summary: str | None, price_doc: str, template: str) -> str:
    client = OpenAI()
    user_content = [
        {"type": "input_text", "text": "以下提供若干文件，请基于系统指令完成重写。"},
        {"type": "input_text", "text": f"### BASE_DOC\n{base_doc}"},
    ]
    if pdf_summary:
        user_content.append({"type": "input_text", "text": f"### PDF_SUMMARY\n{pdf_summary}"})
    if price_doc:
        user_content.append({"type": "input_text", "text": f"### PRICE_DOC\n{price_doc}"})
    if template:
        user_content.append({"type": "input_text", "text": f"### TEMPLATE\n{template}"})

    response = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text.strip()
    data = response.model_dump()
    parts = []
    for item in data.get("output", []):
        if item.get("type") != "message":
            continue
        for chunk in item.get("content", []):
            if chunk.get("type") == "output_text" and "text" in chunk:
                parts.append(chunk["text"])
    return "\n".join(parts).strip()


def process_single(task: Tuple[Path, Path | None, Path], template_text: str, price_text: str) -> Tuple[Path, bool, str]:
    base_path, pdf_path, output_path = task
    try:
        base_text = base_path.read_text(encoding="utf-8", errors="ignore")
        pdf_text = pdf_path.read_text(encoding="utf-8", errors="ignore") if pdf_path else None
        rewritten = call_llm(base_text, pdf_text, price_text, template_text)
        output_path.write_text(rewritten, encoding="utf-8")
        return output_path, True, ""
    except Exception as exc:
        return output_path, False, f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"


def process_files(tasks: List[Tuple[Path, Path | None, Path]]) -> None:
    load_env()
    template_text, price_text = read_required_files()

    if not tasks:
        console.print("[red]未发现待处理目录（缺少 Markdown）。[/red]")
        return

    first_task = tasks[0]
    console.print(f"[cyan]Processing (1/{len(tasks)}):[/cyan] {first_task[0].relative_to(ROOT)}")
    path, ok, error = process_single(first_task, template_text, price_text)
    if ok:
        console.print(f"[green]Written:[/green] {path}")
    else:
        console.print(f"[red]Failed to process {path}: {error}")
        return

    console.print("[yellow]首个文件已生成，请检查内容。输入 Y 继续批量处理，其它键退出。[/yellow]")
    choice = input().strip().lower()
    if choice not in {"y", "yes"}:
        console.print("[red]已终止后续处理，请审阅输出后再运行。[/red]")
        return

    remaining = tasks[1:]
    if not remaining:
        console.print("[bold green]仅有该一个目录需要处理。[/bold green]")
        return

    console.print(f"[cyan]并发处理剩余 {len(remaining)} 个目录（最多 {MAX_WORKERS} 个线程）…[/cyan]")

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(process_single, task, template_text, price_text): task
            for task in remaining
        }
        for future in concurrent.futures.as_completed(futures):
            base_path, pdf_path, output_path = futures[future]
            try:
                path, ok, error = future.result()
                rel = path.relative_to(ROOT)
                if ok:
                    console.print(f"[green]Written:[/green] {rel}")
                else:
                    console.print(f"[red]Failed {rel}: {error}")
            except Exception as exc:
                console.print(f"[red]Worker exception for {output_path}: {exc}")

    console.print("[bold green]所有文件均已生成 *_rewritten.md，请逐一审阅后再替换原稿。[/bold green]")


if __name__ == "__main__":
    TASKS = gather_tasks()
    process_files(TASKS)
