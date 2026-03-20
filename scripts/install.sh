#!/usr/bin/env bash
# Install dependencies for the OpenClaw skill.
# Works on macOS, Linux, and inside stereOS VMs (NixOS).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== OpenClaw Setup ==="
echo "Skill directory: $SKILL_DIR"

# ---------------------------------------------------------------------------
# Detect NixOS (stereOS VMs use NixOS)
# ---------------------------------------------------------------------------
IS_NIXOS=false
if [ -f /etc/NIXOS ] || [ -d /nix/store ]; then
    IS_NIXOS=true
    echo "Detected NixOS environment"
fi

# ---------------------------------------------------------------------------
# Fix DNS inside stereOS VMs (systemd-resolved stub often broken)
# ---------------------------------------------------------------------------
if $IS_NIXOS; then
    if ! nslookup google.com &>/dev/null 2>&1; then
        echo "Fixing DNS (systemd-resolved not forwarding)..."
        sudo bash -c 'echo "nameserver 8.8.8.8" > /etc/resolv.conf'
    fi
fi

# ---------------------------------------------------------------------------
# Writable directories (shared mount permissions)
# ---------------------------------------------------------------------------
for dir in output .tapes; do
    mkdir -p "$SKILL_DIR/$dir"
    chmod a+rwx "$SKILL_DIR/$dir" 2>/dev/null || true
done

# ---------------------------------------------------------------------------
# OpenClaw
# ---------------------------------------------------------------------------
if ! command -v openclaw &>/dev/null; then
    echo ""
    echo "Installing OpenClaw..."
    curl -fsSL https://openclaw.ai/install.sh | bash
fi

# ---------------------------------------------------------------------------
# Tapes CLI
# ---------------------------------------------------------------------------
if ! command -v tapes &>/dev/null && [ ! -f /usr/local/bin/tapes ]; then
    echo ""
    echo "Installing Tapes CLI..."
    sudo mkdir -p /usr/local/bin
    curl -fsSL https://download.tapes.dev/install | bash

    # NixOS: patch the dynamically linked binary for the nix linker
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

# Verify tapes
if command -v tapes &>/dev/null; then
    tapes version
elif [ -f /usr/local/bin/tapes ]; then
    /usr/local/bin/tapes version
fi

# Initialize Tapes in the project if not already done
if [ ! -f "$SKILL_DIR/.tapes/config.toml" ]; then
    echo "Initializing Tapes..."
    mkdir -p "$SKILL_DIR/.tapes"
    cd "$SKILL_DIR" && tapes init --preset anthropic 2>/dev/null \
        || /usr/local/bin/tapes init --preset anthropic
fi

echo ""
echo "=== Setup complete ==="
