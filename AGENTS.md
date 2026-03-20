# AGENTS.md — setup instructions for AI coding agents

## Prerequisites

1. **Master Blaster CLI** (`mb`) must be installed and on PATH
2. **ANTHROPIC_API_KEY** must be exported in the shell:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```
   The VM reads this at boot and injects it via tmpfs. Without it, `mb up` will fail to provide the key to OpenClaw.

## Setup (step by step)

```bash
# 1. Boot the VM
mb up

# 2. SSH into the VM
mb ssh openclaw-in-a-box

# 3. Run install script (first time — installs Node 22, OpenClaw, Tapes)
bash /workspace/scripts/install.sh

# 4. Start OpenClaw
bash /workspace/scripts/start.sh
#    First run: interactive onboard prompt (requires human input)
#    Subsequent runs: starts gateway automatically
```

## Key paths inside the VM

| Path | What lives there |
|------|-----------------|
| `/workspace/` | Shared mount of the host project directory |
| `/workspace/.openclaw/` | Agent config, persists across restarts |
| `/workspace/.tapes/tapes.sqlite` | Telemetry database |
| `/workspace/output/` | Agent work products |
| `/workspace/scripts/install.sh` | One-time dependency installer |
| `/workspace/scripts/start.sh` | Entrypoint (tapes proxy + openclaw gateway) |

## Lifecycle commands

| Command | Effect |
|---------|--------|
| `mb up` | Boot VM, mount workspace, inject secrets |
| `mb ssh openclaw-in-a-box` | SSH into running VM |
| `mb down` | Stop VM. Secrets destroyed, config persists |
| `mb destroy openclaw-in-a-box` | Remove VM entirely |
| `mb status openclaw-in-a-box` | Check if VM is running |

## Important notes

- `openclaw onboard` is interactive and requires human input the first time. Do not attempt to automate it.
- After onboard completes, `.openclaw/.onboarded` is created. Subsequent `start.sh` runs skip onboard and go straight to `openclaw gateway`.
- Secrets live in tmpfs and are destroyed on `mb down`. The `ANTHROPIC_API_KEY` environment variable must be set on the host before each `mb up`.
- Network egress is restricted to: `api.anthropic.com`, `openclaw.ai`, `registry.npmjs.org`.
- Config in `.openclaw/` and telemetry in `.tapes/` survive `mb down`/`mb up` cycles because they live on the shared mount.

## Development (host-side TypeScript)

```bash
npm install
npm run build
npm test
```

The `src/tape-reader.ts` and `src/tape-writer.ts` modules read/write the `.tapes/tapes.sqlite` database from the host side.
