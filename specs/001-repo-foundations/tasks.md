# 001: Repo foundations (tasks)

- [x] 1. Toolchain: `mise.toml`, `.python-version`, uv workspace, `justfile`, pre-commit, linters config
- [x] 2. Agent conventions: `AGENTS.md`, `CLAUDE.md`, `DESIGN.md`, nested `modules/AGENTS.md`
- [x] 3. ADRs 0001–0016 + index + template; spec template; WAF checklist
- [x] 4. Claude skills, subagents, settings and hooks
- [x] 5. `libs/repo-checks` with BDD features + unit tests at 100% coverage
- [x] 6. `modules/labels` with `tofu test`
- [x] 7. CI (`ci.yml`, `codeql.yml`), Renovate, CODEOWNERS, PR template, devcontainer
- [x] 8. `just check` and `pre-commit run --all-files` green (verified natively on Windows: mise toolchain + Git Bash, 2026-10-23)
- [ ] 8b. Build the devcontainer image and run `just check` inside it (not yet verified: Docker engine was unavailable)
- [ ] 9. First push; enable GitHub settings (secret scanning push protection, private vulnerability reporting, rulesets requiring CI). Moves to code in Phase 1 (`integrations/github` provider)
- [ ] 10. Install the Renovate GitHub App on the repo
