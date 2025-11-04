## ADDED Requirements

### Requirement: Canonical Project Utility Package
The repository MUST expose a `project_utility` package that groups reusable infrastructure helpers (logging bootstrap, context propagation, clock utilities, shared configuration, common exceptions) under a cohesive namespace with documented public exports.

#### Scenario: Import logging helper from canonical namespace
- **GIVEN** an internal module needs to configure structured logging
- **WHEN** it imports `project_utility.logging.configure_logging`
- **THEN** the import succeeds without referencing legacy `shared_utility.*` paths
- **AND** the helper only depends on the standard library and allowed third-party packages (e.g., Rich).

### Requirement: Layer Isolation Guards
Project Utility code MUST NOT import from business, interface, or one-off utility layers; automated checks MUST fail the build when a forbidden dependency is added.

#### Scenario: Accidental business import in utility module
- **GIVEN** `project_utility/context.py` attempts to `import telegram_api.runtime`
- **WHEN** dependency guard checks run as part of the CI pipeline
- **THEN** the check fails with a clear error explaining that Project Utility cannot depend on higher layers.

### Requirement: Transitional Compatibility Shims
Legacy modules that previously hosted utility helpers MUST re-export the new implementations with deprecation guidance until all consumers migrate, ensuring a non-breaking transition.

#### Scenario: Existing code uses legacy import path
- **GIVEN** a module still imports `shared_utility.core.context.ContextBridge`
- **WHEN** the refactored package is deployed
- **THEN** the import continues to work via a shim
- **AND** a deprecation warning or documentation points developers to `project_utility.context` so they can migrate promptly.
