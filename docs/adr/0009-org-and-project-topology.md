---
status: accepted
date: 2026-10-23
decision-makers: liljestk
---

# ADR-0009: Org, folder and project topology

> [ADR-0017](0017-existing-sandbox-org.md) replaces the first decision bullet (organization and domain); the rest of this ADR stands.

## Context and problem statement

A credible landing zone needs an organization (folders, org policies, VPC-SC). The free-trial billing account likely caps linked projects at around 5. The region must balance EU residency, carbon and cost.

## Decision

- **Cloud Identity Free** organization on a domain derived from the repo name (domain TBD; the org's name *is* its primary domain).
- Folders `shared`, `dev`, `prod`; org-level tag `env` bound to the folders.
- Five projects: `gcp-agent-factory-seed`, `-ops` (in `shared`), `-dev` (in `dev`), `-prod` (in `prod`), and one dedicated demo app project `gaf-app-<name>` (in `dev`). Each ID carries a 4-character suffix generated once in bootstrap, because deleted project IDs can never be reused.
- Primary region **`europe-north1`**; DR target `europe-west1`.
- Org policies cover security baselines and **cost guardrails** (`gcp.resourceLocations` limited to EU, a `gcp.restrictServiceUsage` deny list for expensive services, CPU and GPU quotas set to 0). All of them roll out in dry-run first.

## Consequences

- Good: dev and prod isolation with promotion, inside the project quota.
- Bad: inside an env project, platforms are separated by identity, not by project. Per-platform projects become possible once the quota is raised (the project factory makes that a variable change).

## Alternatives considered

- **No org**: no folders, org policies or VPC-SC, so a weak security demo.
- **Per-platform projects (~9)**: the strongest isolation, but it needs a quota increase up front.
- **us-central1**: cheapest, but no EU residency.

## Enforcement

The `foundation` stack is the only creator of folders, projects and policies; `@security` BDD scenarios prove that the key policies deny what they should.
