---
status: accepted
date: 2026-10-23
decision-makers: liljestk
---

# ADR-0005: State stores without Cloud SQL

## Context and problem statement

Services are stateless (principle 2), so state needs managed stores. Cloud SQL, AlloyDB and Memorystore all bill continuously even when idle.

## Decision

- **Firestore, `(default)` database only** (the free tier applies to it alone): kill-switch controls, budgets, idempotency ledger, ADK sessions. Collections are prefixed per platform.
- **BigQuery** for analytics, events and data products.
- **GCS** for raw files, artifacts and state.

## Consequences

- Good: $0 idle; regional HA built in.
- Bad: Firestore IAM can't restrict access per collection, so per-agent isolation inside Firestore is enforced in `agent-core` rather than by IAM. This limitation is accepted and documented in the threat model.
- Bad: no relational joins on operational data; analytical needs go through BigQuery.

## Alternatives considered

- **Cloud SQL (smallest tier)**: still a monthly fixed cost, and ADK's SQL session service would be convenient but isn't worth it.
- **Multiple Firestore databases for isolation**: no free tier beyond `(default)`.

## Enforcement

The org policy `gcp.restrictServiceUsage` denies `sqladmin`, `alloydb` and `redis` (ADR-0009). Any exception needs a new ADR.
