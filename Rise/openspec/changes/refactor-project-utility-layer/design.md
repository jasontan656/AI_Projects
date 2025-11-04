# Design: Project Utility Layer Refactor

## Goals
- Provide a dedicated package for reusable infrastructure primitives that adheres to the layering contract in `PROJECT_STRUCTURE.md`.
- Remove domain-centric naming (`shared_utility.core.*`) from utility helpers.
- Ensure all utility modules remain free of dependencies on business/service layers.
- Create a migration path that avoids breaking existing imports while downstream work is updated.

## Current State Summary
A code scan shows Project Utility-style helpers spread across multiple directories:
- `shared_utility/logging/rich_config.py` – logging bootstrap tied to Rich.
- `shared_utility/core/context.py` – request-id context propagation.
- `shared_utility/timezone.py` – timezone helpers used broadly.
- `shared_utility/config/paths.py` and similar modules – repository path discovery and shared config helpers.
- Common exception helpers are embedded inside business-focused modules.

This fragmentation makes layering blurry: `shared_utility/core` also carries schema/adapters (Foundational layer), so new contributors cannot easily distinguish allowed dependencies. Imports reference the legacy paths directly, preventing future reorganisations.

## Target Architecture
```
src/
  project_utility/
    __init__.py               # defines the supported public surface (re-exports)
    logging.py                # configure_logging, shared logging helpers (Rich integration allowed)
    context.py                # ContextBridge (request id), context utilities
    clock.py                  # philippine_now / ensure_philippine / conversions
    config/
    __init__.py             # aggregation
    paths.py                # repo/log root helpers
    loaders.py (optional)   # shared config reading helpers if needed
  exceptions.py             # optional base exceptions shared across layers
```
Key traits:
- Uses the `src/` layout advocated by the Python Packaging User Guide, keeping import resolution explicit and simplifying future distribution.
- Only depends on stdlib plus approved third-party libs (`rich`, `zoneinfo`), aligning with the spec.
- `__all__` ensures consumers use stable, intentional exports.
- `project_utility` is layer-agnostic; business/service modules import from here.

## Migration Strategy
1. **Audit & Classification** – produce a matrix of current modules vs layer to confirm scope (Task 1).
2. **Package Scaffold** – add the new `src/project_utility/` package with docstrings describing its role; update build metadata (`pyproject.toml`/`setup.cfg`) to map the `src` layout.
3. **Module Migration** – copy the core implementations into their new locations, rewriting module-level names to remove `shared_utility` prefixes and extracting any business-specific logic that snuck in.
4. **Compatibility Shims** – leave thin modules under the legacy paths:
   ```python
   # shared_utility/core/context.py
   from project_utility.context import *
   import warnings
   warnings.warn("Use project_utility.context", DeprecationWarning, stacklevel=2)
   ```
   These shims will be removed after all imports are updated.
5. **Consumer Updates** – update first-party imports to use the new package and run formatters/tests.
6. **Guards** – add a lightweight static check (e.g., script verifying `project_utility` does not import `shared_utility.service_*` or `telegram_api`) to enforce layering.
7. **Documentation** – refresh `PROJECT_STRUCTURE.md` and developer notes with the new directory → layer mapping and migration guidance.
8. **Deprecation Cleanup** – once usage metrics show no legacy imports, remove shims and tighten the guard rules (out of scope if it requires coordination beyond this change).

## Validation Plan
- Unit/integration smoke tests (if available) plus manual `python app.py --help` to verify logging/context wiring.
- Run the new dependency guard to ensure no upward imports.
- `openspec validate refactor-project-utility-layer --strict` before handing off the proposal.

## Alternatives Considered
- **Rename `shared_utility/core` to `shared_utility/project`**: rejected because `core` currently mixes foundational schemas/adapters; moving only utilities prevents large cascaded refactors.
- **Introduce a namespace package within `shared_utility`**: possible, but a top-level `project_utility` package is clearer and avoids implying that every helper lives under `shared_utility`.

## Dependencies / Coordination
- Downstream change owners (e.g., `refactor-snake-case-identifiers`) must be aware of the import-path migration; compatibility shims minimise risk.
- No infrastructure changes required.
