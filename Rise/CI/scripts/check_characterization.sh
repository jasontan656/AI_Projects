#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPTS_DIR="$ROOT_DIR/AI_WorkSpace/Scripts/session_00001_compliance-audit"
PNPM_BIN="pnpm"
SCHEMATHESIS_BIN="$ROOT_DIR/.venv/Scripts/schemathesis"
RADON_BIN="$ROOT_DIR/.venv/Scripts/radon"

if ! command -v "$PNPM_BIN" >/dev/null 2>&1; then
  if [ -x "/c/Users/HP/AppData/Roaming/npm/pnpm.cmd" ]; then
    PNPM_BIN="/c/Users/HP/AppData/Roaming/npm/pnpm.cmd"
  fi
fi

echo "[1/7] Import guard"
python "$SCRIPTS_DIR/Step-01_import_guard.py" --ci

echo "[2/7] Characterization pytest"
PYTHONPATH="$ROOT_DIR/src" python -m pytest \
  tests/business_service/conversation/test_telegram_webhook.py \
  tests/business_service/conversation/test_runtime_gateway.py \
  -q

echo "[3/7] Coverage + channel tests"
PYTHONPATH="$ROOT_DIR/src" python -m pytest \
  tests/business_service/channel/test_coverage_status.py \
  tests/interface_entry/http/test_workflow_coverage.py \
  -q

echo "[4/7] Radon complexity gate"
"$RADON_BIN" cc "$ROOT_DIR/src" -a -s --no-ansi

echo "[5/7] Front-end cycle check (madge)"
cd "$ROOT_DIR/Up"
VITEST_WORKSPACE_ROOT=tests VITEST_SETUP_PATH=tests/setup/vitest.setup.js "$PNPM_BIN" dlx madge --circular src

echo "[6/7] Schemathesis fuzz"
"$SCHEMATHESIS_BIN" run http://127.0.0.1:8000/openapi.json \
  --checks=all \
  --stateful=links \
  --hypothesis-derandomize \
  --max-examples=20

echo "[7/7] Vitest smoke"
VITEST_WORKSPACE_ROOT=tests VITEST_SETUP_PATH=tests/setup/vitest.setup.js "$PNPM_BIN" vitest run tests/unit/ChannelTestPanel.spec.ts

echo "Characterization suite completed."
