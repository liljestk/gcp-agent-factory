@security
Feature: Stack code cannot leak data through a plan
  Plans run code from pull requests and their output is public, so the repo
  checks reject anything that could send data out or put a secret into state.
  These run in-process on every pull request.

  @REQ-LZ-012
  Scenario Outline: Risky constructs in stack code are rejected
    Given a stack file containing <construct>
    When I run the "tofu-safety" check
    Then a finding names the file and line

    Examples:
      | construct                                |
      | a data source of type "external"         |
      | a data source of type "http"             |
      | a "local-exec" provisioner               |
      | a call to "nonsensitive("                |
      | a provider outside the allow-list        |
      | a module sourced from a git URL          |
      | a "google_secret_manager_secret_version" |

  @REQ-LZ-012
  Scenario: Safe stack code passes
    Given a stack file that only uses allow-listed providers and local modules
    When I run the "tofu-safety" check
    Then no findings are reported

  @REQ-LZ-012
  Scenario: ci-plan cannot read data payloads
    When I read every role held by "ci-plan"
    Then none grants access to secret payloads, BigQuery table data or storage objects outside the state bucket
