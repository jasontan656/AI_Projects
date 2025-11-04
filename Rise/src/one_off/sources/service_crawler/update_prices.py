from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urljoin
import os

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.progress import Progress


BASE_URL = os.environ.get("SERVICE_CRAWLER_BASE_URL", "https://immigration.gov.ph")
SERVICES_URL = f"{BASE_URL}/services/"
ROOT_DIR = Path(os.environ.get("SERVICE_CRAWLER_WORKSPACE_ROOT", r"D:/AI_Projects/TelegramChatHistory/Workspace/VBcombined/BI"))
PRICE_SOURCE_PATH = Path(os.environ.get("SERVICE_CRAWLER_PRICE_DOC", str(Path(__file__).resolve().parent / "BI_price.md")))
RAW_OUTPUT_PATH = Path(os.environ.get("SERVICE_CRAWLER_PRICE_RAW", str(Path(__file__).resolve().parent / "prices_raw.txt")))
TEMP_RESULT_PATH = Path(os.environ.get("SERVICE_CRAWLER_PRICE_TEMP", str(Path(__file__).resolve().parent / "pricetemp.md")))
ENV_PATH = Path(os.environ.get("SERVICE_CRAWLER_ENV", r"D:/AI_Projects/Rise/.env"))

VISA_PAGES: List[Tuple[str, str]] = [
    ("Immigrant Visas | Child Born Abroad of Immigrant Mother", "https://immigration.gov.ph/child-born-abroad-of-immigrant-mother/"),
    ("Immigrant Visas | Child Born Subsequent to Issuance of Immigrant Visa", "https://immigration.gov.ph/child-born-subsqeunt-to-the-issuance-of-immigrant-visa-of-the-accompanying-parent-13c/"),
    ("Immigrant Visas | Immigrant Visa by Marriage (13A)", "https://immigration.gov.ph/elementor-2671/"),
    ("Immigrant Visas | Permanent Resident Visa (PRV)", "https://immigration.gov.ph/permanent-resident-visa-prv/"),
    ("Immigrant Visas | Returning Former Natural-Born Filipino Citizen (13G)", "https://immigration.gov.ph/returning-former-natural-born-filipino-citizen-13g/"),
    ("Immigrant Visas | Returning Resident (13E)", "https://immigration.gov.ph/returning-resident-13e/"),
    ("Immigrant Visas | Quota Visa (13)", "https://immigration.gov.ph/quota-visa-13/"),
    ("Non-Immigrant Visa | Temporary Resident Visa (TRV)", "https://immigration.gov.ph/temporary-resident-visa-trv/"),
    ("Non-Immigrant Visa | Temporary Visitor Visa (9A)", "https://immigration.gov.ph/visa-waiver/"),
    ("Non-Immigrant Visa | Treaty Trader or Investor (9D)", "https://immigration.gov.ph/treaty-trader-or-treaty-investor-9d/"),
    ("Non-Immigrant Visa | Accredited Official of Foreign Government (9E)", "https://immigration.gov.ph/accredited-official-of-foreign-government-9e/"),
    ("Non-Immigrant Visa | Student Visa (9F)", "https://immigration.gov.ph/student-visa-9f/"),
    ("Non-Immigrant Visa | Pre-arranged Employment Visa (9G)", "https://immigration.gov.ph/pre-4-arranged-employment-visa-9g/"),
    ("Special Visa | Visa Upon Arrival (SEVUA)", "https://immigration.gov.ph/visa-upon-arrival-sevua/"),
    ("Special Visa | Special Visa for Employment Generation", "https://immigration.gov.ph/special-visa-for-employment-generation/"),
    ("Special Visa | Special Employment Visa for Offshore Banking Unit", "https://immigration.gov.ph/special-employment-visa-for-offshore-banking-unit/"),
    ("Special Visa | Special Visa under E.O. 226 amended by R.A. 8756", "https://immigration.gov.ph/special-visa-under-e-o-226-as-amended-by-r-a-8756/"),
]

CURRENCY_PATTERN = re.compile(
    r"(?:PHP|Php|php|USD|usd|₱|\$)\s*\d|\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:PHP|Php|php|USD|usd|₱|\$)",
    re.IGNORECASE,
)

console = Console()


@dataclass
class FeeRecord:
    service: str
    url: str
    snippets: List[str]


