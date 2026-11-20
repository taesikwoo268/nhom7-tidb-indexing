#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python_cmd="${PYTHON:-python}"
if [[ -z "${PYTHON:-}" && -x .venv/bin/python ]]; then python_cmd=.venv/bin/python; fi
if [[ -z "${PYTHON:-}" && -f .venv/Scripts/python.exe ]]; then python_cmd=.venv/Scripts/python.exe; fi
exec "$python_cmd" -m bench.cli engine "$@"
