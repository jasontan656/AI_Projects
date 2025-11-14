• Repo Layering Model

  - Project Utility Layer
    Provides broadly reusable infrastructure primitives such as logging, contextual state, generic
    configuration, time helpers, and shared exception types. This layer should depend only on the
    standard library or stable third-party packages and expose technology-oriented APIs without
    business semantics. 
  - One-off Utility Layer
    Hosts scripts or tooling with low reuse value—test harnesses, data migration utilities, batch
    jobs, ad-hoc messaging scripts, etc. Because these artifacts are throwaway by design, they may
    invoke higher layers when convenient, but core business code must not depend on them. 
  - Foundational Service Layer
    Encapsulates long-lived enabling services: framework bootstrapping, interface contracts, schema
    validation, telemetry plumbing, configuration loading, external service adapters, and similar.
    It sits on top of the utility layer and exposes well-defined, testable interfaces to the layers
    above. 
  - Interface / Entry Layer
    Handles all ingress concerns: HTTP endpoints, API gateways, webhooks, message-consumer
    entrypoints, and so on. Responsibilities include protocol translation, authentication, request
    validation, and routing to the underlying business capabilities. Keep this layer thin—no
    complex business choreography here. 
  - Business Service Layer
    Hosts reusable, domain-specific services (e.g., conversation orchestration, knowledge snapshot
    lifecycle) that depend on foundational utilities but hide channel specifics. 
  - Business Logic Layer
    Orchestrates concrete workflows, state machines, and end-to-end use cases that stitch together
    Business Service primitives. 
  - Business Asset Layer
    Stores configuration, structured/semistructured datasets, templates, copy decks, or any other
    non-code artifacts consumed by business logic. While not executable code, it must be versioned,
    validated, and kept in sync with the layers that reference it.

  Additional Guidelines

  1. Enforce downward-only dependencies: Business Logic → Business Service → Foundational Service →
     Project Utility; interface entrypoints invoke these layers but do not own business flow; one-
     off utilities and business assets must never become prerequisites for core execution paths.
  2. Document the responsibility boundaries between layers so future refactors converge on this
     architecture.
  3. Maintain a “directory → layer” lookup (e.g., in the project README or engineering handbook) to
     guide contributors when adding new modules.

• Directory & Naming Guidelines

  - For every new feature, document its directory placement in DevDoc (e.g., `app/api/webhooks/telegram/`
    → Interface Layer, `app/workflows/bi/accreditation/` → Business Logic). Avoid dumping files at
    repo root; create descriptive subdirectories aligned to the layer model.
  - Utility helpers belong in subfolders grouped by behavior (`app/utils/serialization`,
    `app/utils/telemetry`, `app/utils/validators`). Keep modules small (“small plugin” mindset) even
    if they share dependencies; cross-imports are preferable to monolithic misc files.
  - Assets (payloads, prompts, templates) live under `app/assets/<domain>/...` and mirror the business
    taxonomy (visa, channel, workflow). Do not mix unrelated assets in a single JSON/YAML.
  - Scripts generated during implementation/testing must live under `AI_WorkSpace/Scripts/session_<id>_<topic>/`
    and include the Step ID in the filename (e.g., `dev/Step-03_seed_workflow.py`, `test/Step-07_ui_capture.har`).

• Handling High-Coupling Files

  - Intentional “fat” files (aggregators, orchestrators) are allowed only when they coordinate multiple
    submodules. Document the rationale, the submodules invoked, and the planned extraction points in
    DevDoc/notes so future work can split them when the feature stabilizes.
  - When accidental coupling is discovered (e.g., utility files mixing unrelated behaviors), log it in
    the issue tracker and create explicit Steps in the task plan (stored under `AI_WorkSpace/Tasks/`) to refactor. Downstream prompts (02–06)
    must see the note so refactoring can be scheduled.
  - Prefer composition over inheritance/monolithic exports. If two domains only share a subset of helpers,
    extract that subset into a new module instead of keeping both domains in the same file.
  - Record naming conventions (e.g., `workflow_service.py`, `channel_policy_store.ts`) in DevDoc so new files
    follow predictable patterns.
 
