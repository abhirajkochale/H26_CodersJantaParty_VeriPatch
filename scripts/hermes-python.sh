#!/usr/bin/env bash
set -euo pipefail
VP_PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export HERMES_HOME="$VP_PROJECT_ROOT/.hermes-runtime/home"
export HERMES_RUNTIME_DIR="$HERMES_HOME/tools"
VP_HERMES_SOURCE="$VP_PROJECT_ROOT/.hermes-runtime/source"
if [[ ! -f "$VP_HERMES_SOURCE/scripts/run-in-hermes-env" ]]; then
  echo 'Official Hermes runtime is not installed. See docs/HERMES_SETUP.md.' >&2
  exit 1
fi
cd "$VP_HERMES_SOURCE"
# Compose the already committed PM environment with Hermes's own helpers.
# A cold dev-launcher otherwise re-runs package resolution on every launch.
source scripts/_activation.sh
VP_ACTIVATION="$(hermes_compose_env "$VP_HERMES_SOURCE" sh)" || exit 1
hermes_apply_env "$VP_ACTIVATION"
if ! hermes_activation_current "$VP_HERMES_SOURCE"; then
  echo 'Hermes dependency inputs changed; run scripts/setup-hermes.sh to sync explicitly.' >&2
  exit 1
fi
exec bash scripts/run-in-hermes-env python "$@"
