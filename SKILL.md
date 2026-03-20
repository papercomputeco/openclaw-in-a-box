---
name: claw-stereo
description: "Template openclaw skill for running agents in stereOS VMs. Use as a starting point for building new skills with Tapes telemetry and observational memory."
version: 0.1.0
metadata:
  { "openclaw": { "emoji": "🔧", "requires": { "bins": ["python3"], "env": [] }, "install": [{ "id": "setup", "kind": "shell", "label": "Run install.sh" }] } }
---

# OpenClaw Skill Template

Template for building openclaw skills that run inside stereOS VMs.

## Overview

This skill provides the standard openclaw integration pattern:
- **jcard.toml** defines the VM configuration
- **install.sh** handles NixOS/macOS dependency setup
- **Tapes** captures all LLM API calls as telemetry
- **Observational memory** persists learnings across sessions
- **agent.py** runs the core agent loop (replace with your logic)

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
mb up       # Boot VM, install deps, start agent
mb attach   # Watch the agent work
```

### Run locally

```bash
python3 scripts/agent.py /path/to/directory --output output/summary.md
```

### After a session

```bash
tapes deck                          # Explore telemetry
python3 scripts/observe_cli.py      # Extract observations
cat .tapes/memory/observations.md   # Review observations
```

## File Structure

```
claw-stereo/
├── SKILL.md              # This file
├── jcard.toml            # stereOS VM config
├── .tapes/               # Tapes telemetry (gitignored)
│   └── memory/           # Observational memory
├── scripts/
│   ├── install.sh        # Setup script
│   ├── agent.py          # Agent loop (replace with your logic)
│   ├── tape_reader.py    # Tapes SQLite reader
│   ├── observer.py       # Observation extractor
│   └── observe_cli.py    # Observer CLI
├── references/           # Domain-specific data
├── output/               # Agent output (gitignored)
└── tests/                # Test suite
```

## Customizing

1. Replace `agent.py` with your domain logic
2. Add domain dependencies to `pyproject.toml` and `install.sh`
3. Update `jcard.toml` resource limits and secrets as needed
4. Add reference data to `references/`
5. Update this SKILL.md with your skill's description and usage
