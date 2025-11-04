from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from dotenv import load_dotenv
from openai import OpenAI
from pdfminer.high_level import extract_text
from rich.console import Console
from rich.progress import track

from .config_loader import resolve_path, get_llm_config

ROOT_DIR = resolve_path("workspace_root")
ENV_PATH = resolve_path("env_file")
TEMP_ROOT = resolve_path("rename_tmp")
ATTACHMENT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_SNIPPET_CHARS = None
BASENAME_GUIDELINES = [
    "ExtensionApplicationForm",
    "NewApplicationForm",
    "Checklist",
    "DependentApplicationForm",
    "CertificationApplication",
]

RENAMER_PROMPT_FALLBACK = (
    "你是文档归档助手。请阅读附件全文（或图像 OCR 内容），判断其在签证/认证流程中的用途。"
    "若现有文件名已满足以下规范，则直接复用原文件名；否则生成符合规范的新名称。规范："
    "1) 文件名仅包含 1-3 个英文单词（驼峰或首字母大写连写均可），例如 Checklist、DependentApplicationForm；"
    "2) 不包含业务名称/部门名称，只描述用途；"
    "3) 内容应反映表单/清单类型（ApplicationForm、Checklist、Certification 等）。"
    " 示例（仅供参考）：{examples}。"
    "命名决策优先依据以下关键词：若正文标题或开头含有 'Checklist'、'Checklist of'、'Checklist for' 等字样，输出 Checklist；"
    "若出现 'Application Form', 'Petition Form', 'Request Form' 等，输出 ApplicationForm 或更具体如 DependentApplicationForm；"
    "若为证明/证明书包含 'Certification'、'Certificate' 等，则输出 CertificationApplication；"
    "如无法根据关键词判断，再综合文意选择最贴切的 1-3 个词。"
    "返回 JSON：{\"filename\": \"...\"}，值需附带扩展名（例如 Checklist.pdf）。"
)

try:
    RENAMER_LLM = get_llm_config("rename_attachments")
except KeyError as exc:
    raise RuntimeError("config.yaml 缺少 llm.rename_attachments 配置。") from exc

RENAMER_MODEL = RENAMER_LLM.get("model")
RENAMER_PROMPT_TEMPLATE = RENAMER_LLM.get("system_prompt")

if not RENAMER_MODEL or not RENAMER_PROMPT_TEMPLATE:
    raise RuntimeError("llm.rename_attachments 需要提供 model 与 system_prompt。")


@dataclass
class Attachment:
    path: Path
    service_name: str

    @property
    def ext(self) -> str:
        return self.path.suffix.lower()

    @property
    def stem(self) -> str:
        return self.path.stem

    @property
    def relative(self) -> Path:
        return self.path.relative_to(ROOT_DIR)


def ensure_environment() -> None:
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH)
    else:
        load_dotenv()


def init_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured.")
    return OpenAI()


def find_attachments(root: Path, service_filter: Optional[str] = None) -> List[Attachment]:
    attachments: List[Attachment] = []
    for dirpath, _, filenames in os.walk(root):
        service_dir = Path(dirpath)
        service_name = service_dir.name
        if service_filter and service_filter.lower() not in service_name.lower():
            continue
        for filename in filenames:
            ext = Path(filename).suffix.lower()
            if ext not in ATTACHMENT_EXTENSIONS:
                continue
            path = service_dir / filename
            attachments.append(Attachment(path=path, service_name=service_name))
    attachments.sort(key=lambda item: str(item.relative))
    return attachments


def extract_pdf_text(path: Path) -> str:
    try:
        text = extract_text(str(path))
    except Exception as exc:  # pragma: no cover - defensive
        return f"[PDF 解析失败] {exc}"
    return text.strip()


def extract_image_b64(path: Path) -> str:
    import base64

    with open(path, "rb") as fh:
        data = fh.read()
    return base64.b64encode(data).decode("utf-8")


def sanitize_filename(name: str, ext: str) -> str:
    name = name.strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    name = name.strip("._")
    if not name:
        name = "attachment"
    if not name.lower().endswith(ext.lower()):
        name = f"{name}{ext}"
    return name


def ensure_unique_filename(dest_dir: Path, filename: str) -> str:
    candidate = filename
    counter = 1
    stem, ext = os.path.splitext(filename)
    while (dest_dir / candidate).exists():
        counter += 1
        candidate = f"{stem}_{counter}{ext}"
    return candidate


def build_prompt_payload(attachment: Attachment, content: str) -> dict:
    return {
        "service_name": attachment.service_name,
        "original_filename": attachment.path.name,
        "extension": attachment.ext,
        "content": content,
    }


