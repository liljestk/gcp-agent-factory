# 002: Bootstrap and CI pipeline (requirements)

## Context

This is the first of four Phase 1 specs in the [roadmap](../../docs/PLAN.md#12-roadmap). The others are 003 foundation, 004 network and 005 budget-enforcer.

This spec builds the layer everything else stands on:

- the trust-root folder and seed project
- encrypted remote state
- keyless CI identities
- a billing-account budget
- the GitHub Actions pipeline that plans every change on its PR and applies it after merge

Once it's done, every later stack reaches GCP only through CI. The two trust-root stacks, `bootstrap` and `github`, are the exception: the owner applies them locally, and CI can't reach them ([ADR-0018](../../docs/adr/0018-trust-root-stacks-applied-locally.md)).

Related ADRs:

- [ADR-0009](../../docs/adr/0009-org-and-project-topology.md): topology
- [ADR-0011](../../docs/adr/0011-opentofu-with-state-encryption.md): encrypted state
- [ADR-0012](../../docs/adr/0012-github-actions-wif-promote-by-digest.md): WIF and the pipeline
- [ADR-0017](../../docs/adr/0017-existing-sandbox-org.md): the org

## Requirements

### REQ-LZ-001: Only this repository can authenticate to Google Cloud

**Statement**: When a GitHub Actions job requests Google credentials, the identity federation shall issue them only if the job runs in `liljestk/gcp-agent-factory`, identified by its immutable repository and owner IDs.

#### Acceptance criteria

- The provider condition requires `repository_id` 1431415117 and `repository_owner_id` 4373495, and never uses the repository name.
- A workflow running in any other repository is refused. That includes a fork's own repository, and a new repository given the same name after a rename or delete.
- Fork pull requests that run here get no token, because GitHub withholds `id-token` from them. No workflow that requests `id-token` is triggered by `pull_request_target`, `workflow_run` or `issue_comment`.
- No CI identity has a service-account key.

**Verified by**: `platforms/landing-zone/tests/features/identity.feature` and `pipeline.feature` (tag `@REQ-LZ-001`)

### REQ-LZ-002: Each CI job gets only the identity its context allows

**Statement**: When a job from this repository authenticates, the identity federation shall issue an apply identity only to the reviewed apply workflow on `main`, in that identity's environment. It shall issue `ci-plan` only to the owner's pull requests and to runs on `main`.

#### Acceptance criteria

- `ci-foundation`, `ci-apply-dev` and `ci-apply-prod` are reachable only from a GitHub-hosted job of `.github/workflows/tofu.yml` at `refs/heads/main`, in the `foundation`, `dev` and `prod` environment respectively.
- `ci-plan` is reachable only from pull-request or manually dispatched runs started by the owner, and from push, schedule or dispatch runs on `main`. A bot's pull request gets a plan when the owner dispatches one.
- No human or group holds Workload Identity User or Service Account Token Creator on a CI identity.

**Verified by**: `platforms/landing-zone/tests/features/identity.feature` (tag `@REQ-LZ-002`)

### REQ-LZ-003: State is encrypted before it leaves the runner, and hard to lose

**Statement**: When any stack writes state or a saved plan, OpenTofu shall encrypt it with its scope's state key before it is stored or uploaded. The state bucket and seed project shall resist accidental deletion.

#### Acceptance criteria

- Each scope (`trust-root`, `shared`, `dev`, `prod`) has its own state key. A stored state object is an encryption envelope with no plaintext resources.
- A root module fails `just check` unless it has exactly one `encryption` block meeting all of these:
  - a `gcp_kms` key provider and an `aes_gcm` method
  - `enforced = true` for state and plans
  - no `fallback`
  - not set in an override file

  Files are read as OpenTofu reads them: a `.tofu` file shadows its `.tf` twin.
- The bucket has:
  - versioning, uniform bucket-level access and public access prevention
  - the bucket CMEK key
  - soft delete and standard labels
  - `prevent_destroy`, with `force_destroy` off
- The seed project has a lien against deletion.
- Each stack and environment pair has its own state prefix.

**Verified by**: `platforms/landing-zone/tests/features/state.feature` (tag `@REQ-LZ-003`)

### REQ-LZ-004: Each CI identity reaches only its own state

**Statement**: When a CI service account accesses the state bucket or a state key, it shall be limited to the state of the stacks it applies, plus the state it plans or consumes.

#### Acceptance criteria

- Reads and writes are limited by prefix allow-lists, and `ci-plan` writes nothing.
- No CI identity can write or delete anything under `trust-root/`, and none can read `trust-root/github/`.
- None of these can write the scope that isn't theirs:
  - `ci-apply-dev` can't write `prod/`
  - `ci-apply-prod` can't write `dev/`
  - `ci-foundation` can't write `dev/` or `prod/`
- Each identity can use only the state keys of the scopes it reads or writes.

**Verified by**: `platforms/landing-zone/tests/features/state.feature` (tag `@REQ-LZ-004`)

### REQ-LZ-005: Pull requests get a plan for every affected stack

**Statement**: When a pull request changes a stack, a module that a stack uses, or the pipeline itself, the pipeline shall plan each affected CI-plannable stack and environment and post the result to the pull request.

#### Acceptance criteria

- **Which changes plan which stacks**:
  - A change to `modules/<name>` plans every stack that uses it, directly or through another module.
  - A change to the toolchain (`mise.toml`), the stack catalog, the workflows or the composite actions plans every stack.
  - Other changes plan nothing.
- **`bootstrap` and `github`**: `bootstrap` is planned. `github` is never planned in CI; the owner plans it locally.
- **Comments**:
  - Each stack and environment has one sticky comment, authored by `github-actions[bot]` and found by a marker, and updated on every push.
  - The job that writes comments holds no Google credentials.
- **Required check**: the aggregate `tofu-plan` check passes only when every plan job passed, or none ran.

**Verified by**: `platforms/landing-zone/tests/features/pipeline.feature` (tag `@REQ-LZ-005`)

### REQ-LZ-006: Merges apply the reviewed plan, in stack order

**Statement**: When a change to a CI-applied stack merges to `main`, the pipeline shall apply the exact saved plan shown to the approver. It shall do so in the order `foundation → network → ops → data → agents → apps`, dev before prod.

#### Acceptance criteria

- **Who and where**: apply jobs run only from `tofu.yml` on `main`. `foundation` and `prod` applies wait for the owner's approval.
- **The plan that gets applied**:
  - The run shows the post-merge plan summary and the SHA-256 of the encrypted plan file.
  - The apply job refuses a plan file with a different hash, and OpenTofu refuses a stale plan.
- **Order**:
  - A tier applies only after the earlier tiers succeeded or were unaffected.
  - Within a tier, prod waits for dev.
  - No apply job runs while `bootstrap` has unapplied changes; the run says "apply bootstrap first".
- **Never applied by CI**: no apply job is ever generated for `bootstrap` or `github`.
- **Exercised end to end**: the €0 `ci-canary` stack in dev and prod exercises this path.

**Verified by**: `platforms/landing-zone/tests/features/pipeline.feature` (tag `@REQ-LZ-006`)

### REQ-LZ-007: Drift opens an issue

**Statement**: Every night, the pipeline shall plan every CI-applied stack and environment plus `bootstrap`, and run the read-only security checks. It shall keep one open issue per problem.

#### Acceptance criteria

- **Drift found**: when a plan has changes, an issue labelled `drift` names the stack, environment and changed addresses. A comment is added whenever that set changes, and issues aren't duplicated.
- **Drift resolved**: when the stack is clean again, the issue is closed.
- **Check failed**: when the plan fails (exit code 1), an issue "Drift check failed: `<stack>/<env>`" is opened, so a broken check isn't silent.
- **Security checks**: a failing read-only `@security` scenario opens or updates an issue.

**Verified by**: `platforms/landing-zone/tests/features/pipeline.feature` (tag `@REQ-LZ-007`)

### REQ-LZ-008: Deployment rules live in code

**Statement**: The `github` stack shall define the GitHub environments and their protection rules, the `main` ruleset, and the non-secret variables CI needs.

#### Acceptance criteria

- **Environments**:
  - `foundation` and `prod` require the owner's review.
  - All three environments deploy only from `main`.
  - Admins can't bypass the rules, and the environments are protected from deletion.
  - Self-review can't be prevented with a single maintainer; that is an accepted gap.
- **Ruleset**: the `main` ruleset (`25774561`) is imported, not recreated. It keeps spec 001's required checks and adds `tofu-plan`.
- **Variables**: the WIF provider name, service-account emails, state bucket name and state key IDs reach workflows as GitHub variables, never as secrets or copied literals.
- **Order**: the stack is applied right after `bootstrap`'s first run, before anything else merges.

**Verified by**: `platforms/landing-zone/tests/features/pipeline.feature` (tag `@REQ-LZ-008`)

### REQ-LZ-009: The seed project holds only the bootstrap layer, and bootstrap converges

**Statement**: The `bootstrap` stack shall create the seed project in the `trust-root` folder, with standard labels, only the allow-listed APIs and a billing link. A second plan after any apply shall show no changes.

#### Acceptance criteria

- The seed project ID is `gcp-agent-factory-seed-<sfx>`, and the 4-character suffix is generated once and kept in state.
- Every labelable resource `bootstrap` creates (project, keys, bucket) carries the standard labels from `modules/labels`.
- The seed has no VPC network and enables exactly the APIs listed in the design.
- After the first run and the state migration, `bootstrap` plans empty and no local state file is left.

**Verified by**: `platforms/landing-zone/tests/features/bootstrap.feature` (tag `@REQ-LZ-009`)

### REQ-LZ-010: Org, folder and seed IAM have one owner

**Statement**: The `bootstrap` stack shall manage the following, and keep CI identities out of the trust root:

- every org-level, top-level-folder and seed-project role binding held by a CI identity or a platform group
- every billing-account role held by a CI identity

#### Acceptance criteria

- **Creator roles**: at org level, Project Creator is held only by `gcp-org-admins`, and Billing Account Creator by nobody. `ci-foundation` creates projects only in `shared`, `dev` and `prod`.
- **CI roles**:
  - Each CI identity holds exactly its allow-listed roles per scope (org, folder, seed, billing account).
  - None holds a role on `trust-root` or the seed apart from `ci-plan`'s viewer roles.
  - None holds Organization Administrator, Security Admin or a basic role.
- **Deny policy**: a deny policy on `trust-root` denies every CI identity the trust-root permissions listed in the design.
- **Billing account**: `ci-foundation` holds exactly Billing Account User and Billing Account Costs Manager (authoritative). Billing Account Administrator stays additive.
- **Seed admin roles**: Owner, Editor and the admin roles for storage, KMS, WIF and service accounts are held only by `gcp-org-admins`.
- **No mixed modes**: no role is managed both authoritatively and additively, so an extra member always shows up as drift.

**Verified by**: `platforms/landing-zone/tests/features/bootstrap.feature` (tag `@REQ-LZ-010`)

### REQ-LZ-011: A billing-account budget exists from the first apply

**Statement**: The `bootstrap` stack shall create a monthly budget on the billing account that measures gross cost.

#### Acceptance criteria

- The amount is €85 per month, with credits excluded, so the free-trial credit can't hide spend.
- It alerts at 25, 50, 75, 90 and 100%, by email to the billing account's administrators and users.

**Verified by**: `platforms/landing-zone/tests/features/bootstrap.feature` (tag `@REQ-LZ-011`)

### REQ-LZ-012: Stack code can't leak data through a plan

**Statement**: The repo checks shall reject stack and module code that could send data out or put a secret into state when it is planned. `ci-plan` shall hold no role that reads data payloads.

#### Acceptance criteria

- **Providers**: every provider in OpenTofu code must be on the allow-list (`hashicorp/google`, `hashicorp/google-beta`, `hashicorp/random`, `integrations/github`). That covers providers declared in `required_providers`, pinned in a lock file, or used through a `resource`, `data` or `ephemeral` type, including data sources inside `check` blocks. `external` and `http` are therefore rejected.
- **Provider blocks** may set only allow-listed arguments, so no custom endpoint, credential or base URL can redirect CI's token.
- **State** lives only in the `gcs` backend, and `terraform_remote_state` reads only from `gcs`. In both cases only `bucket` and `prefix` may be set, and `cloud` blocks are rejected.
- **Also rejected**:
  - provisioners anywhere
  - `nonsensitive(`, also inside templates
  - module sources that aren't local, leave the repository, or point into a directory the checks skip
  - types that handle secret payloads (Secret Manager versions, KMS secrets, service-account keys and tokens)
  - escape sequences that could hide any of these
- **File reads**: `file()`, `templatefile()` and `fileset()` read only literal paths inside the module, or paths declared in the stack's `inputs`.
- **`ci-plan`** holds no Secret Manager accessor, BigQuery data or Storage object role outside the state bucket.

**Verified by**: `libs/repo-checks/tests/features/tofu_safety.feature` and `platforms/landing-zone/tests/features/safety.feature` (tag `@REQ-LZ-012`)

## Out of scope

- **Spec 003 (foundation)**:
  - folder contents, other projects, org policies, tags, project budgets and essential contacts
  - removing the Owner role that `ci-foundation` gets automatically on projects it creates, so no CI identity holds a basic role on any project
  - the conftest plan policies (labels, avoid list, no public IAM), before its first apply
  - deciding whether to accept an Infracost API key or rely on the `cost-impact` skill and budgets
- **Spec 004**: network and VPC-SC, including the Access Context Manager role that needs a `bootstrap` change first.
- **Spec 005**: the budget-enforcer (kill switch L2/L3). It's the first container image, so 005 also decides where Artifact Registry and the image-build identity live. If that's the seed, it's a trust-root change.
- **Later specs**: `ci-killswitch` and other CI identities, each added to `bootstrap` by the spec that needs it.
