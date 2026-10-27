locals {
  # The trust condition and the two gates, as CEL. They live in one template so the module and
  # the gate tests in tests/iac read exactly the same expressions.
  gates = jsondecode(templatefile("${path.module}/gates.json.tftpl", {
    repository          = var.repository
    repository_id       = var.repository_id
    repository_owner_id = var.repository_owner_id
    owner_actor_id      = coalesce(var.owner_actor_id, var.repository_owner_id)
    apply_workflow      = var.apply_workflow
  }))
}

resource "google_iam_workload_identity_pool" "github" {
  project                   = var.project_id
  workload_identity_pool_id = var.pool_id
  display_name              = "GitHub Actions"
  description               = "Keyless CI for ${var.repository} (spec 002)."
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = var.provider_id
  display_name                       = "GitHub Actions OIDC"

  # Pinned to immutable IDs: a renamed or re-created repository with the same name can't match.
  attribute_condition = local.gates.condition
  attribute_mapping = {
    "google.subject"                = "assertion.sub"
    "attribute.repository_id"       = "assertion.repository_id"
    "attribute.repository_owner_id" = "assertion.repository_owner_id"
    "attribute.plan"                = local.gates.plan
    "attribute.deploy"              = local.gates.deploy
  }

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_binding" "workload_identity_user" {
  for_each = var.service_accounts

  service_account_id = "projects/${var.project_id}/serviceAccounts/${each.value.email}"
  role               = "roles/iam.workloadIdentityUser"
  members = [
    "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.${each.value.gate}/${each.value.gate == "plan" ? "allowed" : each.value.environment}",
  ]
}
