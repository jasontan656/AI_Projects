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
 
