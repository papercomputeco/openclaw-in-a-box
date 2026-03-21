# AGENTS.md — rules for AI coding agents working in this repo

## The Rule

**All integration work happens inside the stereOS VM through the OpenClaw gateway.**

Do NOT:
- Run `gog`, `gh`, or other integration CLIs directly from the host or via SSH
- Bypass the OpenClaw gateway to "test" things manually
- Execute triage, labeling, or any Gmail/GitHub/Discord actions outside the VM

Why: stereOS is the security and isolation boundary. Tapes is the audit trail. If you run commands directly, there's no telemetry, no audit log, no isolation. The entire value of this project is that the agent operates inside a sandboxed VM with every action recorded.

The correct flow is always:
```
mb up → mb ssh → install.sh → start.sh → OpenClaw gateway → agent uses skills
```

## Prerequisites

1. **Master Blaster CLI** (`mb`) must be installed and on PATH
2. **ANTHROPIC_API_KEY** must be exported in the shell
3. Integration tokens exported for whichever skills you want:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   export GH_TOKEN="ghp_..."           # for GitHub triage
   export DISCORD_TOKEN="your-token"    # for Discord bot
   ```

## Setup

```bash
# Boot the VM
mb up

# SSH into the VM
mb ssh openclaw-in-a-box

# Install dependencies (first time)
bash /workspace/scripts/install.sh

# Start the agent (tapes proxy + openclaw gateway)
bash /workspace/scripts/start.sh
```

For Gmail: `gog` auth must be set up on the host first (see `quickstart/gmail/README.md`), then exported into the VM via `gog auth tokens export/import`.

## What start.sh does

1. Checks which integrations are available (gog, gh, DISCORD_TOKEN)
2. Starts Tapes proxy in background — captures all LLM traffic to `.tapes/tapes.sqlite`
3. Runs `openclaw onboard --non-interactive --accept-risk --skip-health` on first run
4. Runs `openclaw gateway --skills-dir /workspace/skills --verbose` on subsequent runs

The gateway loads all skills from `skills/` and the agent can invoke them.

## Key paths inside the VM

| Path | What lives there |
|------|-----------------|
| `/workspace/skills/` | Agent skills (gmail-triage, github-org-triage, discord-bot) |
| `/workspace/.openclaw/` | Agent config, persists across restarts |
| `/workspace/.tapes/tapes.sqlite` | Telemetry database — every LLM call logged |
| `/workspace/output/` | Agent work products (INBOX_REPORT.md, etc.) |
| `/workspace/scripts/install.sh` | One-time dependency installer |
| `/workspace/scripts/start.sh` | Entrypoint (tapes proxy + openclaw gateway) |

## Lifecycle

| Command | Effect |
|---------|--------|
| `mb up` | Boot VM, mount workspace, inject secrets via tmpfs |
| `mb ssh openclaw-in-a-box` | SSH into running VM |
| `mb down` | Stop VM. Secrets destroyed from memory. Config persists. |
| `mb destroy openclaw-in-a-box` | Remove VM entirely |

## Security model

- **Network egress is allowlisted** — the VM can only reach Anthropic, Gmail, GitHub, Discord, OpenClaw, and npm. Nothing else.
- **Secrets live in tmpfs** — destroyed when VM stops. Never written to disk.
- **2-hour timeout** — VM auto-destructs if forgotten.
- **Tapes captures everything** — every LLM interaction logged to SQLite for audit.
- **Skills are read-only by default** — gmail-triage never deletes or sends. github-org-triage never merges or closes.
