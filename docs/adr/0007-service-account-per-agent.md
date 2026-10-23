---
status: accepted
date: 2026-10-23
decision-makers: liljestk
---

# ADR-0007: One service account per agent, generated from a manifest

## Context and problem statement

Agents must have their own identities, be tagged, be attributable for FinOps and be individually killable. Hand-maintained IAM drifts.

## Decision

Each agent has a manifest `platforms/agents/registry/<name>.yaml` (validated by `contracts/agent.schema.json`). OpenTofu iterates over the manifests and, per agent, creates:

- the service account `agt-<name>` with only the roles the manifest declares (custom roles where predefined ones are too broad);
- the Cloud Run service, plus **invoker bindings only for the callers listed in the manifest** (an IAM-enforced call graph);
- the task topic, DLQ and subscription; the Firestore control document; the labels and Resource Manager tags; a label-filtered budget; SLOs and alerts.

The agent identity also appears in OpenTelemetry resource attributes and in Vertex AI request labels.

## Consequences

- Good: one reviewable file per agent; least privilege by construction; per-agent audit trail, cost and kill switch (L1 = disable the SA).
- Bad: the manifest schema becomes a contract that needs versioning (`apiVersion`).

## Alternatives considered

- **One shared runtime SA**: no isolation, no attribution, and no per-agent hard kill.
- **Agent Engine Agent Identity**: attractive later, but currently test-only and tied to Agent Engine.

## Enforcement

JSON Schema validation in CI; conftest blocks primitive roles and wildcard members; `@security` BDD scenarios prove that one agent can't access another's resources.
