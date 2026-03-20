# claw-stereo

OpenClaw skill template for running agents in stereOS VMs. Provides the full integration pattern: stereos VM config, tapes telemetry, observational memory, and a placeholder agent loop.

## Quickstart

### stereOS (recommended)

```bash
mb up          # boot VM, install deps, start agent
mb attach      # watch the agent
```

### Local

```bash
bash scripts/install.sh
python3 scripts/agent.py . --output output/summary.md
```

## Use as Template

This repo is a starting point for new openclaw skills:

1. Fork or copy this repo
2. Replace `scripts/agent.py` with your agent logic
3. Update `jcard.toml` with your resource needs and secrets
4. Add dependencies to `pyproject.toml` and `scripts/install.sh`
5. Update `SKILL.md` with your skill's metadata and docs

The tapes integration (`tape_reader.py`, `observer.py`, `observe_cli.py`) and stereos setup (`install.sh`, `jcard.toml`) are reusable as-is.

## Testing

```bash
pip install pytest pytest-cov
python3 -m pytest --cov --cov-report=term-missing
```

## Project Structure

See `SKILL.md` for the full file structure and customization guide.
