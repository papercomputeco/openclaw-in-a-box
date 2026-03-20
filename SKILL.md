---
name: claw-stereo
description: "Run OpenClaw in a stereOS VM with Tapes telemetry. Onboard once, spin up and down."
version: 0.1.0
metadata:
  { "openclaw": { "emoji": "🔧", "requires": { "bins": [], "env": ["ANTHROPIC_API_KEY"] }, "install": [{ "id": "setup", "kind": "shell", "label": "Run install.sh" }] } }
---

# claw-stereo

Run OpenClaw in a stereOS VM with Tapes telemetry.

## How it works

1. `mb up` boots a stereOS VM and runs `install.sh` (Node.js, OpenClaw, Tapes)
2. `start.sh` checks if OpenClaw is onboarded:
   - **First run:** runs `openclaw onboard` (interactive setup)
   - **After that:** runs `openclaw gateway` (starts the control plane)
3. Config persists in `.openclaw/` on the shared mount across `mb up`/`mb down`
4. Secrets (API keys) live in tmpfs -- destroyed when the VM tears down
5. Tapes captures all LLM interactions in `.tapes/tapes.sqlite`

## Usage

```bash
mb up           # boot + onboard (first time) or start gateway
mb attach       # interact with the agent
mb down         # tear down VM (config persists, secrets destroyed)
```
