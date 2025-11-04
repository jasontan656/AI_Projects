from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from typing import Iterable, List

from dotenv import load_dotenv
from openai import OpenAI
from pdfminer.high_level import extract_text
from rich.console import Console
from rich.progress import track

from project_utility.clock import philippine_from_timestamp, philippine_iso

console = Console()

ATTACHMENT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = Path(os.environ.get("SERVICE_CRAWLER_ENV", r"D:/AI_Projects/Rise/.env"))
DEFAULT_ROOT = Path(os.environ.get("SERVICE_CRAWLER_WORKSPACE_ROOT", r"D:/AI_Projects/TelegramChatHistory/Workspace/VBcombined/BI"))


def ensure_environment() -> None:
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH)
    else:
        load_dotenv()


def init_client() -> OpenAI | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print(
            "[yellow]OPENAI_API_KEY not detected; image parsing will use placeholder text.[/yellow]",
            highlight=False,
        )
        return None
    return OpenAI()


def find_service_directories(root: Path) -> Iterable[Path]:
    for dirpath, _, filenames in os.walk(root):
        has_attachment = any(
            Path(filename).suffix.lower() in ATTACHMENT_EXTENSIONS for filename in filenames
        )
        if has_attachment:
            yield Path(dirpath)


def collect_attachments(service_dir: Path) -> List[Path]:
    files = []
    for path in sorted(service_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in ATTACHMENT_EXTENSIONS:
            files.append(path)
    return files


def remove_existing_pdfsum(root: Path, console: Console) -> None:
    count = 0
    for pdfsum_path in root.rglob("PDFSUM.md"):
        pdfsum_path.unlink(missing_ok=True)
        count += 1
    if count:
        console.print(
            f"[yellow]Removed {count} existing PDFSUM.md file(s).[/yellow]",
            highlight=False,
        )


def extract_pdf_text(path: Path) -> str:
    try:
        text = extract_text(str(path))
    except Exception as exc:  # pragma: no cover - defensive
        return f"[PDF 解析失败] {exc}"
    lines = [line.rstrip() for line in text.splitlines()]
    cleaned = "\n".join(line for line in lines if line)
    return cleaned.strip()


def extract_image_text(path: Path, client: OpenAI | None, model: str) -> str:
    if client is None:
        return "[图像未解析：缺少 OpenAI API 配置]"
    with open(path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("utf-8")
    prompt = [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "请逐行提取这张图像中的文字信息，保持原有顺序。若为表格，可按行分组描述。",
                },
                {"type": "input_image", "image": {"b64_json": b64}},
            ],
        }
    ]
    try:
        response = client.responses.create(model=model, input=prompt, temperature=0.1)
        content = response.output[0].content[0].text.strip()
    except Exception as exc:  # pragma: no cover - defensive
        content = f"[图像解析失败] {exc}"
    return content


def append_attachment_block(file: Path, attachment: Path, text: str) -> None:
    lines = [
        f"## {attachment.name}",
        f"- 路径: `{attachment.name}`",
        f"- 更新: {philippine_from_timestamp(attachment.stat().st_mtime).isoformat()}",
        "",
        "```",
        text or "[未提取到文本]",
        "```",
        "",
    ]
    with open(file, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def process_directory(root: Path, client: OpenAI | None, model: str) -> None:
    directories = list(find_service_directories(root))
    for service_dir in track(
        directories,
        description="Building PDFSUM",
        console=console,
    ):
        attachments = collect_attachments(service_dir)
        if not attachments:
            continue
        pdfsum_path = service_dir / "PDFSUM.md"
        header = [
            "# 附件文字汇总",
            "",
            f"- 生成时间: {philippine_iso()}",
            f"- 来源目录: `{service_dir.name}`",
            "",
        ]
        pdfsum_path.write_text("\n".join(header), encoding="utf-8")
        for attachment in attachments:
            suffix = attachment.suffix.lower()
            if suffix == ".pdf":
                text = extract_pdf_text(attachment)
            elif suffix in IMAGE_EXTENSIONS:
                text = extract_image_text(attachment, client, model)
            else:
                text = "[暂不支持的附件类型]"
            append_attachment_block(pdfsum_path, attachment, text)
        console.print(
            f"[green]✓[/green] {service_dir.relative_to(root)} -> PDFSUM.md",
            highlight=False,
        )


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="将 BI 目录附件解析并写入 PDFSUM.md（逐附件追加）。")
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="BI 业务根目录路径",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        help="用于图像解析的 OpenAI 模型（默认读取 OPENAI_MODEL）。",
    )
    args = parser.parse_args(argv)

    if not args.root.exists():
        console.print(f"[red]Root path not found:[/red] {args.root}", highlight=False)
        return 1

    ensure_environment()
    client = init_client()

    remove_existing_pdfsum(args.root, console)
    console.print("[bold cyan]Starting PDFSUM generation...[/bold cyan]")
    process_directory(args.root, client, args.model)
    console.print("[bold green]PDFSUM generation completed.[/bold green]")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
