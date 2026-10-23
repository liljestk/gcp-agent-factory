@REQ-REPO-003
Feature: Every requirement is traced to a test
  A requirement without a test is a wish, and a test tagged with an unknown
  requirement is noise. Both fail the build.

  Background:
    Given a file "specs/007-demo/requirements.md" containing:
      """
      # 007: Demo

      ### REQ-DEMO-001: Agents can be stopped
      """

  Scenario: A requirement verified by a tagged scenario passes
    Given a file "tests/stop.feature" containing:
      """
      @REQ-DEMO-001
      Feature: Stop agents
      """
    When I run the "traceability" check
    Then no findings are reported

  Scenario: A requirement verified by a tftest covers comment passes
    Given a file "modules/demo/tests/demo.tftest.hcl" containing:
      """
      # covers: REQ-DEMO-001
      run "plan" {}
      """
    When I run the "traceability" check
    Then no findings are reported

  Scenario: A requirement without any test is rejected
    When I run the "traceability" check
    Then a finding for "specs/007-demo/requirements.md:3" mentions "REQ-DEMO-001 has no test"

  Scenario: A scenario tagged with an unknown requirement is rejected
    Given a file "tests/stop.feature" containing:
      """
      @REQ-DEMO-001 @REQ-DEMO-999
      Feature: Stop agents
      """
    When I run the "traceability" check
    Then exactly 1 finding is reported
    And a finding for "tests/stop.feature:1" mentions "REQ-DEMO-999 is not defined"

  Scenario: A requirement defined twice is rejected
    Given a file "specs/008-copy/requirements.md" containing:
      """
      ### REQ-DEMO-001: Agents can be stopped (copy)
      """
    And a file "tests/stop.feature" containing:
      """
      @REQ-DEMO-001
      Feature: Stop agents
      """
    When I run the "traceability" check
    Then a finding for "specs/008-copy/requirements.md:1" mentions "already defined at specs/007-demo/requirements.md:3"

  Scenario: Template folders are ignored
    Given a file "specs/_template/requirements.md" containing:
      """
      ### REQ-AREA-001: Example
      """
    And a file "tests/stop.feature" containing:
      """
      @REQ-DEMO-001
      Feature: Stop agents
      """
    When I run the "traceability" check
    Then no findings are reported
