## Why
- The standalone `config/runtime_policy.json` diverges from current behaviour; policy defaults are already embedded in code, and the file duplicates state that rarely changes.
- Maintaining the JSON + loader contracts forces asset guards, bootstrap timelines, and deployment scripts to manage an extra artefact that operators no longer edit.
- Removing the file and its design simplifies configuration and reduces the risk of stale policy fingerprints.

## What Changes
- Delete `config/runtime_policy.json` and any design assets or loader requirements that mandate its presence.
- Inline deterministic runtime policy defaults inside `foundational_service.policy.runtime` so bootstrap continues working without external files, while still allowing an override path for custom deployments.
- Relax asset guard checks, bootstrap telemetry, and knowledge snapshot validation so they no longer expect the runtime policy artefact.

## Impact
- Bootstrap will rely on code-defined defaults unless an explicit override path is provided, reducing filesystem dependencies.
- Observability timelines and asset guard reports will change to omit runtime policy file references.
- Requires regression tests to ensure policy-sensitive code paths (deterministic seeds, refusal strategy) still pick up the embedded defaults.
