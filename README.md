# openclaw-in-a-box

Run OpenClaw in a [stereOS](https://stereos.ai) VM with [Tapes](https://tapes.dev) telemetry.

## Prerequisites

- [Master Blaster](https://github.com/papercomputeco/masterblaster) (`mb` CLI)
- `ANTHROPIC_API_KEY` exported in your shell — the VM injects it via tmpfs at boot:
  ```bash
  export ANTHROPIC_API_KEY="sk-ant-..."
  ```
  Add this to your `.zshrc` or `.bashrc` so it's always available.

## Quickstart

```bash
# Boot the VM
mb up

# SSH in
mb ssh openclaw-in-a-box

# Install openclaw + tapes (first time)
bash /workspace/scripts/install.sh

# Onboard openclaw (first time, interactive)
export PATH="$HOME/.npm-global/bin:$PATH"
openclaw onboard

# Subsequent runs: start the gateway directly
bash /workspace/scripts/start.sh
```

## Quickstart Guides

| Guide | Description |
|-------|-------------|
| [Gmail Triage](quickstart/gmail/) | Sunday inbox cleanup with an ephemeral Gmail agent |
| [GitHub Org Triage](quickstart/github/) | Daily org sheriff that flags stale PRs, blocked issues, and release risk |
| [Discord Bot](quickstart/discord/) | Interactive AI bot for your Discord server |

Each guide includes its own `jcard.toml`, OpenClaw skills, and scripts. See the guide README for setup instructions.

Want all three in one VM? Merge the `egress_allow` lists and `[secrets]` blocks into a single `jcard.toml`, drop all skill folders into one `skills/` directory, and export every token before `mb up`. The gateway loads all skills at startup and switches between them based on channel or command. See the [Combining Integrations](SKILL.md#combining-integrations) section for details.

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
mb ssh         →  install.sh (first time) → openclaw onboard (first time)
                                           → openclaw gateway (after onboard)
mb down        →  VM stopped, secrets gone, config persisted
mb up + ssh    →  install cached, skip onboard, start gateway
mb destroy     →  VM removed entirely
```

- **Config** persists on the shared mount (`.openclaw/`) across `mb down`/`mb up` cycles
- **Secrets** live in tmpfs -- destroyed on `mb down`
- **Tapes** captures the audit trail in `.tapes/`

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  HOST                                                        │
│                                                              │
│  $ mb up / ssh / down / destroy                              │
│       │                                                      │
│       │  reads jcard.toml                                    │
│       │  injects ANTHROPIC_API_KEY via tmpfs                 │
│       │  mounts ./ → /workspace                              │
│       ▼                                                      │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  stereOS VM  (NixOS · 2 CPU · 4 GiB)                  │  │
│  │                                                        │  │
│  │  install.sh ──► Node 22 + OpenClaw CLI + Tapes CLI     │  │
│  │                                                        │  │
│  │  start.sh ──┬──► tapes serve proxy  (background)       │  │
│  │             │       ▲                                   │  │
│  │             │       │  intercepts LLM traffic           │  │
│  │             │       ▼                                   │  │
│  │             └──► openclaw gateway ◄──► api.anthropic.com│  │
│  │                                                        │  │
│  │  egress: api.anthropic.com, openclaw.ai, npmjs.org     │  │
│  └────────────────────────────────────────────────────────┘  │
│       │                                                      │
│       │  shared mount (persists across mb down/up)           │
│       ▼                                                      │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  .openclaw/          agent config + .onboarded marker  │  │
│  │  .tapes/tapes.sqlite telemetry (TapeReader/TapeWriter) │  │
│  │  output/             agent work products               │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## What's Included

| File | Purpose |
|------|---------|
| [`jcard.toml`](https://stereos.ai/reference/jcard-schema/) | stereOS VM config (resources, network, secrets) |
| `scripts/install.sh` | Installs Node.js, OpenClaw, Tapes CLI in the VM |
| `scripts/start.sh` | Starts tapes proxy + openclaw gateway |
| `src/tape-reader.ts` | Read conversation data from `.tapes/tapes.sqlite` |
| `src/tape-writer.ts` | Write conversation nodes to `.tapes/tapes.sqlite` |

## Development

```bash
npm install
npm run build
npm test
```
