@security
Feature: ci-plan cannot read data payloads
  The repo checks keep stack code from leaking data through a plan; their
  scenarios live next to the code in libs/repo-checks (tofu_safety.feature).
  This read-only check runs nightly against the live seed as ci-plan.

  @REQ-LZ-012
  Scenario: ci-plan cannot read data payloads
    When I read every role held by "ci-plan"
    Then none grants access to secret payloads, BigQuery table data or storage objects outside the state bucket
