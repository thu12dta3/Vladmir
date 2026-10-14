#!/usr/bin/env bash
set -euo pipefail
VLADMIR_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$VLADMIR_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
exec "${VLADMIR_PYTHON:-$HOME/.local/share/vladmir/core-env/bin/python}" "$VLADMIR_ROOT/tests/integration_smoke.py"
