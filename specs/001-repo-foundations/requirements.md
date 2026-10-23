# 001: Repo foundations (requirements)

## Context

Phase 0 of the [roadmap](../../docs/PLAN.md#12-roadmap): a monorepo whose conventions are machine-checked from the first commit, so humans and coding agents can build the platforms on a solid base. No GCP resources are created.

## Requirements

### REQ-REPO-001: Skills and subagents are well-formed

**Statement**: The repo checks shall reject any Claude skill or subagent whose front matter is missing, malformed, misnamed or lacks a description.

#### Acceptance criteria

- Every `.claude/skills/<dir>/` contains `SKILL.md` with a `name` equal to `<dir>` and a non-empty `description` of at most 1024 characters.
- Every `.claude/agents/<file>.md` has a `name` equal to the file stem and a non-empty `description`.

**Verified by**: `libs/repo-checks/tests/features/skills.feature`

### REQ-REPO-002: ADRs are well-formed and indexed

**Statement**: The repo checks shall reject ADRs with an invalid file name, front matter status or title, or that are missing from the ADR index.

#### Acceptance criteria

- File names match `NNNN-kebab-title.md`, numbers are unique, and `0000` is reserved for the template.
- `status` is one of `proposed`, `accepted`, `rejected`, `deprecated` or `superseded by ADR-NNNN`.
- The first heading is `# ADR-NNNN: …` with the file's number.
- `docs/adr/README.md` links every ADR file.

**Verified by**: `libs/repo-checks/tests/features/adrs.feature`

### REQ-REPO-003: Every requirement is traced to a test

**Statement**: The repo checks shall fail when a requirement has no test, or when a test references a requirement that doesn't exist or is defined twice.

#### Acceptance criteria

- Requirements are headings `REQ-<AREA>-<NNN>` in `specs/*/requirements.md` (folders starting with `_` are ignored).
- References are `@REQ-…` tags in `.feature` files or `# covers: REQ-…` comments in `*.tftest.hcl` files.

**Verified by**: `libs/repo-checks/tests/features/traceability.feature`

### REQ-REPO-004: Coverage exclusions are justified

**Statement**: The repo checks shall reject any coverage-exclusion pragma in Python code that doesn't state a reason.

#### Acceptance criteria

- A pragma written as `pragma: no cover -- <reason>` (or `no branch`) is accepted; without `-- <reason>` it is reported with file and line.

**Verified by**: `libs/repo-checks/tests/features/pragmas.feature`

### REQ-REPO-005: Third-party CI and hook code is pinned to commit SHAs

**Statement**: The repo checks shall reject GitHub Actions `uses:` references and pre-commit `rev:` values that aren't full 40-character commit SHAs.

#### Acceptance criteria

- Local actions (`./…`) are allowed; `docker://` references must be pinned by `@sha256:` digest.
- Pre-commit `local`/`meta` repos have no `rev` and are ignored.

**Verified by**: `libs/repo-checks/tests/features/pins.feature`

### REQ-REPO-006: Standard labels come from one module

**Statement**: The `labels` OpenTofu module shall produce the standard label set and reject values that break GCP label rules or the platform taxonomy.

#### Acceptance criteria

- Output contains `env`, `platform`, `component`, `owner`, `cost-center`, `managed-by=opentofu` and `repo=gcp-agent-factory`, plus optional `agent`, `app` and `data-product`.
- Unknown `env`/`platform`, invalid characters or lengths, and `extra` labels that try to override a standard key are rejected.

**Verified by**: `modules/labels/tests/labels.tftest.hcl`

### REQ-REPO-007: Coding agents can't run destructive commands

**Statement**: The Claude Code PreToolUse hook shall block shell commands that apply or destroy infrastructure, delete cloud resources, create service-account keys or force-push, and shall allow everything else.

#### Acceptance criteria

- A blocked command exits with code 2 and explains the reason on stderr.
- Malformed or non-Bash hook input is allowed through (fail open), so tooling is never bricked.

**Verified by**: `tests/tooling/features/guard.feature`

### REQ-REPO-008: The repository follows its own conventions

**Statement**: Running all repo checks against this repository shall report no findings.

**Verified by**: `libs/repo-checks/tests/features/repository.feature`

## Out of scope

- GCP resources, WIF and GitHub repo settings (Phase 1).
- Trivy, conftest, Infracost and `tofu plan` gates (they arrive with the first stacks in Phase 1).
