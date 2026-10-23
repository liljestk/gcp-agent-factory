---
name: spec-new
description: Scaffold a new spec folder (requirements, design, tasks) for a feature or change in gcp-agent-factory. Use before implementing anything bigger than a small fix, or when the user asks to "spec", "plan a feature" or "write requirements".
---

# spec-new

Creates `specs/<NNN-slug>/` from `specs/_template/` and wires requirement IDs into the traceability check.

## Steps

1. **Pick the number**: the next free `NNN` in `specs/` (three digits, never reused). Slug is kebab-case, ≤ 5 words.
2. **Pick the area code** for requirement IDs: `REPO`, `LZ` (landing zone), `AGT` (agents), `DATA`, `OPS`, `FIN` (FinOps), `APP`, or a new short uppercase code if none fits. Search `specs/` with grep for the highest existing `REQ-<AREA>-NNN` and continue from it.
3. **Copy the template**: `requirements.md`, `design.md`, `tasks.md`. Fill in:
   - `requirements.md`: one `### REQ-<AREA>-<NNN>: <title>` heading per requirement, an EARS-style statement ("When…, the… shall…"), observable acceptance criteria, and **Verified by** pointing at the feature file.
   - `design.md`: every section, especially **Cost impact** (use the `cost-impact` skill) and **Security impact**. Mention any avoid-list item from `DESIGN.md`; each one needs an ADR.
   - `tasks.md`: ordered, test-first checklist.
4. **Write the feature file(s)** next to the code that will implement them, with scenarios tagged `@REQ-<AREA>-<NNN>` (use the `bdd-scenario` skill). For OpenTofu modules, add `# covers: REQ-…` to the `*.tftest.hcl` instead.
5. **Index it**: add a row to the table in `specs/README.md`.
6. **Architecture change?** Run the `adr-new` skill too.
7. Run `just repo-checks`. Traceability fails until each requirement has a test reference, which is intended.

## Rules

- Requirements describe **observable behaviour**, not implementation.
- Keep a spec small enough to ship in one or a few PRs. Split otherwise.
- Never renumber or reuse requirement IDs. Mark removed ones as `(withdrawn)` in the heading text and remove their tests.
