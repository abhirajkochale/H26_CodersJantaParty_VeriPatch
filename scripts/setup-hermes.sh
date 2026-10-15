#!/bin/bash
set -euo pipefail
VP_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VP_SOURCE="$VP_ROOT/.hermes-runtime/source"
VP_COMMIT=db44c46208f1b421b4ecb7e56bf9d68b0423906f
mkdir -p "$VP_ROOT/.hermes-runtime"
if [ ! -d "$VP_SOURCE/.git" ]; then
  git clone https://github.com/NousResearch/hermes-agent.git "$VP_SOURCE"
fi
if [ -n "$(git -C "$VP_SOURCE" status --porcelain)" ]; then
  echo 'Hermes source has local changes; refusing to overwrite.' >&2; exit 1
fi
git -C "$VP_SOURCE" checkout --detach "$VP_COMMIT"
export HERMES_HOME="$VP_ROOT/.hermes-runtime/home"
export HERMES_RUNTIME_DIR="$HERMES_HOME/tools"
mkdir -p "$HERMES_HOME/plugins/veripatch-probe" "$HERMES_HOME/plugins/veripatch-maintenance"
cp "$VP_ROOT/hermes/config.yaml" "$HERMES_HOME/config.yaml"
cp "$VP_ROOT/hermes/probe-plugin/plugin.yaml" "$VP_ROOT/hermes/probe-plugin/__init__.py" "$HERMES_HOME/plugins/veripatch-probe/"
cp "$VP_ROOT/hermes/maintenance-plugin/plugin.yaml" "$VP_ROOT/hermes/maintenance-plugin/__init__.py" "$HERMES_HOME/plugins/veripatch-maintenance/"
# Official PM honors this choice; browser/computer tools are unnecessary.
bash "$VP_SOURCE/scripts/install.sh" --dir "$VP_SOURCE" --hermes-home "$HERMES_HOME" --stage venv --non-interactive
bash "$VP_SOURCE/scripts/install.sh" --dir "$VP_SOURCE" --hermes-home "$HERMES_HOME" --stage python-deps --skip-browser --skip-computer-use --non-interactive
bash "$VP_SOURCE/setup-hermes.sh" --runtime-only --test-environment
"$VP_ROOT/scripts/hermes-python.sh" -c 'from run_agent import AIAgent; from hermes_cli.version_info import get_version_info; print(get_version_info())'
echo 'Hermes is isolated. Check free disk/RAM before downloading the model (docs/HERMES_SETUP.md).'
