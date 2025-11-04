from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.progress import track

BASE_URL = os.environ.get("SERVICE_CRAWLER_BASE_URL", "https://immigration.gov.ph")
SERVICES_URL = f"{BASE_URL}/services/"
ROOT_DIR = Path(os.environ.get("SERVICE_CRAWLER_WORKSPACE_ROOT", r"D:/AI_Projects/TelegramChatHistory/Workspace/VBcombined/BI"))
ENV_PATH = Path(os.environ.get("SERVICE_CRAWLER_ENV", r"D:/AI_Projects/Rise/.env"))
ATTACHMENT_SUFFIXES = {".pdf", ".jpg", ".jpeg", ".png"}
console = Console()

# Visa pages that live outside the generic /services listing.
VISA_PAGES = [
    {"category": "Immigrant Visas", "name": "Child Born Abroad of Immigrant Mother", "url": "https://immigration.gov.ph/child-born-abroad-of-immigrant-mother/"},
    {"category": "Immigrant Visas", "name": "Child Born Subsequent to the Issuance of Immigrant Visa of the Accompanying Parent", "url": "https://immigration.gov.ph/child-born-subsqeunt-to-the-issuance-of-immigrant-visa-of-the-accompanying-parent-13c/"},
    {"category": "Immigrant Visas", "name": "Immigrant Visa by Marriage (13A)", "url": "https://immigration.gov.ph/elementor-2671/"},
    {"category": "Immigrant Visas", "name": "Permanent Resident Visa (PRV)", "url": "https://immigration.gov.ph/permanent-resident-visa-prv/"},
    {"category": "Immigrant Visas", "name": "Returning Former Natural-Born Filipino Citizen (13G)", "url": "https://immigration.gov.ph/returning-former-natural-born-filipino-citizen-13g/"},
    {"category": "Immigrant Visas", "name": "Returning Resident (13E)", "url": "https://immigration.gov.ph/returning-resident-13e/"},
    {"category": "Immigrant Visas", "name": "Quota Visa (13)", "url": "https://immigration.gov.ph/quota-visa-13/"},
    {"category": "Non-Immigrant Visa", "name": "Temporary Resident Visa (TRV)", "url": "https://immigration.gov.ph/temporary-resident-visa-trv/"},
    {"category": "Non-Immigrant Visa", "name": "Temporary Visitor Visa (9A)", "url": "https://immigration.gov.ph/visa-waiver/"},
    {"category": "Non-Immigrant Visa", "name": "Treaty Trader or Treaty Investor (9D)", "url": "https://immigration.gov.ph/treaty-trader-or-treaty-investor-9d/"},
    {"category": "Non-Immigrant Visa", "name": "Accredited Official of Foreign Government (9E)", "url": "https://immigration.gov.ph/accredited-official-of-foreign-government-9e/"},
    {"category": "Non-Immigrant Visa", "name": "Student Visa (9F)", "url": "https://immigration.gov.ph/student-visa-9f/"},
    {"category": "Non-Immigrant Visa", "name": "Pre-arranged Employment Visa (9G)", "url": "https://immigration.gov.ph/pre-4-arranged-employment-visa-9g/"},
    {"category": "Special Visa", "name": "Visa Upon Arrival (SEVUA)", "url": "https://immigration.gov.ph/visa-upon-arrival-sevua/"},
    {"category": "Special Visa", "name": "Special Visa for Employment Generation", "url": "https://immigration.gov.ph/special-visa-for-employment-generation/"},
    {"category": "Special Visa", "name": "Special Employment Visa for Offshore Banking Unit", "url": "https://immigration.gov.ph/special-employment-visa-for-offshore-banking-unit/"},
    {"category": "Special Visa", "name": "Special Visa under E.O. 226, as amended by R.A. 8756", "url": "https://immigration.gov.ph/special-visa-under-e-o-226-as-amended-by-r-a-8756/"},
]


@dataclass
class Attachment:
    url: str
    title: str
    kind: str
    source: str  # "anchor" or "llm"


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def ensure_environment() -> None:
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH)
    else:
        load_dotenv()


def build_directory_index(root: Path) -> Dict[str, Path]:
    index: Dict[str, Path] = {}
    for subdir in root.iterdir():
        if subdir.is_dir():
            index.setdefault(normalize(subdir.name), subdir)
    return index


