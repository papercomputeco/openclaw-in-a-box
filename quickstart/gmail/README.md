# Gmail Triage Setup

Set up Gmail access for the openclaw-in-a-box agent. This is a one-time credential setup on the host — the agent runs inside the VM.

For a detailed walkthrough of the full setup (with screenshots and lessons learned), see [WALKTHROUGH.md](WALKTHROUGH.md).

## Install gog CLI

```bash
brew install steipete/tap/gogcli
```

## Create Google OAuth Credentials

You need a Google Cloud "Desktop app" OAuth client:

1. **Create a Google Cloud project** at [console.cloud.google.com/projectcreate](https://console.cloud.google.com/projectcreate)
2. **Enable the Gmail API** at [console.cloud.google.com/apis/library/gmail.googleapis.com](https://console.cloud.google.com/apis/library/gmail.googleapis.com)
3. **Configure the OAuth consent screen** at [console.cloud.google.com/auth/branding](https://console.cloud.google.com/auth/branding)
   - Choose "External" user type
   - Add your email as a test user (required — without this the OAuth flow will fail)
4. **Create OAuth credentials** at [console.cloud.google.com/auth/clients](https://console.cloud.google.com/auth/clients)
   - Application type: **Desktop app**
   - Download the JSON file immediately — Google no longer shows the secret after this dialog

## Authenticate Gmail

```bash
# Register the OAuth client
gog auth credentials ~/Downloads/client_secret_*.json

# Connect your Gmail account (opens browser for authorization)
gog auth add you@gmail.com --services gmail

# Verify
gog auth list
export GOG_ACCOUNT=you@gmail.com
gog gmail labels list
```

## Export Auth for the VM

The VM doesn't have access to your host keychain. Export the token and import it inside the VM:

```bash
# On the host — export token to a portable file
gog auth tokens export you@gmail.com --out /tmp/gog-token.json
cp ~/Downloads/client_secret_*.json /tmp/gog-creds.json
chmod 644 /tmp/gog-token.json /tmp/gog-creds.json

# Copy to shared mount (visible inside VM at /workspace/)
cp /tmp/gog-token.json /tmp/gog-creds.json /path/to/openclaw-in-a-box/

# Inside the VM (mb ssh openclaw-in-a-box)
export GOG_KEYRING_PASSWORD="openclaw"
gog auth credentials /workspace/gog-creds.json
gog auth tokens import /workspace/gog-token.json

# Clean up — delete the token file from the shared mount
rm /workspace/gog-token.json /workspace/gog-creds.json
```

## Run the Agent

From the repo root (not this directory):

```bash
mb up
mb ssh openclaw-in-a-box
bash /workspace/scripts/install.sh   # first time
bash /workspace/scripts/start.sh
```

Then invoke the triage skill:

```bash
openclaw agent --agent main --message "/gmail-triage"
```

The agent classifies unread messages and applies actions:

| Category | Action |
|----------|--------|
| Newsletter | Label `newsletters`, archive |
| Receipt | Label `receipts`, archive |
| Action needed | Star, label `action-needed` |
| FYI | Mark as read |

Never deletes messages or sends replies. Every LLM call logged to Tapes.

## Skill Reference

The triage logic lives in `skills/gmail-triage/SKILL.md` at the repo root. Edit it to customize categories, actions, or safety constraints.

## References

- [gog CLI](https://github.com/steipete/gogcli) — Google Workspace bridge
- [gogcli.sh](https://gogcli.sh/) — gog documentation
- [stereOS jcard schema](https://stereos.ai/reference/jcard-schema/) — VM configuration
- [Tapes](https://tapes.dev) — agent telemetry
