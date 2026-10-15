#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x app/.venv/bin/python || ! -f frontend/dist/index.html ]]; then
  echo 'Install app/requirements.txt and build frontend first; see README.md.' >&2
  exit 1
fi
exec env PYTHONPATH=app app/.venv/bin/python -m veripatch serve
