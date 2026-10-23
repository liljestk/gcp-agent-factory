# repo-checks

Machine checks for the conventions in [`AGENTS.md`](../../AGENTS.md) and [`DESIGN.md`](../../DESIGN.md). Spec: [001: repo foundations](../../specs/001-repo-foundations/requirements.md).

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

Exit code `0` = clean, `1` = findings (printed as `path:line: [check] message`).
