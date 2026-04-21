#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"

if [[ -x "$VENV_PYTHON" ]]; then
  exec "$VENV_PYTHON" "$ROOT_DIR/main.py"
fi

exec python3 "$ROOT_DIR/main.py"
