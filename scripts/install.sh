#!/usr/bin/env bash
# Install OpenClaw + Tapes inside a stereOS VM.
# Works on macOS, Linux, and NixOS.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== OpenClaw Setup ==="

# ---------------------------------------------------------------------------
# Detect NixOS (stereOS VMs use NixOS)
# ---------------------------------------------------------------------------
IS_NIXOS=false
if [ -f /etc/NIXOS ] || [ -d /nix/store ]; then
    IS_NIXOS=true
    echo "Detected NixOS environment"
fi

# ---------------------------------------------------------------------------
# Fix DNS inside stereOS VMs
# ---------------------------------------------------------------------------
if $IS_NIXOS; then
    if ! nslookup google.com &>/dev/null 2>&1; then
        echo "Fixing DNS..."
        sudo bash -c 'echo "nameserver 8.8.8.8" > /etc/resolv.conf'
    fi
fi

# ---------------------------------------------------------------------------
# Node.js
# ---------------------------------------------------------------------------
if ! command -v node &>/dev/null; then
    if $IS_NIXOS; then
        echo "Installing Node.js via nix..."
        nix profile install nixpkgs#nodejs_22
    else
        echo "ERROR: node not found. Install Node.js 20+ first."
        exit 1
    fi
fi
echo "Node version: $(node --version)"

# ---------------------------------------------------------------------------
# Writable directories (shared mount permissions)
# ---------------------------------------------------------------------------
for dir in output .tapes .openclaw; do
    sudo mkdir -p "$SKILL_DIR/$dir"
    sudo chmod a+rwx "$SKILL_DIR/$dir" 2>/dev/null || true
done

# ---------------------------------------------------------------------------
# OpenClaw
# ---------------------------------------------------------------------------
export PATH="$HOME/.npm-global/bin:$PATH"

if ! command -v openclaw &>/dev/null; then
    echo ""
    echo "Installing OpenClaw..."
    curl -fsSL https://openclaw.ai/install.sh | bash
fi

echo "OpenClaw: $(openclaw --version 2>/dev/null || echo 'installed, PATH needs refresh')"

# ---------------------------------------------------------------------------
# Tapes CLI
# ---------------------------------------------------------------------------
if ! command -v tapes &>/dev/null && [ ! -f /usr/local/bin/tapes ]; then
    echo ""
    echo "Installing Tapes CLI..."
    sudo mkdir -p /usr/local/bin
    curl -fsSL https://download.tapes.dev/install | bash

    if $IS_NIXOS && [ -f /usr/local/bin/tapes ]; then
        INTERP=$(find /nix/store -name "ld-linux-*.so.1" 2>/dev/null | head -1)
        if [ -n "$INTERP" ]; then
            if ! command -v patchelf &>/dev/null; then
                nix profile install nixpkgs#patchelf
            fi
            echo "Patching tapes binary for NixOS..."
            patchelf --set-interpreter "$INTERP" /usr/local/bin/tapes
        fi
    fi
fi

# Initialize Tapes
if [ ! -f "$SKILL_DIR/.tapes/config.toml" ]; then
    echo "Initializing Tapes..."
    cd "$SKILL_DIR" && tapes init --preset anthropic 2>/dev/null \
        || /usr/local/bin/tapes init --preset anthropic 2>/dev/null \
        || echo "Tapes init skipped (install tapes manually if needed)"
fi

echo ""
echo "=== Setup complete ==="
echo "Run 'openclaw onboard' to configure (first time only)"
