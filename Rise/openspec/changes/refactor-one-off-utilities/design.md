# Design: One-off Utility Layer Refactor

## Goals
- Isolate throwaway / low-reuse scripts into a canonical package that can be enumerated, documented, and safely removed.
- Prevent production code from depending on one-off scripts.
- Provide a Typer-based CLI harness to run scripts with metadata-driven guardrails.

## Current State Summary
- `shared_utility/scripts/` contains mix of validation tooling, pipeline scripts, and other utilities. Some are reusable (e.g., validators), others are ad-hoc (e.g., init data stores, generate snapshot).
- `shared_utility/service_crawler/` hosts numerous grab-bag scripts; some appear one-off (rename attachments, rewrite markdown) but live alongside reusable components.
- `tools/` folder contains ad-hoc helpers (e.g., `generate_semantic_docs.py`). The `sitecustomize.py` ensures `src` path is available but does not help track scripts.
- No metadata tracks script ownership, safety, or expiry; cleanup is manual.

## Target Architecture
```
src/
  one_off/
    __init__.py
    cli.py            # Typer app exposing commands
    registry.py       # Metadata registry (owner, description, safe-to-run)
    commands/
      __init__.py
      shared_utility/
         generate_snapshot.py
         rename_attachments.py
         ...
      service_crawler/
         fetch_forms.py
         ...
```
- Each command module exposes a `run` function annotated with metadata.
- CLI entrypoint collects registered commands, grouping them by source (shared_utility, service_crawler, etc.).
- Metadata includes: `summary`, `owner`, `danger_level`, optional `expires` date.

## Migration Strategy
1. **Audit** – classify scripts.
2. **Scaffold** – create Typer CLI with metadata decorators. CLI command: `python -m one_off <command>`.
3. **Migrate** – move scripts, adapting imports to `project_utility`. Keep functionality intact.
4. **Compatibility** – add stubs or README updates instructing new usage; optionally provide thin wrappers that call into the new CLI.
5. **Guards** – add import guard (fail if `one_off` is imported from non-CLI contexts) or lint script verifying absence of `from one_off` in production packages.
6. **Docs** – update architecture doc and add `docs/one_off_utilities.md` listing commands.
7. **Validation** – run selective commands, confirm CLI output, ensure guard passes.

## Validation Plan
- `python -m one_off --help`
- Run sample commands (e.g., knowledge base snapshot) to ensure functionality preserved.
- Execute guard script verifying no forbidden imports.
- `openspec validate` for the change.

## Alternatives Considered
- Keep scripts in place and only document them: rejected because it does not enforce isolation or guardrails.
- Use simple `__main__` modules without Typer: Typer offers minimal overhead and metadata integration.

## Dependencies / Coordination
- Communicate new CLI entrypoint to teams using existing scripts.
- Ensure documentation references the new package.
