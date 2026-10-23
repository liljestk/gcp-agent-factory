---
status: accepted
date: 2026-10-23
decision-makers: liljestk
---

# ADR-0006: Event contracts with CloudEvents and Protobuf

## Context and problem statement

Agents, data pipelines and ops services exchange events. Schema drift silently breaks consumers and the data products built on `agent.events`.

## Decision

- Envelope: **CloudEvents 1.0** attributes (`id` doubles as the idempotency key, plus `source`, `type`, `subject`, `time`).
- Payload schemas in **Protobuf** under `libs/events`, linted by `buf lint` and checked with `buf breaking` against `main` in CI.
- **Pub/Sub topic schemas** enforce the Protobuf definition at publish time, using JSON encoding so messages stay human-readable and BigQuery-subscription friendly.
- Python models are generated from the protos.

## Consequences

- Good: the broker rejects invalid messages; breaking changes fail CI before merge.
- Bad: adds `buf` to the toolchain and a codegen step.

## Alternatives considered

- **JSON Schema + Pydantic only**: simpler, but Pub/Sub can't enforce it and compatibility checks are weaker.
- **Avro**: supported by Pub/Sub, but its tooling is weaker for Python services.

## Enforcement

The `buf breaking` CI job (Phase 3) and topic schema settings in `modules/pubsub-channel`.
