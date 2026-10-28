# bootstrap

The trust root ([spec 002](../../../../specs/002-bootstrap-and-ci-pipeline/design.md), [ADR-0018](../../../../docs/adr/0018-trust-root-stacks-applied-locally.md)). Only the owner applies this stack, from their own workstation. CI plans it read-only as `ci-plan`, and the bootstrap gate stops every CI apply while it has unapplied changes.

## What it creates

| File | Resources |
|---|---|
| [`main.tf`](main.tf) | the folders `trust-root`, `shared`, `dev` and `prod`; the seed project `gcp-agent-factory-seed-<sfx>` in `trust-root`, with a lien and only the allow-listed APIs |
| [`identities.tf`](identities.tf) | `ci-plan`, `ci-foundation`, `ci-apply-dev`, `ci-apply-prod`, and the GitHub pool and provider ([`modules/wif-github`](../../../../modules/wif-github)) |
| [`state.tf`](state.tf) | key ring `tfstate` with one state key per scope, an owner-only key for the `github` stack's state, and the bucket key; the state bucket `gcp-agent-factory-tfstate-<sfx>` and its prefix-scoped policy |
| [`iam.tf`](iam.tf) | org, folder, seed and billing-account IAM |
| [`guardrails.tf`](guardrails.tf) | the deny policy and folder org policies on `trust-root`; Data Access logs for token exchange and minting, state reads and key use |
| [`budget.tf`](budget.tf) | the €85 monthly gross-cost budget on the billing account |

## How IAM is managed

Every role is managed in exactly one mode, so a grant made outside this stack shows up as drift on the next plan:

- **Whole policies**: the four folders, the state bucket, each state key and each CI account. `trust-root`'s policy is empty.
- **One authoritative binding per role**: every org, seed and billing-account role a CI identity holds, plus Project Creator and Deny Admin (`gcp-org-admins`), and the roles nobody may hold: Billing Account Creator, Service Account Token Creator, OpenID Token Creator, Service Account User and Workload Identity User at org level and on the seed. An empty member list means nobody.
- **Additive**: only roles no CI identity holds, all for the owner's groups: Organization Administrator and Folder Creator for `gcp-org-admins`, and Billing Account Administrator for `gcp-billing-admins`. That last one stays additive so the personal billing owner (ADR-0017) can't be locked out. Deny Admin is authoritative, because deny-policy changes can't themselves be denied.

On the seed, Editor is kept for Google's APIs service agent, which Google grants it on every project; nobody else holds it.

**The deny policy** on `trust-root` has two rules. The four CI accounts are denied every change to the folder, the seed and what it holds. Every identity of the GitHub pool is denied the same, except minting tokens for the CI accounts, which is how CI signs in. The list also covers side doors: HMAC keys, managed folders in the bucket, new pool identities and the seed's audit trail. Every permission on it is one deny policies support. Changes to deny policies and to the billing account can't be denied; IAM and drift detection cover those.

## Inputs

| Name | Required | Description |
|---|---|---|
| `org_id`, `customer_id` | yes | the organization and its directory customer ID (ADR-0017) |
| `identity_domain` | yes | domain of the `gcp-*` groups |
| `billing_account` | yes | the billing account the seed links to and the budget watches |
| `region` | no | default `europe-north1`; European regions only |
| `repository`, `repository_id`, `repository_owner_id` | no | default to this repository's name and immutable IDs |
| `state_bucket`, `state_key` | after the first run | this stack's own backend bucket and trust-root key (early-evaluated) |
| `quota_project` | after the first run | the seed, so API quota is charged to it |

`terraform.tfvars` holds the identifying values (org, customer, domain, billing account). They identify but don't authorize, so it is committed at the first run (spec 002 task 11).

## Outputs

`org_id`, `customer_id`, `identity_domain`, `region`, `folders`, `seed_project_id`, `seed_project_number`, `state_bucket`, `state_keys` (by scope), `workload_identity_provider`, `ci_service_accounts` and `wif_gates`. The `github` stack turns them into GitHub variables; nothing here is secret.

## Running it

The first run starts on a local backend with a passphrase override, because the keys don't exist yet, and then migrates to the bucket. Before it, the owner needs Organization Administrator and Folder Creator through `gcp-org-admins` and Billing Account Administrator through `gcp-billing-admins`. Everything else this stack grants itself. The step-by-step procedure, including isolated credentials, lives in `docs/runbooks/bootstrap.md` (spec 002 task 9).

Tests run offline on mock providers and only plan, because the keys' and bucket's `prevent_destroy` would make an apply run's clean-up fail:

```bash
just test-iac
```

## Cost notes

About €0.36 a month idle: six software KMS keys at about €0.06 each, and a few MB of state. Folders, the project, IAM, the deny policy, org policies, WIF and the budget are free. The seed's Data Access logs add a few dozen entries per CI run, well inside the free logging allotment.
