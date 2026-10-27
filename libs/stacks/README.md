# stacks

The stack catalog and the CI plan/apply matrix for the OpenTofu root modules. Spec: [002: bootstrap and CI pipeline](../../specs/002-bootstrap-and-ci-pipeline/requirements.md) (REQ-LZ-005, REQ-LZ-006).

```bash
uv run stacks matrix --base <sha>   # jobs for the change from <sha> to HEAD
uv run stacks matrix --all          # every job (drift runs)
uv run stacks validate              # catalog rules, every stack path, the module graph
```

The catalog is [`platforms/stacks.yaml`](../../platforms/stacks.yaml). `matrix` prints one line of JSON:

| Key | Content |
|---|---|
| `plan` | the instances CI plans, sorted by ID; each has `id`, `stack`, `instance`, `path`, `state_prefix`, `environment` |
| `apply` | every apply group `<tier>/<shared\|dev\|prod>` in apply order, mapped to its affected instances (empty when unaffected) |

What a change affects:

- **Reading the diff**: `--base` runs `git diff --name-only --no-renames -z <sha>...HEAD` itself. A rename counts as a delete plus an add, so moving code out of a stack still plans it. Names are read raw, so non-ASCII and quoted names match.
- **Which stacks**:
  - A path inside a stack, inside a local module it uses (followed transitively through `.tf`, `.tofu`, `.tf.json` and `.tofu.json`), or matching one of its `inputs` affects that stack.
  - A path under any `all-stacks-paths` entry affects every stack. That list includes the pipeline, the toolchain and this tool.
- **Trust-root stacks** are applied only by the owner (ADR-0018). They never appear under `apply`, and a stack with `plan: local` never appears under `plan`.

It fails closed (exit `1`, message on stderr) instead of guessing when:

- git fails, for example in a shallow clone without the merge base
- a module source isn't a literal path inside the repository
- a file can't be parsed
- anything on the way is a symlink
- a stack uses a module inside another stack's directory
- the catalog breaks a rule (a CI-applied trust-root stack, a repeated key, an unknown key and so on)
