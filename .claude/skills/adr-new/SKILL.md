---
name: adr-new
description: Create a new Architecture Decision Record (MADR format) in docs/adr and register it in the index. Use when a change introduces or alters an architectural decision, adds an avoid-list service, changes an invariant, or the user asks to "record a decision" or "write an ADR".
---

# adr-new

## Steps

1. **Number**: the next free `NNNN` in `docs/adr/` (`0000` is the template).
2. **File**: `docs/adr/NNNN-kebab-case-title.md`, copied from `0000-template.md`.
3. **Front matter**: `status: proposed` (only a human moves it to `accepted`), `date: <today, YYYY-MM-DD>`, `decision-makers: liljestk`.
4. **Title**: `# ADR-NNNN: <imperative title>`. The number must match the file name.
5. **Sections**: context (constraints: cost, security, free-trial limits), decision, consequences (good **and** bad), alternatives considered, and **Enforcement** (how a test, policy or lint keeps it true; "review only" is a smell).
6. **Index**: add a row to `docs/adr/README.md` in number order.
7. **Superseding**: never rewrite an accepted ADR's decision. Create a new ADR and set the old one's status to `superseded by ADR-NNNN`.
8. **Invariants**: if the decision adds or changes an invariant, update the table in `DESIGN.md` §3 with its enforcement and status.
9. Run `just repo-checks` (`adrs` validates format, numbering and index).

## Quality bar

- One decision per ADR.
- Quantify cost where relevant (idle per month, per use).
- Link the spec that motivated it.
