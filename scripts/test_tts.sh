#!/usr/bin/env bash
set -euo pipefail
VLADMIR_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$VLADMIR_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
exec "${VLADMIR_PYTHON:-$HOME/.local/share/vladmir/core-env/bin/python}" - <<'PY'
from mark.config import load_config
from mark.tts import speak
speak('Teste de voz do Vladmir. Sistema de áudio funcionando.', 'pt', load_config())
PY
