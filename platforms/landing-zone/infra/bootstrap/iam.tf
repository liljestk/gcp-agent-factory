# Org, top-level folder, seed and billing-account IAM (REQ-LZ-010). Each role is managed in exactly
# one mode: authoritative bindings list every member, groups included, so an extra member shows up
# as drift; additive grants are only for roles no CI identity holds.

locals {
  # Roles that let a principal act as, or mint tokens for, a service account. Nobody holds them at
  # org level or on the seed; the CI accounts' own policies grant only Workload Identity User to
  # their gate (modules/wif-github).
  impersonation_roles = toset([
    "roles/iam.serviceAccountTokenCreator",
    "roles/iam.serviceAccountOpenIdTokenCreator",
    "roles/iam.serviceAccountUser",
    "roles/iam.workloadIdentityUser",
  ])

  org_authoritative = merge(
    { for role in local.impersonation_roles : role => [] },
    {
      "roles/browser"                        = [local.ci_member["ci-plan"]]
      "roles/iam.securityReviewer"           = [local.ci_member["ci-plan"]]
      "roles/iam.denyReviewer"               = [local.ci_member["ci-plan"]]
      "roles/orgpolicy.policyViewer"         = [local.ci_member["ci-plan"]]
      "roles/resourcemanager.folderViewer"   = [local.ci_member["ci-plan"]]
      "roles/resourcemanager.tagViewer"      = [local.ci_member["ci-plan"]]
      "roles/orgpolicy.policyAdmin"          = [local.ci_member["ci-foundation"], local.org_admins]
      "roles/resourcemanager.tagAdmin"       = [local.ci_member["ci-foundation"]]
      "roles/essentialcontacts.admin"        = [local.ci_member["ci-foundation"]]
      "roles/resourcemanager.projectCreator" = [local.org_admins]
      "roles/billing.creator"                = []
      # Deny-policy changes can't themselves be denied, so whoever holds this guards the deny
      # policy. Organization Administrator can always grant it back.
      "roles/iam.denyAdmin" = [local.org_admins]
    },
  )

  # The owner's standing roles for running this stack.
  org_additive = {
    "roles/resourcemanager.organizationAdmin" = local.org_admins
    "roles/resourcemanager.folderCreator"     = local.org_admins
  }

  # Folder policies are managed whole. trust-root holds nothing, so nothing CI holds is inherited
  # by the seed; ci-foundation's folder roles sit on shared, dev and prod only.
  folder_roles = {
    trust-root = {}
    shared     = local.foundation_folder_roles
    dev        = local.foundation_folder_roles
    prod       = local.foundation_folder_roles
  }
  foundation_folder_roles = {
    "roles/resourcemanager.folderAdmin"    = [local.ci_member["ci-foundation"]]
    "roles/resourcemanager.projectCreator" = [local.ci_member["ci-foundation"]]
    "roles/billing.projectManager"         = [local.ci_member["ci-foundation"]]
    "roles/resourcemanager.tagUser"        = [local.ci_member["ci-foundation"]]
  }

  seed_authoritative = merge(
    { for role in local.impersonation_roles : role => [] },
    {
      "roles/owner"                         = [local.org_admins]
      "roles/storage.admin"                 = [local.org_admins]
      "roles/cloudkms.admin"                = [local.org_admins]
      "roles/iam.workloadIdentityPoolAdmin" = [local.org_admins]
      "roles/iam.serviceAccountAdmin"       = [local.org_admins]
      "roles/iam.serviceAccountKeyAdmin"    = []
      # Google grants its APIs service agent Editor on every new project; nobody else holds it.
      "roles/editor"                            = ["serviceAccount:${module.seed.number}@cloudservices.gserviceaccount.com"]
      "roles/serviceusage.serviceUsageConsumer" = sort(values(local.ci_member))
      "roles/cloudkms.viewer"                   = [local.ci_member["ci-plan"]]
      "roles/iam.workloadIdentityPoolViewer"    = [local.ci_member["ci-plan"]]
      "roles/iam.serviceAccountViewer"          = [local.ci_member["ci-plan"]]
      "roles/serviceusage.serviceUsageViewer"   = [local.ci_member["ci-plan"]]
    },
  )

  billing_authoritative = {
    "roles/billing.user"         = [local.ci_member["ci-foundation"]]
    "roles/billing.costsManager" = [local.ci_member["ci-foundation"]]
    "roles/billing.viewer"       = [local.ci_member["ci-plan"]]
  }
  # Additive, so the personal billing owner (ADR-0017) can't be locked out.
  billing_additive = {
    "roles/billing.admin" = local.billing_admins
  }
}

resource "google_organization_iam_binding" "authoritative" {
  for_each = local.org_authoritative

  org_id  = var.org_id
  role    = each.key
  members = each.value
}

resource "google_organization_iam_member" "additive" {
  for_each = local.org_additive

  org_id = var.org_id
  role   = each.key
  member = each.value

  # These wrap the owner's own access, granted outside this stack; destroying one would strip it.
  lifecycle {
    prevent_destroy = true
  }
}

data "google_iam_policy" "folder" {
  for_each = local.folder_roles

  dynamic "binding" {
    for_each = each.value
    content {
      role    = binding.key
      members = binding.value
    }
  }
}

resource "google_folder_iam_policy" "this" {
  for_each = local.folder_roles

  folder      = google_folder.this[each.key].name
  policy_data = data.google_iam_policy.folder[each.key].policy_data
}

resource "google_project_iam_binding" "seed" {
  for_each = local.seed_authoritative

  project = module.seed.project_id
  role    = each.key
  members = each.value
}

resource "google_billing_account_iam_binding" "authoritative" {
  for_each = local.billing_authoritative

  billing_account_id = var.billing_account
  role               = each.key
  members            = each.value
}

resource "google_billing_account_iam_member" "additive" {
  for_each = local.billing_additive

  billing_account_id = var.billing_account
  role               = each.key
  member             = each.value

  lifecycle {
    prevent_destroy = true
  }
}
