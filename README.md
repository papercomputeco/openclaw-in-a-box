# claw-stereo

Run OpenClaw in a stereOS VM with Tapes telemetry.

## Lifecycle

```
mb up       →  install.sh (deps)  →  start.sh  →  openclaw onboard (first run)
                                                →  openclaw gateway  (subsequent runs)
mb down     →  VM destroyed, secrets gone
mb up       →  install.sh (cached) → start.sh  →  openclaw gateway  (config persisted)
```

Onboarding happens once. Config persists on the shared mount (`.openclaw/`).
Secrets live in tmpfs -- destroyed on `mb down`. Tapes captures the audit trail.

## Prerequisites

- [Master Blaster](https://github.com/papercomputeco/masterblaster) (`mb` CLI)
- `ANTHROPIC_API_KEY` exported in your shell (e.g. in `.zshrc`)

## Quickstart

```bash
# First time: boots VM, installs deps, runs openclaw onboard
mb up

# Attach to watch / interact
mb attach

# Tear down (secrets destroyed, config + tapes persist)
mb down

# Next time: boots VM, skips onboard, starts gateway directly
mb up
```

## What's Included

| File | Purpose |
|------|---------|
| `jcard.toml` | stereOS VM config (resources, network, secrets, agent prompt) |
| `scripts/install.sh` | Installs Node.js, OpenClaw, Tapes CLI in the VM |
| `scripts/start.sh` | Onboard-once-then-gateway lifecycle |
| `src/tape-reader.ts` | Read conversation data from `.tapes/tapes.sqlite` |
| `src/tape-writer.ts` | Write conversation nodes to `.tapes/tapes.sqlite` |

## After a session

```bash
tapes deck              # explore telemetry
tapes search "query"    # search session turns
```

## Development

```bash
npm install
npm run build
npm test
```
