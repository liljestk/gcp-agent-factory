Feature: Plan and apply only what a change affects
  The pipeline turns a diff into plan and apply jobs from the stack catalog.
  It reads the diff from git so renames and unusual names can't hide, follows
  module references, treats pipeline and toolchain files as affecting every
  stack, fails closed on anything it can't follow, and never applies a
  trust-root stack (ADR-0018).

  Background:
    Given the stack catalog:
      | stack      | tier       | instances  | plan  | apply |
      | bootstrap  |            | trust-root | ci    | local |
      | github     |            | trust-root | local | local |
      | network    | network    | dev, prod  | ci    | ci    |
      | dns        | network    | shared     | ci    | ci    |
      | foundation | foundation | shared     | ci    | ci    |
      | ci-canary  | canary     | dev, prod  | ci    | ci    |
    And the stack "bootstrap" uses module "project", which uses module "kms"
    And the stack "network" uses module "vpc"

  @REQ-LZ-005
  Scenario: A module change plans every stack that uses it, directly or not
    When the affected stacks are computed for a change to "modules/kms/main.tf"
    Then the plan jobs are "bootstrap/trust-root"

  @REQ-LZ-005
  Scenario: A change inside a stack plans and applies each of its instances
    When the affected stacks are computed for a change to "stacks/network/main.tf"
    Then the plan jobs are "network/dev, network/prod"
    And the apply groups with jobs are "network/dev, network/prod"

  @REQ-LZ-005
  Scenario Outline: Pipeline and toolchain changes plan every stack CI can plan
    When the affected stacks are computed for a change to "<path>"
    Then the plan jobs are "bootstrap/trust-root, ci-canary/dev, ci-canary/prod, dns/shared, foundation/shared, network/dev, network/prod"

    Examples:
      | path                                  |
      | mise.toml                             |
      | platforms/stacks.yaml                 |
      | .github/workflows/tofu.yml            |
      | .github/actions/tofu-stack/action.yml |

  @REQ-LZ-005
  Scenario: A change outside stacks, modules and the pipeline plans nothing
    When the affected stacks are computed for a change to "docs/PLAN.md"
    Then nothing is planned or applied

  @REQ-LZ-005
  Scenario: The github stack is never planned in CI
    When the affected stacks are computed for a change to "stacks/github/main.tf"
    Then nothing is planned or applied

  @REQ-LZ-005
  Scenario: Moving a file out of a stack still plans the stack
    Given the repository is committed
    When a commit moves "stacks/network/main.tf" to "archive/main.tf"
    And the jobs are computed from git since the first commit
    Then the plan jobs are "network/dev, network/prod"

  @REQ-LZ-005
  Scenario: A file with a non-ASCII name is not overlooked
    Given the repository is committed
    When a commit adds "stacks/network/brandvägg.tf"
    And the jobs are computed from git since the first commit
    Then the plan jobs are "network/dev, network/prod"

  @REQ-LZ-005
  Scenario: A module source the pipeline can't follow stops the run
    Given the stack "network" also uses a module with the source expression "local.module_path"
    When the jobs are computed for every stack
    Then the run fails because "must be a literal string"

  @REQ-LZ-006
  Scenario: Trust-root stacks are planned but never applied
    When the jobs are computed for every stack
    Then the plan jobs include "bootstrap/trust-root"
    And no apply job exists for "bootstrap" or "github"

  @REQ-LZ-006
  Scenario: Apply groups follow the stack order, shared before dev before prod
    When the jobs are computed for every stack
    Then the apply groups in order are "canary/shared, canary/dev, canary/prod, foundation/shared, foundation/dev, foundation/prod, network/shared, network/dev, network/prod"
    And the apply groups with jobs are "canary/dev, canary/prod, foundation/shared, network/shared, network/dev, network/prod"

  @REQ-LZ-006
  Scenario: A catalog that lets CI apply a trust-root stack is rejected
    Given the catalog says CI applies the stack "bootstrap"
    When the catalog is loaded
    Then it is rejected because "only trust-root stacks are applied locally"

  @REQ-LZ-006
  Scenario: A stack can't pull in another stack's code as a module
    Given the stack "foundation" uses the directory of stack "bootstrap" as a module
    When the jobs are computed for every stack
    Then the run fails because "inside stack 'bootstrap'"
