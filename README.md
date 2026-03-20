# claw-stereo

OpenClaw setup for running agents in stereOS VMs with Tapes telemetry.

## Quickstart

### stereOS

```bash
mb up          # boot VM, install deps, start tapes proxy
mb attach      # attach to the VM
```

### Local

```bash
bash scripts/install.sh
```

## What's Included

- `jcard.toml` -- stereos VM config (opencode-mixtape, claude-code harness)
- `scripts/install.sh` -- NixOS/macOS setup (python, tapes CLI, permissions)
- `scripts/tape_reader.py` -- stdlib-only reader for `.tapes/tapes.sqlite`
- Tests with 100% coverage

## Use as Template

1. Fork or copy this repo
2. Add your agent script to `scripts/`
3. Update the `[agent] prompt` in `jcard.toml` to run your script
4. Add dependencies to `pyproject.toml` and `scripts/install.sh`
5. Update `SKILL.md` with your skill's metadata

The tapes integration (`tape_reader.py`) and stereos setup (`install.sh`, `jcard.toml`) are reusable as-is.

## Testing

```bash
uv sync --group dev
uv run pytest --cov --cov-report=term-missing
```
