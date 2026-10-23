---
status: accepted
date: 2026-10-23
decision-makers: liljestk
---

# ADR-0010: Serverless network without NAT or load balancers

## Context and problem statement

Cloud NAT, load balancers and Serverless VPC Access connectors are the biggest hidden fixed costs in small GCP setups. Agents should also not reach the internet by default (exfiltration risk).

## Decision

- One VPC per env project, a `europe-north1` subnet with Private Google Access, **no Cloud NAT**, no external IPs, and default-deny egress except to the Google API VIPs.
- Private DNS maps `*.googleapis.com` to `restricted.googleapis.com` (VPC-SC compatible).
- Cloud Run uses **Direct VPC egress** (no connector). The agent manifest declares `egress: google-apis-only` (default) or `internet` (a reviewed exception that uses Cloud Run's own internet egress, e.g. for the GitHub API).
- **VPC Service Controls** perimeter around dev and prod, in dry-run first, enforced in prod in Phase 7. Ingress rules cover the CI apply identities.
- Ingress through Cloud Run URLs with IAM or IAP; no load balancers.

## Consequences

- Good: about $0 network cost; strong default egress posture.
- Bad: no Cloud Armor, custom domains through a load balancer, or multi-region anycast. All are acceptable for a demo.

## Alternatives considered

- **Shared VPC host project**: adds a project for no benefit when each env has one workload project.
- **NAT for all egress**: about $30+/month per gateway, and it weakens the egress posture.

## Enforcement

Org policies `compute.vmExternalIpAccess` and `compute.skipDefaultNetworkCreation`; conftest rejects `google_compute_router_nat` and forwarding rules without an ADR exception.
