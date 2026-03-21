#!/usr/bin/env bash
# Start the GitHub org triage agent inside a stereOS VM.
# Requires: openclaw + tapes + gh installed via install.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

export PATH="$HOME/.npm-global/bin:/usr/local/bin:$PATH"
export LD_LIBRARY_PATH="${HOME}/.nix-profile/lib:${LD_LIBRARY_PATH:-}"
export OPENCLAW_HOME="${SKILL_DIR}/.openclaw"

# Ensure output directory exists
mkdir -p "$SKILL_DIR/output"

# Verify gh CLI is available and authenticated
if ! command -v gh &>/dev/null; then
    echo "ERROR: gh CLI not found. Run install.sh first."
    exit 1
fi

if ! gh auth status &>/dev/null 2>&1; then
    echo "Authenticating gh with GH_TOKEN..."
    gh auth status || echo "WARN: gh auth failed — check GH_TOKEN"
fi

# Tapes proxy (background) — captures all LLM traffic for audit
tapes serve proxy \
    --config-dir "$SKILL_DIR/.tapes" \
    --sqlite "$SKILL_DIR/.tapes/tapes.sqlite" &
sleep 2

# Load the github-org-triage skill and start the gateway
if [ ! -f "$OPENCLAW_HOME/.onboarded" ]; then
    echo "=== First run: run 'openclaw onboard' to configure ==="
    openclaw onboard
    touch "$OPENCLAW_HOME/.onboarded"
else
    echo "=== Starting GitHub org triage agent ==="
    openclaw gateway --skills-dir "$SKILL_DIR/skills" --verbose
fi
