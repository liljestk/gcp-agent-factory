resource "google_project" "this" {
  project_id      = var.project_id
  name            = var.name
  folder_id       = var.folder_id
  billing_account = var.billing_account
  labels          = var.labels

  # GCP creates the default network only when the Compute Engine API is first enabled, so a
  # project without compute has none. Asking the provider to delete it (false) makes it turn
  # compute on first, which would add an API nobody manages; only do that where compute runs.
  auto_create_network = !var.delete_default_network
  deletion_policy     = var.deletion_policy
}

resource "google_project_service" "this" {
  for_each = var.services

  project = google_project.this.project_id
  service = each.value

  # Turning an API off can break whatever still uses it; removing it from the list is enough.
  disable_on_destroy         = false
  disable_dependent_services = false
}

resource "google_resource_manager_lien" "this" {
  count = var.lien_reason == null ? 0 : 1

  parent       = "projects/${google_project.this.number}"
  restrictions = ["resourcemanager.projects.delete"]
  origin       = "gcp-agent-factory"
  reason       = var.lien_reason
}
