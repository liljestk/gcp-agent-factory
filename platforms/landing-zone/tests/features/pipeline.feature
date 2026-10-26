Feature: Plan on pull request, apply on merge, watch for drift
  Every change to infrastructure is planned on its pull request and applied
  from main in stack order, and drift is reported as an issue. The untagged
  scenarios run in-process on every pull request; the @acceptance ones run
  on GitHub when the pipeline changes.

  @REQ-LZ-005
  Scenario: A module change plans every stack that uses it
    Given the stack "bootstrap" uses module "kms" through module "project"
    When the affected stacks are computed for a change to "modules/kms/main.tf"
    Then "bootstrap" is planned

  @REQ-LZ-005
  Scenario: A toolchain change plans every stack, a docs change plans none
    When the affected stacks are computed for a change to "mise.toml"
    Then every CI-plannable stack is planned
    When the affected stacks are computed for a change to "docs/PLAN.md"
    Then nothing is planned

  @REQ-LZ-005
  Scenario: The github stack is never planned in CI
    When the affected stacks are computed for a change to "platforms/landing-zone/infra/github/main.tf"
    Then nothing is planned

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
  Scenario: Trust-root stacks get no apply job, and prod waits for dev
    When the apply matrix is computed for a change to every stack
    Then no apply job exists for "bootstrap" or "github"
    And every prod job needs the dev job of the same tier
    And an unaffected tier does not block the tiers after it

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
