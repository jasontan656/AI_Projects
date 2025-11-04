## Tasks
- [x] 1. Audit existing scripts (`shared_utility/scripts`, `shared_utility/service_crawler`, `tools`) and classify each as one-off or reusable; produce an `audit.md`.
- [x] 2. Scaffold `src/one_off/` Typer package with metadata model, CLI entrypoint, and configuration for script registration.
- [x] 3. Migrate identified one-off scripts into the new package, wiring them as Typer commands with metadata annotations.
- [x] 4. Provide compatibility wrappers or documentation updates for legacy invocation paths; remove relocated files.
- [x] 5. Implement guard checks (static or runtime) ensuring production code cannot import `one_off` modules.
- [x] 6. Document the new structure in `openspec/PROJECT_STRUCTURE.md` and maintainers’ guide; include instructions for adding/removing scripts.
- [x] 7. Validate: run key scripts via the new CLI, execute guard checks, and run `python -m one_off --help` to ensure the dispatcher loads.
