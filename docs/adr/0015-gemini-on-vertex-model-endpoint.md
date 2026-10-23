---
status: proposed
date: 2026-10-23
decision-makers: liljestk
---

# ADR-0015: Gemini on Vertex AI and model endpoint location

## Context and problem statement

Token spend is the main variable cost. Per-agent attribution needs billing-visible labels. EU residency is preferred, but not every Gemini model is offered in every region.

## Decision (proposed until model availability is verified in Phase 3)

- Call Gemini through **Vertex AI**, not the AI Studio API: **request labels** (`agent`, `env`, `platform`) flow into the billing export.
- Default to the **Flash tier**, with a Flash-Lite fallback; use the Pro tier only where an eval proves it's needed. Models are set per agent in the manifest.
- Endpoint: an EU regional endpoint (prefer `europe-north1`, otherwise the nearest EU region offering the model). The `global` endpoint is a documented last resort because it relaxes residency.
- Use context caching for long, stable system prompts.

## Consequences

- Good: per-agent token cost in BigQuery; cost tracked against eval quality.
- Bad: some models may need a non-local EU region, which adds latency.

## Open items

- Check current model availability in `europe-north1` and other EU regions.
- Check request-label limits (key format, per-request cap) and whether the chosen models use dynamic shared quota.

## Enforcement

The manifest schema restricts allowed `location` values; `agent-core`'s model factory always attaches the labels; a unit test asserts this.
