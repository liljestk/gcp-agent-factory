# modules/AGENTS.md: reusable OpenTofu modules

Extends the root `AGENTS.md`. Scaffold new modules with the `tofu-module-new` skill.

## Layout (every module)

```text
modules/<name>/
├── README.md         # purpose, inputs, outputs, example, cost notes
├── versions.tf       # required_version (+ required_providers when it creates resources)
├── variables.tf      # description + type (+ validation) for every variable
├── main.tf
├── outputs.tf        # description for every output
└── tests/<name>.tftest.hcl   # `# covers: REQ-…` comment + run blocks
```

## Rules

- No `provider`, `backend` or `terraform { cloud {} }` blocks. Callers configure providers.
- Labels: take a `labels` input produced by `modules/labels`; never build label maps by hand.
- Tests run offline: use `command = plan`, `mock_provider` and `override_resource`/`override_data`. CI has no cloud credentials at the test stage.
- Cover every `validation` block with an `expect_failures` run, plus at least one happy-path run that asserts outputs.
- Names derive from inputs, never from `random_*` resources inside reusable modules (randomness belongs to `bootstrap`).
- Secure defaults: CMEK-ready, uniform bucket access, no public IAM, deletion protection where the resource supports it.
- Cost: note any resource with an idle cost in the README; most modules should have none.

## Commands

```bash
just test-iac      # tofu test for all modules
just lint-iac      # tofu fmt -check + tflint
```
