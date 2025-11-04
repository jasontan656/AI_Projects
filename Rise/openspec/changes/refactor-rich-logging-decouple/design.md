# Design: Rich Logging Extraction

## Overview
We will relocate the Rich logging bootstrap logic from `app.py` into a dedicated utility module. The new module should live under `shared_utility/logging/rich_config.py` so it is colocated with other shared infrastructure helpers.

## Module Structure
- `shared_utility/logging/__init__.py` (new if absent) can export `configure_logging` for ergonomics.
- `shared_utility/logging/rich_config.py`
  - Contains class definitions for filters, console handlers, alert handlers, plain formatter, and helper utilities that were previously nested inside `app.py`.
  - Exposes `configure_logging()` with the same behavior as the current `_configure_logging()` function.
  - Accepts optional keyword overrides if future services need to tweak log file names or console width (not required now but consider design to make extension easy).

## `app.py` Changes
- Replace `_configure_logging()` and related helper classes with a simple import:
  ```python
  from shared_utility.logging.rich_config import configure_logging
  ```
- Call `configure_logging()` near startup before any logging occurs.
- Remove now-unused imports (`OrderedDict`, `NamedTuple`, etc.) if they are no longer needed.

## Reuse Considerations
- The new module should not depend on FastAPI or aiogram. It should rely only on `logging`, `pathlib`, and shared configuration helpers.
- Keep idempotency: calling `configure_logging()` multiple times should not duplicate handlers. Reuse existing logic or add guards if necessary.

## Validation
- Manual smoke test: run `python app.py --help` (or start the service in dev mode) and confirm Rich console output still appears.
- Check that log files are created under the same directory as before.
- Optional: future enhancement could add a small unit test that imports and executes `configure_logging()` using a temporary directory, but not in scope unless requested.
