# Tasks: Refactor Interface / Entry Layer

- [x] Scaffold `src/interface_entry/` package structure (bootstrap, http, telegram, middleware, config) and update `pyproject.toml`.
- [x] Migrate FastAPI app factory & middleware from `app.py` into `interface_entry.bootstrap.app`, leaving `app.py` as a thin launcher.
- [x] Port aiogram bootstrap, webhook routes, and metrics plumbing into `interface_entry.telegram` modules; remove legacy `telegram_api/runtime.py` & `routes.py`.
- [x] Move Telegram handlers/adapters into `interface_entry.telegram.handlers` and `interface_entry.telegram.adapters`, aligning with foundational contracts.
- [x] Load manifests/config from `config/` via `interface_entry.config.manifest_loader`; drop hardcoded references in `app.py`.
- [x] Update imports/tests/tooling to use the new package; delete the `telegram_api/` package after migration.
- [x] Refresh documentation (`openspec/PROJECT_STRUCTURE.md`, `openspec/project.md`) to reflect the Interface Layer structure.
- [x] Validate with `openspec validate refactor-interface-entry-layer --strict`, `PYTHONPATH=src python -m unittest tests.interface_entry.test_manifest_loader`, and `python -m compileall src`.