def ensure_environment() -> None:
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH)
    else:
        load_dotenv()


def fetch_service_links(session: requests.Session) -> List[Tuple[str, str]]:
    console.print(f"[cyan]Fetching services hub:[/cyan] {SERVICES_URL}")
    resp = session.get(SERVICES_URL, timeout=60)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    results: List[Tuple[str, str]] = []
    seen_urls = set()
    for anchor in soup.select("article a[href]"):
        name = anchor.get_text(strip=True)
        href = anchor.get("href", "").strip()
        if not name or href.startswith("#"):
            continue
        if not href.lower().startswith("http"):
            href = urljoin(BASE_URL, href)
        if not href.lower().startswith(f"{BASE_URL}/services/"):
            continue
        if href in seen_urls:
            continue
        seen_urls.add(href)
        results.append((name, href))
    console.print(f"[cyan]Discovered {len(results)} service entries from hub[/cyan]")
    return results


def _format_rows(rows: List[Tuple[str, str]]) -> List[str]:
    formatted: List[str] = []
    for left, right in rows:
        left_clean = left.strip()
        right_clean = right.strip()
        if left_clean and right_clean and contains_currency(right_clean):
            formatted.append(f"{left_clean} — {right_clean}")
    return formatted


def contains_currency(text: str) -> bool:
    return bool(CURRENCY_PATTERN.search(text))


def parse_fee_block(content_html: str) -> List[str]:
    if not content_html:
        return []
    soup = BeautifulSoup(content_html, "html.parser")
    results: List[str] = []
    tables = soup.find_all("table")
    for table in tables:
        text = table.get_text(" ", strip=True)
        if not contains_currency(text):
            continue
        rows: List[Tuple[str, str]] = []
        for tr in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if len(cells) < 2:
                continue
            header_tokens = {"item description", "amount"}
            normalized = {cells[0].strip().lower(), cells[1].strip().lower()}
            if normalized == header_tokens:
                continue
            if all(cell.isupper() for cell in cells):
                continue
            rows.append((cells[0], cells[1]))
        results.extend(_format_rows(rows))
    if results:
        return results
    items: List[str] = []
    for li in soup.find_all("li"):
        text = li.get_text(" ", strip=True)
        if text and contains_currency(text):
            items.append(text)
    if items:
        return items
    paragraphs = [
        p.get_text(" ", strip=True)
        for p in soup.find_all("p")
        if p.get_text(strip=True) and contains_currency(p.get_text(" ", strip=True))
    ]
    return paragraphs


def extract_fee_snippets(article: BeautifulSoup) -> List[str]:
    anchor_texts = [
        "How much does it cost",
        "How much is the fee",
        "How much are the fees",
        "How much do I need to pay",
        "Fees and Charges",
    ]
    snippets: List[str] = []
    for anchor in article.find_all(["a", "button"]):
        text = anchor.get_text(" ", strip=True)
        if not text:
            continue
        normalized = text.lower()
        if not any(token.lower() in normalized for token in anchor_texts):
            continue
        href = anchor.get("href", "")
        target = None
        if href and href.startswith("#"):
            target = article.find(id=href.lstrip("#"))
        if target is None:
            target = anchor.find_next_sibling()
        block_snippets = parse_fee_block(target.decode_contents() if target else None)
        if block_snippets:
            snippets.extend(block_snippets)
    unique = list(dict.fromkeys(snippets))
    return unique


def gather_fee_records(session: requests.Session) -> List[FeeRecord]:
    records: List[FeeRecord] = []
    service_links = fetch_service_links(session)
    tasks_map: Dict[str, str] = {}
    for name, url in service_links:
        tasks_map[url] = name
    for title, url in VISA_PAGES:
        tasks_map.setdefault(url, title)
    aggregator_pages = [
        ("Services Overview", SERVICES_URL),
        ("Visas Overview", "https://immigration.gov.ph/visas/"),
    ]
    for title, url in aggregator_pages:
        tasks_map[url] = title
    tasks = list(tasks_map.items())
    with Progress(console=console) as progress:
        task = progress.add_task("[green]Scanning services...", total=len(tasks))
        for service_url, service_name in tasks:
            try:
                resp = session.get(service_url, timeout=90)
                resp.raise_for_status()
            except Exception as exc:
                console.print(f"[red]Failed fetching[/red] {service_name}: {exc}")
                records.append(FeeRecord(service=service_name, url=service_url, snippets=["(not found)"]))
                progress.advance(task)
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            article = soup.find("article") or soup
            snippets = extract_fee_snippets(article)
            if snippets:
                records.append(FeeRecord(service=service_name, url=service_url, snippets=snippets))
            else:
                records.append(FeeRecord(service=service_name, url=service_url, snippets=["(not found)"]))
            progress.advance(task)
    console.print(f"[bold green]Collected fee snippets for {len(records)} services.[/bold green]")
    return records


