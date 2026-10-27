# 002: Bootstrap and CI pipeline (tasks)

Work through in order. Tick a task only when its tests pass under `just check`.

- [x] 1. Write the `.feature` scenarios tagged with the requirement IDs (`platforms/landing-zone/tests/features/`)
- [x] 2. `libs/stacks` + `platforms/stacks.yaml`: move the in-process `pipeline` scenarios next to the code, write unit tests at 100%, then the code (module expansion, "all stacks" paths, trust-root modes, tiers) (REQ-LZ-005/006)
- [x] 3. `repo-checks encryption` and `repo-checks tofu-safety`: move the `safety` scenarios, write unit tests, then the checks (REQ-LZ-003/012). Reuse the HCL parsing from `libs/stacks`, and also flag `file()`, `templatefile()` and `fileset()` paths that leave the module directory unless the stack declares them in `inputs`. Follow-ups from the review:
  - match a file read only against the `inputs` of the stacks that actually use its directory
  - require a committed lock file for every stack that uses a provider
  - reject `TF_ENCRYPTION` in workflows (task 7)
  - leaks through attacker-owned GCP resources are VPC-SC's job (spec 004)
- [x] 4. `modules/kms`, `modules/project`, `modules/wif-github`, each with `tofu test`: plan and deploy gates evaluated against claim fixtures, labels, lien, rotation (`# covers:` REQ-LZ-001/002/003/009)
- [ ] 5. `bootstrap` stack with `tofu test` on mock providers (REQ-LZ-004/010/011). Keep its tests on `command = plan`, because the keys' `prevent_destroy` makes an apply run's cleanup fail. It covers:
  - folders and the per-identity role allow-list per scope
  - one mode per role, and the deny policy
  - state prefix and key grants, bucket protections
  - the gross-cost billing-account budget
  - from the module reviews:
    - no Service Account Token Creator for anyone on the CI identities
    - a `@security` check that no seed, `trust-root` or org grant (Workload Identity User, Token Creator, Service Account User, OpenID Token Creator) reaches a CI identity or the pool
    - a deny policy that also covers moving the project, its liens and its billing link
    - a single provider in pool `github`, enforced with `iam.workloadIdentityPoolProviders`
    - Data Access logs for `sts` and `iamcredentials` on the seed
    - `compute.skipDefaultNetworkCreation` on `trust-root`
- [ ] 6. `github` stack with `tofu test`: environments, reviewers, branch policies, `can_admins_bypass = false`, `prevent_destroy`, the ruleset import with `tofu-plan`, variables (REQ-LZ-008)
- [ ] 7. `ci-canary` stack (dev and prod), workflows `tofu.yml` and `drift.yml`, and the composite actions. actionlint and zizmor clean; `gha-creds-*.json` added to `.gitignore`; `stacks validate` added to `just check` once every catalog path exists. The matrix job checks out with `fetch-depth: 0` and runs `stacks matrix --base` under `shell: bash`. The aggregate `tofu-plan` fails unless the matrix job succeeded. PR runs plan the union of the base and head versions of the tool and catalog. Matrix values reach `run:` steps only through `env:`. `stacks validate` also checks that a workflow job exists for every non-empty apply group. The apply job checks that the run's commit is still `main`'s head, so re-running an old push can't roll infra back (REQ-LZ-005/006/007)
- [ ] 8. Step definitions for the deployed scenarios in `libs/testing`, a `just acceptance` recipe, and the nightly run in `drift.yml` as `ci-plan`
- [ ] 9. `docs/runbooks/bootstrap.md` (first run, isolated credentials, migration, stale plans, locks, state restore, trust-root change flow); add `gcloud` to `mise.toml`; rehearse the encryption sequence locally with `pbkdf2`
- [ ] 10. `just check` green; `tofu-reviewer`, `security-reviewer`, `waf-reviewer` and `finops-reviewer` run on the implementation
- [ ] 11. **Owner**: manual prerequisites (PLAN §12), first `bootstrap` apply, state migration, `github` apply, credential clean-up
- [ ] 12. The deployed `@security` scenarios pass; a PR touching `bootstrap` shows an empty CI plan; a `ci-canary` merge applies dev and waits for approval on prod; the STS refusal from a scratch repository is confirmed
