## ADDED Requirements
### Requirement: Python Modules And Packages Use Snake Case
Rise repository Python packages and module filenames MUST use lowercase snake_case naming to match PEP 8 guidance.

#### Scenario: Module Rename
- **GIVEN** a Python module or package directory that uses mixed or upper case characters
- **WHEN** the repository is standardised
- **THEN** the file/directory MUST be renamed to snake_case
- **AND** every import or reference MUST be updated to the new path

#### Scenario: New Python Module
- **GIVEN** a contributor adds a Python module or package in the future
- **THEN** the filename MUST already be snake_case
- **AND** the contributor MUST avoid camelCase, PascalCase, or hyphenated names

### Requirement: Functions And Variable Identifiers Use Snake Case
All non-constant Python identifiers that represent functions, methods, and mutable values MUST use snake_case naming, excluding framework-required or external contract names.

#### Scenario: Function Or Method Definition
- **GIVEN** a function, coroutine, or method defined inside the repo
- **WHEN** its name is evaluated for style compliance
- **THEN** the name MUST be snake_case
- **AND** legacy CamelCase or mixedCase names MUST be renamed without changing behaviour

#### Scenario: Regular Variable Or Attribute
- **GIVEN** a module, local, or instance/class attribute that represents a mutable value
- **WHEN** it is refactored under this change
- **THEN** the identifier MUST be snake_case
- **AND** renames MUST exclude constants (still CONSTANT_CASE) and any values mandated by external APIs, schemas, or environment variable names

### Requirement: Configurable Assets Prefer Snake Case Keys Under Internal Control
Configuration assets owned by Rise (YAML, JSON, or script-generated dictionaries) MUST default to snake_case keys unless externally specified.

#### Scenario: Internal Configuration Schema
- **GIVEN** a configuration file or in-memory schema where Rise defines the keys consumed inside the repo
- **WHEN** the asset is reviewed for naming alignment
- **THEN** keys under Rise control MUST be snake_case
- **AND** keys that mirror third-party contracts MUST remain untouched even if they are not snake_case
