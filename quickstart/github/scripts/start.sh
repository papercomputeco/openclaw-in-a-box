#!/usr/bin/env bash
# Start the GitHub org triage agent inside a stereOS VM.
# Requires: openclaw + tapes (via install.sh) and gh CLI (preinstalled in mixtape image)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

export PATH="$HOME/.npm-global/bin:/usr/local/bin:$PATH"
export LD_LIBRARY_PATH="${HOME}/.nix-profile/lib:${LD_LIBRARY_PATH:-}"
export OPENCLAW_HOME="${SKILL_DIR}/.openclaw"

# Ensure required directories exist
mkdir -p "$OPENCLAW_HOME"
mkdir -p "$SKILL_DIR/output"

# Verify required CLIs are available
for cmd in gh tapes openclaw; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "ERROR: $cmd not found. Run install.sh first."
        exit 1
    fi
done

# Validate GitHub authentication
if [ -n "${GH_TOKEN:-}" ]; then
    echo "Validating GH_TOKEN via GitHub API..."
    if ! gh api user &>/dev/null 2>&1; then
        echo "ERROR: GH_TOKEN appears invalid or lacks required permissions."
        exit 1
    fi
else
    echo "ERROR: gh CLI is not authenticated and GH_TOKEN is not set."
    echo "       Run 'gh auth login' or set GH_TOKEN with appropriate scopes."
    exit 1
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
