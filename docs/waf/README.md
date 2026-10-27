# Well-Architected Framework checklist

Mapping of the [Google Cloud Well-Architected Framework](https://cloud.google.com/architecture/framework) pillars (plus the AI/ML perspective) to concrete controls in this repo. Status: ✅ in place · 🟡 partial · ⬜ planned (phase).
The `waf-review` skill and `waf-reviewer` subagent use this file; update it in the same PR that changes a control.

## Operational excellence

| Control | Where | Status |
|---|---|---|
| Everything as code; no click-ops after bootstrap | `platforms/*/infra`, `modules/`, `platforms/stacks.yaml`; trust-root stacks owner-applied (ADR-0018) | 🟡 conventions ✅ · stacks ⬜ P1 |
| One command for all gates, identical in CI | `justfile`, `.github/workflows/ci.yml` | ✅ |
| Decisions recorded | `docs/adr/` | ✅ |
| Drift detection | `drift.yml` (spec 002): nightly plans incl. `bootstrap`, read-only `@security` checks; `github` settings read-only | ⬜ P1 |
| SLOs, dashboards and alerts as code | `platforms/ops/observability` | ⬜ P2 |
| Runbooks and game days | `docs/runbooks/`, `chaos.yml` | ⬜ P2/P5 |

## Security, privacy and compliance

| Control | Where | Status |
|---|---|---|
| Keyless CI (WIF pinned to repo ID, plan and deploy gates) | `modules/wif-github`, `bootstrap` (spec 002) | ⬜ P1 |
| Trust root: CI holds no role on `trust-root` or the seed, deny policy, org IAM one mode per role | `bootstrap` `tofu test`, `@security` scenarios, ADR-0018 | ⬜ P1 |
| Org policies (keys, public access, locations, services) | foundation stack | ⬜ P1 |
| Privileged identities outside IaC (super admins, break-glass, billing-account owner): phishing-resistant 2SV, closed groups, org inventory | bootstrap runbook, ADR-0017 | ⬜ P1 (manual) |
| Identity per agent and app, least privilege | `modules/agent-service`, `app-tenant` | ⬜ P3/P6 |
| VPC-SC perimeter, restricted VIP, no default egress | network stack | ⬜ P1 (dry-run) / P7 (enforce) |
| CMEK for state and data | state: client-side encryption with per-scope keys + CMEK + per-prefix IAM (spec 002); data stacks | ⬜ P1/P4 |
| SHA-pinned supply chain, attestations | `repo-checks pins`, Renovate, dependency review + Dependabot alerts, deploy workflow | 🟡 pins ✅ · attestations ⬜ P3 |
| Static analysis and secret scanning | CodeQL, ruff `S`, zizmor, gitleaks, GitHub push protection | ✅ |
| Protected `main`: PRs only, required CI and CodeQL checks, no force push | GitHub ruleset `main` (click-ops until spec 002's `github` stack imports ruleset 25774561) | ✅ |
| Agent guardrails (tool allow-list, HITL, prompt-injection defences) | `libs/agent-core` | ⬜ P3 |
| Coding-agent guardrails | `.claude/settings.json`, `.claude/hooks/` | ✅ |

## Reliability

| Control | Where | Status |
|---|---|---|
| IaC change safety and state recovery: saved plans with hash check, stale-plan refusal, per-stack concurrency, dev before prod, versioned state, `prevent_destroy`, lien | spec 002 | ⬜ P1 |
| Idempotent consumers, DLQs, retries | `agent-core`, `modules/pubsub-channel` | ⬜ P3 |
| Durable orchestration and HITL | Cloud Workflows | ⬜ P3 |
| Canary and automated rollback | deploy workflow | ⬜ P3 |
| DR: region-parametrised IaC, backups, drill | stacks, `docs/runbooks/dr.md` | ⬜ P5 |

## Cost optimization

| Control | Where | Status |
|---|---|---|
| Serverless, scale-to-zero, avoid list | `DESIGN.md` §4 | ✅ policy · conftest enforcement ⬜ P1 (spec 003) |
| Standard labels everywhere | `modules/labels` | 🟡 module ✅ · plan policy ⬜ P1 (spec 003) |
| Budgets (gross cost, credits excluded) and kill-switch layers | billing-account budget in `bootstrap` (spec 002), project budgets (spec 003), `budget-enforcer` (spec 005), ADR-0008 | ⬜ P1/P3 |
| Cost diff on PRs | Infracost (needs an API key; spec 003 decides) | ⬜ P1 |
| Per-agent token attribution | Vertex request labels, `dp_finops` | ⬜ P3/P4 |

## Performance optimization

| Control | Where | Status |
|---|---|---|
| Rate limiting and backpressure | Cloud Tasks, `max_instances` | ⬜ P3 |
| Right-sized models, context caching | agent manifests, ADR-0015 | ⬜ P3 |
| Latency thresholds in evals and SLOs | evals, SLOs | ⬜ P3 |

## Sustainability

| Control | Where | Status |
|---|---|---|
| Low-carbon region (`europe-north1`) | ADR-0009 | ✅ decided |
| Scale-to-zero, lifecycle rules, short retention | modules | ⬜ P1+ |
| Carbon footprint reporting | ops | ⬜ P2 |

## AI/ML perspective

| Control | Where | Status |
|---|---|---|
| Evals as release gates | ADK evalsets | ⬜ P3 |
| Prompt and model versioning | agent packages, manifests | ⬜ P3 |
| Token budgets and kill switches | `agent-core` | ⬜ P3 |
| Run telemetry as a data product | `dp_agents.runs` | ⬜ P4 |
