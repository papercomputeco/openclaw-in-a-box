#!/usr/bin/env bash
# Start openclaw inside the stereOS VM.
# Onboards on first run (interactive), starts gateway on subsequent runs.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

export PATH="$HOME/.npm-global/bin:/usr/local/bin:$PATH"
export LD_LIBRARY_PATH="${HOME}/.nix-profile/lib:${LD_LIBRARY_PATH:-}"
export OPENCLAW_HOME="${SKILL_DIR}/.openclaw"

# Ensure output directory exists
mkdir -p "$SKILL_DIR/output"

# Check which integrations are available (warn, don't fail)
echo "=== Checking integrations ==="

if command -v gog &>/dev/null; then
    echo "  ✓ gog CLI found (Gmail)"
else
    echo "  ○ gog CLI not found — Gmail triage skill unavailable"
fi

if command -v gh &>/dev/null && gh api user &>/dev/null 2>&1; then
    echo "  ✓ gh CLI authenticated (GitHub)"
elif command -v gh &>/dev/null; then
    echo "  ○ gh CLI found but not authenticated — run 'gh auth login'"
else
    echo "  ○ gh CLI not found — GitHub triage skill unavailable"
fi

if [ -n "${DISCORD_TOKEN:-}" ]; then
    echo "  ✓ DISCORD_TOKEN set (Discord)"
else
    echo "  ○ DISCORD_TOKEN not set — Discord bot skill unavailable"
fi

echo ""

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
    openclaw gateway --skills-dir "$SKILL_DIR/skills" --verbose
fi
