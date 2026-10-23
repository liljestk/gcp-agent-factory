---
name: tofu-module-new
description: Scaffold a reusable OpenTofu module under modules/ with variables, validation, outputs, README and offline tofu tests. Use when adding a new building block (e.g. pubsub-channel, agent-service, data-product) or when the user asks for a new Terraform/OpenTofu module.
---

# tofu-module-new

Follow `modules/AGENTS.md`. Reference implementation: `modules/labels`.

## Steps

1. Create `modules/<name>/` with `versions.tf`, `variables.tf`, `main.tf`, `outputs.tf`, `README.md` and `tests/<name>.tftest.hcl`.
2. `versions.tf`: `required_version = ">= 1.13.0"` and, if it creates resources, `required_providers` with a pessimistic pin (`~> X.Y`) for `hashicorp/google` and `google-beta` as needed. **No provider or backend blocks.**
3. `variables.tf`: `description` + `type` for every variable; `validation` for anything with a constrained format (names, regions, sizes). Accept `labels = map(string)` produced by `modules/labels`; never build label maps here.
4. `main.tf`: secure defaults: uniform bucket-level access, public access prevention, no `allUsers`, CMEK-ready (`kms_key_name` variable), deletion protection where available, and `max_instances`-style caps for compute. No `local-exec` or `null_resource`.
5. `outputs.tf`: `description` on every output; expose IDs and names, not whole resources.
6. Tests (offline, no credentials):
   - Start the file with `# covers: REQ-<AREA>-<NNN>` for the requirements it proves.
   - `mock_provider "google" {}` (and `google-beta`), `command = plan`.
   - One happy-path `run` asserting key attributes and outputs.
   - One `run` with `expect_failures = [var.<x>]` per validation block.
   - Use `override_resource` / `override_data` for computed values you assert on.
7. `README.md`: purpose, inputs and outputs tables, example, and **Cost notes** (idle cost of anything it creates; most modules should have none).
8. Run `just lint-iac` and `just test-iac`.

## Checklist before done

- [ ] Every validation has a failing-case test
- [ ] Labels come in as a variable
- [ ] Idle cost noted in the README
- [ ] Requirement traced via `# covers:`
