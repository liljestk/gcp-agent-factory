@REQ-REPO-005
Feature: Third-party CI and hook code is pinned to commit SHAs
  Tags can be moved by whoever controls the upstream repository. Commit SHAs can't.

  Scenario: A workflow with SHA-pinned and local actions passes
    Given a file ".github/workflows/ci.yml" containing:
      """
      jobs:
        build:
          steps:
            - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
            - uses: ./.github/actions/setup
      """
    When I run the "pins" check
    Then no findings are reported

  Scenario: A workflow action pinned to a tag is rejected
    Given a file ".github/workflows/ci.yml" containing:
      """
      jobs:
        build:
          steps:
            - uses: actions/checkout@v7
      """
    When I run the "pins" check
    Then a finding for ".github/workflows/ci.yml:4" mentions "actions/checkout@v7 must be pinned to a full 40-character commit SHA"

  Scenario: A Docker action must be pinned by digest
    Given a file ".github/workflows/ci.yml" containing:
      """
      jobs:
        build:
          steps:
            - uses: docker://alpine:3
      """
    When I run the "pins" check
    Then a finding for ".github/workflows/ci.yml:4" mentions "must be pinned by @sha256 digest"

  Scenario: A pre-commit hook repository pinned to a tag is rejected
    Given a file ".pre-commit-config.yaml" containing:
      """
      repos:
        - repo: https://github.com/pre-commit/pre-commit-hooks
          rev: v6.0.0
          hooks:
            - id: check-yaml
        - repo: local
          hooks:
            - id: ruff
      """
    When I run the "pins" check
    Then exactly 1 finding is reported
    And a finding for ".pre-commit-config.yaml" mentions "rev 'v6.0.0' must be a full 40-character commit SHA"
