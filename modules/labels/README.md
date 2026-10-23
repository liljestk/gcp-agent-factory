# labels

The **single source of standard labels** (INV-02, REQ-REPO-006). Every labelable resource gets its labels from this module; never write a label map by hand.

## Usage

```hcl
module "labels" {
  source    = "../../../modules/labels"
  env       = "dev"
  platform  = "agents"
  component = "orchestrator"
  owner     = "platform-team"
  agent     = "orchestrator"
}

resource "google_cloud_run_v2_service" "this" {
  # ...
  labels = module.labels.labels
}
```

## Inputs

| Name | Required | Description |
|---|---|---|
| `env` | yes | `shared`, `dev` or `prod` |
| `platform` | yes | `landing-zone`, `agents`, `data`, `ops` or `apps` |
| `component` | yes | component slug |
| `owner` | yes | owning team slug |
| `cost_center` | no | default `demo` |
| `repo` | no | default `gcp-agent-factory` |
| `agent` / `app` / `data_product` | no | added only when set |
| `extra` | no | additional labels; can't override standard keys |

## Outputs

| Name | Description |
|---|---|
| `labels` | `map(string)` with `env`, `platform`, `component`, `owner`, `cost-center`, `managed-by=opentofu`, `repo` + optional keys |

## Cost notes

Creates no resources. Labels drive FinOps attribution in the billing export (keep values low-cardinality: never request or run IDs).
