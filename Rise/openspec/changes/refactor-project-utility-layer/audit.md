# Project Utility Layer Audit

Date: 2025-11-03

Scope: Identify reusable infrastructure helpers that must migrate into the canonical `project_utility` package.

## Logging
- `shared_utility/logging/rich_config.py`
  - Provides `configure_logging()` plus Rich/standard logging handlers and formatters.
  - Depends on stdlib logging, `rich`, and local configuration constants only.
- `shared_utility/logging/__init__.py`
  - Thin export wrapper around `configure_logging`.

## Context / Request ID
- `shared_utility/core/context.py`
  - Defines `ContextBridge` for context-local request IDs.
  - Only depends on stdlib (`contextvars`, `uuid`) and is consumed by FastAPI/Telegram surfaces.

## Clock / Timezone
- `shared_utility/timezone.py`
  - Supplies `philippine_now`, `philippine_iso`, `philippine_from_timestamp`, etc.
  - Contains fallback exception `ZoneInfoNotFoundError`.

## Configuration Helpers
- `shared_utility/config/paths.py`
  - Repository/log directory resolution helpers (`get_repo_root`, `get_log_root`).
- `shared_utility/config/__init__.py`
  - Currently empty aside from package marker; will become compatibility shim after migration.

## Candidate Extras (Evaluate During Migration)
- `shared_utility/core/tracing.py`
  - Async tracing helper built on stdlib logging; consider inclusion if packaged as general-purpose instrumentation.
- Any shared exception definitions embedded in foundational modules (e.g., timezone fallback) should relocate into the new layer when they serve generic infrastructure needs.

No other modules meet the Project Utility criteria; business-specific helpers (contracts, schema, service crawlers) remain out of scope.
