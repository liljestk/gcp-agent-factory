# kms

A Cloud KMS key ring with software keys that rotate, and a fully managed IAM policy per key (spec 002, REQ-LZ-003 and REQ-LZ-004). `bootstrap` uses it for the per-scope state keys and the state bucket's CMEK key.

## Usage

```hcl
module "tfstate_keys" {
  source     = "../../../../modules/kms"
  project_id = module.seed.project_id
  location   = "europe-north1"
  key_ring   = "tfstate"
  labels     = module.labels.labels
  keys = {
    state-dev = {
      encrypters_decrypters = ["serviceAccount:${google_service_account.ci["ci-apply-dev"].email}"]
      decrypters            = []
    }
    bucket = {
      encrypters_decrypters = ["serviceAccount:${data.google_storage_project_service_account.gcs.email_address}"]
    }
  }
}
```

## Inputs

| Name | Required | Description |
|---|---|---|
| `project_id` | yes | project that holds the key ring |
| `location` | yes | region or multi-region; it can never change |
| `key_ring` | yes | key ring name; key rings can't be deleted |
| `keys` | yes | keys by name: `rotation_period` (default `7776000s`, 90 days; at least a day), `encrypters_decrypters`, `decrypters` |
| `labels` | yes | from `modules/labels` |

## Outputs

| Name | Description |
|---|---|
| `key_ring_id` | key ring ID |
| `key_ids` | crypto key IDs by name |

## Notes

- **Each key's whole IAM policy is managed.** The listed members are the only ones with any role on the key. A key with no members gets an empty policy, and so does the key ring, so a grant on the ring can't reach every key. Anything added outside OpenTofu shows up as drift and is removed on the next apply.
- **Members:** only service accounts, the Cloud Storage service agent and groups are accepted. Users, principal sets and public principals are refused.
- **Ordering:** `key_ids` becomes available only after the keys' policies are set, so a bucket that uses a key as CMEK doesn't race its grant.
- **Keys can't be removed by accident:** every key has `prevent_destroy`. GCP never deletes keys, only their versions, so removing one takes a deliberate change to this module.
- **Software protection only.** HSM keys cost more and nothing here needs them.

## Cost notes

Each active key version costs about €0.06 per month, plus about €0.03 per 10,000 operations. Rotation adds a version every `rotation_period`, and old versions stay enabled so older data still decrypts. Five keys come to about €0.30 per month.
