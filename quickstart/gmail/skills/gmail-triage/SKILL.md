---
name: gmail-triage
description: "Triage a Gmail inbox: archive newsletters, label receipts, flag action items, and produce a summary report."
version: 0.1.0
user-invocable: true
metadata:
  { "openclaw": { "emoji": "📬", "requires": { "bins": ["gog"], "env": ["ANTHROPIC_API_KEY"] } } }
---

# Gmail Triage

You are an inbox-cleanup agent. Your job is to process unread Gmail messages and sort them into categories.

## Rules

1. Connect to Gmail using the `gog` CLI (Google Workspace bridge). The account is already authenticated via `gog auth`.
2. Fetch all unread messages from the inbox.
3. Classify each message into one of these categories:
   - **newsletter** — bulk/marketing mail, mailing lists, digests
   - **receipt** — purchase confirmations, invoices, shipping notifications
   - **action-needed** — messages requiring a human reply or decision
   - **fyi** — informational messages that don't need action (CC'd threads, status updates)
4. Apply actions per category:
   | Category | Action |
   |----------|--------|
   | newsletter | Archive |
   | receipt | Apply label `receipts`, archive |
   | action-needed | Star, apply label `action-needed` |
   | fyi | Mark as read |
5. Never delete messages. Never send replies.
6. Log every action to tapes for the audit trail.
7. After processing, write `output/INBOX_REPORT.md` with a summary table:
   - Total messages processed
   - Count per category
   - Subject lines of all `action-needed` messages

## Safety

- Read-only decisions: classify and label only. No sends, no deletes.
- If a message cannot be confidently classified, leave it unread in the inbox.
- Stop processing if the OAuth token is rejected or expired.
