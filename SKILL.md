---
name: claw-stereo
description: "OpenClaw setup for running agents in stereOS VMs with Tapes telemetry."
version: 0.1.0
metadata:
  { "openclaw": { "emoji": "🔧", "requires": { "bins": [], "env": [] }, "install": [{ "id": "setup", "kind": "shell", "label": "Run install.sh" }] } }
---

# OpenClaw Tapes Setup

Minimal openclaw configuration for running agents in stereOS VMs with Tapes telemetry.

## Overview

- **jcard.toml** defines the VM configuration
- **install.sh** installs OpenClaw, Tapes, and fixes NixOS quirks
- **src/tape-reader.ts** reads conversation data from `.tapes/tapes.sqlite`
- **src/tape-writer.ts** writes conversation nodes to `.tapes/tapes.sqlite`

## Setup

```bash
cd {baseDir}
bash scripts/install.sh
```

## Usage

### Run in stereOS VM

```bash
mb up       # Boot VM, install openclaw + tapes
mb attach   # Attach to the VM
```

### After a session

```bash
tapes deck              # Explore telemetry
tapes search "query"    # Search session turns
```

## File Structure

```
claw-stereo/
├── SKILL.md              # This file
├── jcard.toml            # stereOS VM config
├── .tapes/               # Tapes telemetry (gitignored)
├── scripts/
│   └── install.sh        # Setup script (openclaw, tapes, permissions)
├── src/
│   ├── index.ts          # Package exports
│   ├── tape-reader.ts    # Tapes SQLite reader
│   └── tape-writer.ts    # Tapes SQLite writer
├── references/           # Domain-specific data
└── tests/                # Test suite
```
