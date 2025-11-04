# Proposal: Refactor Rich Logging Bootstrap

## Context
`app.py` currently defines and configures all Rich-based logging handlers, filters, and formatters inline. The bootstrap code mixes console rendering concerns with the FastAPI application lifecycle, making the module difficult to reason about and hard to reuse for other services. The user requested that we “remove 屎山日志相关代码 from app.py，decouple richlog codes from business codes,” so business logic should only import and call a helper instead of embedding the implementation.

## Problem
- Logging responsibilities are tightly coupled with the web application bootstrap, increasing the risk of regressions whenever we touch either area.
- Reusing the logging stack in future workers or CLIs would require copy-pasting the entire block from `app.py`.
- Testing and maintenance are painful because the module mixes concerns (FastAPI routes, aiogram bootstrap, logging utilities).

## Goals
1. Extract Rich logging configuration into a dedicated module/package with a clean public function.
2. Ensure `app.py` only needs to import that helper and invoke a single function to configure logging.
3. Preserve current logging features (Rich console, panel alerts, file handlers, UVicorn alias filter, component-specific rotating logs) without behavior regressions.

## Non-Goals
- Overhauling the log schema, file layout, or retention policy.
- Introducing alternative logging backends or changing runtime configuration sources.
- Modifying unrelated FastAPI or aiogram behaviors.

## Proposed Solution
1. Create a new module (e.g., `shared_utility.logging.rich_config`) that encapsulates all handler/filter/formatter classes and exposes a `configure_logging()` entrypoint returning nothing.
2. Move `_MaxLevelFilter`, `_RichConsoleHandler`, `_RichAlertHandler`, `_ConsolePlainFormatter`, `_UvicornLogAliasFilter`, helper utilities, and file-handler setup logic into that module. Keep the function interface stable so future services can reuse it.
3. Update `app.py` to import `configure_logging` from the new module and invoke it, deleting the inlined class definitions.
4. Maintain current log paths and naming conventions by reusing `shared_utility.config.paths.get_log_root`.
5. Add unit or smoke tests (if feasible) or CLI validation steps to ensure the helper can be imported and called without side effects.

## Risks & Mitigations
- **Risk:** Relocation may break implicit exports if other modules relied on the inner classes. *Mitigation:* audit repository references; re-export through the new module if necessary.
- **Risk:** Differences in module import order could change logging initialization. *Mitigation:* ensure `configure_logging()` retains idempotent behavior and is called before other components log messages.
- **Risk:** Path or encoding issues if the new module changes working directories. *Mitigation:* continue using absolute paths derived from `get_log_root()`.

## Impact
This refactor simplifies `app.py`, reduces maintenance overhead, and provides a reusable logging helper for future services.

## Open Questions
- Do we want to expose customization hooks (e.g., toggling Rich features) via environment variables? (Out of scope unless requested later.)
