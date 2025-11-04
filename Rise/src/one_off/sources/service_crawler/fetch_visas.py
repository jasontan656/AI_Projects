import os
import re
from pathlib import Path
from typing import Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = Path(os.environ.get("SERVICE_CRAWLER_WORKSPACE_ROOT", r"D:/AI_Projects/TelegramChatHistory/Workspace/VBcombined/BI"))
ENV_PATH = Path(os.environ.get("SERVICE_CRAWLER_ENV", r"D:/AI_Projects/Rise/.env"))
VISA_DATA = [
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

def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())

def setup_environment():
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH)
    else:
        load_dotenv()

def classify_file(title: str, url: str) -> str:
    text = f"{title} {url}".lower()
    if "checklist" in text or "requirements" in text:
        return "checklist"
    if "application" in text or "form" in text or "request" in text:
        return "application_form"
    if "guide" in text or "notes" in text or "manual" in text:
        return "guide"
    return "other"

def download_file(url: str, dest_dir: Path, base_name: str) -> Path:
    filename = Path(url).name.split("?")[0]
    temp_path = dest_dir / filename
    if temp_path.exists():
        temp_path.unlink()
    print(f"[DOWNLOAD] {url} -> {temp_path}")
    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with open(temp_path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    fh.write(chunk)
    ext = temp_path.suffix or Path(url).suffix or ".pdf"
    target_path = dest_dir / f"{base_name}{ext}"
    if target_path.exists():
        target_path.unlink()
    temp_path.rename(target_path)
    print(f"[INFO] Saved as {target_path}")
    return target_path

def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article")
    if not article:
        return ""
    for tag in article.find_all(["nav", "aside", "form", "script", "style"]):
        tag.decompose()
    text = article.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)

def summarize_to_markdown(service_name: str, category: str, url: str, raw_text: str) -> str:
    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    prompt = (
        "You are a documentation specialist. Rewrite the provided visa service description "
        "as a structured Markdown guide with sections: Overview, Eligibility, Requirements, "
        "Process, Fees (if mentioned), Notes, References.\n"
        f"Service Name: {service_name}\n"
        f"Category: {category}\n"
        f"Source URL: {url}\n"
        "Source Text:\n"
        f"{raw_text[:6000]}\n"
        "Respond only with the Markdown content."
    )
    response = client.responses.create(
        model=model,
        input=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.output[0].content[0].text.strip()

def main():
    setup_environment()
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.0 Safari/537.36"
    })
    folder_lookup = {
        normalize(path.name): path
        for path in BASE_DIR.iterdir()
        if path.is_dir()
    }
    for entry in VISA_DATA:
        name = entry["name"]
        url = entry["url"]
        category = entry["category"]
        key = normalize(name)
        dest_dir = folder_lookup.get(key)
        if not dest_dir:
            dest_dir = BASE_DIR / re.sub(r"[^A-Za-z0-9]", "", name)
            dest_dir.mkdir(parents=True, exist_ok=True)
            folder_lookup[key] = dest_dir
        try:
            resp = session.get(url, timeout=60)
            resp.raise_for_status()
        except Exception as exc:
            print(f"[ERROR] Failed to fetch {url}: {exc}")
            continue
        raw_text = extract_text(resp.text)
        if raw_text:
            markdown = summarize_to_markdown(name, category, url, raw_text)
            md_path = dest_dir / f"{dest_dir.name}.md"
            md_path.write_text(markdown, encoding="utf-8")
            print(f"[INFO] Markdown updated: {md_path}")
        soup = BeautifulSoup(resp.text, "html.parser")
        anchors = soup.find_all("a", href=True)
        counts: Dict[str, int] = {}
        for a in anchors:
            href = a["href"].strip()
            if not re.search(r"\.(pdf|jpg|jpeg|png)$", href.lower()):
                continue
            if not href.lower().startswith("http"):
                href = urljoin(url, href)
            file_category = classify_file(a.get_text(" ", strip=True), href)
            counts.setdefault(file_category, 0)
            counts[file_category] += 1
            suffix = f"{counts[file_category]:02d}"
            base_name = f"{dest_dir.name}-{file_category}-{suffix}"
            try:
                download_file(href, dest_dir, base_name)
            except Exception as exc:
                print(f"[ERROR] Download failed {href}: {exc}")
        print(f"[DONE] {name}")

if __name__ == "__main__":
    main()
