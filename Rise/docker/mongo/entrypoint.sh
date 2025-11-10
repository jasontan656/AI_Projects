#!/bin/bash
set -euo pipefail
SOURCE_KEYFILE="/docker-key-secrets/keyfile"
RUNTIME_KEYFILE="/tmp/mongo-repl.key"
if [ -f "$SOURCE_KEYFILE" ]; then
  cp "$SOURCE_KEYFILE" "$RUNTIME_KEYFILE"
  chmod 600 "$RUNTIME_KEYFILE"
  chown 999:999 "$RUNTIME_KEYFILE"
fi
exec python3 /usr/local/bin/docker-entrypoint.py "$@"