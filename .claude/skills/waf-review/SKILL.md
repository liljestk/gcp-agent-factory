---
name: waf-review
description: Review a change or design against the Google Cloud Well-Architected Framework pillars using docs/waf/README.md, and update the checklist. Use for PR-sized infra or architecture changes, before accepting an ADR, or when the user asks for a WAF or best-practice review.
---

# waf-review

## Steps

1. Read `docs/waf/README.md` and the change (diff, spec `design.md`, ADR).
2. For **each pillar** (operational excellence, security, reliability, cost, performance, sustainability, AI/ML), ask:
   - Does the change add, weaken or complete a control in the checklist?
   - Is the control **enforced** (test, policy, lint) or only documented?
   - Does it conflict with a `DESIGN.md` invariant?
3. Report in this format:

   ```markdown
   | Pillar | Finding | Severity (high/med/low/info) | Suggested fix |
   |---|---|---|---|
   ```

   Then a verdict line: `WAF: pass` / `WAF: pass with follow-ups` / `WAF: changes required`.
4. If the change completes a planned control, update its status in `docs/waf/README.md` in the same PR (⬜ → 🟡 → ✅).

## Severity guide

- **high**: breaks an invariant, opens public access, adds an unbudgeted idle cost, or removes a recovery path.
- **med**: control only documented, not enforced; missing DLQ, retry or label; no test for a failure mode.
- **low**: naming, docs, observability gaps.
