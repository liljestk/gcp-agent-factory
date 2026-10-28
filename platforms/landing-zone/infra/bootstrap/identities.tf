# Keyless CI identities (REQ-LZ-001, REQ-LZ-002). Each gate reaches exactly one account.

locals {
  ci = {
    ci-plan       = { gate = "plan", environment = null, description = "Read-only plans for pull requests, main and the nightly drift run." }
    ci-foundation = { gate = "deploy", environment = "foundation", description = "Applies shared stacks: folders' contents, projects, org policies, tags, contacts." }
    ci-apply-dev  = { gate = "deploy", environment = "dev", description = "Applies dev stacks." }
    ci-apply-prod = { gate = "deploy", environment = "prod", description = "Applies prod stacks." }
  }

  # Built from the accounts' own arguments, so every reference waits for the account to exist.
  ci_email  = { for name, account in google_service_account.ci : name => "${account.account_id}@${account.project}.iam.gserviceaccount.com" }
  ci_member = { for name, email in local.ci_email : name => "serviceAccount:${email}" }
}

resource "google_service_account" "ci" {
  for_each = local.ci

  project      = module.seed.project_id
  account_id   = each.key
  display_name = each.key
  description  = each.value.description
}

module "wif" {
  source = "../../../../modules/wif-github"

  project_id          = module.seed.project_id
  repository          = var.repository
  repository_id       = var.repository_id
  repository_owner_id = var.repository_owner_id
  service_accounts = {
    for name, account in local.ci : name => {
      email       = local.ci_email[name]
      gate        = account.gate
      environment = account.environment
    }
  }
}