def fetch_service_links(session: requests.Session) -> Dict[str, str]:
    console.print(f"[cyan]Fetching services hub:[/cyan] {SERVICES_URL}", highlight=False)
    resp = session.get(SERVICES_URL, timeout=60)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    links: Dict[str, str] = {}
    for anchor in soup.select("article a[href]"):
        name = anchor.get_text(strip=True)
        href = anchor["href"].strip()
        if not name or href.startswith("#"):
            continue
        if not href.lower().startswith("http"):
            href = urljoin(BASE_URL, href)
        links[name] = href
    console.print(f"[cyan]Discovered {len(links)} service entries from hub[/cyan]", highlight=False)
    return links


def collect_anchor_candidates(soup: BeautifulSoup, base_url: str) -> List[Attachment]:
    candidates: List[Attachment] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        resolved = urljoin(base_url, href)
        ext = Path(urlparse(resolved).path).suffix.lower()
        if ext not in ATTACHMENT_SUFFIXES:
            continue
        title = anchor.get_text(" ", strip=True) or Path(urlparse(resolved).path).name
        kind = classify_attachment(title, resolved)
        candidates.append(Attachment(url=resolved, title=title, kind=kind, source="anchor"))
    return candidates


def classify_attachment(title: str, url: str) -> str:
    text = f"{title} {url}".lower()
    if "checklist" in text or "requirements" in text:
        return "checklist"
    if "application" in text or "form" in text or "request" in text:
        return "application_form"
    if "guide" in text or "manual" in text or "notes" in text:
        return "guide"
    raise ValueError(f"Unrecognized attachment type: {title} {url}")


def extract_article_text(soup: BeautifulSoup) -> str:
    article = soup.find("article")
    if not article:
        article = soup.body or soup
    clone = BeautifulSoup(str(article), "html.parser")
    for tag in clone.find_all(["script", "style", "nav", "form"]):
        tag.decompose()
    text = clone.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    cleaned = "\n".join(line for line in lines if line)
    return cleaned[:8000]


def llm_extract_attachments(
    client: Optional[OpenAI],
    model: str,
    service_name: str,
    service_url: str,
    article_text: str,
    anchor_candidates: List[Attachment],
) -> List[Attachment]:
    if client is None:
        return []
    payload = {
        "service_name": service_name,
        "service_url": service_url,
        "anchor_links": [
            {"title": item.title, "url": item.url, "kind": item.kind} for item in anchor_candidates
        ],
        "article_excerpt": article_text,
    }
    prompt = (
        "你是资料稽核员。请阅读给定的服务页面摘要与锚点列表，"
        "确认所有可下载的附件（PDF/JPG/PNG），确保无遗漏或重复。"
        "请返回 JSON：{\"attachments\": [{\"url\": \"...\", \"title\": \"...\", \"kind\": \"application_form|checklist|guide|other\"}]}. "
        "若无新增附件，可只返回空数组。确保每个 url 为绝对地址。"
    )
    try:
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": "You respond with strict JSON matching the requested schema."},
                {"role": "user", "content": prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            temperature=0.2,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "attachments_bundle",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "attachments": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "url": {"type": "string"},
                                        "title": {"type": "string"},
                                        "kind": {
                                            "type": "string",
                                            "enum": ["application_form", "checklist", "guide", "other"],
                                        },
                                    },
                                    "required": ["url", "title", "kind"],
                                    "additionalProperties": False,
                                },
                            }
                        },
                        "required": ["attachments"],
                        "additionalProperties": False,
                    },
                }
            },
        )
    except Exception as exc:  # pragma: no cover - defensive
        console.print(
            f"[yellow]LLM extraction failed[/yellow] {service_name}: {exc}",
            highlight=False,
        )
        return []
    try:
        text_payload = getattr(response, "output_text", None)
        if text_payload:
            data = json.loads(text_payload)
        else:
            dump = response.model_dump()
            output_items = dump.get("output", [])
            text_chunks = []
            for item in output_items:
                if item.get("type") != "message":
                    continue
                for chunk in item.get("content", []):
                    if chunk.get("type") == "output_text" and "text" in chunk:
                        text_chunks.append(chunk["text"])
            if not text_chunks:
                return []
            data = json.loads(text_chunks[0])
    except Exception as exc:  # pragma: no cover - defensive
        console.print(
            f"[yellow]Unable to parse LLM response[/yellow] {service_name}: {exc}",
            highlight=False,
        )
        return []
    attachments = []
    for item in data.get("attachments", []):
        url = item.get("url")
        title = item.get("title") or ""
        kind = item.get("kind") or "other"
        if not url:
            continue
        ext = Path(urlparse(url).path).suffix.lower()
        if ext not in ATTACHMENT_SUFFIXES:
            continue
        attachments.append(Attachment(url=url, title=title, kind=kind, source="llm"))
    return attachments


