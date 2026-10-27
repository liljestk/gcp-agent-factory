---
status: proposed
date: 2026-10-26
decision-makers: liljestk
---

# ADR-0018: Apply the trust-root stacks locally, everything else through CI

## Context and problem statement

Two stacks decide who can deploy:

- **`bootstrap`** creates the seed project, the state bucket and KMS keys, the WIF pool, the CI service accounts and their org-level and billing-account roles. It also removes the domain-wide creator grants ([ADR-0017](0017-existing-sandbox-org.md)).
- **`github`** sets the GitHub environments, required reviewers, deployment branches and the `main` ruleset ([ADR-0012](0012-github-actions-wif-promote-by-digest.md)).

Whoever applies these can give any CI identity any power, including its own.

To apply them from CI, a service account would need org IAM admin plus Billing Account Administrator on the free-trial billing account. A GitHub App would also need repo admin, with its private key stored as a secret. That is a standing super-credential, and it would be gated only by a single maintainer's approval. These stacks change rarely, about once per phase.

Keeping CI away from the trust root takes more than not applying `bootstrap` from CI. [ADR-0009](0009-org-and-project-topology.md) puts the seed project in the `shared` folder, and `ci-foundation` would administer folders. Folder Admin includes `setIamPolicy` on the folder, and that is inherited by the seed project. So `ci-foundation` could grant itself access to the state, the keys and the WIF pool.

INV-03 says infra changes reach GCP only through CI, but `bootstrap` can't: its first run creates the very identities CI uses.

## Decision

- **`bootstrap` and `github` are trust-root stacks.** Only the owner applies them, locally:
  - `bootstrap` with their org identity
  - `github` with a short-lived, fine-grained GitHub token for this repository
- **Changes still go through a PR.**
  - CI plans `bootstrap` on the PR with the read-only `ci-plan`.
  - After merge, the owner applies from a clean checkout of `origin/main`. The apply recipe checks this.
  - The owner plans `github` locally.
- **`bootstrap` owns the org root**: the top-level folders `trust-root`, `shared`, `dev` and `prod`, and all org-level IAM.
  - The seed project moves from `shared` (ADR-0009) to its own `trust-root` folder.
  - No CI identity holds any role on `trust-root`, on the seed project, or at org level that is inherited by them, apart from `ci-plan`'s viewer roles. The one exception is Organization Policy Administrator, which can only be granted at org level; see Consequences.
  - `ci-foundation` administers folders, projects and project billing on `shared`, `dev` and `prod` only.
  - An IAM deny policy on `trust-root`, managed by `bootstrap`, denies every CI identity the permissions that would change IAM, keys, the WIF pool, the state bucket, or the seed project's existence and billing. It holds even if a grant slips through.
- **CI watches for drift.**
  - Every night it plans `bootstrap` with `ci-plan`.
  - It also checks the GitHub environments, branch policies and the ruleset read-only, with the default `GITHUB_TOKEN`.
- **Every other stack** (`foundation` onwards) is applied only by CI.
- **INV-03 is reworded**: infra changes reach GCP only through CI, except the trust-root stacks, which the owner applies locally.

## Consequences

- Good: no CI identity can grant org-level, billing or trust-root roles, change its own trust, or reach trust-root state. No GitHub admin secret exists.
- Good: the first run and every later run use the same path, so there is no hand-over from local to CI to get wrong.
- Bad: the trust-root credential lives on the owner's workstation, next to coding agents that read untrusted content. Claude's deny rules and hook are an accident guard, not a security boundary. Instead, the runbook requires:
  - a separate gcloud configuration for trust-root applies, with no coding agent running
  - revoking application-default credentials afterwards
  - a GitHub token that expires the same day
- Bad: a trust-root change needs the owner at a terminal, and each later spec that needs new seed APIs or CI roles must land a `bootstrap` change first. CI enforces this order: apply jobs wait until `bootstrap` plans empty.
- Bad: Organization Policy Administrator can only be granted at org level, so `ci-foundation` can still set policies on the seed project. That allows denial of service (for example, blocking an API), not takeover. Drift detection and the deny policy limit the damage.
- Bad: ADR-0009's "foundation is the only creator of folders and projects" no longer holds. `bootstrap` creates the top-level folders and the seed project.

## Alternatives considered

- **Apply `bootstrap` from CI**, with a `ci-bootstrap` service account behind an `environment:bootstrap` that requires a reviewer. This keeps INV-03 without exceptions, but needs the standing super-credential described above. A compromised approval would hand over the whole org and the billing account.
- **Keep the seed in `shared` and rely on a deny policy alone**: this works, but if the deny policy is ever wrong, one stray grant reopens the takeover path. A folder with no CI roles at all fails safe.
- **A GitHub App with admin rights for the `github` stack**: a long-lived private key in GitHub secrets, just to manage a handful of settings.

## Enforcement

- **IAM, as the real control**: no CI identity can write `trust-root/` state, hold a role on the `trust-root` folder or the seed project (apart from `ci-plan`'s viewer roles), or hold an org-level admin role. The deny policy backs this up.
- **The `bootstrap` stack's `tofu test`** pins each CI identity's exact role set per scope as an allow-list:
  - org, folder, seed and billing account
  - the deny policy's principals and permissions
  - that no role is managed both authoritatively and additively
- **The pipeline's stack catalog** marks `bootstrap` and `github` as local-only. Its unit tests prove that no apply job is generated for them and that `github` is never planned in CI.
- **The nightly drift run** plans `bootstrap` and runs the read-only `@security` checks, opening an issue on any difference.
- **DESIGN.md INV-03** states the exception.
