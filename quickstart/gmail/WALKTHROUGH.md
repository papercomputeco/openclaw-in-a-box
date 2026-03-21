# Ship a Secure OpenClaw Setup in Minutes

In February 2026, Meta's director of AI alignment gave an OpenClaw agent access to her Gmail inbox. The agent speedran deleting over 200 emails while ignoring her commands to stop. She had to physically run to her Mac to kill the process. The root cause: context window compaction dropped the safety constraint that said "ask before acting."

This wasn't a failure of OpenClaw. It was a failure of how the agent was deployed. No network boundary. No kill switch beyond physically reaching the machine. No flight recorder to replay what the agent saw, what it decided, and why it ignored the stop command.

This project exists to make that scenario impossible.

*This walkthrough was generated from Tapes session recordings. Every command, error, and decision described here comes from replaying the actual agent sessions captured in `.mb/tapes/tapes.sqlite` during development. That's the point: when you have the recordings, writing accurate technical content is just reading the tape.*

## What stereOS Gives You

**stereOS** is the runtime that keeps the agent in a box. It's an ephemeral VM platform built for exactly this problem:

- **Network egress allowlist.** The agent can only reach the APIs you explicitly permit. Gmail, Anthropic, npm. Nothing else. If the agent tries to `curl` somewhere unexpected, the network layer blocks it. This isn't application-level filtering. It's at the VM's network stack.
- **Secrets in tmpfs.** API keys are injected into RAM-backed storage at boot. They're never written to disk. The moment the VM stops, they're gone. No `.env` files sitting on a server.
- **Auto-teardown timeout.** The VM self-destructs after 2 hours. If you walk away, credentials don't linger. The agent doesn't keep running overnight.
- **Declarative config.** One `jcard.toml` file defines the entire sandbox: resources, network policy, secrets, timeout. Reproducible, auditable, version-controlled.

Without stereOS, you're running an agent with full network access and persistent credentials. That's how emails get deleted.

## What Tapes Gives You

**Tapes** is the flight recorder. It sits between the agent and the LLM API as a transparent proxy, capturing every request and response to SQLite.

When the Meta incident happened, there was no way to replay the agent's reasoning. Why did it start deleting? What did the compacted context look like? At what point did it lose the safety constraint? Without a recording, all you have is the outcome: 200 emails gone.

With Tapes, you get:

- **Every LLM call logged.** The full prompt, the full response, token counts, timestamps. Content-addressed with hash chains so the sequence is tamper-evident.
- **Isolated black box.** The agent's recordings live in `.mb/tapes/tapes.sqlite`, separate from any host-side telemetry. You can hand this file to an auditor, replay it for debugging, or aggregate sessions for self-learning.
- **Replay any decision.** Walk the hash chain to see: the agent received this email list, it classified this message as a newsletter, it decided to archive. If something goes wrong, you know exactly where and why.
- **Cost tracking.** Sum `prompt_tokens` and `completion_tokens` across sessions to measure what agent autonomy actually costs.

Over time, these recordings become training data. Analyze 100 triage sessions to find where the skill definition falls short. Which email categories does the agent struggle with? Which prompts produce better classification? The black box isn't just for compliance. It's how agents get better.

Tapes also makes iterating on content and updates much easier. When you have recordings of what the agent actually did, writing documentation, blog posts, and changelogs becomes trivial because you have the complete source of truth. You're not reconstructing from memory or guessing at what happened three days ago. You're reading the tape. Every prompt, every response, every decision is right there in the SQLite database, so your technical writing is grounded in exactly what occurred rather than a rough approximation of it.

