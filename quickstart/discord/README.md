# Discord Bot Setup

Set up Discord access for the openclaw-in-a-box agent. This is a one-time credential setup — the agent runs inside the VM.

## Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and click **New Application**
2. Name your application and click **Create**
3. Go to **Bot** in the left sidebar, click **Reset Token**, and copy the token
4. Under **Privileged Gateway Intents**, enable:
   - **Message Content Intent**
   - **Server Members Intent**
5. Go to **OAuth2 > URL Generator**:
   - Under **Scopes**, select `bot` and `applications.commands`
   - Under **Bot Permissions**, select `Send Messages`, `Read Message History`, and `View Channels`
   - Copy the generated URL and open it to invite the bot to your server

## Export the Token

```bash
export DISCORD_TOKEN="your-bot-token"
```

Add this to your `.zshrc` or `.bashrc` so it's available on each `mb up`.

## Run the Agent

From the repo root:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export DISCORD_TOKEN="your-bot-token"
mb up
mb ssh openclaw-in-a-box
bash /workspace/scripts/install.sh   # first time
bash /workspace/scripts/start.sh
```

Then invoke the bot skill:

```bash
openclaw agent --agent main --message "/discord-bot report"
```

## What the Bot Does

| Capability | What it does |
|------------|-------------|
| Q&A | Answers questions using Claude when mentioned with `@bot` |
| Thread summary | Summarizes long threads on request |
| Activity report | Produces `output/DISCORD_REPORT.md` with channel stats and key discussions |

Never deletes messages, sends DMs, or bans users. Every interaction logged to `.mb/tapes/tapes.sqlite`.

## Skill Reference

The bot logic lives in `skills/discord-bot/SKILL.md` at the repo root. Edit it to customize behavior for your server.

## References

- [Discord Developer Portal](https://discord.com/developers/applications) — create and manage bots
- [Discord Bot Permissions](https://discord.com/developers/docs/topics/permissions) — permission flags
- [stereOS jcard schema](https://stereos.ai/reference/jcard-schema/) — VM configuration
- [Tapes](https://tapes.dev) — agent telemetry
