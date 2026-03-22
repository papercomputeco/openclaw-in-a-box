# openclaw-in-a-box

Run OpenClaw in a [stereOS](https://stereos.ai) VM with [Tapes](https://tapes.dev) telemetry.

## Get Started

Paste this into Claude Code, OpenCode, or any coding harness:

```
Set up openclaw-in-a-box from https://github.com/papercomputeco/openclaw-in-a-box — clone the repo and follow SKILL.md to get me running with a secure OpenClaw setup.
```

The agent clones the repo, checks your environment, asks which integrations you want, and walks you through setup.

<details>
<summary>Manual setup</summary>

Prerequisites: [Master Blaster](https://github.com/papercomputeco/masterblaster) (`mb` CLI) and `ANTHROPIC_API_KEY` exported.

```bash
git clone https://github.com/papercomputeco/openclaw-in-a-box
cd openclaw-in-a-box
export ANTHROPIC_API_KEY="sk-ant-..."
mb up
mb ssh openclaw-in-a-box
bash /workspace/scripts/install.sh   # first time
bash /workspace/scripts/start.sh
```
</details>

## Integrations

The VM comes pre-configured for three integrations. Set up whichever ones you need -- the agent loads all available skills at startup.

| Integration | Setup Guide | What It Does |
|-------------|-------------|--------------|
| [Gmail Triage](quickstart/gmail/) | Google OAuth + `gog` CLI | Archive newsletters, label receipts, flag action items |
| [GitHub Org Triage](quickstart/github/) | `GH_TOKEN` + `gh` CLI | Flag stale PRs, blocked issues, release risk |
| [Discord Bot](quickstart/discord/) | `DISCORD_TOKEN` | Respond to mentions, summarize threads |

Each guide walks through the one-time credential setup for that integration. Export the tokens before `mb up`:

```bash
# Model provider (pick one)
export ANTHROPIC_API_KEY="sk-ant-..."     # default: Anthropic
# --- OR ---
export MODEL_PROVIDER="ollama"
export MODEL_NAME="minimax-m2.7:cloud"
export OLLAMA_API_KEY="..."

# Integrations (optional)
export GH_TOKEN="ghp_..."
export DISCORD_TOKEN="your-token"
```

## Model Providers

By default the agent uses Claude via Anthropic. You can switch to Ollama-hosted models (cloud or local) by setting environment variables before `mb up`.

| Provider | Env Vars | Notes |
|----------|----------|-------|
| Anthropic (default) | `ANTHROPIC_API_KEY` | Claude models |
| Ollama Cloud | `MODEL_PROVIDER=ollama` `MODEL_NAME=minimax-m2.7:cloud` `OLLAMA_API_KEY` | No local GPU needed |
| Ollama Local | `MODEL_PROVIDER=ollama` `MODEL_NAME=llama3.3` | Requires Ollama + pulled model on host |

### Ollama Cloud example

```bash
export MODEL_PROVIDER="ollama"
export MODEL_NAME="kimi-k2.5:cloud"
export OLLAMA_API_KEY="..."    # from ollama.com/settings
mb up
```

Cloud models for agentic work: `minimax-m2.7:cloud`, `kimi-k2.5:cloud`, `minimax-m2.5:cloud`.

## Commands

| Command | What it does |
|---------|-------------|
| `mb up` | Boot the VM, mount `./` at `/workspace`, inject secrets via tmpfs |
| `mb ssh openclaw-in-a-box` | SSH into the running VM |
| `mb down` | Stop the VM. Secrets destroyed, config + tapes persist on host |
| `mb destroy openclaw-in-a-box` | Remove the VM and all its resources |
| `mb status openclaw-in-a-box` | Check if the VM is running |

## Lifecycle

```
mb up          →  VM boots, shared mount at /workspace
mb ssh         →  install.sh (first time) → start.sh
                                           → openclaw onboard (first time)
                                           → openclaw gateway (after onboard)
mb down        →  VM stopped, secrets gone, config persisted
mb up + ssh    →  install cached, skip onboard, start gateway
mb destroy     →  VM removed entirely
```

- **Config** persists on the shared mount (`.openclaw/`) across `mb down`/`mb up` cycles
- **Secrets** live in tmpfs -- destroyed on `mb down`
- **Tapes** captures the agent's black box in `.mb/tapes/`

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  HOST                                                        │
│                                                              │
│  $ mb up / ssh / down / destroy                              │
│       │                                                      │
│       │  reads jcard.toml                                    │
│       │  injects secrets via tmpfs                           │
│       │  mounts ./ → /workspace                              │
│       ▼                                                      │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  stereOS VM  (NixOS · 2 CPU · 4 GiB · 2h timeout)     │  │
│  │                                                        │  │
│  │  install.sh ──► Node 22 + OpenClaw CLI + Tapes CLI     │  │
│  │                                                        │  │
│  │  start.sh ──┬──► tapes serve proxy  (background)       │  │
│  │             │       ▲                                   │  │
│  │             │       │  intercepts LLM traffic           │  │
│  │             │       ▼                                   │  │
│  │             └──► openclaw gateway ◄──► LLM API       │  │
│  │                    (Anthropic or Ollama)               │  │
│  │                       │                                 │  │
│  │                       ├──► gog    ◄──► Gmail API        │  │
│  │                       ├──► gh     ◄──► GitHub API       │  │
│  │                       └──► discord ◄──► Discord API     │  │
│  │                                                        │  │
│  │  skills/gmail-triage/    SKILL.md                       │  │
│  │  skills/github-org-triage/ SKILL.md                     │  │
│  │  skills/discord-bot/     SKILL.md                       │  │
│  └────────────────────────────────────────────────────────┘  │
│       │                                                      │
│       │  shared mount (persists across mb down/up)           │
│       ▼                                                      │
│  .openclaw/              agent config + .onboarded marker     │
│  .mb/tapes/tapes.sqlite  agent black box (VM telemetry)      │
│  output/                 agent work products                 │
└──────────────────────────────────────────────────────────────┘
```

## What's Included

| File | Purpose |
|------|---------|
| [`jcard.toml`](https://stereos.ai/reference/jcard-schema/) | stereOS VM config (resources, network, secrets) |
| `scripts/install.sh` | Installs Node.js, OpenClaw, Tapes CLI in the VM |
| `scripts/start.sh` | Starts tapes proxy + openclaw gateway with all skills |
| `skills/` | Agent skills for Gmail, GitHub, and Discord integrations |
| `quickstart/` | Per-integration credential setup guides |

## Development

```bash
npm install
npm run build
npm test
```
