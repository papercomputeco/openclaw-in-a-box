#!/usr/bin/env bash
# Start openclaw inside the stereOS VM.
# Onboards on first run, starts the gateway on subsequent runs.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

# ---------------------------------------------------------------------------
# OpenClaw config lives on the shared mount so it persists across mb up/down
# ---------------------------------------------------------------------------
export OPENCLAW_HOME="${SKILL_DIR}/.openclaw"
mkdir -p "$OPENCLAW_HOME"
chmod a+rwx "$OPENCLAW_HOME" 2>/dev/null || true

# ---------------------------------------------------------------------------
# Tapes proxy (background) — captures all LLM API calls
# ---------------------------------------------------------------------------
export PATH="/usr/local/bin:$PATH"
export LD_LIBRARY_PATH="${HOME}/.nix-profile/lib:${LD_LIBRARY_PATH:-}"

tapes serve proxy \
    --config-dir /workspace/.tapes \
    --sqlite /workspace/.tapes/tapes.sqlite &
sleep 2

# ---------------------------------------------------------------------------
# Onboard once, then gateway on subsequent runs
# ---------------------------------------------------------------------------
if [ ! -f "$OPENCLAW_HOME/.onboarded" ]; then
    echo "=== First run: onboarding openclaw ==="
    openclaw onboard
    touch "$OPENCLAW_HOME/.onboarded"
else
    echo "=== Starting openclaw gateway ==="
    openclaw gateway --verbose
fi
