# Capability: Foundational Service Platform

## ADDED Requirements

### Requirement: Expose canonical Foundational Service package
The repository MUST expose a `foundational_service` package under `src/` that aggregates bootstrap, contracts, telemetry, policy, integrations, and diagnostics subpackages documented in `PROJECT_STRUCTURE.md`.

#### Scenario: Import canonical bootstrap module
GIVEN the project dependencies are installed
WHEN `from foundational_service.bootstrap.aiogram import bootstrap_aiogram` is executed
THEN the import succeeds without relying on `shared_utility` internals
AND the module exports typed interfaces for bootstrap state and results.

#### Scenario: Discover subpackages
GIVEN the repository root
WHEN listing `pkgutil.iter_modules(foundational_service.__path__)`
THEN entries for `bootstrap`, `contracts`, `telemetry`, `policy`, `integrations`, and `diagnostics` are present.

### Requirement: Provide compatibility shims with deprecation warnings
Legacy imports under `shared_utility` MUST continue to work during the migration window via thin re-export modules that emit a `DeprecationWarning` on import.

#### Scenario: Import legacy behavior contract path
GIVEN `warnings.simplefilter("error", DeprecationWarning)`
WHEN importing `shared_utility.contracts.behavior_contract`
THEN a `DeprecationWarning` is raised referencing `foundational_service.bootstrap`
AND the module re-exports the new bootstrap functions for backward compatibility.

### Requirement: Enforce downward dependencies
Modules inside `foundational_service` MUST NOT import from interface, business service, business logic, or one-off utility layers. Tooling MUST verify this during CI.

#### Scenario: Dependency guard rejects upward import
GIVEN a lint task or static check configured for the repo
WHEN a `foundational_service` module attempts to import `telegram_api.handlers`
THEN the guard fails with an error explaining the layer violation
AND the CI task exits non-zero.

