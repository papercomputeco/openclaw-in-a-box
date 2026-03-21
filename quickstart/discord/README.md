# Discord Bot Quickstart

Interactive AI bot for your Discord server. Boot a stereOS VM, let OpenClaw connect to Discord, answer questions and summarize threads, tear it all down. The bot token exists only while the VM runs.

## Prerequisites

- [Master Blaster](https://github.com/papercomputeco/masterblaster) (`mb` CLI)
- `ANTHROPIC_API_KEY` exported in your shell
- `DISCORD_TOKEN` — a Discord bot token

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export DISCORD_TOKEN="your-bot-token"
```

## 1. Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and click **New Application**.
2. Name your application and click **Create**.
3. Go to **Bot** in the left sidebar, click **Reset Token**, and copy the token — this is your `DISCORD_TOKEN`.
4. Under **Privileged Gateway Intents**, enable:
   - **Message Content Intent**
   - **Server Members Intent**
5. Go to **OAuth2 > URL Generator** in the left sidebar:
   - Under **Scopes**, select `bot`
   - Under **Bot Permissions**, select `Send Messages`, `Read Message History`, and `View Channels`
   - Copy the generated URL and open it to invite the bot to your server

## 2. Configure

The included `jcard.toml` declares a `discord-bot` VM with:
- Restricted egress: Discord, Anthropic API, OpenClaw, and npm registry only
- 2-hour timeout (auto-teardown if you forget)
- Token injected via tmpfs (RAM-only, never written to disk)

```toml
[network]
egress_allow = [
  "api.anthropic.com",
  "discord.com",
  "gateway.discord.gg",
  # ...
]

[timeout]
duration = "2h"
```

## 3. Launch

```bash
cd quickstart/discord

# Boot the VM
mb up

# SSH in
mb ssh discord-bot

# Install openclaw + tapes (first time only)
bash /workspace/scripts/install.sh

# Start the agent
bash /workspace/scripts/start.sh
```

On first run, `openclaw onboard` will prompt for interactive setup. It writes the Discord channel configuration to `~/.openclaw/openclaw.json`:

```json
{
  "channels": {
    "discord": {
      "enabled": true,
      "token": "$DISCORD_TOKEN"
    }
  }
}
```

Subsequent runs skip straight to the gateway.

## 4. The Bot Responds

Once connected, the bot appears online in your Discord server. It responds when:
- Mentioned with `@bot` in any channel it can see
- A message is sent in a designated bot channel

| Capability | What it does |
|------------|-------------|
| Q&A | Answers questions using Claude |
| Thread summary | Summarizes long threads on request |
| Activity report | Produces `output/DISCORD_REPORT.md` with channel stats and key discussions |

The bot never deletes messages, sends DMs, or bans users. Every interaction is logged to [Tapes](https://tapes.dev) for a full audit trail.

## 5. Review Results

```bash
# From inside the VM
cat /workspace/output/DISCORD_REPORT.md

# Or from the host after mb down
cat output/DISCORD_REPORT.md
```

## 6. Teardown

```bash
# Stop the VM — bot token destroyed from memory
mb down

# Or remove everything
mb destroy discord-bot
```

The bot token lived in tmpfs and is gone the moment the VM stops. Config persists in `.openclaw/` on the shared mount so you can `mb up` again without re-onboarding.

## Skill Reference

The bot logic lives in `skills/discord-bot/SKILL.md`. It defines:
- Response behavior (when and how to reply)
- Thread summarization rules
- Activity report format
- Safety constraints (no deletes, no DMs, no bans)

Edit the skill to customize the bot's behavior for your server.

## File Layout

```
quickstart/discord/
├── jcard.toml                    # VM config (network, secrets, timeout)
├── scripts/
│   └── start.sh                  # Tapes proxy + openclaw gateway
├── skills/
│   └── discord-bot/
│       └── SKILL.md              # Agent skill: bot behavior + safety
├── output/                       # Agent writes DISCORD_REPORT.md here
└── README.md                     # This file
```

## References

- [Discord Developer Portal](https://discord.com/developers/applications) — create and manage Discord bots
- [Discord Bot Permissions](https://discord.com/developers/docs/topics/permissions) — permission flags reference
- [OpenClaw Skills](https://docs.openclaw.ai/tools/skills) — how skills work, SKILL.md format, loading precedence
- [stereOS jcard schema](https://stereos.ai/reference/jcard-schema/) — VM configuration reference
- [Tapes](https://tapes.dev) — audit trail and telemetry for agent actions
