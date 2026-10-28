# repo-checks

Machine checks for the conventions in [`AGENTS.md`](../../AGENTS.md) and [`DESIGN.md`](../../DESIGN.md). Specs: [001: repo foundations](../../specs/001-repo-foundations/requirements.md) and [002: bootstrap and CI pipeline](../../specs/002-bootstrap-and-ci-pipeline/requirements.md) (the OpenTofu checks).

```bash
uv run repo-checks all            # every check (what `just repo-checks` runs)
uv run repo-checks traceability   # a single check
uv run repo-checks pins --root /path/to/repo
```

| Check | Requirement | Rule |
|---|---|---|
| `skills` | REQ-REPO-001 | `.claude/skills/<dir>/SKILL.md` front matter: `name == <dir>`, description ≤ 1024 chars |
| `subagents` | REQ-REPO-001 | `.claude/agents/<file>.md` front matter: `name == <file stem>`, description present |
| `adrs` | REQ-REPO-002 | file name, `status`, `# ADR-NNNN:` title, listed in `docs/adr/README.md` |
| `traceability` | REQ-REPO-003 | every `REQ-*` in `specs/*/requirements.md` has a `@REQ-*` scenario or `# covers:` tftest, and vice versa |
| `pragmas` | REQ-REPO-004 | coverage exclusions in Python carry `-- <reason>` |
| `pins` | REQ-REPO-005 | workflow `uses:` and pre-commit `rev:` are full commit SHAs |
| `encryption` | REQ-LZ-003 | every root module (a directory with a `backend` block, or a stack in `platforms/stacks.yaml`) has an `encryption` block with `enforced = true` for `state` and `plan` |
| `tofu-safety` | REQ-LZ-012 | OpenTofu code can't leak data through a plan: no `external`/`http` data sources, provisioners, `nonsensitive(`, unlisted providers (in `required_providers` or lock files), non-local module sources, or secret versions in state; `file()`-style reads stay in the module or are declared stack `inputs` |

Exit code `0` = clean, `1` = findings (printed as `path:line: [check] message`).
