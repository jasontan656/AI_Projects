## Why
- Startup boot logs pack message and metadata onto one line, making it hard to scan during debugging sessions.
- Operators requested tree-style formatting to quickly see the relationship between log keys like `step`, `description`, and nested context.

## What Changes
- Update the Rich console handler to render multi-line tree output for info-level records such as `startup.step`.
- Emit structured metadata beneath the primary message using Unicode tree glyphs so parent/child relationships are visually obvious.
- Keep warning/error handling untouched to preserve the alert panel behaviour.

## Impact
- Console output becomes easier to parse; file-based logs remain unchanged.
- Requires manual sanity check by starting the app and ensuring the new layout displays as expected.
