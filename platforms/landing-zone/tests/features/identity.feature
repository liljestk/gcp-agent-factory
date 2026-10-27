@security
Feature: Keyless CI identities
  Only this repository can reach Google Cloud, and each job gets only the
  identity its context allows. These read-only checks run nightly as
  ci-plan and after each bootstrap apply.

  @REQ-LZ-001
  Scenario: The trust condition uses immutable IDs, not the repository name
    When I read the "github" workload identity provider
    Then its condition requires repository ID "1431415117" and owner ID "4373495"
    And its condition does not mention the repository name

  @REQ-LZ-001
  Scenario Outline: Tokens from other repositories fail the trust condition
    Given the claims of a GitHub token from <origin>
    When the live provider condition is evaluated against them
    Then the result is <result>

    Examples:
      | origin                              | result |
      | this repository                     | true   |
      | a fork's own repository             | false  |
      | a new repository with the same name | false  |
      | a repository of another owner       | false  |

  @REQ-LZ-001
  Scenario: No CI identity has a key
    When I list the keys of every CI service account
    Then none has a user-managed key

  @REQ-LZ-002
  Scenario Outline: Apply identities are reachable only from the reviewed workflow on main
    Given the claims of a GitHub token for <job>
    When the live deploy mapping is evaluated against them
    Then it maps to "<value>"

    Examples:
      | job                                          | value      |
      | tofu.yml on main in environment prod         | prod       |
      | tofu.yml on main in environment foundation   | foundation |
      | tofu.yml on a branch in environment prod     | none       |
      | another workflow on main in environment prod | none       |
      | tofu.yml on main on a self-hosted runner     | none       |
      | tofu.yml on main without an environment      | none       |

  @REQ-LZ-002
  Scenario Outline: ci-plan is reachable only for the owner's pull requests and runs on main
    Given the claims of a GitHub token for <run>
    When the live plan mapping is evaluated against them
    Then it maps to "<value>"

    Examples:
      | run                                    | value   |
      | a pull request opened by the owner     | allowed |
      | a pull request opened by a bot         | denied  |
      | a dispatch by the owner on a PR branch | allowed |
      | a push to a branch other than main     | denied  |
      | the nightly schedule on main           | allowed |

  @REQ-LZ-002
  Scenario: Each CI identity is bound only to its own gate
    When I read the IAM policy of every CI service account
    Then "ci-plan" is usable only by the "plan" gate value "allowed"
    And "ci-foundation", "ci-apply-dev" and "ci-apply-prod" are usable only by their own "deploy" gate value
    And no human or group holds "Workload Identity User" or "Service Account Token Creator" on any of them