def request_filename_from_llm(
    client: OpenAI,
    model: str,
    attachment: Attachment,
    content: str,
    image_b64: Optional[str] = None,
    prompt_template: str = "",
) -> str:
    payload = build_prompt_payload(attachment, content)
    system_prompt = prompt_template.format(examples=", ".join(BASENAME_GUIDELINES))

    user_content = [{"type": "input_text", "text": json.dumps(payload, ensure_ascii=False)}]
    if image_b64:
        mime = "image/jpeg"
        if attachment.ext == ".png":
            mime = "image/png"
        user_content.append(
            {
                "type": "input_image",
                "image_url": f"data:{mime};base64,{image_b64}",
            }
        )

    response = client.responses.create(
        model=model,
        temperature=0.2,
        text={
            "format": {
                "type": "json_schema",
                "name": "attachment_filename",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "pattern": r"^[A-Z][A-Za-z]*(?:[A-Z][A-Za-z]*){0,2}\.[A-Za-z0-9]+$",
                            "description": "Existing filename or new one with 1-3 PascalCase words and an extension, e.g., Checklist.pdf.",
                        }
                    },
                    "required": ["filename"],
                    "additionalProperties": False,
                },
            }
        },
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    raw_text = getattr(response, "output_text", None)
    if not raw_text:
        dump = response.model_dump()
        text_chunks: List[str] = []
        for item in dump.get("output", []):
            if item.get("type") != "message":
                continue
            for chunk in item.get("content", []):
                if chunk.get("type") == "output_text" and "text" in chunk:
                    text_chunks.append(chunk["text"])
        raw_text = text_chunks[0] if text_chunks else ""
    raw_text = raw_text.strip()
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        snippet = raw_text.split("```")[-2] if "```" in raw_text else raw_text
        data = json.loads(snippet)
    filename = data["filename"]
    return filename


def rename_attachment(attachment: Attachment, new_name: str) -> Path:
    dest_dir = attachment.path.parent
    sanitized = sanitize_filename(new_name, attachment.ext)
    if sanitized.lower() == attachment.path.name.lower():
        return attachment.path
    unique = ensure_unique_filename(dest_dir, sanitized)
    new_path = dest_dir / unique
    attachment.path.rename(new_path)
    return new_path


def store_temp_excerpt(attachment: Attachment, snippet: str) -> None:
    tmp_path = TEMP_ROOT / attachment.relative.with_suffix(".txt")
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_text(snippet, encoding="utf-8")


def process_attachment(
    console: Console,
    client: OpenAI,
    model: str,
    attachment: Attachment,
    dry_run: bool = False,
) -> Optional[Path]:
    if attachment.ext == ".pdf":
        content = extract_pdf_text(attachment.path)
        image_b64 = None
    else:
        content = ""
        image_b64 = extract_image_b64(attachment.path)

    store_temp_excerpt(attachment, content or "[image]")

    try:
        suggested = request_filename_from_llm(
            client=client,
            model=model,
            attachment=attachment,
            content=content,
            image_b64=image_b64,
            prompt_template=prompt_template,
        )
    except Exception as exc:  # pragma: no cover - defensive
        console.print(
            f"[red]LLM request failed[/red] {attachment.relative}: {exc}",
            highlight=False,
        )
        return None

    if dry_run:
        console.print(
            f"[yellow]DRY-RUN[/yellow] {attachment.relative} -> {suggested}",
            highlight=False,
        )
        return None

    try:
        new_path = rename_attachment(attachment, suggested)
    except Exception as exc:  # pragma: no cover - defensive
        console.print(
            f"[red]Rename failed[/red] {attachment.relative}: {exc}",
            highlight=False,
        )
        return None

    console.print(
        f"[green]RENAMED[/green] {attachment.relative} -> {new_path.name}",
        highlight=False,
    )
    return new_path


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="调用 LLM 为 BI 附件生成语义化文件名。")
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT_DIR,
        help="BI 根目录路径。",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="用于命名和 OCR 的模型。",
    )
    parser.add_argument(
        "--service",
        help="仅处理包含此关键词的业务目录。",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="仅处理前 N 个附件，便于调试。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅输出建议文件名，不实际重命名。",
    )
    parser.add_argument(
        "--reset-temp",
        action="store_true",
        help="运行前清空临时缓存目录。",
    )
    args = parser.parse_args(argv)

    console = Console()

    if not args.root.exists():
        console.print(f"[red]Root path not found:[/red] {args.root}", highlight=False)
        return 1

    ensure_environment()
    client = init_client()

    if args.reset_temp and TEMP_ROOT.exists():
        shutil.rmtree(TEMP_ROOT)
        console.print(f"[yellow]Cleared temp directory[/yellow] {TEMP_ROOT}", highlight=False)

    attachments = find_attachments(args.root, args.service)
    if args.limit:
        attachments = attachments[: args.limit]

    if not attachments:
        console.print("[yellow]No attachments found for processing.[/yellow]", highlight=False)
        return 0

    console.print(f"[magenta]Using model:[/magenta] {args.model}", highlight=False)
    console.print(f"[bold cyan]Pending attachments: {len(attachments)}[/bold cyan]")
    renamed = 0
    for attachment in track(attachments, description="Renaming attachments", console=console):
        result = process_attachment(console, client, args.model, attachment, dry_run=args.dry_run)
        if result:
            renamed += 1
    console.print(f"[bold green]Renamed {renamed} attachment(s).[/bold green]")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
