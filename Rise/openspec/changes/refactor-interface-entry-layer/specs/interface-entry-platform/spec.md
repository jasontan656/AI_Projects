# Capability: Interface Entry Platform

## ADDED Requirements

### Requirement: Expose canonical interface_entry package
The repository MUST expose an `interface_entry` package under `src/` that provides HTTP and protocol-specific entrypoints (FastAPI app factory, telegram runtime) without embedding foundational logic.

#### Scenario: Build FastAPI app via interface_entry
GIVEN project dependencies are installed
WHEN executing `from interface_entry.bootstrap.app import create_app` and calling `create_app()`
THEN a FastAPI instance is returned with middleware and routes registered
AND no module import from deprecated `telegram_api` or `shared_utility` occurs.

### Requirement: Organize entry submodules by concern
Interface Entry code MUST be organized into subpackages for `bootstrap`, `http`, `telegram`, `middleware`, and `config`, each owning a focused responsibility.

#### Scenario: Inspect interface_entry namespace
GIVEN the repository root
WHEN listing `pkgutil.iter_modules(interface_entry.__path__)`
THEN entries for `bootstrap`, `http`, `telegram`, `middleware`, and `config` are present.

### Requirement: Retire legacy telegram_api package
The legacy `telegram_api` package MUST be removed after migration, with all consumers updated to import from `interface_entry`.

#### Scenario: Import legacy path
GIVEN a Python REPL
WHEN attempting `import telegram_api`
THEN an `ImportError` is raised indicating the module is unavailable.

