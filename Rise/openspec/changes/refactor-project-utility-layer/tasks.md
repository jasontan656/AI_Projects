## Tasks
- [x] 1. Catalogue existing helpers that belong to the Project Utility Layer (context, logging, clock, config, shared exceptions) and document ownership in a short audit note.
- [x] 2. Scaffold the new `src/project_utility/` package with submodules (`logging`, `context`, `clock`, `config`, `exceptions`) and define `__all__` exports.
- [x] 3. Update build metadata (`pyproject.toml` or `setup.cfg`) so the repository adopts the `src` layout and exposes the `project_utility` package for tooling.
- [x] 4. Migrate existing implementations into the new package, rewriting naming and dependencies to satisfy the layer contract (standard library + approved third-party only).
- [x] 5. Introduce compatibility shims under legacy paths and update first-party imports to use `project_utility` directly; add lint/test coverage that flags new legacy imports.
- [x] 6. Add dependency guard checks (e.g., lightweight import test or static analyser rule) ensuring project utility modules do not import higher-layer packages.
- [x] 7. Update documentation (PROJECT_STRUCTURE, developer docs) to include the new directory → layer mapping and deprecation guidance; remove shims once downstream adoption is confirmed.
- [x] 8. Run validation: `pytest`/targeted smoke scripts if available, plus any new lint/import guard to confirm no regressions.
