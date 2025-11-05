## ADDED Requirements
### Requirement: Embedded Runtime Policy Defaults
Foundational services MUST provide deterministic runtime policy defaults directly in code so that deployments can start without an external JSON policy file.

#### Scenario: Bootstrap without runtime_policy.json
- **GIVEN** `config/runtime_policy.json` is absent
- **WHEN** `bootstrap_aiogram` initialises the runtime
- **THEN** the loader supplies the embedded default policy
- **AND** deterministic settings such as seed and refusal strategy remain populated.

## REMOVED Requirements
### Requirement: Runtime Policy JSON Artefact
Foundational services MUST NOT require `config/runtime_policy.json` to exist for successful startup; the asset guard MUST NOT flag its absence as a violation.

#### Scenario: Asset guard runs without policy file
- **GIVEN** the repository does not contain `config/runtime_policy.json`
- **WHEN** the asset guard executes
- **THEN** it reports status `ok`
- **AND** it does not register a missing-file violation for the policy artefact.
