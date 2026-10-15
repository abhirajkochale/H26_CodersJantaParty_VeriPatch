#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHONPATH=app app/.venv/bin/python -m pytest app/tests -q
npm run build --prefix frontend
bash -n worker/setup.sh
