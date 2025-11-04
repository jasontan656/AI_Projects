from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple


@dataclass(frozen=True)
class ScriptMetadata:
    command: str
    module: str
    summary: str
    owner: str
    group: str
    danger_level: str = "low"
    tags: Sequence[str] = ()


SCRIPTS: List[ScriptMetadata] = [
    ScriptMetadata(
        command="crawler-build-pdfsum",
        module="one_off.sources.service_crawler.build_pdfsum",
        summary="Generate PDF summaries for crawler attachments.",
        owner="service-crawler",
        group="service_crawler",
        tags=("crawler", "pdf"),
    ),
    ScriptMetadata(
        command="crawler-convert-yaml",
        module="one_off.sources.service_crawler.convert_yaml",
        summary="Convert crawler YAML assets.",
        owner="service-crawler",
        group="service_crawler",
        danger_level="medium",
        tags=("crawler", "yaml"),
    ),
    ScriptMetadata(
        command="crawler-dedupe-pdfs",
        module="one_off.sources.service_crawler.dedupe_pdfs",
        summary="Deduplicate crawler PDF attachments.",
        owner="service-crawler",
        group="service_crawler",
        tags=("crawler", "pdf"),
    ),
    ScriptMetadata(
        command="crawler-fetch-forms",
        module="one_off.sources.service_crawler.fetch_forms",
        summary="Fetch forms for crawler datasets.",
        owner="service-crawler",
        group="service_crawler",
        tags=("crawler", "http"),
    ),
    ScriptMetadata(
        command="crawler-fetch-visas",
        module="one_off.sources.service_crawler.fetch_visas",
        summary="Fetch visa data for crawler datasets.",
        owner="service-crawler",
        group="service_crawler",
        tags=("crawler", "http"),
    ),
    ScriptMetadata(
        command="crawler-modify-yaml",
        module="one_off.sources.service_crawler.modify_yaml",
        summary="Bulk modify YAML records.",
        owner="service-crawler",
        group="service_crawler",
        danger_level="medium",
        tags=("crawler", "yaml"),
    ),
    ScriptMetadata(
        command="crawler-rename-attachments",
        module="one_off.sources.service_crawler.rename_attachments",
        summary="Rename crawler attachments via LLM.",
        owner="service-crawler",
        group="service_crawler",
        danger_level="high",
        tags=("crawler", "llm"),
    ),
    ScriptMetadata(
        command="crawler-rewrite-md",
        module="one_off.sources.service_crawler.rewrite_md",
        summary="Rewrite crawler markdown descriptions.",
        owner="service-crawler",
        group="service_crawler",
        tags=("crawler", "markdown"),
    ),
    ScriptMetadata(
        command="crawler-show-info",
        module="one_off.sources.service_crawler.show_info",
        summary="Display crawler dataset info.",
        owner="service-crawler",
        group="service_crawler",
        tags=("crawler",),
    ),
    ScriptMetadata(
        command="crawler-update-prices",
        module="one_off.sources.service_crawler.update_prices",
        summary="Update service pricing information.",
        owner="service-crawler",
        group="service_crawler",
        danger_level="medium",
        tags=("crawler", "pricing"),
    ),
]
