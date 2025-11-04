# Proposal: Refactor Project Utility Layer

## Context
- The repository’s Project Utility Layer is defined in `PROJECT_STRUCTURE.md` as the home for reusable infrastructure primitives (logging, contextual state, configuration, time helpers, shared exceptions).
- Current code that logically belongs to this layer is scattered across `shared_utility/core/`, `shared_utility/config/`, `shared_utility/logging/`, and top-level helpers like `shared_utility/timezone.py`.
- Many modules expose business-centric names (e.g., `shared_utility.core.context`) or reside beside domain-specific packages, making the layer boundary unclear and encouraging upward dependency leaks.
- Several downstream modules import these helpers through legacy paths, creating tight coupling and blocking future enforcement of the layering model.

We verified current packaging guidance through the `context 7` MCP server (Python Packaging User Guide) to align this plan with modern namespace and layout recommendations. Assumptions below continue to reference the tech stack documented in `openspec/project.md`.

## Problem Statement
We need to converge all Project Utility Layer code into a dedicated, well-defined package that:
1. Exposes a clean public surface grouped by concern (logging, context, clock, config, exceptions).
2. Depends only on the standard library or vetted third-party packages (Rich for logging is acceptable per project conventions).
3. Provides migration shims for existing import paths, enabling incremental rollout without breaking active work.
4. Documents layering rules so other teams can onboard to the new layout without rediscovery.

## Proposed Changes
- Introduce a new top-level package (working name: `project_utility`) under a `src/` layout (per Python Packaging User Guide) housing the canonical modules:
  - `logging` – owns `configure_logging` and related helpers.
  - `context` – wraps `ContextBridge` and request-id propagation.
  - `clock` – consolidates timezone helpers (`philippine_now`, `ensure_philippine`, etc.).
  - `config` – centralises repository-path helpers and shared configuration loaders.
  - `exceptions` – curated common exception base types if required.
- Refactor existing implementations (currently under `shared_utility/...`) into the new package, rewriting as needed to remove domain naming and enforce layering constraints.
- Add thin compatibility modules under the old paths that re-export from `project_utility` while emitting deprecation warnings, then update first-party imports to rely on the new package.
- Establish automated checks (lint/import tests) ensuring that Project Utility modules do not import business/service packages.
- Produce comprehensive documentation mapping directories to the new layer and outlining allowed dependencies.

## Scope
**In scope**
- Auditing all modules that satisfy the Project Utility remit (logging, context, config, timezone helpers, core reusable exceptions).
- Rewriting and relocating those modules into the new package.
- Updating first-party imports and providing deprecation shims.
- Adding guardrails/tests that block regressions.
- Documentation updates reflecting the new structure and usage expectations.

**Out of scope**
- Refactoring Foundational/Business layers beyond dependency updates required by this change.
- Rewriting one-off scripts or business services unless they need import changes.
- Introducing new functionality unrelated to utility responsibilities.

## Risks & Mitigations
- **Risk**: Import-path churn breaks work-in-progress branches.
  - **Mitigation**: Provide compatibility shims with clear deprecation warnings and communicate the migration window.
- **Risk**: Hidden dependencies from project utility code into higher layers create circular imports after relocation.
  - **Mitigation**: Add automated dependency guards and restructure offending code during the refactor.
- **Risk**: Large change surface impacts review velocity.
  - **Mitigation**: Deliver work in sequenced tasks (audit → package scaffolding → module migration → consumer updates → cleanup).

## Open Questions
- Do we need additional shared exceptions besides existing ones in the codebase? (Recommend deciding during design; can start with current set.)
- Should compatibility shims live permanently or be removed after a deprecation period? (Proposal assumes a short-term shim, removable after downstream updates.)
