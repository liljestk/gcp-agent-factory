@REQ-REPO-004
Feature: Coverage exclusions are justified
  100% coverage is only meaningful if every exclusion says why it exists.

  Scenario: A justified exclusion passes
    Given a file "src/app.py" containing:
      """
      def handler() -> None:  # pragma: no cover -- exercised by the deployed smoke suite
          pass
      """
    When I run the "pragmas" check
    Then no findings are reported

  Scenario: An exclusion without a reason is rejected
    Given a file "src/app.py" containing:
      """
      import os

      def handler() -> None:  # pragma: no cover
          pass
      """
    When I run the "pragmas" check
    Then a finding for "src/app.py:3" mentions "needs a reason"

  Scenario: A branch exclusion without a reason is rejected
    Given a file "src/app.py" containing:
      """
      if True:  # pragma: no branch
          pass
      """
    When I run the "pragmas" check
    Then a finding for "src/app.py:1" mentions "needs a reason"
