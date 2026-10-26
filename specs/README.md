# Specs

Spec-driven development (ADR-0016). Each feature or change of meaningful size gets a folder:

```text
specs/<NNN-slug>/
├── requirements.md   # WHAT: numbered requirements (REQ-<AREA>-<NNN>) + acceptance criteria
├── design.md         # HOW: design, WAF pillar notes, cost impact, security impact
└── tasks.md          # ordered checklist the implementer (human or agent) works through
```

Rules:

- Requirement IDs are headings: `### REQ-<AREA>-<NNN>: <title>`. IDs are never reused.
- Executable acceptance criteria live in `.feature` files tagged `@REQ-…`, or in `*.tftest.hcl` with a `# covers: REQ-…` comment. `repo-checks traceability` fails if any requirement has no test, or if a test references an unknown requirement.
- Folders starting with `_` (like `_template/`) are ignored by the checks.
- Use the `spec-new` skill to scaffold.

| Spec | Title | Status |
|---|---|---|
| [001](001-repo-foundations/requirements.md) | Repo foundations (Phase 0) | in progress |
| [002](002-bootstrap-and-ci-pipeline/requirements.md) | Bootstrap and CI pipeline (Phase 1, part 1) | draft |
