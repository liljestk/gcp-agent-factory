# 001: Repo foundations (design)

## Overview

Phase 0 sets up the toolchain (mise, uv, just, devcontainer), agent conventions (AGENTS/CLAUDE/DESIGN.md, skills, subagents, hooks), the decision record (ADRs) and CI quality gates. Two small pieces of real code exercise every gate:

1. **`libs/repo-checks`**: a stdlib + PyYAML CLI that machine-checks repo conventions (REQ-REPO-001…005, 008).
2. **`modules/labels`**: the single source of standard labels (REQ-REPO-006), tested offline with `tofu test`.

The Claude hooks (`.claude/hooks/*.py`) are stdlib-only scripts (they must run on a bare host), covered by `tests/tooling`.

## Components and changes

| Component | Change |
|---|---|
| `libs/repo-checks` | checks `skills`, `subagents`, `adrs`, `traceability`, `pragmas`, `pins`; `repo-checks all` exits non-zero on findings |
| `modules/labels` | variables with validation → `labels` output |
| `.claude/hooks/guard_bash.py` | PreToolUse guard, exits 2 on destructive patterns |
| `.claude/hooks/format_on_edit.py` | PostToolUse formatter, never blocks |
| `.github/workflows/ci.yml` | jobs `python`, `iac`, `repo`, `secrets`, `dependency-review`, each calling `just` recipes |
| `.github/workflows/codeql.yml` | CodeQL for Python and Actions |

## Well-Architected notes

- **Operational excellence**: one command (`just check`) locally and in CI; pinned tools.
- **Security**: SHA-pinned dependencies, gitleaks, zizmor, CodeQL, destructive-command guard, least-privilege workflow permissions.
- **Reliability**: deterministic tests, no network in unit or BDD tests.
- **Cost**: GitHub-hosted runners on a public repo are free; no GCP spend.

## Cost impact

$0. No cloud resources.

## Security impact

No identities or cloud access. CI jobs run with `contents: read` only; `security-events: write` is limited to the CodeQL job.

## Alternatives considered

- **Off-the-shelf linters for conventions** (e.g. `pin-github-action`, custom pre-commit hooks): there's no single tool for ADR, skill and traceability rules, and a small typed package is easy to test to 100%.
