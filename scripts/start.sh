#!/usr/bin/env bash
# Start openclaw inside the stereOS VM.
# Onboards on first run (interactive), starts gateway on subsequent runs.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

export PATH="$HOME/.npm-global/bin:/usr/local/bin:$PATH"
export LD_LIBRARY_PATH="${HOME}/.nix-profile/lib:${LD_LIBRARY_PATH:-}"
export OPENCLAW_HOME="${SKILL_DIR}/.openclaw"

# Tapes proxy (background)
tapes serve proxy \
    --config-dir "$SKILL_DIR/.tapes" \
    --sqlite "$SKILL_DIR/.tapes/tapes.sqlite" &
sleep 2

# Onboard once, then gateway
if [ ! -f "$OPENCLAW_HOME/.onboarded" ]; then
    echo "=== First run: run 'openclaw onboard' to configure ==="
    openclaw onboard
    touch "$OPENCLAW_HOME/.onboarded"
else
    echo "=== Starting openclaw gateway ==="
    openclaw gateway --verbose
fi
