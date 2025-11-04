# One-off Utility Layer Audit

Date: 2025-11-03

## Shared Utility Scripts

| Path | Classification | Notes |
| --- | --- | --- |
| `shared_utility/scripts/auto_discovery_and_runtime_spec.py` | One-off | Ad-hoc orchestrator doc discovery; invoked manually. |
| `shared_utility/scripts/check_anchors.py` | One-off | Batch validation script (markdown anchors). |
| `shared_utility/scripts/check_doc_conflicts.py` | One-off | Conflict detector for docs. |
| `shared_utility/scripts/check_kb_index.py` | One-off | Knowledge base validator executed manually. |
| `shared_utility/scripts/conformance_check.py` | One-off | Layout/spec audit script. |
| `shared_utility/scripts/generate_snapshot.py` | One-off | Snapshot generator (batch). |
| `shared_utility/scripts/init_data_stores.py` | One-off | Dev-only bootstrap for Mongo/Redis. |
| `shared_utility/scripts/kb_pipeline_spec.py` | One-off | KB pipeline spec exporter. |
| `shared_utility/scripts/validate_pricing.py` | One-off | Pricing YAML linter. |
| `shared_utility/scripts/validate_prompts.py` | One-off | Prompt registry validator. |
| `shared_utility/scripts/validate_selectors.py` | One-off | Layout selector validator. |

All scripts rely on argparse and produce side effects (file IO, network). No production modules import them directly.

## Service Crawler Utilities

| Path | Classification | Notes |
| --- | --- | --- |
| `shared_utility/service_crawler/build_pdfsum.py` | One-off | PDF summariser used during data ingestion. |
| `shared_utility/service_crawler/config_loader.py` | Shared helper | Utility module used by other crawler scripts (retain as library under one-off namespace). |
| `shared_utility/service_crawler/convert_yaml.py` | One-off | Large batch converter for YAML assets. |
| `shared_utility/service_crawler/dedupe_pdfs.py` | One-off | Deduplication batch job. |
| `shared_utility/service_crawler/fetch_forms.py` | One-off | Data ingestion script hitting remote sources. |
| `shared_utility/service_crawler/fetch_visas.py` | One-off | Visa metadata fetcher. |
| `shared_utility/service_crawler/modify_yaml.py` | One-off | YAML mass-edit tool. |
| `shared_utility/service_crawler/rename_attachments.py` | One-off | Bulk rename of attachments. |
| `shared_utility/service_crawler/rewrite_md.py` | One-off | Markdown rewrite helper. |
| `shared_utility/service_crawler/show_info.py` | One-off | Simple info dumper. |
| `shared_utility/service_crawler/update_prices.py` | One-off | Pricing updater for crawler dataset. |

`config_loader.py` provides reusable helpers for the other crawler scripts. All other modules are single-purpose jobs with no inbound imports.

## Tools

| Path | Classification | Notes |
| --- | --- | --- |
| `tools/generate_semantic_docs.py` | One-off | Generates documentation snapshots; not used at runtime. |
| `tools/check_project_utility_deps.py` | Guard utility | Acts as lint/guard; keep outside one-off scope. |

## Summary
- Total one-off commands to migrate: 21.
- Shared helper (`config_loader.py`) should accompany the one-off package so dependent commands continue to function.
- No production packages import these scripts; restructuring will not break runtime paths. Compatibility wrappers will be added for the legacy entrypoints.
