# Gmail Triage Quickstart

Sunday inbox cleanup with an ephemeral agent. Boot a stereOS VM, let OpenClaw sort your unread mail, review the report, tear it all down. Credentials exist only while the VM runs.

## Prerequisites

- [Master Blaster](https://github.com/papercomputeco/masterblaster) (`mb` CLI)
- `ANTHROPIC_API_KEY` exported in your shell
- [gog CLI](https://github.com/steipete/gogcli) for Google Workspace access

```bash
export ANTHROPIC_API_KEY="sk-ant-..."

# Install gog
brew install steipete/tap/gogcli
```

## 1. Create Google OAuth Credentials

You need a Google Cloud "Desktop app" OAuth client. This is a one-time setup:

1. **Create a Google Cloud project** at [console.cloud.google.com/projectcreate](https://console.cloud.google.com/projectcreate)
2. **Enable the Gmail API** at [console.cloud.google.com/apis/library/gmail.googleapis.com](https://console.cloud.google.com/apis/library/gmail.googleapis.com)
3. **Configure the OAuth consent screen** at [console.cloud.google.com/auth/branding](https://console.cloud.google.com/auth/branding)
   - Choose "External" user type
   - Add your email as a test user
4. **Create OAuth credentials** at [console.cloud.google.com/auth/clients](https://console.cloud.google.com/auth/clients)
   - Application type: **Desktop app**
   - Download the JSON file (it will be named `client_secret_*.json`)

## 2. Authenticate Gmail

```bash
# Store the OAuth client credentials (one-time)
gog auth credentials ~/Downloads/client_secret_*.json

# Connect your Gmail account — opens a browser for authorization
gog auth add you@gmail.com --services gmail

# Verify the connection
gog auth list

# Test it works
export GOG_ACCOUNT=you@gmail.com
gog gmail labels list
```

The refresh token is stored in your system keychain. On a headless server, `gog auth add` prints a URL you can open in a local browser, then paste the redirect URL back into the terminal.

## 3. Configure

The included `jcard.toml` declares a `gmail-triage` VM with:
- Gmail + Anthropic API egress only (no other network access)
- 2-hour timeout (auto-teardown if you forget)
- Credentials injected via tmpfs (RAM-only, never written to disk)

```toml
[network]
egress_allow = [
  "api.anthropic.com",
  "gmail.googleapis.com",
  "oauth2.googleapis.com",
  # ...
]

[timeout]
duration = "2h"
```

## 4. Launch

```bash
cd quickstart/gmail

# Boot the VM
mb up

# SSH in
mb ssh gmail-triage

# Install openclaw + tapes + gog (first time only)
bash /workspace/scripts/install.sh

# Start the agent
bash /workspace/scripts/start.sh
```

On first run, `openclaw onboard` will prompt for interactive setup. Subsequent runs skip straight to the gateway.

## 5. The Agent Triages

The `gmail-triage` skill uses the `gog` CLI to access Gmail and instructs the agent to:

| Category | Action |
|----------|--------|
| Newsletters | Archive |
| Receipts | Label `receipts`, archive |
| Action needed | Star, label `action-needed` |
| FYI | Mark as read |

The agent never deletes messages or sends replies. Every action is logged to [Tapes](https://tapes.dev) for a full audit trail.

## 6. Review Results

```bash
# From inside the VM
cat /workspace/output/INBOX_REPORT.md

# Or from the host after mb down
cat output/INBOX_REPORT.md
```

The report includes total messages processed, counts per category, and subject lines for everything flagged `action-needed`.

## 7. Teardown

```bash
# Stop the VM — credentials destroyed from memory
mb down

# Or remove everything
mb destroy gmail-triage
```

Credentials lived in tmpfs and are gone the moment the VM stops. Config persists in `.openclaw/` on the shared mount so you can `mb up` again next Sunday without re-onboarding.

## Skill Reference

The triage logic lives in `skills/gmail-triage/SKILL.md`. It defines:
- Classification categories and their actions
- Safety constraints (no deletes, no sends)
- Output format for `INBOX_REPORT.md`

Edit the skill to customize categories or add new ones for your workflow.

## File Layout

```
quickstart/gmail/
├── jcard.toml                    # VM config (network, secrets, timeout)
├── scripts/
│   └── start.sh                  # Tapes proxy + openclaw gateway
├── skills/
│   └── gmail-triage/
│       └── SKILL.md              # Agent skill: triage rules + safety
├── output/                       # Agent writes INBOX_REPORT.md here
└── README.md                     # This file
```

## References

- [gog CLI (gogcli)](https://github.com/steipete/gogcli) — Google Workspace bridge for Gmail, Calendar, Drive, and more
- [gogcli.sh](https://gogcli.sh/) — gog documentation and examples
- [OpenClaw Skills](https://docs.openclaw.ai/tools/skills) — how skills work, SKILL.md format, loading precedence
- [OpenClaw Gmail PubSub](https://docs.openclaw.ai/automation/gmail-pubsub) — real-time Gmail integration with webhooks
- [stereOS jcard schema](https://stereos.ai/reference/jcard-schema/) — VM configuration reference
- [Tapes](https://tapes.dev) — audit trail and telemetry for agent actions
