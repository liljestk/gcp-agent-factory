---
status: accepted
date: 2026-10-23
decision-makers: liljestk
---

# ADR-0011: OpenTofu with client-side state encryption

## Context and problem statement

All infrastructure must be IaC. State files contain sensitive data (resource attributes, sometimes secrets) and are a high-value target.

## Decision

- **OpenTofu** (pinned in `mise.toml`) for everything.
- GCS backend in `gcp-agent-factory-seed`: versioning, uniform access, public-access prevention, CMEK, and one state per `stack × env`.
- **OpenTofu state and plan encryption** (`aes_gcm` with a `gcp_kms` key provider), so state is encrypted before it leaves the runner.
- Stacks share data through a small, explicit set of outputs (`terraform_remote_state`, read-only); modules never read remote state.
- Lock files are committed for root modules.

## Consequences

- Good: a stolen bucket object or a leaked CI artifact is useless without KMS decrypt.
- Bad: KMS becomes critical for every plan and apply; key rotation and access must be designed in bootstrap.
- Bad: some Terraform-only ecosystem tools may not support encrypted state.

## Alternatives considered

- **Terraform**: no client-side state encryption; BSL licence.
- **Pulumi / Config Connector**: further from the "OpenTofu" requirement.

## Enforcement

The bootstrap stack creates the key and backend; CI fails if a stack lacks the `encryption` block (repo check, Phase 1).
