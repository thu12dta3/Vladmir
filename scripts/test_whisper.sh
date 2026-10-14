#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 || ! -f "$1" ]]; then echo "Uso: $0 arquivo.wav" >&2; exit 2; fi
VLADMIR_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$VLADMIR_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
exec "${VLADMIR_PYTHON:-$HOME/.local/share/vladmir/core-env/bin/python}" - "$1" <<'PY'
import sys
from mark.audio import transcribe
from mark.config import load_config
cfg=load_config(); print(transcribe(sys.argv[1], cfg['whisper']['command_model'], cfg))
PY
