# wif-github

Keyless CI: a workload identity pool and GitHub Actions provider, pinned to one repository's immutable IDs, plus authoritative Workload Identity User bindings that tie each CI service account to a gate (spec 002, REQ-LZ-001 and REQ-LZ-002).

## The gates

[`gates.json.tftpl`](gates.json.tftpl) holds three CEL expressions:

| Expression | Role |
|---|---|
| `condition` | the provider's trust condition. Only tokens whose `repository_id` and `repository_owner_id` match are accepted, never matched by name, and only if they pass the plan or the deploy gate. Anything else is refused at the exchange |
| `plan` | `attribute.plan = "allowed"` for the owner's pull requests and manual dispatches, and for push, schedule and dispatch runs on `main`; everything else is `denied` (for example a bot's PR, a branch push, `pull_request_target`). A bot's PR is allowed only when the owner triggers an event on it, since no claim names the PR author |
| `deploy` | `attribute.deploy = <environment>` only for a push to `main` running the apply workflow itself (not a workflow calling it), in a GitHub-hosted job with a GitHub environment; otherwise `none`, which can't be used as an environment name |

`tests/iac/test_wif_gates.py` evaluates the same template against token claims for each case, using cel-python.

## Usage

```hcl
module "wif" {
  source              = "../../../../modules/wif-github"
  project_id          = module.seed.project_id
  repository          = "liljestk/gcp-agent-factory"
  repository_id       = "1431415117"
  repository_owner_id = "4373495"
  service_accounts = {
    ci-plan       = { email = google_service_account.ci["ci-plan"].email, gate = "plan" }
    ci-foundation = { email = google_service_account.ci["ci-foundation"].email, gate = "deploy", environment = "foundation" }
  }
}
```

## Inputs

| Name | Required | Description |
|---|---|---|
| `project_id` | yes | project that holds the pool (the seed) |
| `pool_id` / `provider_id` | no | default `github` / `github-actions` |
| `repository` | yes | `owner/name`; pins the apply workflow only |
| `repository_id` / `repository_owner_id` | yes | immutable numeric IDs the trust condition requires |
| `owner_actor_id` | no | user whose PRs and dispatches may plan; defaults to `repository_owner_id` |
| `apply_workflow` | no | default `.github/workflows/tofu.yml` |
| `service_accounts` | yes | by name: `email`, `gate` (`plan` or `deploy`) and, for `deploy`, `environment` |

## Outputs

| Name | Description |
|---|---|
| `pool_name` | full pool resource name |
| `provider_name` | full provider resource name, for `google-github-actions/auth` |
| `principal_sets` | the principal set each account trusts |
| `gates` | the rendered condition and gates, for the live checks |

## Notes

- **The bindings are authoritative,** so nobody else, human or group, holds Workload Identity User on these accounts.
- **What this module doesn't cover:**
  - The accounts' other roles are managed by `bootstrap`. CI needs no Service Account Token Creator, because Workload Identity User already allows minting their tokens.
  - Fork pull requests never reach the pool, because GitHub withholds `id-token` from them.

## Cost notes

Workload identity pools, providers and token exchanges are free.
