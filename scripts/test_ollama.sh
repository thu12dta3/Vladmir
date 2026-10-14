#!/usr/bin/env bash
set -euo pipefail
VLADMIR_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$VLADMIR_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
exec "${VLADMIR_PYTHON:-$HOME/.local/share/vladmir/core-env/bin/python}" - <<'PY'
import sys
from mark.brain import _ollama
from mark.config import load_config
from mark.selfcheck import ollama_status
cfg = load_config()
ready, message = ollama_status(cfg)
if not ready:
    print(f'FALTA: {message}', file=sys.stderr)
    raise SystemExit(1)
print(_ollama('Responda apenas: Vladmir online.', cfg))
PY
