• Repo Layering Model

  - Project Utility Layer
    Provides broadly reusable infrastructure primitives such as logging, contextual state, generic
    configuration, time helpers, and shared exception types. This layer should depend only on the
    standard library or stable third-party packages and expose technology-oriented APIs without
    business semantics. Source now lives under `src/project_utility/`; the legacy `shared_utility`
    package has been removed.
  - One-off Utility Layer
    Hosts scripts or tooling with low reuse value—test harnesses, data migration utilities, batch
    jobs, ad-hoc messaging scripts, etc. Because these artifacts are throwaway by design, they may
    invoke higher layers when convenient, but core business code must not depend on them. Source
    now lives under `src/one_off/` with a Typer CLI (`python -m one_off <command>`); legacy paths
    simply delegate to the CLI.
  - Foundational Service Layer
    Encapsulates long-lived enabling services: framework bootstrapping, interface contracts, schema
    validation, telemetry plumbing, configuration loading, external service adapters, and similar.
    It sits on top of the utility layer and exposes well-defined, testable interfaces to the layers
    above. Source now lives under `src/foundational_service/`; the former `shared_utility`
    implementation has been fully retired.
  - Interface / Entry Layer
    Handles all ingress concerns: HTTP endpoints, API gateways, webhooks, message-consumer
    entrypoints, and so on. Responsibilities include protocol translation, authentication, request
    validation, and routing to the underlying business capabilities. Keep this layer thin—no
    complex business choreography here. Source now lives under `src/interface_entry/`, with
    subpackages for FastAPI/bootstrap (`interface_entry.bootstrap`), HTTP middleware
    (`interface_entry.http`), Telegram runtime/handlers (`interface_entry.telegram`), and shared
    configuration helpers (`interface_entry.config`).
  - Business Service Layer
    Hosts reusable, domain-specific services (e.g., conversation orchestration, knowledge snapshot
    lifecycle) that depend on foundational utilities but hide channel specifics. Source now lives
    under `src/business_service/`, with initial modules for Telegram conversations
    (`business_service.conversation`) and knowledge snapshot management (`business_service.knowledge`).
    These services present typed APIs consumed by interface and future business logic layers.
  - Business Logic Layer
    Orchestrates concrete workflows, state machines, and end-to-end use cases that stitch together
    Business Service primitives. For Telegram conversations it owns
    `TelegramConversationFlow.process`, including short-circuit handling for ignored updates,
    triage/history prompt preparation, policy-gated refusal responses, and adapter contract
    finalization/validation before returning a `ConversationResult`. “Messy” logic is tolerated as
    long as each unit owns a single responsibility, while all side effects or heavy lifting remain
    delegated to the business service layer.
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
      - `src/project_utility/` → Project Utility Layer
      - `src/foundational_service/` → Foundational Service Layer
      - `src/interface_entry/` → Interface / Entry Layer
      - `shared_utility/` → (retired) legacy path removed after foundational refactor
