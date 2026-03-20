# openclaw-in-a-box

Run OpenClaw in a stereOS VM with Tapes telemetry.

## Prerequisites

- [Master Blaster](https://github.com/papercomputeco/masterblaster) (`mb` CLI)
- `ANTHROPIC_API_KEY` exported in your shell (e.g. in `.zshrc`)

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

## Lifecycle

```
mb up          →  VM boots, shared mount at /workspace
mb ssh         →  install.sh (first time) → openclaw onboard (first time)
                                           → openclaw gateway (after onboard)
mb down        →  VM destroyed, secrets gone
mb up + ssh    →  install cached, openclaw config persisted in .openclaw/
```

Config persists on the shared mount (`.openclaw/`).
Secrets live in tmpfs -- destroyed on `mb down`.
Tapes captures the audit trail in `.tapes/`.

## What's Included

| File | Purpose |
|------|---------|
| `jcard.toml` | stereOS VM config (resources, network, secrets) |
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
