# Well-Architected Framework checklist

Mapping of the [Google Cloud Well-Architected Framework](https://cloud.google.com/architecture/framework) pillars (plus the AI/ML perspective) to concrete controls in this repo. Status: ✅ in place · 🟡 partial · ⬜ planned (phase).
The `waf-review` skill and `waf-reviewer` subagent use this file; update it in the same PR that changes a control.

## Operational excellence

| Control | Where | Status |
|---|---|---|
| Everything as code; no click-ops after bootstrap | `platforms/*/infra`, `modules/` | 🟡 conventions ✅ · stacks ⬜ P1 |
| One command for all gates, identical in CI | `justfile`, `.github/workflows/ci.yml` | ✅ |
| Decisions recorded | `docs/adr/` | ✅ |
| Drift detection | `drift.yml` | ⬜ P1 |
| SLOs, dashboards and alerts as code | `platforms/ops/observability` | ⬜ P2 |
| Runbooks and game days | `docs/runbooks/`, `chaos.yml` | ⬜ P2/P5 |

## Security, privacy and compliance

| Control | Where | Status |
|---|---|---|
| Keyless CI (WIF pinned to repo ID) | bootstrap stack | ⬜ P1 |
| Org policies (keys, public access, locations, services) | foundation stack | ⬜ P1 |
| Identity per agent and app, least privilege | `modules/agent-service`, `app-tenant` | ⬜ P3/P6 |
| VPC-SC perimeter, restricted VIP, no default egress | network stack | ⬜ P1 (dry-run) / P7 (enforce) |
| CMEK for state and data | bootstrap, data stacks | ⬜ P1/P4 |
| SHA-pinned supply chain, attestations | `repo-checks pins`, Renovate, deploy workflow | 🟡 pins ✅ · attestations ⬜ P3 |
| Static analysis and secret scanning | CodeQL, ruff `S`, zizmor, gitleaks, GitHub push protection | ✅ |
| Protected `main`: PRs only, required CI and CodeQL checks, no force push | GitHub ruleset `main` (click-ops until Phase 1 moves it to code) | ✅ |
| Agent guardrails (tool allow-list, HITL, prompt-injection defences) | `libs/agent-core` | ⬜ P3 |
| Coding-agent guardrails | `.claude/settings.json`, `.claude/hooks/` | ✅ |

## Reliability

| Control | Where | Status |
|---|---|---|
| Idempotent consumers, DLQs, retries | `agent-core`, `modules/pubsub-channel` | ⬜ P3 |
| Durable orchestration and HITL | Cloud Workflows | ⬜ P3 |
| Canary and automated rollback | deploy workflow | ⬜ P3 |
| DR: region-parametrised IaC, backups, drill | stacks, `docs/runbooks/dr.md` | ⬜ P5 |

## Cost optimization

| Control | Where | Status |
|---|---|---|
| Serverless, scale-to-zero, avoid list | `DESIGN.md` §4 | ✅ policy · enforcement ⬜ P1 |
| Standard labels everywhere | `modules/labels` | 🟡 module ✅ · plan policy ⬜ P1 |
| Budgets and kill-switch layers | `budget-enforcer`, ADR-0008 | ⬜ P1/P3 |
| Cost diff on PRs | Infracost | ⬜ P1 |
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