def write_raw_output(records: List[FeeRecord]) -> None:
    lines: List[str] = []
    for record in records:
        lines.append(f"## {record.service}")
        lines.append(f"URL: {record.url}")
        valid_snippets = [s for s in record.snippets if s and s != "(not found)"]
        if valid_snippets:
            lines.append("Fees:")
            for snippet in valid_snippets:
                lines.append(f"- {snippet}")
        else:
            lines.append("Fees: (not found)")
        lines.append("---")
    RAW_OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    console.print(f"[blue]Raw fee snippets saved to[/blue] {RAW_OUTPUT_PATH}")


def load_existing_price_doc() -> str:
    if PRICE_SOURCE_PATH.exists():
        return PRICE_SOURCE_PATH.read_text(encoding="utf-8")
    console.print(f"[yellow]Warning: {PRICE_SOURCE_PATH} not found. Using empty baseline.[/yellow]")
    return ""


def merge_with_llm(existing_doc: str, raw_snippets: str) -> str:
    ensure_environment()
    client = OpenAI()
    system_prompt = (
        "You are BI_PRICE_EDITOR. Update the Bureau of Immigration price reference Markdown.\n"
        "- Maintain a clear Markdown structure grouped by service.\n"
        "- Update existing fees if new data provides different amounts (label changes as '(updated Oct 2025)').\n"
        "- Add new services from RAW_DATA if not in the existing document.\n"
        "- Include currency, amount, applicable notes, and links where provided.\n"
        "- Remove obviously outdated or duplicate rows.\n"
        "- Output only the revised Markdown."
    )
    user_payload = json.dumps(
        {
            "existing_document": existing_doc,
            "raw_data": raw_snippets,
            "instructions": "Ensure all fees correspond to the latest 2025 information gathered from the official site.",
        },
        ensure_ascii=False,
    )
    response = client.responses.create(
        model="gpt-5",
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [{"type": "input_text", "text": user_payload}]},
        ],
    )
    output_text = getattr(response, "output_text", None)
    if not output_text:
        data = response.model_dump()
        chunks = []
        for item in data.get("output", []):
            if item.get("type") != "message":
                continue
            for part in item.get("content", []):
                if part.get("type") == "output_text" and "text" in part:
                    chunks.append(part["text"])
        output_text = "\n".join(chunks)
    return output_text.strip()


def main() -> None:
    ensure_environment()
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
            )
        }
    )
    if RAW_OUTPUT_PATH.exists() and RAW_OUTPUT_PATH.stat().st_size > 0:
        console.print(f"[yellow]Detected existing raw fee data at {RAW_OUTPUT_PATH}, skipping crawl.[/yellow]")
    else:
        if RAW_OUTPUT_PATH.exists():
            RAW_OUTPUT_PATH.unlink()
        records = gather_fee_records(session)
        write_raw_output(records)

    existing_doc = load_existing_price_doc()
    raw_data = RAW_OUTPUT_PATH.read_text(encoding="utf-8")
    console.print("[yellow]Review prices_raw.txt and confirm to proceed with LLM merge.[/yellow]")
    console.print("请输入 Y 继续合并，或按其他任意键退出：", end="")
    try:
        user_input = input().strip().lower()
    except EOFError:
        user_input = ""
    if user_input not in {"y", "yes"}:
        console.print("[red]Merge aborted by user. Edit prices_raw.txt and rerun when ready.[/red]")
        return

    console.print("[magenta]Invoking GPT-5.1 to merge price data...[/magenta]")
    merged_markdown = merge_with_llm(existing_doc, raw_data)
    TEMP_RESULT_PATH.write_text(merged_markdown, encoding="utf-8")
    console.print(f"[bold green]Updated price reference written to {TEMP_RESULT_PATH}[/bold green]")


if __name__ == "__main__":
    main()
