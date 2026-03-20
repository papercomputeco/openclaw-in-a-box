# Gmail Triage Quickstart

Sunday inbox cleanup with an ephemeral agent. Boot a stereOS VM, let OpenClaw sort your unread mail, review the report, tear it all down. The OAuth token exists only while the VM runs.

## Prerequisites

- [Master Blaster](https://github.com/papercomputeco/masterblaster) (`mb` CLI)
- `ANTHROPIC_API_KEY` exported in your shell
- `GMAIL_OAUTH_TOKEN` for Gmail API access ([setup guide](https://developers.google.com/gmail/api/quickstart/js))

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export GMAIL_OAUTH_TOKEN="ya29.a0..."
```

## 1. Configure

The included `jcard.toml` declares a `gmail-triage` VM with:
- Gmail + Anthropic API egress only (no other network access)
- 2-hour timeout (auto-teardown if you forget)
- OAuth token injected via tmpfs (RAM-only, never written to disk)

```toml
[network]
egress_allow = [
  "api.anthropic.com",
  "gmail.googleapis.com",
  "oauth2.googleapis.com",
  # ...
]

[secrets]
GMAIL_OAUTH_TOKEN = "${GMAIL_OAUTH_TOKEN}"
```

## 2. Launch

```bash
cd quickstart/gmail

# Boot the VM
mb up

# SSH in
mb ssh gmail-triage

# Install openclaw + tapes (first time only)
bash /workspace/scripts/install.sh

# Start the agent
bash /workspace/scripts/start.sh
```

On first run, `openclaw onboard` will prompt for interactive setup. Subsequent runs skip straight to the gateway.

## 3. The Agent Triages

The `gmail-triage` skill instructs the agent to:

| Category | Action |
|----------|--------|
| Newsletters | Archive |
| Receipts | Label `receipts`, archive |
| Action needed | Star, label `action-needed` |
| FYI | Mark as read |

The agent never deletes messages or sends replies. Every action is logged to [Tapes](https://tapes.dev) for a full audit trail.

## 4. Review Results

```bash
# From inside the VM
cat /workspace/output/INBOX_REPORT.md

# Or from the host after mb down
cat output/INBOX_REPORT.md
```

The report includes total messages processed, counts per category, and subject lines for everything flagged `action-needed`.

## 5. Teardown

```bash
# Stop the VM — OAuth token destroyed from memory
mb down

# Or remove everything
mb destroy gmail-triage
```

The OAuth token lived in tmpfs and is gone the moment the VM stops. Config persists in `.openclaw/` on the shared mount so you can `mb up` again next Sunday without re-onboarding.

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
