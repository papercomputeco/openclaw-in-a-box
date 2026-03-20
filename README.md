# claw-stereo

OpenClaw setup for running agents in stereOS VMs with Tapes telemetry.

## Quickstart

### stereOS

```bash
mb up          # boot VM, install openclaw + tapes
mb attach      # attach to the VM
```

### Local

```bash
bash scripts/install.sh
```

## What's Included

- `jcard.toml` -- stereos VM config (opencode-mixtape, claude-code harness)
- `scripts/install.sh` -- NixOS/macOS setup (openclaw, tapes CLI, permissions)
- `src/tape-reader.ts` -- reads conversation data from `.tapes/tapes.sqlite`
- `src/tape-writer.ts` -- writes conversation nodes to `.tapes/tapes.sqlite`

## Use as Template

1. Fork or copy this repo
2. Add your agent logic
3. Update the `[agent] prompt` in `jcard.toml` to run your agent
4. Update `SKILL.md` with your skill's metadata

## Development

```bash
npm install
npm run build
npm test
```