(See [Agents Need Black Box Recorders](https://papercompute.com/blog/agents-need-black-box-recorders/) for the full argument.)

## OpenClaw in the Box

**OpenClaw** is the agent framework. It's powerful: Markdown-driven skills, a WebSocket gateway, Claude-powered reasoning. But power without guardrails is how inboxes get deleted.

openclaw-in-a-box is the reference implementation for running OpenClaw responsibly:

- **stereOS** provides the sandbox: network boundaries, ephemeral credentials, auto-teardown
- **Tapes** provides the flight recorder: every decision logged, replayable, auditable
- **OpenClaw** provides the agent: skill-driven, extensible, Claude-powered

The result: you know exactly what the agent can reach, exactly what it decided, and the whole thing self-destructs when you're done.

## The Stack

- **OpenClaw.** Agent framework. Loads skills from Markdown, runs a gateway, dispatches to Claude.
- **stereOS.** Ephemeral VM runtime. Network sandboxing, tmpfs secrets, auto-teardown.
- **Tapes.** Telemetry proxy. Every LLM call recorded to SQLite with hash chains.
- **gog.** CLI bridge for Google Workspace. OAuth, keychain storage, Gmail access.

## Prerequisites

Two things before starting:

1. **Master Blaster CLI** (`mb`). Manages the VM lifecycle.
2. **Anthropic API key.** Exported as `ANTHROPIC_API_KEY`.

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Step 1: Clone and Boot

```bash
git clone https://github.com/papercomputeco/openclaw-in-a-box
cd openclaw-in-a-box
mb up
```

`mb up` reads `jcard.toml` and boots a stereOS VM:

```toml
mixtape = "opencode-mixtape:latest"
name = "openclaw-in-a-box"

[resources]
cpus   = 2
memory = "4GiB"
disk   = "20GiB"

[network]
mode = "nat"
egress_allow = [
  "api.anthropic.com", "openclaw.ai", "registry.npmjs.org",
  "gmail.googleapis.com", "oauth2.googleapis.com",
  "accounts.google.com", "www.googleapis.com",
  "api.github.com", "github.com",
  "discord.com", "gateway.discord.gg", "cdn.discordapp.com",
]

[timeout]
duration = "2h"

[secrets]
ANTHROPIC_API_KEY = "${ANTHROPIC_API_KEY}"
GH_TOKEN = "${GH_TOKEN}"
DISCORD_TOKEN = "${DISCORD_TOKEN}"
```

The egress allowlist covers all three integrations (Gmail, GitHub, Discord). Secrets are read from your shell environment and injected into `/run/stereos/secrets/` on a tmpfs mount inside the VM.

## Step 2: Install Dependencies

```bash
mb ssh openclaw-in-a-box
bash /workspace/scripts/install.sh
```

The install script detects it's running on NixOS (stereOS uses NixOS) and installs:

1. **Node.js 22** via `nix profile install`
2. **OpenClaw CLI** via `curl -fsSL https://openclaw.ai/install.sh | bash`
3. **Tapes CLI** via `curl -fsSL https://download.tapes.dev/install | bash` (patched for NixOS dynamic linker)
4. **gog CLI** downloaded from GitHub releases, statically linked so no NixOS patching needed

It also creates writable directories: `output/`, `.tapes/`, `.openclaw/`.

## Step 3: Set Up Gmail OAuth (One-Time, On the Host)

The agent needs OAuth credentials to access Gmail. This setup happens on the host machine, not inside the VM.

### Create a Google Cloud Project

Navigate to [console.cloud.google.com/projectcreate](https://console.cloud.google.com/projectcreate). We named ours `gmail-triage`.

### Enable the Gmail API

Navigate to the Gmail API library page for your project and click **Enable**.

### Configure OAuth Consent Screen

In Google Auth Platform, click **Get started** and walk through:

1. **App Information.** Name: `gmail-triage`, support email: your Gmail.
2. **Audience.** Select **External** (required for personal Gmail accounts). The app starts in Testing mode.
3. **Contact Information.** Your email.
4. **Finish.** Agree to the User Data Policy.

### Add Yourself as a Test User

Navigate to **Audience** and click **+ Add users**. Add your Gmail address. Without this, the OAuth flow will fail with access denied because the app is in Testing mode and only explicitly added test users can authorize it.

### Create Desktop App Credentials

Navigate to **Clients**, click **+ Create client**:

- **Application type:** Desktop app
- **Name:** Desktop client 1

Click **Create**. A dialog appears with the Client ID and a **Download JSON** button.

**Gotcha we hit:** Google's newer Auth Platform UI no longer lets you view or download client secrets after the initial dialog. If you miss the download, go to the client's detail page, click the info icon, and use **+ Add secret** to create a new one. The new secret has a download icon next to it.

### Register Credentials with gog

```bash
brew install steipete/tap/gogcli

# Register the OAuth client
gog auth credentials ~/Downloads/client_secret_*.json

# Authenticate your Gmail account (opens browser)
gog auth add you@gmail.com --services gmail

# Verify
gog auth list
export GOG_ACCOUNT=you@gmail.com
gog gmail labels list
```

The refresh token is stored in your system keychain.

### Export Auth Into the VM

The VM doesn't have access to your host keychain. Export the token and import it inside the VM:

```bash
# On the host
gog auth tokens export you@gmail.com --out /tmp/gog-token.json
cp ~/Downloads/client_secret_*.json /tmp/gog-creds.json
chmod 644 /tmp/gog-token.json /tmp/gog-creds.json
# Copy to shared mount
cp /tmp/gog-token.json /tmp/gog-creds.json /path/to/openclaw-in-a-box/

# Inside the VM
export GOG_KEYRING_PASSWORD="openclaw"
gog auth credentials /workspace/gog-creds.json
gog auth tokens import /workspace/gog-token.json

# Clean up from shared mount
rm /workspace/gog-token.json /workspace/gog-creds.json
```

The `GOG_KEYRING_PASSWORD` is needed because the VM has no GUI keychain. gog falls back to a file-based keyring encrypted with this password.

## Step 4: Start the Agent

```bash
bash /workspace/scripts/start.sh
```

Here's what `start.sh` does in order:

1. **Loads secrets from tmpfs.** Reads every file in `/run/stereos/secrets/` and exports them as environment variables.
2. **Copies skills.** Copies `skills/gmail-triage/`, `skills/github-org-triage/`, and `skills/discord-bot/` into OpenClaw's skill directory.
3. **Checks integrations.** Reports which CLIs and tokens are available:
   ```
   === Checking integrations ===
     ✓ gog CLI found (Gmail)
     ○ gh CLI not found — GitHub triage skill unavailable
     ○ DISCORD_TOKEN not set — Discord bot skill unavailable
   ```
4. **Starts Tapes proxy.** Background process on port 8080 that intercepts all Anthropic API calls. Writes to `.mb/tapes/tapes.sqlite`, a dedicated black box recorder for the agent, completely separate from any host-side telemetry. This separation is critical: the agent's decision log should never be mixed with the user's coding sessions. (See [Agents Need Black Box Recorders](https://papercompute.com/blog/agents-need-black-box-recorders/))
5. **Onboards OpenClaw** (first run). `openclaw onboard --non-interactive --accept-risk --skip-health`
6. **Starts the gateway.** `openclaw gateway run --verbose`

The gateway discovers all registered skills and makes them available as commands.

## Step 5: Triage the Inbox

With the gateway running, send a command to the agent:

```bash
openclaw agent \
  --agent main \
  --message "/gmail-triage" \
  --json
```

The agent reads the `gmail-triage` skill (a Markdown file that defines classification rules), uses `gog` to fetch unread messages, and classifies them using Claude:

```
## Needs Attention
- State DMV: Complete your application (deadline approaching)
- Team standup invite: Tuesday 9am PDT

## Worth a Glance
- Domain registrar: Auto-renewal successful
- Shipping notification: Package arriving Thursday
- SaaS vendor: Reaching out about your account

## Low Priority / FYI
- Purchase confirmation: Order #12345
- Payment app: $16.57 at Coffee Shop
- Ride receipt: Friday morning trip
- School district (x3): Daily parent digests
- Tech newsletter: Weekly roundup
```

The skill defines four categories with specific actions:

| Category | Action |
|----------|--------|
| Newsletter | Label `newsletters`, archive |
| Receipt | Label `receipts`, archive |
| Action needed | Star, label `action-needed` |
| FYI | Mark as read |

Safety constraints baked into the skill: never delete messages, never send replies. If a message can't be confidently classified, leave it unread.

## Step 6: Verify Telemetry

The Tapes proxy inside the VM captures every LLM interaction to the agent's dedicated black box: `.mb/tapes/tapes.sqlite`.

This is deliberately separate from the host-side `.tapes/tapes.sqlite` (which records the user's coding sessions with Claude Code). The agent's decision log is its own isolated record. You can hand it to an auditor, replay it for debugging, or analyze it for self-learning without noise from unrelated sessions.

Check the proxy log:

```bash
cat /workspace/.mb/tapes/start.log | grep "conversation stored"
```

```
{"time":"2026-03-21T09:39:31","level":"INFO","msg":"conversation stored","head":"7087c66d...","provider":"anthropic"}
{"time":"2026-03-21T09:39:36","level":"INFO","msg":"conversation stored","head":"deccb66b...","provider":"anthropic"}
{"time":"2026-03-21T09:39:45","level":"INFO","msg":"conversation stored","head":"8575f5d0...","provider":"anthropic"}
```

Each entry is a complete conversation turn stored with a content-addressed hash. The hash chain means you can trace the full reasoning sequence: what the agent saw, what it decided, and why.

The SQLite database contains a `nodes` table with:
- `role` (user/assistant)
- `model` (claude-opus-4-6)
- `provider` (anthropic)
- `prompt_tokens` / `completion_tokens` (usage tracking)
- `content` (the full request and response)
- `created_at` (timestamp)

This is the flight recorder. If the agent miscategorizes an email, you can replay the conversation to see exactly what input it received and what reasoning it produced.

### What a Tapes Session Looks Like

Query the black box directly to see the agent's reasoning:

```bash
# From the host — the .mb/ directory is on the shared mount
sqlite3 .mb/tapes/tapes.sqlite \
  "SELECT role, substr(content, 1, 200) FROM nodes ORDER BY created_at DESC LIMIT 4"
```

```
assistant | [{"text":"Here's your inbox triage for the last 2 days (20 threads):
            \n\n## Needs Attention\n- State DMV: Complete your application
            \n- Team standup invite: Tuesday 9am PDT..."}]
user      | [{"type":"tool_result"}]
assistant | [{"tool_input":{"command":"gog gmail messages list ..."},...}]
user      | /gmail-triage
```

Read bottom to top: the user invoked `/gmail-triage`, the agent called `gog` to list messages, received the results, then produced the classification. Every step is captured. Because the recording is right there in the SQLite database, you can write accurate technical content about what happened: documentation, blog posts, incident reports, all grounded in exactly what the agent saw and decided rather than a reconstruction from memory.

Now imagine the Meta incident with this recording. You'd see exactly where in the conversation the safety constraint was present, exactly when context compaction dropped it, and exactly which LLM response first decided to delete instead of ask. The difference between "200 emails gone, no idea why" and a complete forensic replay.

Over time, these recordings become training data. Analyze 100 triage sessions to find where skill definitions fall short. Which email categories does the agent struggle with? The black box isn't just for incident response. It's how agents get better.

## Step 7: Teardown

```bash
# From the host
mb down openclaw-in-a-box
```

The moment `mb down` runs:
- The `ANTHROPIC_API_KEY` in tmpfs is gone
- The VM's ephemeral state is gone
- The gog refresh token (in the VM's file-based keyring) is gone

What persists on the shared mount:
- `.openclaw/` for agent config, so next boot skips onboarding
- `.mb/tapes/tapes.sqlite` for the agent's black box recording
- `output/` for reports

Next time: `mb up` then `mb ssh` then `bash /workspace/scripts/start.sh`, and the agent is ready.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  HOST                                                        │
│                                                              │
│  $ mb up / ssh / down                                        │
│       │                                                      │
│       │  jcard.toml → egress allowlist + tmpfs secrets       │
│       │  mounts ./ → /workspace                              │
│       ▼                                                      │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  stereOS VM  (NixOS · 2 CPU · 4 GiB · 2h timeout)     │  │
│  │                                                        │  │
│  │  /run/stereos/secrets/ANTHROPIC_API_KEY  (tmpfs)       │  │
│  │                                                        │  │
│  │  start.sh                                              │  │
│  │    ├── tapes serve proxy (:8080)                        │  │
│  │    │     ▲  intercepts all LLM traffic                  │  │
│  │    │     ▼                                              │  │
│  │    └── openclaw gateway (:18789)                        │  │
│  │          │                                              │  │
│  │          ├── Claude API (via Tapes proxy)                │  │
│  │          ├── gog CLI → Gmail API                         │  │
│  │          └── skills/gmail-triage/SKILL.md                │  │
│  │                                                        │  │
│  │  egress: anthropic, gmail, github, discord, npm only   │  │
│  └────────────────────────────────────────────────────────┘  │
│       │                                                      │
│       │  shared mount (persists across restarts)             │
│       ▼                                                      │
│  .openclaw/                agent config                      │
│  .mb/tapes/tapes.sqlite agent black box (isolated)       │
│  output/                   INBOX_REPORT.md                   │
└──────────────────────────────────────────────────────────────┘
```

## What We Learned Building This

**The orchestrator skill pattern works.** The root `SKILL.md` acts as a setup orchestrator. It detects what's installed, asks the user which integrations they want, and walks through setup. The three integration skills (`gmail-triage`, `github-org-triage`, `discord-bot`) handle the actual work. One VM, multiple skills, user picks what they need.

**Don't bypass the VM.** Early in development we made the mistake of running `gog` commands directly via SSH to "test" the triage. This worked functionally but completely bypassed the Tapes proxy. No telemetry, no audit trail, no isolation. The whole value of stereOS is that the agent operates inside the sandbox with everything recorded. If you're running commands directly, you're just using a fancy SSH tunnel.

**Secrets need explicit loading in stereOS.** The secrets are injected into `/run/stereos/secrets/` as root-owned files on tmpfs. The SSH session doesn't automatically export them as environment variables. `start.sh` has to `sudo cat` each secret file and export it. This is by design. Secrets aren't leaked into the process environment by default.

**OpenClaw skills are security-scoped.** When we tried symlinking skills from the shared mount into OpenClaw's skill directory, it rejected them: "Skipping skill path that resolves outside its configured root." Skills need to be copied, not linked. This prevents a mounted volume from injecting arbitrary skills into the agent.

**gog token export/import bridges host and VM.** The OAuth refresh token lives in the host's system keychain. The VM has no GUI keychain. The solution: `gog auth tokens export` on the host creates a portable JSON file, `gog auth tokens import` inside the VM loads it into a password-protected file-based keyring. The portable file should be deleted immediately after import.

**Non-interactive onboard is essential for automation.** `openclaw onboard` normally requires TTY input. `--non-interactive --accept-risk --skip-health` lets `start.sh` run the full pipeline without human intervention after the first setup.

**Separate the agent's black box from host telemetry.** See the dedicated section below.

## The `.mb/tapes/` Pattern: Agent Black Box Recorders

This is the most important architectural decision in the project and one we think should become a convention for any VM-based agent runtime.

### The Problem

When we first set this up, both the host-side Tapes proxy (recording the developer's Claude Code session) and the VM-side Tapes proxy (recording the OpenClaw agent) were writing to the same `.tapes/tapes.sqlite`. The result: a single database with interleaved entries from two completely different contexts. You couldn't tell which rows were the agent deciding to archive a newsletter vs the developer asking Claude Code to fix a bug in `start.sh`.

This defeats the purpose of telemetry. An audit trail that mixes operator activity with autonomous agent decisions is useless for:

- **Compliance.** "Show me exactly what the agent did with access to this Gmail account."
- **Debugging.** "The agent miscategorized an email, replay its reasoning."
- **Self-learning.** "Analyze 100 triage sessions to find classification patterns the agent gets wrong."

### The Fix

The VM's agent writes to `.mb/tapes/tapes.sqlite`. The host's developer tools write to `.tapes/tapes.sqlite`. Two databases, clean separation.

```
.tapes/tapes.sqlite       ← Host: developer coding sessions (Claude Code, etc.)
.mb/tapes/tapes.sqlite    ← VM: agent black box (OpenClaw via Tapes proxy)
```

The `.mb/` directory is the namespace for Master Blaster-managed VM data. The agent's telemetry belongs there because it's produced by a process running inside the MB-managed VM. It persists on the shared mount (survives `mb down`/`mb up`) but is clearly separated from host-side tooling.

### Why `.mb/tapes/` Specifically

- **`.mb/`** signals "this data was produced by a Master Blaster VM." Other MB-managed state could live here too (agent config, session snapshots, crash dumps).
- **`tapes/`** within `.mb/` keeps the Tapes convention. The SQLite schema is the same. Any tool that reads Tapes data works on both files.
- **Not `.tapes/vm/`** because nesting it under the host's `.tapes/` directory implies the host owns it. The VM's data should have its own top-level namespace.

### What This Enables

With a clean agent-only recording, you can:

1. **Audit a session.** `sqlite3 .mb/tapes/tapes.sqlite "SELECT role, content FROM nodes ORDER BY created_at"` gives you the full conversation between the agent and Claude, with no noise.
2. **Measure cost.** Sum `prompt_tokens` and `completion_tokens` for just the agent's work, separate from developer usage.
3. **Replay decisions.** The hash-chained `nodes` table lets you walk the agent's reasoning tree for any triage run.
4. **Train improvements.** Aggregate recordings across sessions to identify where the agent's skill definitions need refinement. Which email categories does it struggle with? What prompts lead to better classification?
5. **Compare runs.** Diff two triage sessions to see if a skill edit improved or degraded performance.

### Proposal for Master Blaster

This pattern should be the default in `mb`. When a VM writes telemetry, logs, or session data to the shared mount, it should go under `.mb/`, not mixed into the host project's own tooling directories. `mb` could:

- Create `.mb/` automatically on first `mb up`
- Add `.mb/` to `.gitignore` during `mb init`
- Provide `mb tapes` as a convenience command to query `.mb/tapes/tapes.sqlite`
- Support `mb tapes export` to extract a session recording for sharing or archival

The flight recorder metaphor is apt. Every commercial aircraft has a black box. Every autonomous agent should too, and it should be the runtime's responsibility to provide it, not something each project has to wire up manually.

(See [Agents Need Black Box Recorders](https://papercompute.com/blog/agents-need-black-box-recorders/) for the full argument.)

## The Skill That Drives It All

The triage logic is a Markdown file. No code. Edit `skills/gmail-triage/SKILL.md` to change categories, actions, or safety constraints:

```markdown
---
name: gmail-triage
description: "Triage a Gmail inbox: archive newsletters, label receipts,
  flag action items, and produce a summary report."
---

# Gmail Triage

You are an inbox-cleanup agent.

## Rules
1. Fetch all unread messages from the inbox.
2. Classify each message: newsletter, receipt, action-needed, fyi
3. Apply actions per category:
   | newsletter | Archive |
   | receipt | Label receipts, archive |
   | action-needed | Star, label action-needed |
   | fyi | Mark as read |
4. Never delete messages. Never send replies.
5. Write output/INBOX_REPORT.md with a summary.
```

That's it. The agent reads this, understands the rules, and executes them using `gog` CLI commands. Change the categories, add new ones, tighten the safety constraints. It's all prose.

## References

- [gog CLI](https://github.com/steipete/gogcli). Google Workspace bridge.
- [OpenClaw](https://openclaw.ai). Agent framework.
- [stereOS](https://stereos.ai). Ephemeral VM platform.
- [Tapes](https://tapes.dev). Agent telemetry.
- [stereOS jcard schema](https://stereos.ai/reference/jcard-schema/). VM configuration reference.
