---
name: claw-stereo
description: "OpenClaw setup for running agents in stereOS VMs with Tapes telemetry."
version: 0.1.0
metadata:
  { "openclaw": { "emoji": "🔧", "requires": { "bins": ["python3"], "env": [] }, "install": [{ "id": "setup", "kind": "shell", "label": "Run install.sh" }] } }
---

# OpenClaw Tapes Setup

Minimal openclaw configuration for running agents in stereOS VMs with Tapes telemetry.

## Overview

- **jcard.toml** defines the VM configuration
- **install.sh** handles NixOS/macOS dependency setup and Tapes installation
- **tape_reader.py** reads conversation data from `.tapes/tapes.sqlite`

## Requirements

- Python 3.11+
- stereOS VM (via Master Blaster) or local environment

## Setup

```bash
cd {baseDir}
bash scripts/install.sh
```

## Usage

### Run in stereOS VM

```bash
mb up       # Boot VM, install deps, start tapes proxy
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
│   ├── install.sh        # Setup script (python, tapes, permissions)
│   └── tape_reader.py    # Tapes SQLite reader (stdlib only)
├── references/           # Domain-specific data
└── tests/                # Test suite
```

## Customizing

1. Add your agent script to `scripts/` and update `jcard.toml` agent prompt
2. Add dependencies to `pyproject.toml` and `install.sh`
3. Update `jcard.toml` resource limits and secrets as needed
4. Update this SKILL.md with your skill's description
