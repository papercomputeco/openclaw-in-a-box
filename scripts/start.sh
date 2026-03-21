#!/usr/bin/env bash
# Start openclaw inside the stereOS VM.
# Loads secrets from stereOS tmpfs, starts Tapes proxy, runs the gateway.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

export PATH="$HOME/.npm-global/bin:/usr/local/bin:$PATH"
export LD_LIBRARY_PATH="${HOME}/.nix-profile/lib:${LD_LIBRARY_PATH:-}"
export OPENCLAW_HOME="${SKILL_DIR}/.openclaw"

# ---------------------------------------------------------------------------
# Load secrets from stereOS tmpfs (/run/stereos/secrets/)
# Requires passwordless sudo (default in stereOS VMs).
# Empty secret files (token not exported on host) are skipped.
# ---------------------------------------------------------------------------
SECRETS_DIR="/run/stereos/secrets"
if [ -d "$SECRETS_DIR" ]; then
    for secret_file in "$SECRETS_DIR"/*; do
        key="$(basename "$secret_file")"
        val="$(sudo cat "$secret_file" 2>/dev/null || true)"
        if [ -n "$val" ]; then
            export "$key"="$val"
        fi
    done
fi

# Ensure output directory exists
mkdir -p "$SKILL_DIR/output"

# ---------------------------------------------------------------------------
# Copy skills into openclaw's skill directory (if not already there)
# ---------------------------------------------------------------------------
OPENCLAW_SKILLS="/home/admin/.npm-global/lib/node_modules/openclaw/skills"
if [ -d "$SKILL_DIR/skills" ] && [ -d "$OPENCLAW_SKILLS" ]; then
    for skill_dir in "$SKILL_DIR/skills"/*/; do
        skill_name="$(basename "$skill_dir")"
        if [ ! -d "$OPENCLAW_SKILLS/$skill_name" ]; then
            cp -r "$skill_dir" "$OPENCLAW_SKILLS/$skill_name"
        fi
    done
fi

# ---------------------------------------------------------------------------
# Check which integrations are available
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Tapes proxy (background) — the agent's black box recorder
# ---------------------------------------------------------------------------
# Writes to .mb/tapes/, not .tapes/. The host's .tapes/ is for the user's
# coding sessions. The VM's black box is MB-managed data.
# See: https://papercompute.com/blog/agents-need-black-box-recorders/
VM_TAPES_DIR="$SKILL_DIR/.mb/tapes"
mkdir -p "$VM_TAPES_DIR"

tapes serve proxy \
    --config-dir "$VM_TAPES_DIR" \
    --sqlite "$VM_TAPES_DIR/tapes.sqlite" &
sleep 2

# ---------------------------------------------------------------------------
# Onboard once, then start gateway
# ---------------------------------------------------------------------------
if [ ! -f "$OPENCLAW_HOME/.onboarded" ]; then
    echo "=== First run: onboarding openclaw ==="
    openclaw onboard --non-interactive --accept-risk --skip-health
    touch "$OPENCLAW_HOME/.onboarded"
fi

echo "=== Starting openclaw gateway ==="
openclaw gateway run --verbose
