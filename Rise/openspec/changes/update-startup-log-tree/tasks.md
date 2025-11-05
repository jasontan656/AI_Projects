1. Review `src/project_utility/logging.py` to confirm how Rich console handlers assemble message + extras.
2. Refactor the info-level console render to split the primary message onto its own line and print metadata with tree glyphs.
3. Manually exercise a startup log sample (e.g., `python app.py --help` or targeted unit) to confirm the new layout.
4. Run `openspec validate update-startup-log-tree --strict` and any lightweight linting affected by the change.
