#!/usr/bin/env bash
# Run every check. CI runs exactly this script, so a local pass means a CI pass.
#   Locally:  scripts/check.sh            (uses .venv)
#   In CI:    PYTHON=python scripts/check.sh
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-.venv/bin/python}"
TY_VERSION="0.0.107"

echo "==> pytest"
"$PY" -m pytest -q

echo "==> ty check (type checker)"
uvx "ty@${TY_VERSION}" check --python "$("$PY" -c 'import sys; print(sys.prefix)')" app.py app_pages src

echo "All checks passed."
