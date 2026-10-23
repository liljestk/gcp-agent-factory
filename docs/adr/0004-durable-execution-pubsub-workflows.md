---
status: accepted
date: 2026-10-23
decision-makers: liljestk
---

# ADR-0004: Durable execution with Pub/Sub, Workflows and Cloud Tasks

## Context and problem statement

Agent work must survive crashes, retries and duplicate deliveries, and support long-running, human-approved steps. The requirement named Temporal "or a GCP-native alternative". The budget rules out anything that must run all the time.

## Decision

- **Pub/Sub** for async commands and events: every subscription has a dead-letter topic, an exponential-backoff retry policy and max delivery attempts; snapshots enable replay.
- **Cloud Workflows** for multi-step orchestration: per-step retries, saga compensation, and **callbacks** for human-in-the-loop. Executions are durable for up to a year.
- **Cloud Tasks** for rate-limited and delayed dispatch in front of expensive agents.
- **Idempotency ledger** in Firestore (TTL) keyed by message idempotency keys; ADK session state lives in Firestore.
- A **`DurableExecutor` port** in `agent-core` with a Workflows adapter, so a Temporal adapter (the official ADK Temporal plugin) can be added without touching agents.

## Consequences

- Good: pay-per-use and effectively free at demo volume; fully managed; recoverable by design.
- Bad: Workflows YAML is less expressive than code-first workflows; complex logic stays in agents and ADK graphs.
- Bad: at-least-once delivery everywhere, so handlers must be idempotent (INV-06).

## Alternatives considered

- **Temporal Cloud**: a great developer experience, but workers must poll all the time (Cloud Run min instances or worker pools) on top of a subscription. That fixed cost hits the budget early.
- **Self-hosted Temporal**: needs a persistent database and services that are always on, which costs even more.
- **Eventarc only**: routing without durable orchestration or human-in-the-loop.

## Enforcement

`modules/pubsub-channel` refuses subscriptions without a DLQ; conftest double-checks plans. BDD `@chaos` scenarios cover poison messages, duplicate delivery and resume after a crash.
