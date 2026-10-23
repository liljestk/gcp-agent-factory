---
status: accepted
date: 2026-10-23
decision-makers: liljestk
---

# ADR-0014: Data products with ODCS contracts and Dataform

## Context and problem statement

The data platform must manage data products that aren't defined yet, securely and cheaply. Composer, Dataflow and Dataproc are too expensive.

## Decision

- A data product is a folder `platforms/data/products/<name>/` holding an **ODCS** (Open Data Contract Standard) `contract.yaml`, Dataform SQL and BDD features.
- Layers: GCS `raw` → BigQuery `<domain>_raw` → `<domain>_curated` → `dp_<product>` (the published interface).
- Ingestion: Pub/Sub BigQuery subscriptions and load jobs. Transformation: **Dataform** (free; only queries are billed). Scheduling: one Cloud Scheduler job per env feeding a dispatcher Workflow.
- Governance: CMEK, policy tags (column-level), row access policies, authorized views, `maximum_bytes_billed` and daily query quotas.
- The first products dogfood the platform: `dp_finops`, `dp_agents`, `dp_ops`, plus a synthetic `dp_retail` demo domain (BigQuery public datasets are US-only).

## Consequences

- Good: near-zero idle cost; contracts are testable in CI; the platform's own telemetry becomes demo data.
- Bad: Dataform is SQL-only; Python transformations would need Cloud Run jobs.

## Alternatives considered

- **dbt Core on Cloud Run jobs**: viable, but Dataform is native and free.
- **Dataplex data products and Analytics Hub as the primary store**: kept optional until their costs are understood.

## Enforcement

`modules/data-product` derives datasets, IAM and alerts from the contract; `check-jsonschema` validates contracts; freshness SLOs alert on breaches.
