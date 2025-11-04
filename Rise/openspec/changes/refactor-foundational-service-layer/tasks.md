# Tasks: Refactor Foundational Service Layer

- [x] Establish `src/foundational_service/` package skeleton (bootstrap, contracts, telemetry, policy, integrations, diagnostics) with `pyproject.toml` updates and stub exports.
- [x] Migrate core envelope + toolcall utilities into `foundational_service.contracts.*`, add unit tests covering envelope validation and Telegram adapter transforms.
- [x] Extract bootstrap state + metrics into `foundational_service.bootstrap.state/diagnostics`, ensure aiogram bootstrap rewrites compile with type hints.
- [x] Rebuild `behavior_bootstrap` as `foundational_service.bootstrap.aiogram.bootstrap_aiogram`, delegating runtime policy + telemetry loading to new modules.
- [x] Relocate telemetry bus/config + runtime policy loaders; introduce typed runtime policy model and update consumers.
- [x] Move OpenAI bridge + knowledge base loaders into `foundational_service.integrations`, update async flows to inject dependencies.
- [x] Update interface callers (`app.py`, `telegram_api/runtime.py`, scripts) to use new APIs; add or update smoke tests to cover bootstrap and webhook validation.
- [x] Remove legacy `shared_utility` implementations after migrating consumers to the canonical packages.
- [x] Document layering rules + migration notes in repo docs; update README or equivalent map referenced by `PROJECT_STRUCTURE.md`.
- [x] Run `openspec validate refactor-foundational-service-layer --strict`, targeted unit tests, and linters (e.g., `python -m compileall`, `PYTHONPATH=src python -m unittest tests.foundational_service.test_contracts`) to verify no regressions.
