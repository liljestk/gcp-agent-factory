# 001: Repo foundations (tasks)

- [x] 1. Toolchain: `mise.toml`, `.python-version`, uv workspace, `justfile`, pre-commit, linters config
- [x] 2. Agent conventions: `AGENTS.md`, `CLAUDE.md`, `DESIGN.md`, nested `modules/AGENTS.md`
- [x] 3. ADRs 0001–0016 + index + template; spec template; WAF checklist
- [x] 4. Claude skills, subagents, settings and hooks
- [x] 5. `libs/repo-checks` with BDD features + unit tests at 100% coverage
- [x] 6. `modules/labels` with `tofu test`
- [x] 7. CI (`ci.yml`, `codeql.yml`), Renovate, CODEOWNERS, PR template, devcontainer
- [x] 8. `just check` and `pre-commit run --all-files` green (verified natively on Windows: mise toolchain + Git Bash, 2026-10-23)
- [x] 8b. Build the devcontainer image and run `just check` inside it on a fresh clone (green, 2026-10-24). A bind-mounted Windows folder makes every file look executable (ruff `EXE002`), so `AGENTS.md` recommends a container volume; the first start runs `just deps` so no container-only git hooks land in the shared checkout
- [x] 9. First push; enable GitHub settings (2026-10-24, CI green on Linux): secret scanning push protection (on by default for public repos), private vulnerability reporting, Dependabot alerts (which turn on the dependency graph that `dependency review` needs; automatic fix PRs stay off, Renovate owns updates), and ruleset `main` (no deletion or force push, PRs only with 0 approvals, the 7 CI and CodeQL checks required from GitHub Actions, branch up to date). Moves to code in Phase 1 (`integrations/github` provider)
- [ ] 10. Install the Renovate GitHub App on the repo
