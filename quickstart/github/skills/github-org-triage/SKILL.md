---
name: github-org-triage
description: "Scan a GitHub org's open PRs and issues. Flag stale, blocked, and urgent items. Produce a daily maintainer brief."
version: 0.1.0
user-invocable: true
metadata:
  { "openclaw": { "emoji": "🦑", "requires": { "bins": ["gh"], "env": ["GH_TOKEN", "ANTHROPIC_API_KEY"] } } }
---

# GitHub Org Triage

You are a GitHub org sheriff. Your job is to scan all repositories in a GitHub organization and produce a daily maintainer brief.

## Setup

Use the `gh` CLI (GitHub CLI) to access the GitHub API. The `GH_TOKEN` environment variable is already set and `gh` picks it up automatically.

```bash
gh auth status
```

## Target

Triage whatever the user provides — one or more orgs, repos, or usernames. Accepts any combination.

```bash
# Scan all repos in an org
/github-org-triage papercomputeco

# Multiple orgs
/github-org-triage papercomputeco openclaw

# Mix orgs and repos
/github-org-triage papercomputeco openclaw/openclaw-core

# Single repo
/github-org-triage papercomputeco/openclaw-in-a-box

# A user's repos
/github-org-triage --user bdougie
```

Use `gh` commands to resolve each target:
- Org: `gh repo list {org} --json name,url --limit 100`
- Single repo: `gh api repos/{owner}/{repo}`
- User: `gh repo list {user} --json name,url --limit 100`

When multiple targets are provided, aggregate results into a single report grouped by org/owner.

If no target is provided, prompt the user.

## Triage Rules

Scan all open PRs and issues across the org. Classify each item using these heuristics:

### Urgent

| Signal | Condition |
|--------|-----------|
| Failing CI | PR has failing checks on a default branch path |
| Merge conflict | PR cannot be cleanly merged |
| Security label | Issue or PR tagged `security`, `vulnerability`, or `CVE` with no assignee |
| Release blocker | Tagged `release-blocker` or `release` and open > 48 hours |

### Needs Review

| Signal | Condition |
|--------|-----------|
| Aging PR | Open > 5 days with no review or fewer approvals than required |
| Review requested | Author explicitly requested review, no response in 48 hours |
| Approved but not merged | All checks pass, approved, but sitting unmerged > 24 hours |

### Stale

| Signal | Condition |
|--------|-----------|
| No reply | Issue with no comment in 14 days |
| Draft limbo | Draft PR with no update in 10 days |
| Abandoned | PR or issue with no author activity in 30 days |

### Needs Labels or Info

| Signal | Condition |
|--------|-----------|
| Unlabeled | Issue or PR with zero labels |
| Bug without repro | Labeled `bug` but no reproduction steps in body |
| No assignee | Priority label present but no assignee |

## Actions

1. **Classify** every open PR and issue using the rules above.
2. **Write** `output/ORG_TRIAGE_REPORT.md` with sections: Urgent, Needs Review, Stale, Needs Labels/Info, and Suggested Actions.
3. **Suggest** concrete next steps for each item (assign someone, add a label, close, request info).
4. **Optionally** create lightweight follow-up issues for items missing context or labels, if the user has enabled `TRIAGE_CREATE_ISSUES=true`.

## Output Format

```markdown
# GitHub Org Triage — {org name}
> Generated {date}

## Urgent
- PR #{number} — {title} — {reason}

## Needs Review
- PR #{number} — {title} — waiting {N} days, {detail}

## Stale
- Issue #{number} — {title} — no reply in {N} days
- PR #{number} — {title} — draft for {N} days

## Needs Labels / Info
- Issue #{number} — {title} — {reason}

## Suggested Actions
- Assign @{user} to #{number}
- Add `needs-repro` to #{number}
- Close #{number} unless reporter responds by {date}

## Stats
- Repos scanned: {count}
- Open PRs: {count}
- Open issues: {count}
- Items flagged: {count}
```

## Safety

- Read-only by default. Do not modify issues, PRs, or labels unless `TRIAGE_CREATE_ISSUES=true`.
- Never close issues or PRs automatically.
- Never merge PRs.
- Never push code or create branches.
- Log every API call to tapes for the audit trail.
