---
status: proposed
date: 2026-10-25
decision-makers: liljestk
---

# ADR-0017: Use the existing sandbox org, with smartass.dad for identities

## Context and problem statement

[ADR-0009](0009-org-and-project-topology.md) planned a Cloud Identity Free organization on a new domain derived from the repo name. The owner would rather not buy a domain (an at-cost `.dev` runs about $10–15 a year, and a name containing "gcp" risks Google's brand guidelines). They also want DNS to stay on Cloudflare.

The owner verified `smartass.dad`, a domain they already hold on Cloudflare, with a DNS TXT record. They added it as a **secondary domain** to a Google account they already had. Google creates one organization per Workspace or Cloud Identity account and names it after the account's **primary** domain, so no new org appears. A domain can belong to only one Google account.

That org holds no projects or users that matter: it's a sandbox (owner, 2026-10-25). It may still carry state the platform didn't create:

- Google grants the primary domain Project Creator and Billing Account Creator on a new org.
- Orgs created since May 2024 enforce some security policies by default.
- It may already hold an access policy, tag keys or log sinks.

Three more facts shape the design:

- `smartass.dad` mail goes to AWS SES (its MX record), not Google. Sign-in, groups and IAM work without Google mail. But nothing sent to an `@smartass.dad` address reaches a Google group or inbox, and that includes security notices for users on the domain.
- The free-trial billing account was opened with the owner's personal Google account, outside any org. No org control (policies, 2-step verification, log sinks) reaches it.
- `iam.allowedPolicyMemberDomains` checks the principal named in a policy, not the members of a group.

## Decision

- **Org**: the platform lives in the existing organization of the owner's Google account. This replaces ADR-0009's first decision bullet; the rest of ADR-0009 stands. The `foundation` stack takes the org over as it is:
  - It removes the domain-wide Project Creator and Billing Account Creator grants, so only `ci-foundation` creates projects.
  - It imports any org policy Google already enforces instead of creating it.
  - It rolls out the remaining policies in dry-run first.
- **Identities**: `smartass.dad` is the platform's identity domain. The groups from PLAN §4.1 and the break-glass account live on it.
  - The groups are security groups that only admins can add members to.
  - The account doesn't allow members from outside it, because the domain restriction doesn't look inside groups.
  - Super admins and break-glass use phishing-resistant 2-step verification (security keys or passkeys), with recovery addresses off `smartass.dad`.
- **Domain restriction**: `iam.allowedPolicyMemberDomains` is keyed on the account's directory customer ID. Dry-run must show that it accepts WIF principal sets and the Google service agents the platform relies on (budget alerts to Pub/Sub, log-sink writers). If it doesn't, the managed `iam.managed.allowedPolicyMembers` replaces it.
- **Billing**: the free-trial billing account stays with the personal account.
  - From it, the owner grants `gcp-billing-admins@smartass.dad` Billing Account Administrator.
  - Bootstrap, run by a member of that group, grants `ci-foundation` Billing Account User and Billing Account Costs Manager and keeps those grants in state.
  - Budgets sit on the billing account, so they cover every project linked to it, inside the org or not.
  - The personal account gets the same phishing-resistant 2-step verification.
- **Notifications**: essential contacts (security, technical, billing, suspension, legal), budget emails and alert channels go to one address on `smartass.dad`. It must be set up before the first `foundation` apply, and tested end to end:
  - SES delivers it to an inbox the owner reads.
  - `essentialcontacts.allowedContactDomains` is `@smartass.dad` only.
  - No notification goes to a `gcp-*` group address.
- The primary domain isn't secret, but nothing needs it: stacks address the org by `org_id` and `customer_id`.

## Consequences

- Good: no domain to buy or move, and no second Google account to run. One TXT record on Cloudflare was the whole setup, so Phase 1 can start now.
- Good: org policies and VPC-SC work as ADR-0009 planned, at $0 extra in GCP.
- Bad: the org's display name is the other domain, not something derived from `gcp-agent-factory`. This is cosmetic.
- Bad: the org must stay a sandbox for as long as the platform runs. Anything later added to it inherits the org policies: EU-only locations, the service deny list, no service-account keys and the domain restriction. CPU and GPU quota caps are set per project, so they only reach projects the factory creates.
- Bad: some controls sit outside IaC, so drift detection can't see them. The bootstrap runbook checks them at every phase gate instead. They are:
  - Admin console settings (2-step verification, group membership rules)
  - the personal billing owner
  - the accounts behind the identity and mail path: Cloudflare holds the verification record, and AWS runs SES
- Bad: the personal account can still unlink projects, delete budgets or upgrade to paid, which removes L4 (ADR-0008). It can also grant billing roles to anyone. Billing-account IAM in bootstrap state and a billing-account log sink make that visible; they don't prevent it.
- Bad: alerting depends on the owner's AWS SES setup, which sits outside the GCP budgets.

## Alternatives considered

- **A new Cloud Identity Free account with `smartass.dad` as its primary domain**: a clean org with a fitting name. But the domain would first have to leave the existing account, and it adds a second admin account to secure. It would be worth it only if the existing org held real work, and it doesn't.
- **Buy a repo-named domain (ADR-0009's plan)**: it costs money, carries the brand risk, and is still bound by the one-account-per-domain rule.
- **A folder in the existing org, with policies set at folder level**: Organization Policy Administrator can only be granted at org level, so CI would hold org-wide policy power anyway. In a sandbox org, a folder boundary isolates nothing.
- **Move the billing account into the org**: that would put it under org controls. But it's unverified whether the free-trial credit survives the move, so this is deferred until checked (PLAN §13).

## Enforcement

- **Variables**: `foundation` takes `org_id`, `customer_id`, `identity_domain` and `notification_email` as validated variables, covered by `tofu test`. Group addresses derive from `identity_domain`, and `notification_email` rejects `gcp-*` group addresses. A `repo-checks` rule rejects literal org IDs, customer IDs and `smartass.dad` in `.tf` files.
- **`@security` BDD scenarios**:
  - During dry-run, the violation log flags a `gmail.com` member and shows no violations for the platform's own principals.
  - After enforcement, that grant is denied, CI still authenticates through WIF, and a budget alert still reaches Pub/Sub.
- **Nightly checks**:
  - Drift detection covers the billing-account IAM in bootstrap state.
  - A Cloud Asset Inventory check fails on any folder or project under the org that `foundation` doesn't manage.
  - A read-only Groups check fails on any `gcp-*` group member from outside the account.
  - An ops log sink on the billing account alerts on IAM and project-link changes.
- **Manual, in the bootstrap runbook at every phase gate**:
  - an inventory of the org before the first apply: IAM, policies, access policies, tag keys, sinks, contacts and workforce pools
  - 2-step verification for super admins, break-glass and the billing owner
  - external group members turned off
  - 2FA on Cloudflare and AWS
  - auto-renew and registrar lock for `smartass.dad`
  - a test message to the notification address
