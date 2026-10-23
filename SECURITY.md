# Security policy

## Reporting a vulnerability

Please **do not open a public issue**. Use GitHub's [private vulnerability reporting](https://github.com/liljestk/gcp-agent-factory/security/advisories/new) for this repository. You'll get an acknowledgement within 5 working days.

## Scope

This is a demo platform. In scope: anything in this repository, including OpenTofu code, GitHub Actions workflows, agent code and prompts (including prompt-injection paths), and the documented GCP configuration.

## Baseline controls

- Keyless CI via Workload Identity Federation pinned to this repository's immutable ID. No service-account keys (enforced by org policy).
- All third-party GitHub Actions and pre-commit hooks pinned to commit SHAs; Renovate updates them after a 7-day cooldown.
- Secret scanning with gitleaks (pre-commit + CI) and GitHub push protection.
- Static analysis: CodeQL, ruff security rules (bandit), zizmor for workflows, tflint for IaC.
- Least-privilege identity per agent and app; agents can't change infrastructure directly.

The security rules contributors and coding agents must follow are in [`AGENTS.md`](AGENTS.md#security-rules-never).
