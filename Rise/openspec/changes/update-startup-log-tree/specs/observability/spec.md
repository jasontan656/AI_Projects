## ADDED Requirements
### Requirement: Tree-Formatted Startup Console Logs
Console logging for info-level startup records MUST display metadata using a tree layout beneath the primary message so operators can identify parent/child context at a glance.

#### Scenario: Startup step metadata formatted as tree
- **GIVEN** the application emits a `startup.step` info record with `step`, `description`, or other structured metadata
- **WHEN** the record is rendered by the Rich console handler
- **THEN** the console prints the base message on one line followed by the metadata on subsequent lines
- **AND** each metadata line is prefixed by tree connector glyphs that make the hierarchy obvious.
