#!/usr/bin/env bash
# Install OpenClaw + Tapes inside a stereOS VM.
# Works on macOS, Linux, and NixOS.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

GOG_VERSION="0.12.0"

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
for dir in output .tapes .openclaw .mb/tapes; do
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

# ---------------------------------------------------------------------------
# gog CLI (Google Workspace bridge — needed for Gmail triage skill)
# ---------------------------------------------------------------------------
if ! command -v gog &>/dev/null; then
    echo ""
    echo "Installing gog CLI..."
    if $IS_NIXOS; then
        # Download pre-built binary
        GOG_ARCH="$(uname -m)"
        case "$GOG_ARCH" in
            aarch64) GOG_ARCH="arm64" ;;
            x86_64)  GOG_ARCH="amd64" ;;
        esac
        curl -fsSL "https://github.com/steipete/gogcli/releases/download/v${GOG_VERSION}/gogcli_${GOG_VERSION}_linux_${GOG_ARCH}.tar.gz" \
            | sudo tar -xz -C /usr/local/bin gog
        sudo chmod +x /usr/local/bin/gog

        # Patch for NixOS dynamic linker
        if [ -f /usr/local/bin/gog ]; then
            INTERP=$(find /nix/store -name "ld-linux-*.so.1" 2>/dev/null | head -1)
            if [ -n "$INTERP" ]; then
                command -v patchelf &>/dev/null || nix profile install nixpkgs#patchelf
                patchelf --set-interpreter "$INTERP" /usr/local/bin/gog 2>/dev/null \
                    && echo "Patched gog binary for NixOS" \
                    || echo "gog is statically linked (no patching needed)"
            fi
        fi
    elif command -v brew &>/dev/null; then
        brew install steipete/tap/gogcli
    else
        echo "WARN: Could not install gog. Install manually for Gmail triage."
    fi
fi

if command -v gog &>/dev/null; then
    echo "gog: $(gog --version 2>/dev/null || echo 'installed')"
fi

# Initialize Tapes with the correct provider preset
TAPES_PRESET="${MODEL_PROVIDER:-anthropic}"
if [ ! -f "$SKILL_DIR/.tapes/config.toml" ]; then
    echo "Initializing Tapes (preset: $TAPES_PRESET)..."
    cd "$SKILL_DIR" && tapes init --preset "$TAPES_PRESET" 2>/dev/null \
        || /usr/local/bin/tapes init --preset "$TAPES_PRESET" 2>/dev/null \
        || echo "Tapes init skipped (install tapes manually if needed)"
fi

echo ""
echo "=== Setup complete ==="
echo "Run 'openclaw onboard' to configure (first time only)"
