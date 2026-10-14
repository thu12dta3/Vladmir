#!/usr/bin/env bash
set -euo pipefail
VLADMIR_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VLADMIR_TEST_DIR="$(mktemp -d -t vladmir-tests-XXXXXXXX)"
trap 'rm -rf -- "$VLADMIR_TEST_DIR"' EXIT
export VLADMIR_KNOWLEDGE_DB="$VLADMIR_TEST_DIR/knowledge.sqlite3"
"${VLADMIR_PYTHON:-$HOME/.local/share/vladmir/core-env/bin/python}" -m unittest discover -s "$VLADMIR_ROOT/tests" -p 'test_*.py' -v
