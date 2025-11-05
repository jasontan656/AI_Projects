## Why
- Operators perceive the service as frozen during startup because expensive operations (aiogram bootstrap, knowledge snapshot load, Telegram checks) emit no immediate logs.
- Providing incremental progress logs makes it easier to distinguish real hangs from expected I/O delays, especially on slower WSL2 filesystems.

## What Changes
- Add structured `_log_startup_step` calls before and after heavy synchronous startup segments, including aiogram bootstrap, knowledge snapshot load, and webhook registration.
- Emit live progress logs inside the `--clean` path so Redis/Mongo purges are visible as they run.
- Keep existing tree-formatted console output, only augmenting the sequence of emitted steps.

## Impact
- Startup console output becomes more granular without changing behaviour.
- No config or runtime policy changes; only logging additions.
- Requires a quick manual sanity check (e.g., `python3 app.py --help`) to confirm the new steps display in order.
