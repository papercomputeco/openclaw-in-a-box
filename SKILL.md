---
name: openclaw-in-a-box
description: "Orchestrator skill: detects environment, asks user which integrations to enable, drives setup, and hands off to sub-skills."
version: 0.2.0
user-invocable: true
metadata:
  { "openclaw": { "emoji": "🦞", "requires": { "bins": [], "env": ["ANTHROPIC_API_KEY"] } } }
---

# openclaw-in-a-box

You are the setup orchestrator. Your job is to get the user from zero to a running OpenClaw agent inside a secure stereOS VM with Tapes telemetry.

## Step 0: Clone if needed

If the repo isn't already cloned, clone it:

```bash
git clone https://github.com/papercomputeco/openclaw-in-a-box
cd openclaw-in-a-box
```

If already in the repo directory, skip this step.

## Step 1: Detect environment

Run these checks and report a status summary:

```bash
# Host tools
command -v mb    # Master Blaster CLI
echo $ANTHROPIC_API_KEY | head -c 10  # API key present (don't print full key)

# Integration tools
command -v gog   # Gmail bridge
gog auth list    # Gmail account connected
command -v gh    # GitHub CLI
gh auth status   # GitHub authenticated
echo ${DISCORD_TOKEN:+set}  # Discord token present
```

Print a short status table:

```
Environment:
  mb CLI:          ✓ installed
  ANTHROPIC_API_KEY: ✓ set

Integrations:
  Gmail:   ✗ gog CLI not found
  GitHub:  ✓ gh authenticated
  Discord: ✗ DISCORD_TOKEN not set
```

If `mb` is not installed, tell the user to install Master Blaster first: https://github.com/papercomputeco/masterblaster

If `ANTHROPIC_API_KEY` is not set, tell the user to export it: `export ANTHROPIC_API_KEY="sk-ant-..."`

## Step 2: Ask what they want

Ask the user which integrations to enable. Don't assume all three. Present only the ones that aren't already set up:

- **Gmail Triage** — archive newsletters, label receipts, star action items
- **GitHub Org Triage** — flag stale PRs, blocked issues, release risk
- **Discord Bot** — respond to mentions, summarize threads

If everything is already configured, skip to Step 4.

## Step 3: Drive setup for each chosen integration

### Gmail setup

1. Install gog: `brew install steipete/tap/gogcli`
2. Walk user through Google Cloud Console:
   - Create project at console.cloud.google.com/projectcreate
   - Enable Gmail API
   - Configure OAuth consent screen (External, add test user)
   - Create Desktop app OAuth credentials
   - Download `client_secret_*.json`
3. Register credentials: `gog auth credentials ~/Downloads/client_secret_*.json`
4. Authenticate (requires user interaction — opens browser):
   ```bash
   gog auth add USER@gmail.com --services gmail
   ```
5. Verify: `gog auth list` and `gog gmail labels list`

### GitHub setup

1. Install gh if missing: `brew install gh`
2. Authenticate (requires user interaction):
   ```bash
   gh auth login
   ```
   Or if user has a token: `export GH_TOKEN="ghp_..."`
3. Verify: `gh auth status`

### Discord setup

1. Walk user through Discord Developer Portal:
   - Create application at discord.com/developers/applications
   - Create bot, copy token
   - Enable Message Content Intent
   - Generate invite URL with bot + applications.commands scopes
2. Export token: `export DISCORD_TOKEN="..."`
3. Remind user to add the export to their shell profile

## Step 4: Boot and run

Once the chosen integrations are configured:

```bash
cd /path/to/openclaw-in-a-box
mb up
mb ssh openclaw-in-a-box
bash /workspace/scripts/install.sh   # first time
bash /workspace/scripts/start.sh
```

Report which skills loaded and which integrations are active.

## Step 5: Hand off to sub-skills

Once the gateway is running, the user invokes skills directly:

- `/gmail-triage` — triage unread inbox
- `/github-org-triage papercomputeco` — scan an org
- `/discord-bot report` — generate activity report

Each skill has its own rules in `skills/`. You don't need to know their internals — just get the user to the point where they can invoke them.

## Rules

- Never store secrets in files. Tokens go in env vars or system keychains.
- If a setup step requires user interaction (OAuth browser flow, password entry), tell the user to run the command themselves. Don't try to automate password entry.
- If a step fails, diagnose the error and suggest a fix. Don't retry blindly.
- Only set up what the user asked for. Don't push integrations they didn't choose.