def merge_attachments(anchor_items: Iterable[Attachment], llm_items: Iterable[Attachment]) -> List[Attachment]:
    merged: Dict[str, Attachment] = {}
    for item in list(anchor_items) + list(llm_items):
        normalized_url = normalize_url(item.url)
        if normalized_url not in merged:
            merged[normalized_url] = item
        else:
            # Prefer LLM-provided kind/title when available.
            existing = merged[normalized_url]
            if existing.source == "anchor" and item.source == "llm":
                merged[normalized_url] = Attachment(
                    url=item.url,
                    title=item.title or existing.title,
                    kind=item.kind or existing.kind,
                    source="llm",
                )
    return list(merged.values())


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    path = re.sub(r"/+", "/", parsed.path)
    return f"{parsed.scheme}://{parsed.netloc}{path}".lower()


def build_target_filename(slug: str, url: str) -> str:
    name = Path(urlparse(url).path).name or "attachment"
    sanitized = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    if "." not in sanitized:
        sanitized = f"{sanitized}.bin"
    return f"{slug}-{sanitized}"


def download_attachment(session: requests.Session, attachment: Attachment, dest_dir: Path) -> None:
    slug = dest_dir.name
    filename = build_target_filename(slug, attachment.url)
    target_path = dest_dir / filename
    if target_path.exists():
        console.print(
            f"[yellow]Skip[/yellow] {target_path.name} (exists)",
            highlight=False,
        )
        return
    dest_dir.mkdir(parents=True, exist_ok=True)
    console.print(
        f"[cyan]Download[/cyan] {attachment.url} -> {target_path}",
        highlight=False,
    )
    with session.get(attachment.url, stream=True, timeout=90) as resp:
        resp.raise_for_status()
        with open(target_path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    fh.write(chunk)
    console.print(f"[green]Saved[/green] {target_path}", highlight=False)


def resolve_destination(
    directory_index: Dict[str, Path], service_name: str
) -> Path:
    key = normalize(service_name)
    if key in directory_index:
        return directory_index[key]
    new_dir = ROOT_DIR / re.sub(r"[^A-Za-z0-9]", "", service_name)
    new_dir.mkdir(parents=True, exist_ok=True)
    directory_index[key] = new_dir
    return new_dir


def process_page(
    session: requests.Session,
    client: Optional[OpenAI],
    model: str,
    service_name: str,
    service_url: str,
    dest_dir: Path,
) -> None:
    console.print(
        f"[bold cyan]Processing[/bold cyan] {service_name} -> {service_url}",
        highlight=False,
    )
    resp = session.get(service_url, timeout=90)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    article_text = extract_article_text(soup)
    anchor_candidates = collect_anchor_candidates(soup, service_url)
    llm_candidates = llm_extract_attachments(client, model, service_name, service_url, article_text, anchor_candidates)
    merged = merge_attachments(anchor_candidates, llm_candidates)
    if not merged:
        console.print(
            f"[yellow]No attachments found[/yellow] for {service_name}",
            highlight=False,
        )
        return

    for attachment in merged:
        if not attachment.title:
            attachment.title = Path(urlparse(attachment.url).path).name
        if attachment.kind == "other":
            attachment.kind = classify_attachment(attachment.title, attachment.url)
        try:
            download_attachment(session, attachment, dest_dir)
        except Exception as exc:  # pragma: no cover - defensive
            console.print(
                f"[red]Failed to download[/red] {attachment.url}: {exc}",
                highlight=False,
            )
    console.print(f"[bold green]Done[/bold green] {service_name}", highlight=False)


def gather_tasks(session: requests.Session) -> Dict[str, str]:
    tasks = fetch_service_links(session)
    for entry in VISA_PAGES:
        tasks.setdefault(entry["name"], entry["url"])
    return tasks


def main() -> None:
    ensure_environment()
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI() if api_key else None

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/127.0.0.0 Safari/537.36"
            )
        }
    )

    directory_index = build_directory_index(ROOT_DIR)
    tasks = gather_tasks(session)
    for service_name, service_url in track(
        list(tasks.items()), description="Fetching services", console=console
    ):
        dest_dir = resolve_destination(directory_index, service_name)
        try:
            process_page(session, client, model, service_name, service_url, dest_dir)
        except Exception as exc:
            console.print(
                f"[red]Error processing[/red] {service_name}: {exc}",
                highlight=False,
            )


if __name__ == "__main__":
    main()
