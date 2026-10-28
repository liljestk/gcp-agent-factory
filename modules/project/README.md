# project

A Google Cloud project with standard labels, the APIs you list, no default network unless compute is enabled, and optionally a lien that blocks deletion (spec 002, REQ-LZ-003 and REQ-LZ-009). `bootstrap` uses it for the seed project; spec 003 uses it for every other project.

## Usage

```hcl
module "seed" {
  source          = "../../../../modules/project"
  project_id      = "gcp-agent-factory-seed-${random_string.suffix.result}"
  name            = "gcp-agent-factory seed"
  folder_id       = google_folder.trust_root.name
  billing_account = var.billing_account
  services        = ["cloudkms.googleapis.com", "iam.googleapis.com", "storage.googleapis.com"]
  labels          = module.labels.labels
  lien_reason     = "Holds the OpenTofu state for every stack."
}
```

## Inputs

| Name | Required | Description |
|---|---|---|
| `project_id` | yes | 6-30 lowercase letters, digits and hyphens, starting with a letter |
| `name` | yes | display name |
| `folder_id` | yes | `folders/<number>` or the number |
| `billing_account` | yes | billing account ID, e.g. `012345-6789AB-CDEF01` |
| `services` | no | APIs to enable and manage (`*.googleapis.com`); Google's own defaults for new projects are left alone |
| `delete_default_network` | no | default `false`; `true` turns the Compute Engine API on to delete the default network |
| `labels` | yes | from `modules/labels` |
| `deletion_policy` | no | `PREVENT` (default), `ABANDON` or `DELETE` |
| `lien_reason` | no | when set, a lien blocks deleting the project |

## Outputs

| Name | Description |
|---|---|
| `project_id` | project ID |
| `number` | project number |
| `services` | enabled APIs, sorted |

## Notes

- **APIs:** removing one from `services` stops managing it but doesn't turn it off, so nothing that still depends on it breaks.
- **Default network:** GCP creates one only when the Compute Engine API is first enabled. A project that never enables compute, like the seed, has none. For projects that do run compute, spec 003 enforces `compute.skipDefaultNetworkCreation`. `delete_default_network = true` is only for the case where a default network already exists, because it makes the provider turn compute on to delete it.
- **Deleting the project:**
  1. set `lien_reason = null` and `deletion_policy = "DELETE"`
  2. apply
  3. destroy, or remove the module

  The end-of-trial teardown follows these steps.
- **IAM:** none. A project's creator gets Owner on it automatically. Spec 003 removes that grant and adds the roles it actually needs.

## Cost notes

A project, its APIs and a lien cost nothing. Whatever runs in the project is billed to `billing_account`.
