---
status: accepted
date: 2026-10-23
decision-makers: liljestk
---

# ADR-0003: Cloud Run as the agent runtime

## Context and problem statement

Agents need an isolated identity, autoscaling, authenticated ingress and near-zero idle cost on a $300 budget.

## Decision

Run **one Cloud Run service per agent**: scale-to-zero, request-based billing, `max_instances` caps, startup CPU boost, Direct VPC egress, and its own service account (ADR-0007). Human-facing endpoints use IAP on Cloud Run directly (no load balancer). Service-to-service calls use Cloud Run IAM with Google-signed ID tokens.

## Consequences

- Good: $0 idle; per-agent identity, revisions, canaries and rollback come built in.
- Good: the same pattern serves vended apps (landing zone paved road).
- Bad: we build session and memory persistence ourselves (Firestore) instead of getting Agent Engine's managed sessions and Memory Bank.
- Bad: we must confirm IAP-on-Cloud-Run GA status (it was Preview in 2025).

## Alternatives considered

- **Vertex AI Agent Engine**: managed sessions, memory and per-agent Agent Identity, but sessions and memory are billed, and Agent Identity is documented as test-only and needs an org. Kept as an optional deploy target (Phase 7).
- **GKE Autopilot**: pod and node costs, plus operational weight, for no demo benefit.

## Enforcement

`modules/agent-service` is the only way to deploy an agent; conftest checks `max_instances` and that ingress isn't public without IAP.
