---
name: cost-impact
description: Assess and write the cost impact of a change for the $300 GCP free-trial budget (idle cost, per-use cost, free tiers, labels, budgets, guardrails). Use when a spec's design.md needs a Cost impact section, when infra or new services are added, or when the user asks "what will this cost".
---

# cost-impact

Context: a $300 credit over 90 days. Targets: **≤ $15/month idle** and **≤ $60/month during active demos**. Budgets and kill-switch layers are in ADR-0008.

## Steps

1. **List every billable thing** the change adds or changes: services, resources, API calls, log volume, tokens.
2. **Check the avoid list** in `DESIGN.md` §4. Any hit means stop: it needs an ADR with numbers and an owner.
3. For each item, estimate:
   - **Idle cost per month** (anything that bills while nobody uses it: instances, IPs, NAT, load balancers, keys, zones, endpoints).
   - **Per-use cost** with a realistic demo volume (requests, GiB scanned, tokens in/out).
   - The **free tier** it falls under, and whether other usage already consumes it.
4. **Guardrails present?** `max_instances`, `maximum_bytes_billed`, BigQuery daily quota, lifecycle and retention rules, token budget in the agent manifest, Cloud Tasks rate limits.
5. **Attribution**: standard labels via `modules/labels`; Vertex AI calls carry request labels; the resource falls under a project or label-filtered budget.
6. Write the **Cost impact** section:

   ```markdown
   ## Cost impact
   | Item | Idle / month | Per use | Free tier | Guardrail |
   |---|---|---|---|---|
   | … | $0 | ~$0.002 / run | 2M req/month | max_instances=2 |
   Net: +$X idle, ~$Y at demo volume. Budget: <project/label budget>. Avoid-list hits: none.
   ```

7. Prices change: say "approx." and recommend checking the GCP pricing calculator for anything above $1/month.

## Red flags

- Anything with `min_instances > 0`, always-on endpoints, NAT, load balancers, or extra Firestore databases.
- Unbounded loops calling models (no token budget) or unbounded BigQuery queries (no byte cap).
- High-cardinality labels or metrics (per-request IDs).
