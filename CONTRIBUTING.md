# Contributing

1. Read [`AGENTS.md`](AGENTS.md). It applies to humans too.
2. For anything beyond a small fix, start a spec in `specs/` (template in `specs/_template/`).
3. Branch from `main` and use Conventional Commits (enforced by a commit-msg hook).
4. Run `just check` before pushing. CI runs exactly the same recipes.
5. Open a PR with the template filled in, including **cost impact** and **security impact**.

## Development environment

- Windows: use the devcontainer. It pins every tool and avoids path and line-ending issues.
- macOS/Linux: `mise install && just setup`.

## Reviews

Infra changes get an OpenTofu plan and a cost diff on the PR (from Phase 1). Changes to agents, prompts or tools trigger agent evals (from Phase 3).
