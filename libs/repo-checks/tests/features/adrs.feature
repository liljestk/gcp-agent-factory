@REQ-REPO-002
Feature: ADRs are well-formed and indexed
  Decisions are only useful if they can be found and their status is clear.

  Background:
    Given a file "docs/adr/README.md" containing:
      """
      | [0001](0001-use-cloud-run.md) | Use Cloud Run | accepted |
      """

  Scenario: A well-formed, indexed ADR passes
    Given a file "docs/adr/0001-use-cloud-run.md" containing:
      """
      ---
      status: accepted
      date: 2026-10-23
      ---

      # ADR-0001: Use Cloud Run
      """
    When I run the "adrs" check
    Then no findings are reported

  Scenario: An ADR with an unknown status is rejected
    Given a file "docs/adr/0001-use-cloud-run.md" containing:
      """
      ---
      status: maybe
      ---

      # ADR-0001: Use Cloud Run
      """
    When I run the "adrs" check
    Then a finding for "docs/adr/0001-use-cloud-run.md" mentions "invalid status 'maybe'"

  Scenario: A superseded ADR names its successor
    Given a file "docs/adr/0001-use-cloud-run.md" containing:
      """
      ---
      status: superseded by ADR-0007
      ---

      # ADR-0001: Use Cloud Run
      """
    When I run the "adrs" check
    Then no findings are reported

  Scenario: An ADR whose title number differs from its file name is rejected
    Given a file "docs/adr/0001-use-cloud-run.md" containing:
      """
      ---
      status: accepted
      ---

      # ADR-0002: Use Cloud Run
      """
    When I run the "adrs" check
    Then a finding for "docs/adr/0001-use-cloud-run.md" mentions "first heading must be '# ADR-0001: <title>'"

  Scenario: An ADR missing from the index is rejected
    Given a file "docs/adr/0002-use-pubsub.md" containing:
      """
      ---
      status: proposed
      ---

      # ADR-0002: Use Pub/Sub
      """
    When I run the "adrs" check
    Then a finding for "docs/adr/0002-use-pubsub.md" mentions "not linked from docs/adr/README.md"

  Scenario: An ADR with a badly formed file name is rejected
    Given a file "docs/adr/Use_Cloud_Run.md" containing:
      """
      # Use Cloud Run
      """
    When I run the "adrs" check
    Then a finding for "docs/adr/Use_Cloud_Run.md" mentions "file name must be NNNN-kebab-case-title.md"

  Scenario: Two ADRs with the same number are rejected
    Given a file "docs/adr/0001-use-cloud-run.md" containing:
      """
      ---
      status: accepted
      ---

      # ADR-0001: Use Cloud Run
      """
    And a file "docs/adr/0001-use-gke.md" containing:
      """
      ---
      status: rejected
      ---

      # ADR-0001: Use GKE
      """
    When I run the "adrs" check
    Then a finding for "docs/adr/0001-use-gke.md" mentions "duplicate ADR number 0001"
