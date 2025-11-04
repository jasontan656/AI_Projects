## Why
- Multiple Python modules and directories (for example `shared_utility` and `openai_agents/AgentContract`) use PascalCase or camel case, diverging from PEP 8 and the Wemake Python style guide guidance on snake_case modules.
- Several helper functions, CLI scripts, and mutable attributes follow mixed casing, increasing friction when onboarding or running lint tools.
- Internal configuration assets mix naming styles, making it harder to reason about keys and automate validation.

## What Changes
- Rename existing Python packages and modules under our control to snake_case and update every import or reference accordingly.
- Refactor non-constant function, coroutine, and variable identifiers that still use mixed casing so they follow snake_case while preserving behaviour.
- Normalise internal-only configuration keys (YAML/JSON/dict literals) to snake_case without breaking external API contracts.
- Document the new expectations inside the repository specs so future contributions align by default.

## Impact
- Requires coordinated bulk renames across Python files; import paths, dynamic loaders, and packaging scripts must be verified.
- Downstream tooling (tests, scripts, deployment pipelines) must be exercised after renames to ensure no runtime regressions.
- Future contributors gain a single, documented convention that matches the latest Python style references and simplifies static analysis.
