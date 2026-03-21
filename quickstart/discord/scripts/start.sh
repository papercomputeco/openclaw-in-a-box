#!/usr/bin/env bash
# Start the Discord bot agent inside a stereOS VM.
# Requires: openclaw + tapes (via install.sh)

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
for cmd in tapes openclaw; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "ERROR: $cmd not found. Run install.sh first."
        exit 1
    fi
done

# Validate Discord token is set
if [ -z "${DISCORD_TOKEN:-}" ]; then
    echo "ERROR: DISCORD_TOKEN is not set."
    echo "       Create a bot at https://discord.com/developers/applications"
    echo "       and export DISCORD_TOKEN with your bot token."
    exit 1
fi

# Tapes proxy (background) — captures all LLM traffic for audit
tapes serve proxy \
    --config-dir "$SKILL_DIR/.tapes" \
    --sqlite "$SKILL_DIR/.tapes/tapes.sqlite" &
sleep 2

# Load the discord-bot skill and start the gateway
if [ ! -f "$OPENCLAW_HOME/.onboarded" ]; then
    echo "=== First run: run 'openclaw onboard' to configure ==="
    openclaw onboard
    touch "$OPENCLAW_HOME/.onboarded"
else
    echo "=== Starting Discord bot agent ==="
    openclaw gateway --skills-dir "$SKILL_DIR/skills" --verbose
fi
