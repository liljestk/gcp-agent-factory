Feature: Plan on pull request, apply on merge, watch for drift
  Every change to infrastructure is planned on its pull request and applied
  from main in stack order, and drift is reported as an issue. Which stacks a
  change affects is specified next to the code, in libs/stacks. The untagged
  scenarios here read the workflow files in-process; the @acceptance ones run
  on GitHub when the pipeline changes.

  @REQ-LZ-005 @security
  Scenario: The job that comments holds no Google credentials
    When I read the "tofu.yml" workflow
    Then the job with "pull-requests: write" has no "id-token" permission
    And the aggregate "tofu-plan" job needs every plan job

  @REQ-LZ-001 @security
  Scenario: No authenticating workflow uses a dangerous trigger
    When I read every workflow that requests "id-token: write"
    Then none is triggered by "pull_request_target", "workflow_run" or "issue_comment"

  @REQ-LZ-006
  Scenario: The workflow applies tiers in order, prod after dev
    When I read the "tofu.yml" workflow
    Then every prod apply job needs the dev apply job of the same tier
    And each tier runs unless an earlier tier failed or was cancelled
    And every apply job runs only in the environment of its instance

  @REQ-LZ-006 @acceptance
  Scenario: A merged canary change applies dev and waits for approval on prod
    Given a change to the "ci-canary" stack is merged to main
    When the pipeline runs
    Then "ci-canary" is applied in "dev" from the saved plan of the same run
    And the "prod" apply waits for approval in the "prod" environment
    And the job summary shows the plan and its SHA-256

  @REQ-LZ-006 @acceptance
  Scenario: No CI apply runs while bootstrap has unapplied changes
    Given "bootstrap" has a merged change the owner has not applied yet
    When a change to "ci-canary" is merged to main
    Then the run stops with "apply bootstrap first"

  @REQ-LZ-007 @acceptance
  Scenario: Drift opens one issue, comments on changes, and closes when resolved
    Given a "ci-canary" output was changed outside OpenTofu
    When the nightly drift run finishes twice
    Then exactly one open issue labelled "drift" names "ci-canary"
    When the change is reverted and the drift run finishes again
    Then that issue is closed

  @REQ-LZ-007 @acceptance
  Scenario: A failing drift check is reported, not silent
    Given the drift run cannot read the state of "ci-canary"
    When the nightly drift run finishes
    Then an issue "Drift check failed: ci-canary/dev" is open

  @REQ-LZ-008 @security
  Scenario: Deployment rules match the code
    When I read the repository's environments and rulesets with the default token
    Then "foundation" and "prod" require a review by the owner
    And "foundation", "dev" and "prod" deploy only from "main" and admins cannot bypass them
    And the "main" ruleset requires the CI checks and "tofu-plan" and blocks force pushes
