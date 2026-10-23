@REQ-REPO-008 @acceptance
Feature: The repository follows its own conventions
  The checks are dogfooded: gcp-agent-factory itself must stay clean.

  Scenario: Every repo check passes on gcp-agent-factory
    Given the gcp-agent-factory repository
    When I run repo-checks with "all"
    Then repo-checks exits with code 0
