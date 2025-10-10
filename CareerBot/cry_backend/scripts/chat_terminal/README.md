Chat Terminal (workbench)

Quick CLI to chat with the backend hub via LangServe endpoints.

Requirements
- Python 3.10 in the local .venv
- Backend running (uvicorn main:app) on http://localhost:8000

Run
- From `cry_backend`:
  - `python -m scripts.chat_terminal.start`
  - Or with one-shot message: `python -m scripts.chat_terminal.start --message "hello"`

Options
- `--host` API host (default: http://localhost:8000)
- `--auth-username` initial username (normalized by validator)
- `--authorization` bearer token if available
- `--session-id` reuse an existing session id

Controls
- Interactive prompt: type a message and press Enter
- Multiline: type `>>>` to start, finish with `/end`
- Commands:
  - `/history` show last messages
  - `/clear` clear screen
  - `/exit` quit

Events rendering
- token: streamed LLM tokens
- ui: prints structured UI JSON
- artifact: prints artifact reference URL or info
- final: prints final message and finishes
- error: prints error with error_type
- metrics: prints brief metrics summary

