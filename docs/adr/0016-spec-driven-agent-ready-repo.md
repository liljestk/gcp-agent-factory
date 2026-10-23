---
status: accepted
date: 2026-10-23
decision-makers: liljestk
---

# ADR-0016: Spec-driven, agent-ready repository conventions

## Context and problem statement

Coding agents do much of the building. They need one unambiguous source of instructions, repeatable workflows and guardrails, and humans need to review intent, not just diffs.

## Decision

- **`AGENTS.md`** is canonical (tool-agnostic), with nested `AGENTS.md` per area; **`CLAUDE.md`** imports it and adds only Claude-specific notes.
- **`DESIGN.md`** holds principles and **invariants**, each with an enforcement mechanism.
- **Spec-driven work**: `specs/<NNN-slug>/requirements.md` (requirements with IDs + Gherkin acceptance) → `design.md` (incl. WAF, cost, security) → `tasks.md`.
- **Skills** (`.claude/skills/*/SKILL.md`, a portable format) encode repeatable workflows; **subagents** act as specialised reviewers; **hooks and permissions** block destructive commands.
- **ADRs** (MADR) record decisions; `DESIGN.md` links to them.

## Consequences

- Good: the same context for every agent and human; intent is reviewable; workflows are consistent.
- Bad: docs can drift, which is why the structure is machine-checked.

## Alternatives considered

- **Tool-specific instruction files only**: duplication and drift between tools.
- **Wiki outside the repo**: invisible to coding agents and not versioned with code.

## Enforcement

`repo-checks` validates skill and subagent front matter, ADR format and index, and requirement-to-test traceability. A Claude PreToolUse hook blocks destructive commands.
