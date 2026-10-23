---
status: accepted
date: 2026-10-23
decision-makers: liljestk
---

# ADR-0001: Monorepo layout and toolchain

## Context and problem statement

Four platforms (agents, landing zone, data, ops) share identity, labels, events and CI. They must evolve together, be readable by coding agents, and work the same on a Windows laptop and in CI.

## Decision

- One monorepo, **domain-oriented**: `platforms/<name>/` holds that platform's infra, code and tests. Shared pieces live in `modules/` (OpenTofu) and `libs/` (Python).
- **uv workspace** for Python (one lockfile), **just** as the task runner, **mise** pinning every CLI tool, and a **devcontainer** as the canonical environment on Windows.
- **Version policy**: exact pins, at least 7 days old (a supply-chain cooldown). Renovate proposes upgrades.
- CI calls the same `just` recipes as developers do.

## Consequences

- Good: one PR can change an event schema, its producer, its consumer and their infra atomically; tool drift between laptop and CI disappears.
- Good: path-based CI filters and CODEOWNERS map cleanly onto `platforms/*`.
- Bad: CI must be change-aware to stay fast as the repo grows (path filters, per-stack matrices).
- Bad: Windows users need Docker for the devcontainer (already installed here).

## Alternatives considered

- **Polyrepo per platform**: cross-cutting changes become multi-PR choreography, which is bad for a demo.
- **Make / Taskfile**: `just` is cross-platform, simpler, and has no tab or phony pitfalls.
- **Poetry / pip-tools**: uv is faster and has native workspaces.

## Enforcement

`mise.toml` and `uv.lock` are committed; CI installs from them (`uv sync --frozen`, `jdx/mise-action`). `repo-checks pins` rejects unpinned Actions and hooks.
