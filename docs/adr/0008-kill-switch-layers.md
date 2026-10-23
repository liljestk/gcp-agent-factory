---
status: accepted
date: 2026-10-23
decision-makers: liljestk
---

# ADR-0008: Five kill-switch layers

## Context and problem statement

Agents can loop, get prompt-injected or burn tokens. Billing data lags by hours, so budget alerts alone react too slowly. We need fast, reversible stops and hard backstops.

## Decision

| Layer | Scope | Trigger | Mechanism |
|---|---|---|---|
| L0 | one agent | human, token budget, agent proposal | Firestore flag checked by `KillSwitchPlugin` before each model or tool call (cached ≤10 s) |
| L1 | one agent | `killswitch` workflow | disable the agent's SA, remove invoker bindings, detach its push subscription |
| L2 | one env | 90% of the project budget | `budget-enforcer` sets L0 for all agents and pauses schedulers and triggers |
| L3 | dev/prod project | 110% of the project budget | `budget-enforcer` detaches billing (never seed or ops) |
| L4 | account | free-trial credits exhausted | Google stops services while the account stays on the free trial |

Token accounting in `BudgetPlugin` (in-app, near real time) is the fast line; billing budgets are the backstop.

## Consequences

- Good: stops within seconds for the common case; layered defence for the rare one.
- Bad: L3 stops every service in the project; recovery means re-linking billing and re-applying the stack. This is documented in the runbook.
- Note: **upgrading to a paid account removes L4**, which makes L3 critical.

## Alternatives considered

- **Budgets only**: hours of lag; unacceptable for runaway loops.
- **Vertex AI quota overrides as a cap**: useful where available, but newer Gemini models use dynamic shared quota, so it can't be the primary control.

## Enforcement

BDD scenarios for L0–L2 (Phase 3), an end-to-end budget notification test (Phase 1), and runbooks in `docs/runbooks/`.
