#!/usr/bin/env bash
# Start the Gmail triage agent inside a stereOS VM.
# Requires: openclaw + tapes installed via the root install.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

export PATH="$HOME/.npm-global/bin:/usr/local/bin:$PATH"
export LD_LIBRARY_PATH="${HOME}/.nix-profile/lib:${LD_LIBRARY_PATH:-}"
export OPENCLAW_HOME="${SKILL_DIR}/.openclaw"

# Ensure output directory exists
mkdir -p "$SKILL_DIR/output"

# Tapes proxy (background) — captures all LLM traffic for audit
tapes serve proxy \
    --config-dir "$SKILL_DIR/.tapes" \
    --sqlite "$SKILL_DIR/.tapes/tapes.sqlite" &
sleep 2

# Load the gmail-triage skill and start the gateway
if [ ! -f "$OPENCLAW_HOME/.onboarded" ]; then
    echo "=== First run: run 'openclaw onboard' to configure ==="
    openclaw onboard
    touch "$OPENCLAW_HOME/.onboarded"
else
    echo "=== Starting Gmail triage agent ==="
    openclaw gateway --skills-dir "$SKILL_DIR/skills" --verbose
fi
