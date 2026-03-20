---
name: openclaw-in-a-box
description: "Run OpenClaw in a stereOS VM with Tapes telemetry. Onboard once, spin up and down."
version: 0.1.0
metadata:
  { "openclaw": { "emoji": "🔧", "requires": { "bins": [], "env": ["ANTHROPIC_API_KEY"] }, "install": [{ "id": "setup", "kind": "shell", "label": "Run install.sh" }] } }
---

# openclaw-in-a-box

Run OpenClaw in a stereOS VM with Tapes telemetry.

## Required

`ANTHROPIC_API_KEY` must be exported on the host before `mb up`:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```
The VM injects this via tmpfs at boot. Without it, OpenClaw cannot reach the Anthropic API.

## How it works

1. `mb up` boots a stereOS VM and mounts `./` at `/workspace`
2. `install.sh` installs Node.js 22, OpenClaw CLI, and Tapes CLI (first time only)
3. `start.sh` starts the Tapes proxy, then checks if OpenClaw is onboarded:
   - **First run:** runs `openclaw onboard` (interactive, requires human input)
   - **After that:** runs `openclaw gateway` (starts the control plane)
4. Config persists in `.openclaw/` on the shared mount across `mb up`/`mb down`
5. Secrets (API keys) live in tmpfs -- destroyed when the VM tears down
6. Tapes captures all LLM interactions in `.tapes/tapes.sqlite`

## Usage

```bash
mb up           # boot + onboard (first time) or start gateway
mb attach       # interact with the agent
mb down         # tear down VM (config persists, secrets destroyed)
```
