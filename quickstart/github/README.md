# GitHub Org Triage Setup

Set up GitHub access for the openclaw-in-a-box agent. This is a one-time credential setup on the host — the agent runs inside the VM.

## Create a GitHub Token

Create a token at [github.com/settings/tokens](https://github.com/settings/tokens?type=beta) with `repo` and `read:org` scopes. For fine-grained tokens, grant read-only access to Issues, Pull requests, and Metadata.

```bash
export GH_TOKEN="ghp_..."
```

Or authenticate with the `gh` CLI:

```bash
brew install gh
gh auth login
```

## Run the Agent

From the repo root:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export GH_TOKEN="ghp_..."
mb up
mb ssh openclaw-in-a-box
bash /workspace/scripts/install.sh   # first time
bash /workspace/scripts/start.sh
```

Then invoke the triage skill with any target — an org, a repo, or a username:

```bash
openclaw agent --agent main --message "/github-org-triage papercomputeco"
openclaw agent --agent main --message "/github-org-triage papercomputeco/openclaw-in-a-box"
openclaw agent --agent main --message "/github-org-triage --user bdougie"
```

## What the Agent Does

| Category | What gets flagged |
|----------|-------------------|
| Urgent | Failing CI, merge conflicts, security labels, release blockers |
| Needs Review | PRs aging without review, approved but unmerged |
| Stale | Issues with no reply in 14 days, draft PRs stuck 10+ days |
| Needs Labels/Info | Unlabeled items, bugs without repro steps, unassigned priority issues |

Read-only by default. Never closes issues, merges PRs, or pushes code. Set `TRIAGE_CREATE_ISSUES=true` to let the agent create follow-up issues.

Report written to `output/ORG_TRIAGE_REPORT.md`. Every LLM call logged to `.mb/tapes/tapes.sqlite`.

## Skill Reference

The triage logic lives in `skills/github-org-triage/SKILL.md` at the repo root. Edit it to customize thresholds, labels, or report format.

## References

- [GitHub CLI (gh)](https://cli.github.com/) — GitHub API access
- [GitHub fine-grained tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#fine-grained-personal-access-tokens) — scoped token setup
- [stereOS jcard schema](https://stereos.ai/reference/jcard-schema/) — VM configuration
- [Tapes](https://tapes.dev) — agent telemetry
