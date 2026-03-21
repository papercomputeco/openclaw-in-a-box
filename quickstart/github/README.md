# GitHub Org Triage Quickstart

Daily org sheriff in an ephemeral agent. Boot a stereOS VM, let OpenClaw scan your GitHub org's PRs and issues, get a maintainer brief, tear it down. The token exists only while the VM runs.

## Prerequisites

- [Master Blaster](https://github.com/papercomputeco/masterblaster) (`mb` CLI)
- `ANTHROPIC_API_KEY` exported in your shell
- `GH_TOKEN` — the `gh` CLI picks this up automatically for API access

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export GH_TOKEN="ghp_..."
```

If you don't have a token yet, create one at [github.com/settings/tokens](https://github.com/settings/tokens?type=beta) with `repo` and `read:org` scopes. For fine-grained tokens, grant read-only access to Issues, Pull requests, and Metadata.

The agent accepts any target — an org, a single repo, or a username:

```bash
/github-org-triage papercomputeco                        # whole org
/github-org-triage papercomputeco/openclaw-in-a-box      # single repo
/github-org-triage --user bdougie                        # user's repos
```

## 1. Configure

The included `jcard.toml` declares a `github-org-triage` VM with:
- GitHub + Anthropic API egress only (no other network access)
- 1-hour timeout (triage runs are fast)
- Token injected via tmpfs (RAM-only, never written to disk)

```toml
[network]
egress_allow = [
  "api.anthropic.com",
  "api.github.com",
  "github.com",
  # ...
]

[timeout]
duration = "1h"
```

## 2. Launch

```bash
cd quickstart/github

# Boot the VM
mb up

# SSH in
mb ssh github-org-triage

# Install openclaw + tapes + gh (first time only)
bash /workspace/scripts/install.sh

# Start the agent
bash /workspace/scripts/start.sh
```

On first run, `openclaw onboard` will prompt for interactive setup. Subsequent runs skip straight to the gateway.

## 3. The Agent Triages

The `github-org-triage` skill scans all repos in your org and classifies open items:

| Category | What gets flagged |
|----------|-------------------|
| Urgent | Failing CI, merge conflicts, security labels, release blockers |
| Needs Review | PRs aging without review, approved but unmerged |
| Stale | Issues with no reply in 14 days, draft PRs stuck 10+ days |
| Needs Labels/Info | Unlabeled items, bugs without repro steps, unassigned priority issues |

The agent is read-only by default. It never closes issues, merges PRs, or pushes code. Every API call is logged to [Tapes](https://tapes.dev) for a full audit trail.

To let the agent create lightweight follow-up issues (e.g., requesting repro steps):

```bash
export TRIAGE_CREATE_ISSUES=true
```

## 4. Review Results

```bash
# From inside the VM
cat /workspace/output/ORG_TRIAGE_REPORT.md

# Or from the host after mb down
cat output/ORG_TRIAGE_REPORT.md
```

The report includes urgent items, PRs needing review, stale threads, suggested actions, and stats across all repos scanned.

## 5. Teardown

```bash
# Stop the VM — token destroyed from memory
mb down

# Or remove everything
mb destroy github-org-triage
```

The GitHub token lived in tmpfs and is gone the moment the VM stops. Config persists in `.openclaw/` on the shared mount for the next run.

## Running on a Schedule

For a weekday 8am triage, add a cron job or CI schedule that runs:

```bash
cd quickstart/github && mb up
```

The agent boots, triages, writes the report, and the 1-hour timeout handles teardown automatically.

## Skill Reference

The triage logic lives in `skills/github-org-triage/SKILL.md`. It defines:
- Classification heuristics (time thresholds, label patterns, CI status)
- Output format for `ORG_TRIAGE_REPORT.md`
- Safety constraints (read-only by default)

Edit the skill to customize thresholds, add org-specific labels, or adjust the report format.

## File Layout

```
quickstart/github/
├── jcard.toml                         # VM config (network, secrets, timeout)
├── scripts/
│   └── start.sh                       # Tapes proxy + openclaw gateway
├── skills/
│   └── github-org-triage/
│       └── SKILL.md                   # Agent skill: triage rules + safety
├── output/                            # Agent writes ORG_TRIAGE_REPORT.md here
└── README.md                          # This file
```

## References

- [GitHub CLI (gh)](https://cli.github.com/) — GitHub API access from the command line
- [GitHub fine-grained tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#fine-grained-personal-access-tokens) — scoped token setup
- [OpenClaw Skills](https://docs.openclaw.ai/tools/skills) — how skills work, SKILL.md format, loading precedence
- [stereOS jcard schema](https://stereos.ai/reference/jcard-schema/) — VM configuration reference
- [Tapes](https://tapes.dev) — audit trail and telemetry for agent actions
