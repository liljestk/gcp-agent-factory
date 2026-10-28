# The trust root (spec 002, ADR-0018): top-level folders, the seed project and everything CI
# authenticates with. Only the owner applies this stack; CI plans it read-only.

locals {
  org            = "organizations/${var.org_id}"
  org_admins     = "group:gcp-org-admins@${var.identity_domain}"
  billing_admins = "group:gcp-billing-admins@${var.identity_domain}"

  folders = toset(["trust-root", "shared", "dev", "prod"])

  # APIs the seed needs for the bootstrap layer (spec 002 design); nothing else is enabled.
  seed_services = toset([
    "billingbudgets.googleapis.com",
    "cloudbilling.googleapis.com",
    "cloudkms.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "essentialcontacts.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "orgpolicy.googleapis.com",
    "serviceusage.googleapis.com",
    "storage.googleapis.com",
    "sts.googleapis.com",
  ])
}

module "labels" {
  source = "../../../../modules/labels"

  env       = "shared"
  platform  = "landing-zone"
  component = "bootstrap"
  owner     = "platform-team"
}

# Generated once and kept in state: it makes the seed and bucket names unique (REQ-LZ-009).
resource "random_id" "suffix" {
  byte_length = 2
}

resource "google_folder" "this" {
  for_each = local.folders

  display_name        = each.key
  parent              = local.org
  deletion_protection = true
  deletion_policy     = "PREVENT"
}

module "seed" {
  source = "../../../../modules/project"

  project_id      = "gcp-agent-factory-seed-${random_id.suffix.hex}"
  name            = "gcp-agent-factory-seed"
  folder_id       = google_folder.this["trust-root"].name
  billing_account = var.billing_account
  services        = local.seed_services
  labels          = module.labels.labels
  lien_reason     = "Holds the platform's state, keys and CI identities (spec 002)."
}
