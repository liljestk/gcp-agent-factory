# Architecture Decision Records

Format: [MADR](https://adr.github.io/madr/) with YAML front matter. Copy [`0000-template.md`](0000-template.md) or use the `adr-new` skill.
Allowed `status` values: `proposed`, `accepted`, `rejected`, `deprecated`, `superseded by ADR-NNNN`. `repo-checks adrs` enforces format and this index.

| ADR | Title | Status |
|---|---|---|
| [0001](0001-monorepo-layout-and-toolchain.md) | Monorepo layout and toolchain | accepted |
| [0002](0002-python-and-google-adk.md) | Python and Google ADK 2.x for agents | accepted |
| [0003](0003-cloud-run-agent-runtime.md) | Cloud Run as the agent runtime | accepted |
| [0004](0004-durable-execution-pubsub-workflows.md) | Durable execution with Pub/Sub, Workflows and Cloud Tasks | accepted |
| [0005](0005-state-stores-without-cloud-sql.md) | State stores without Cloud SQL | accepted |
| [0006](0006-event-contracts-cloudevents-protobuf.md) | Event contracts with CloudEvents and Protobuf | accepted |
| [0007](0007-service-account-per-agent.md) | One service account per agent, generated from a manifest | accepted |
| [0008](0008-kill-switch-layers.md) | Five kill-switch layers | accepted |
| [0009](0009-org-and-project-topology.md) | Org, folder and project topology | accepted |
| [0010](0010-serverless-network-without-nat.md) | Serverless network without NAT or load balancers | accepted |
| [0011](0011-opentofu-with-state-encryption.md) | OpenTofu with client-side state encryption | accepted |
| [0012](0012-github-actions-wif-promote-by-digest.md) | GitHub Actions with WIF; build once, promote by digest | accepted |
| [0013](0013-testing-strategy.md) | Testing strategy: 100% coverage, BDD, evals, IaC tests | accepted |
| [0014](0014-data-products-odcs-dataform.md) | Data products with ODCS contracts and Dataform | accepted |
| [0015](0015-gemini-on-vertex-model-endpoint.md) | Gemini on Vertex AI and model endpoint location | proposed |
| [0016](0016-spec-driven-agent-ready-repo.md) | Spec-driven, agent-ready repository conventions | accepted |
| [0017](0017-existing-sandbox-org.md) | Use the existing sandbox org, with smartass.dad for identities | proposed |
| [0018](0018-trust-root-stacks-applied-locally.md) | Apply the trust-root stacks locally, everything else through CI | proposed |
