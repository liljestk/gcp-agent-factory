---
status: accepted
date: 2026-10-23
decision-makers: liljestk
---

# ADR-0012: GitHub Actions with WIF; build once, promote by digest

## Context and problem statement

Deployment must be fully automated from GitHub, with no long-lived credentials, and promotion must be reproducible. The repo is public, which gives us free minutes and environment approvals but also exposes workflows to forks.

## Decision

- **Workload Identity Federation** with the provider condition pinned to `repository_id=1431415117` and `repository_owner_id=4373495`. Separate SAs: `ci-plan`, `ci-apply-dev` (environment `dev`), `ci-apply-prod` (environment `prod`, required reviewer), `ci-foundation` (environment `foundation`, required reviewer) and `ci-killswitch`.
- PR → quality gates + `tofu plan` + cost diff as a PR comment; merge → build images **once**, attest, push by digest → apply and deploy dev → acceptance → approval → the **same digest** to prod with a canary.
- Workflow hygiene: `permissions: {}` by default, `id-token: write` only on jobs that authenticate, `persist-credentials: false`, no `pull_request_target` with a PR checkout, **every action pinned to a commit SHA**, and zizmor + actionlint in CI.

## Consequences

- Good: no keys to leak; an auditable and reproducible chain from commit to prod.
- Bad: approvals by a single maintainer are a formality, but they still create an audit record and a pause.

## Alternatives considered

- **Cloud Build / Cloud Deploy**: GCP-native, but the requirement is GitHub Actions; it would also add cost.
- **SA keys as GitHub secrets**: forbidden (INV-01).

## Enforcement

`repo-checks pins`, zizmor and actionlint in CI; WIF conditions in the bootstrap stack; GitHub environment protection rules managed as code (Phase 1).
