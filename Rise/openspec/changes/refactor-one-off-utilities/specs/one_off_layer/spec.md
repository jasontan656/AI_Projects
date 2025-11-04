## ADDED Requirements

### Requirement: Centralized One-off Utility Package
The repository MUST expose a `one_off` package offering a Typer-based CLI that hosts all low-reuse scripts, each with associated metadata describing purpose, owner, and safety considerations.

#### Scenario: Run a migrated script via CLI
- **GIVEN** a script previously stored under `shared_utility/scripts`
- **WHEN** an engineer runs `python -m one_off <command>`
- **THEN** the command executes via the consolidated CLI
- **AND** metadata describing the script is available through `python -m one_off list` (or similar).

### Requirement: Production Code Isolation
Core production packages MUST NOT import from the `one_off` namespace; automated checks MUST fail when such imports appear.

#### Scenario: Production module imports one-off command
- **GIVEN** a core module attempts `from one_off.commands import some_script`
- **WHEN** guard checks run in CI
- **THEN** the check fails, indicating the one-off layer cannot be consumed by production code.

### Requirement: Legacy Invocation Decommissioning
Legacy file locations for migrated scripts MUST either be removed or provide explicit thin wrappers that delegate to the new CLI with clear messaging.

#### Scenario: Running a legacy script path
- **GIVEN** a user runs `python shared_utility/scripts/generate_snapshot.py`
- **WHEN** the script has been migrated
- **THEN** the legacy entrypoint either forwards to the `one_off` CLI or exits with instructions to use `python -m one_off generate-snapshot`.
