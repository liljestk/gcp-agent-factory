---
name: bdd-scenario
description: Write or extend Gherkin BDD scenarios with pytest-bdd, tagged with requirement IDs, reusing shared step definitions. Use when adding acceptance criteria for a requirement, when the user mentions BDD, Gherkin, features or scenarios, or before implementing behaviour test-first.
---

# bdd-scenario

## Where things live

- Feature files sit beside the code they verify: `<package>/tests/features/*.feature` (repo tooling: `tests/tooling/features/`; deployed-env suites later: `tests/acceptance/`).
- Step definitions live in the nearest `conftest.py` so every test module below it can reuse them. A `test_features.py` binds them with `scenarios("features")`.

## Writing scenarios

```gherkin
@REQ-AGT-008
Feature: Agent kill switch
  Operators need to stop a misbehaving agent within seconds.

  Scenario: A soft-killed agent refuses new work
    Given the agent "finops-analyst" is enabled
    When an operator disables "finops-analyst" with reason "demo"
    And a task is delivered to "finops-analyst"
    Then the task is rejected with reason "agent_disabled"
```

- **Tag** every scenario or feature with the requirement it proves (`@REQ-…`). Add `@smoke`, `@acceptance`, `@security` or `@chaos` for deployed-env suites. Other tags must be registered markers in `pyproject.toml`.
- Use business language: what the actor observes, not function names.
- One behaviour per scenario. Use `Scenario Outline` + `Examples` for input tables.
- Deterministic: no real network, clock or randomness. Use fakes and fixtures (`tmp_path`, emulators).
- Negative paths matter as much as happy paths, especially for security behaviour.

## pytest-bdd mechanics

- `@given(parsers.parse('a file "{path}" containing:'))`: step text with parameters.
- Multiline input: add a `docstring` parameter to the step function (Gherkin `"""` block).
- Share state between steps with `target_fixture="name"` on a `@given`/`@when`, or a small mutable context fixture.
- Reuse before you add: grep existing `conftest.py` files for a matching step first.

## Done when

- `just test` passes with 100% coverage, and `just repo-checks` shows the requirement as traced.
