## ADDED Requirements
### Requirement: Code Comments Use English Text
All inline (`#`) and block comments in repository-managed source files MUST use English wording unless they are mandated by external assets (e.g., quoted logs, localisation resources). Non-ASCII text is allowed only for user-facing strings, not for code comments.

#### Scenario: Rewriting Existing Chinese Comments
- **GIVEN** a Python source file containing Chinese-language comments
- **WHEN** the style pass is applied
- **THEN** those comments MUST be rewritten in clear English or removed if redundant
- **AND** the change MUST keep surrounding pragmas/behaviour intact

#### Scenario: New Comment Added In Future
- **GIVEN** a contributor adds a new inline comment to any repository-managed source file
- **THEN** the comment MUST be written in English
- **AND** any non-English annotation MUST be moved into localisation assets or user-visible strings instead of remaining as code comments
