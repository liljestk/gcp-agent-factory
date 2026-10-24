# gcp-agent-factory

A demo platform on Google Cloud for **building and operating agentic applications**, fully defined in OpenTofu and deployed by GitHub Actions.

| Platform | What it shows |
|---|---|
| **Agents** | multi-agent orchestration with Google ADK on Cloud Run; per-agent identity, budget and kill switch |
| **Landing zone** | secure but simple org/folder/project baseline and a paved road for new apps |
| **Data** | data products on BigQuery with ODCS contracts, Dataform and governance |
| **Ops** | observability, FinOps, durable recovery and agent-assisted incident response |

> **Status:** Phase 0 (repo foundations). Nothing is deployed yet. See the [roadmap](docs/PLAN.md#12-roadmap).

## Quick start

```bash
# macOS/Linux, or Git Bash on Windows (devcontainer option: see AGENTS.md → Setup)
mise install
just setup
just check
```

## Where to read next

- [`AGENTS.md`](AGENTS.md): how to work in this repo (humans and coding agents)
- [`DESIGN.md`](DESIGN.md): principles and invariants
- [`docs/PLAN.md`](docs/PLAN.md): full architecture plan and roadmap
- [`docs/adr/`](docs/adr/README.md): architecture decisions
- [`SECURITY.md`](SECURITY.md): reporting vulnerabilities
