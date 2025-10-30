from __future__ import annotations

import re
from functools import cmp_to_key
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List
import os

from pdfminer.high_level import extract_text
from rich.console import Console
from rich.table import Table
from rich.progress import track

ROOT = Path(os.environ.get("SERVICE_CRAWLER_WORKSPACE_ROOT", r"D:/AI_Projects/TelegramChatHistory/Workspace/VBcombined/BI"))
TEXT_CACHE_ROOT = Path(os.environ.get("SERVICE_CRAWLER_PDF_CACHE", ROOT.parent / ".pdf_text_cache"))
PDF_EXT = ".pdf"
YEAR_PATTERN = re.compile(r"\b(20\d{2})\b")
DOC_NUM_PATTERN = re.compile(r"(?:^|[^0-9])(\d{2,})(?!\d)")


@dataclass
class PdfDoc:
    path: Path
    classification: str
    text: str
    normalized_text: str
    years: List[int] = field(default_factory=list)

    @property
    def best_year(self) -> int:
        return max(self.years) if self.years else 0

    @property
    def mtime(self) -> float:
        return self.path.stat().st_mtime

    @property
    def relative(self) -> Path:
        return self.path.relative_to(ROOT)


def parse_classification(path: Path) -> str:
    text = path.stem.lower()
    if "checklist" in text:
        return "checklist"
    if "application" in text or "form" in text:
        return "application_form"
    return "other"


def extract_pdf_text_safe(path: Path) -> str:
    try:
        text = extract_text(str(path))
    except Exception as exc:  # pragma: no cover - defensive
        return f"[PDF 解析失败] {exc}"
    return text


def normalize_text(text: str) -> str:
    return " ".join(text.split())


def detect_years(text: str) -> List[int]:
    years = []
    for match in YEAR_PATTERN.findall(text):
        try:
            years.append(int(match))
        except ValueError:
            continue
    return sorted(set(years))


def ensure_text_cache(path: Path, text: str) -> None:
    cache_path = TEXT_CACHE_ROOT / path.with_suffix(".txt")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(text, encoding="utf-8")

def extract_doc_number(path: Path) -> int:
    matches = DOC_NUM_PATTERN.findall(path.stem)
    numbers = []
    for match in matches:
        try:
            numbers.append(int(match))
        except ValueError:
            continue
    return max(numbers) if numbers else 0


def load_documents(console: Console) -> Dict[Path, List[PdfDoc]]:
    doc_map: Dict[Path, List[PdfDoc]] = {}
    pdf_paths = list(ROOT.rglob("*.pdf"))
    for pdf_path in track(pdf_paths, description="Scanning PDFs", console=console):
        if not pdf_path.is_file() or pdf_path.suffix.lower() != PDF_EXT:
            continue
        text = extract_pdf_text_safe(pdf_path)
        ensure_text_cache(pdf_path.relative_to(ROOT), text)
        doc = PdfDoc(
            path=pdf_path,
            classification=parse_classification(pdf_path),
            text=text,
            normalized_text=normalize_text(text),
            years=detect_years(text),
        )
        doc_map.setdefault(pdf_path.parent, []).append(doc)
    return doc_map


def choose_doc_to_keep(docs: List[PdfDoc]) -> PdfDoc:
    return max(docs, key=lambda d: (d.best_year, extract_doc_number(d.path), d.mtime))


def deduplicate_directory(directory: Path, docs: List[PdfDoc]) -> List[Path]:
    removed: List[Path] = []
    by_class: Dict[str, List[PdfDoc]] = {}
    for doc in docs:
        by_class.setdefault(doc.classification, []).append(doc)

    for classification, items in by_class.items():
        # Step 1: remove identical content duplicates
        by_text: Dict[str, List[PdfDoc]] = {}
        for doc in items:
            by_text.setdefault(doc.normalized_text, []).append(doc)

        surviving: List[PdfDoc] = []
        for group in by_text.values():
            keep = choose_doc_to_keep(group)
            surviving.append(keep)
            for doc in group:
                if doc is keep:
                    continue
                doc.path.unlink(missing_ok=True)
                removed.append(doc.path)

        # Step 2: if multiple unique versions, keep only highest year
        if len(surviving) <= 1:
            continue
        max_year = max(doc.best_year for doc in surviving)
        if max_year == 0:
            raise RuntimeError(
                f"ambiguous year for {classification} in {directory}"
            )
        for doc in list(surviving):
            if doc.best_year < max_year:
                doc.path.unlink(missing_ok=True)
                removed.append(doc.path)

    return removed


def main() -> None:
    if not ROOT.exists():
        raise SystemExit(f"[ERROR] Root directory not found: {ROOT}")

    console = Console()
    doc_map = load_documents(console)
    total_removed: List[Path] = []
    for directory, docs in doc_map.items():
        console.print(
            f"[cyan]Processing[/cyan] {directory.relative_to(ROOT)} "
            f"([bold]{len(docs)}[/bold] file(s))",
            highlight=False,
        )
        removed = deduplicate_directory(directory, docs)
        if removed:
            for path in removed:
                console.print(
                    f"[red]- Removed[/red] {path.relative_to(ROOT)}",
                    highlight=False,
                )
            total_removed.extend(removed)

    console.print(
        f"[bold green]Summary:[/bold green] processed {len(doc_map)} directories, "
        f"removed {len(total_removed)} files.",
        highlight=False,
    )
    if total_removed:
        sample = "\n".join(str(path.relative_to(ROOT)) for path in total_removed[:5])
        table = Table(title="Sample Removed Files", show_header=False)
        for row in sample.splitlines():
            table.add_row(row)
        console.print(table)


if __name__ == "__main__":
    main()
