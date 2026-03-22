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
2. **Model provider** configured (choose one):

   **Anthropic (default):**
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

   **Ollama Cloud (no local GPU needed):**
   ```bash
   export MODEL_PROVIDER="ollama"
   export MODEL_NAME="minimax-m2.7:cloud"   # or kimi-k2.5:cloud
   export OLLAMA_API_KEY="..."
   ```

   **Ollama Local:**
   ```bash
   export MODEL_PROVIDER="ollama"
   export MODEL_NAME="llama3.3"
   ```

3. Integration tokens exported for whichever skills you want:
   ```bash
   export GH_TOKEN="ghp_..."           # for GitHub triage
   export DISCORD_TOKEN="your-token"    # for Discord bot
   ```

## Skills

Install the Paper Compute skills (includes tapes, confluent-cloud-setup, dagger-check):

```bash
npx skills add papercomputeco/skills
```

This makes the `tapes` skill available for querying past agent sessions from the local SQLite store at `~/.tapes/`.

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

1. Loads secrets from stereOS tmpfs (`/run/stereos/secrets/`) — requires passwordless sudo
2. Copies skills from `/workspace/skills/` into OpenClaw's internal skill directory
3. Checks which integrations are available (gog, gh, DISCORD_TOKEN)
4. Starts Tapes proxy in background — captures all LLM traffic to `.mb/tapes/tapes.sqlite`
5. Runs `openclaw onboard --non-interactive --accept-risk --skip-health` on first run
6. Runs `openclaw gateway run --verbose`

## Key paths inside the VM

| Path | What lives there |
|------|-----------------|
| `/workspace/skills/` | Agent skills (gmail-triage, github-org-triage, discord-bot) |
| `/workspace/.openclaw/` | Agent config, persists across restarts |
| `/workspace/.mb/tapes/tapes.sqlite` | Agent black box — every LLM call inside the VM |
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
- **Separate black box** — the VM's agent sessions are recorded in `.mb/tapes/tapes.sqlite`, isolated from host-side telemetry. This is the agent's flight recorder.
- **Skills are read-only by default** — gmail-triage never deletes or sends. github-org-triage never merges or closes.
