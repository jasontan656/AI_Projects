# Proposal: Refactor One-off Utility Layer

## Context
- The One-off Utility Layer, per `openspec/PROJECT_STRUCTURE.md`, should host low-reuse scripts (tests, migrations, batch jobs) that **must not** be depended on by core services.
- Current repositories mix reusable helpers with one-off scripts under `shared_utility/scripts`, `shared_utility/service_crawler`, and ad-hoc tooling (e.g., `tools/generate_semantic_docs.py`).
- Some scripts rely on shared code without clear boundaries, making it hard to delete them once their purpose is fulfilled.
- After the project utility refactor, we now have a clean base package and need equivalent hygiene for throwaway tooling.

We queried Context7 (`/fastapi/typer`) to gather current guidance on structuring modular CLI/utility code, ensuring our plan aligns with modern Python CLI practices.

## Problem Statement
We must converge all one-off utilities into a well-defined structure that:
1. Keeps “throwaway” scripts isolated from reusable layers.
2. Provides metadata (purpose, owner, safe-to-delete flag) so teams can prune stale scripts confidently.
3. Offers a simple CLI harness (Typer-based) to run the scripts in a controlled environment.
4. Establishes guardrails preventing accidental imports of one-off code from production modules.

## Proposed Changes
- Create a `one_off/` package (Typer application under `src/`) where each command is a self-contained script with metadata.
- Migrate ad-hoc scripts from `shared_utility/scripts`, `shared_utility/service_crawler`, and `tools` into the new package.
- Attach metadata (YAML or decorator-based) describing owner, expiration, side effects.
- Ensure scripts that need project utilities import from `project_utility.*` and not vice versa.
- Provide documentation and indexes so engineers know what each script does and whether it can be run safely.
- Add tooling to detect orphaned scripts and outdated metadata.

## Scope
**In scope**
- Scanning all existing scripts, classifying them as one-off or reusable.
- Migrating one-off scripts into the new package with Typer commands.
- Documenting metadata and run instructions.
- Introducing import guards to block production code from importing one-off scripts.

**Out of scope**
- Rewriting business logic embedded in scripts (only reorganise/migrate).
- Enhancing script functionality beyond structural changes.
- Changing runtime dependencies of the scripts beyond what the new structure requires.

## Risks & Mitigations
- **Risk**: Moving scripts may break existing cron jobs or manual workflows.
  - **Mitigation**: Provide a compatibility wrapper (`python -m one_off <command>`) and update documentation.
- **Risk**: Some scripts might actually be reusable utilities.
  - **Mitigation**: Audit step to classify; reusable logic stays or is moved to project utility layer.
- **Risk**: Metadata maintenance overhead.
  - **Mitigation**: Keep metadata minimal (owner, expires, description) and add lint checks.

## Open Questions
- Do we need to version-control execution logs for certain scripts? (Can be addressed post-migration.)
- Should we enforce automatic expiry of scripts? (Future enhancement.)
