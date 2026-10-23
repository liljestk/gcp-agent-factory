---
status: accepted
date: 2026-10-23
decision-makers: liljestk
---

# ADR-0013: Testing strategy: 100% coverage, BDD, evals, IaC tests

## Context and problem statement

The requirements are "full test coverage" and "good BDD testing". Agents are non-deterministic; infrastructure is hard to unit-test; demo credibility depends on behaviour being proven.

## Decision

| Layer | Tooling | Gate |
|---|---|---|
| Unit / component | pytest (+ Pub/Sub and Firestore emulators) | **100% line + branch** coverage, justified pragmas only |
| Behaviour | **pytest-bdd** Gherkin; one step library runs in-process and against deployed envs | every `REQ-*` traced to a scenario |
| Agent quality | ADK evalsets (trajectory + response) and judge rubrics | thresholds on agent or prompt changes and nightly |
| Contracts | buf, JSON Schema | blocking |
| IaC | `tofu test` (mock providers), conftest on plan JSON, tflint | blocking |
| Post-deploy | `@smoke`, `@acceptance`, `@security` (negative tests) | blocks prod |
| Resilience | `@chaos` game days | monthly |
| Test quality | mutation testing on `libs/` | trend |

## Consequences

- Good: every claim in the demo ("killed agents stop", "duplicates are processed once") is an executable scenario.
- Bad: 100% coverage costs effort; mitigated by keeping I/O at the edges and logic pure.
- Bad: evals cost tokens, so they're label-triggered and capped.

## Alternatives considered

- **behave**: separate runner; pytest-bdd shares fixtures and coverage with the unit tests.
- **Terratest**: Go plus real cloud resources; `tofu test` with mocks is offline and free.

## Enforcement

`fail_under = 100` in `pyproject.toml`; `repo-checks traceability` and `repo-checks pragmas`; required CI checks on `main`.
