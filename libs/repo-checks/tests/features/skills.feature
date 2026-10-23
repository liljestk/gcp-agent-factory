@REQ-REPO-001
Feature: Skills and subagents are well-formed
  Coding agents only discover skills and subagents whose front matter is valid,
  so a broken one must fail the build instead of silently disappearing.

  Scenario: A well-formed skill passes
    Given a file ".claude/skills/spec-new/SKILL.md" containing:
      """
      ---
      name: spec-new
      description: Scaffold a new spec folder.
      ---
      # spec-new
      """
    When I run the "skills" check
    Then no findings are reported

  Scenario: A skill whose name differs from its folder is rejected
    Given a file ".claude/skills/spec-new/SKILL.md" containing:
      """
      ---
      name: new-spec
      description: Scaffold a new spec folder.
      ---
      """
    When I run the "skills" check
    Then a finding for ".claude/skills/spec-new/SKILL.md" mentions "must equal 'spec-new'"

  Scenario: A skill without a description is rejected
    Given a file ".claude/skills/spec-new/SKILL.md" containing:
      """
      ---
      name: spec-new
      ---
      """
    When I run the "skills" check
    Then a finding for ".claude/skills/spec-new/SKILL.md" mentions "description is required"

  Scenario: A skill folder without SKILL.md is rejected
    Given an empty directory ".claude/skills/orphan"
    When I run the "skills" check
    Then a finding for ".claude/skills/orphan" mentions "missing SKILL.md"

  Scenario: A well-formed subagent passes
    Given a file ".claude/agents/tofu-reviewer.md" containing:
      """
      ---
      name: tofu-reviewer
      description: Reviews OpenTofu changes.
      tools: Read, Grep
      ---
      You review OpenTofu code.
      """
    When I run the "subagents" check
    Then no findings are reported

  Scenario: A subagent without front matter is rejected
    Given a file ".claude/agents/tofu-reviewer.md" containing:
      """
      You review OpenTofu code.
      """
    When I run the "subagents" check
    Then a finding for ".claude/agents/tofu-reviewer.md" mentions "missing or invalid YAML front matter"
