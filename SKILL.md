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

## Combining Integrations

Three quickstart integrations are available — Gmail, GitHub, and Discord. Each can run standalone, but they can also be combined into a single VM for a unified agent that triages your inbox, scans your GitHub org, and responds in Discord.

To set up all three:

1. **Merge secrets** — export all required tokens on the host:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   export GH_TOKEN="ghp_..."
   export DISCORD_TOKEN="your-bot-token"
   ```
2. **Merge `jcard.toml`** — combine the `egress_allow` lists and `[secrets]` blocks from each quickstart into a single `jcard.toml`.
3. **Merge skills** — copy all skill directories into a single `skills/` folder:
   ```
   skills/
   ├── gmail-triage/SKILL.md
   ├── github-org-triage/SKILL.md
   └── discord-bot/SKILL.md
   ```
4. **Update `start.sh`** — validate all tokens and point the gateway at the combined skills directory.

The agent loads all skills at startup and can switch between them based on the channel or command. See each quickstart's README for per-integration setup details:
- [Gmail Triage](quickstart/gmail/)
- [GitHub Org Triage](quickstart/github/)
- [Discord Bot](quickstart/discord/)
