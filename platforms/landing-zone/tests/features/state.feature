@security
Feature: Encrypted, partitioned remote state
  State and saved plans are ciphertext outside the runner, the bucket is hard
  to lose, and each CI identity reaches only its own state. These read-only
  checks run nightly as ci-plan.

  @REQ-LZ-003
  Scenario: A stored state object is an encryption envelope
    When I download the state object of stack "bootstrap"
    Then it is an OpenTofu encryption envelope
    And it contains no plaintext resources

  @REQ-LZ-003
  Scenario: The state bucket and seed project resist deletion
    When I read the settings of the state bucket
    Then versioning, uniform bucket-level access and soft delete are on
    And public access prevention is enforced
    And its default encryption key is "tfstate/bucket"
    And it carries the standard labels
    And the seed project has a lien against deletion

  @REQ-LZ-004
  Scenario Outline: The bucket policy limits each identity to its prefixes
    When I read the IAM policy of the state bucket
    Then "<identity>" may <access> objects under "<prefix>": <allowed>

    Examples:
      | identity      | access | prefix                | allowed |
      | ci-plan       | write  | shared/foundation/    | no      |
      | ci-plan       | read   | trust-root/bootstrap/ | yes     |
      | ci-plan       | read   | trust-root/github/    | no      |
      | ci-plan       | write  | trust-root/bootstrap/ | no      |
      | ci-foundation | write  | trust-root/bootstrap/ | no      |
      | ci-foundation | write  | dev/network/          | no      |
      | ci-foundation | write  | shared/foundation/    | yes     |
      | ci-apply-dev  | write  | prod/network/         | no      |
      | ci-apply-dev  | delete | trust-root/bootstrap/ | no      |
      | ci-apply-dev  | write  | dev/network/          | yes     |
      | ci-apply-prod | write  | dev/network/          | no      |

  @REQ-LZ-004
  Scenario Outline: Each identity can use only the state keys it needs
    When I read the IAM policy of state key "<key>"
    Then "<identity>" may <use> with it: <allowed>

    Examples:
      | key              | identity      | use     | allowed |
      | state-prod       | ci-apply-dev  | decrypt | no      |
      | state-dev        | ci-apply-prod | decrypt | no      |
      | state-dev        | ci-foundation | encrypt | no      |
      | state-trust-root | ci-foundation | encrypt | no      |
      | state-shared     | ci-foundation | encrypt | yes     |
      | state-trust-root | ci-apply-dev  | decrypt | yes     |
