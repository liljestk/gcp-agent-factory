---
name: security-review
description: Security review of a change in gcp-agent-factory covering IAM, network egress, secrets, supply chain, GitHub workflows, secure coding (OWASP ASVS L2) and agent risks (OWASP Top 10 for LLM apps, prompt injection, excessive agency). Use before merging infra, workflow, agent or tool changes, or when the user asks for a security review.
---

# security-review

## Checklist

### Identity and access

- [ ] No service-account keys, no `allUsers`/`allAuthenticatedUsers`, no primitive roles on SAs.
- [ ] New permissions are the minimum; custom role if a predefined one is too broad; IAM conditions where useful.
- [ ] WIF bindings are scoped to the repository ID and a GitHub environment.

### Network and data

- [ ] No new internet egress unless the manifest declares it; no external IPs, NAT or public buckets.
- [ ] Sensitive data is classified (policy tags), CMEK where required, retention set.

### Secrets

- [ ] No secrets in code, config, logs or test fixtures; Secret Manager referenced by name only.

### Supply chain and CI

- [ ] Actions and hooks pinned to commit SHAs; `permissions:` minimal per job; `persist-credentials: false`.
- [ ] No `pull_request_target` with a PR checkout; no untrusted input (`github.event.*`) interpolated into `run:`.
- [ ] New dependencies are maintained, licensed and locked.

### Secure coding (ASVS L2)

- [ ] Inputs validated at the boundary (Pydantic); outputs encoded; no `eval`/`exec`/`shell=True`/`pickle` on untrusted data.
- [ ] Errors don't leak internals; logs are structured and carry no PII or secrets.

### Agents (OWASP LLM Top 10 / agentic)

- [ ] Tools are allow-listed in the manifest; side-effectful tools need HITL when `risk_tier ≥ medium`.
- [ ] Prompt injection: untrusted content (web, docs, tickets) is treated as data; tool outputs are validated before reuse.
- [ ] Excessive agency: the agent can't change infra or IAM itself (agents propose, pipelines dispose).
- [ ] Token budget and kill switch apply; outputs validated against schemas.

## Output

```markdown
| # | Area | Finding | Severity | Evidence (file:line) | Fix |
|---|---|---|---|---|---|
```

Verdict: `security: pass` / `pass with follow-ups` / `changes required`. Report only what you verified in the code; mark assumptions as such.
