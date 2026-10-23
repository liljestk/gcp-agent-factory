# CLAUDE.md

@AGENTS.md
@DESIGN.md

## Claude Code specifics

- **Skills** (`.claude/skills/`): `spec-new`, `adr-new`, `tofu-module-new`, `bdd-scenario`, `cost-impact`, `waf-review`, `security-review`. Use them instead of improvising these workflows. Platform-specific skills (`agent-new`, `data-product-new`, `app-new`, `incident-triage`, `killswitch`, `dlq-redrive`) arrive with their phases.
- **Subagents** (`.claude/agents/`): `tofu-reviewer`, `security-reviewer`, `finops-reviewer`, `waf-reviewer`, `test-writer`. Run the relevant reviewers on any PR-sized change before declaring it done.
- **Hooks** (`.claude/hooks/`): a Bash guard blocks destructive cloud and git commands (exit code 2 explains why), and edited files are auto-formatted when `uv`/`tofu` are available. Don't work around a blocked command; ask the human.
- **Permissions** (`.claude/settings.json`): `tofu apply/destroy` and reading state, plan or `.env` files are denied. Personal overrides go in `.claude/settings.local.json` (gitignored).
