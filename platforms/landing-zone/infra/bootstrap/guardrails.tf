# What keeps CI out of the trust root even if a grant slips through (REQ-LZ-010).

locals {
  # Every permission that would change the trust-root folder, the seed or what it holds. All are
  # on Google's list of permissions deny policies support (checked 2026-10-28). Deny-policy and
  # billing-account changes aren't on that list; IAM and drift detection cover those.
  trust_root_denied_permissions = sort([
    "cloudresourcemanager.googleapis.com/folders.create",
    "cloudresourcemanager.googleapis.com/folders.delete",
    "cloudresourcemanager.googleapis.com/folders.move",
    "cloudresourcemanager.googleapis.com/folders.setIamPolicy",
    "cloudresourcemanager.googleapis.com/folders.undelete",
    "cloudresourcemanager.googleapis.com/folders.update",
    "cloudresourcemanager.googleapis.com/projects.create",
    "cloudresourcemanager.googleapis.com/projects.createBillingAssignment",
    "cloudresourcemanager.googleapis.com/projects.delete",
    "cloudresourcemanager.googleapis.com/projects.deleteBillingAssignment",
    "cloudresourcemanager.googleapis.com/projects.move",
    "cloudresourcemanager.googleapis.com/projects.setIamPolicy",
    "cloudresourcemanager.googleapis.com/projects.undelete",
    "cloudresourcemanager.googleapis.com/projects.update",
    "cloudresourcemanager.googleapis.com/projects.updateLiens",
    "iam.googleapis.com/roles.create",
    "iam.googleapis.com/roles.delete",
    "iam.googleapis.com/roles.undelete",
    "iam.googleapis.com/roles.update",
    "iam.googleapis.com/serviceAccounts.actAs",
    "iam.googleapis.com/serviceAccounts.create",
    "iam.googleapis.com/serviceAccounts.delete",
    "iam.googleapis.com/serviceAccounts.disable",
    "iam.googleapis.com/serviceAccounts.enable",
    "iam.googleapis.com/serviceAccounts.getAccessToken",
    "iam.googleapis.com/serviceAccounts.getOpenIdToken",
    "iam.googleapis.com/serviceAccounts.implicitDelegation",
    "iam.googleapis.com/serviceAccounts.setIamPolicy",
    "iam.googleapis.com/serviceAccounts.signBlob",
    "iam.googleapis.com/serviceAccounts.signJwt",
    "iam.googleapis.com/serviceAccounts.undelete",
    "iam.googleapis.com/serviceAccounts.update",
    "iam.googleapis.com/serviceAccountKeys.create",
    "iam.googleapis.com/serviceAccountKeys.delete",
    "iam.googleapis.com/serviceAccountKeys.disable",
    "iam.googleapis.com/serviceAccountKeys.enable",
    "iam.googleapis.com/workloadIdentityPoolProviderKeys.create",
    "iam.googleapis.com/workloadIdentityPoolProviderKeys.delete",
    "iam.googleapis.com/workloadIdentityPoolProviderKeys.undelete",
    "iam.googleapis.com/workloadIdentityPoolProviders.create",
    "iam.googleapis.com/workloadIdentityPoolProviders.delete",
    "iam.googleapis.com/workloadIdentityPoolProviders.undelete",
    "iam.googleapis.com/workloadIdentityPoolProviders.update",
    "iam.googleapis.com/workloadIdentityPools.create",
    "iam.googleapis.com/workloadIdentityPools.createPolicyBinding",
    "iam.googleapis.com/workloadIdentityPools.delete",
    "iam.googleapis.com/workloadIdentityPools.deletePolicyBinding",
    "iam.googleapis.com/workloadIdentityPools.setIamPolicy",
    "iam.googleapis.com/workloadIdentityPools.undelete",
    "iam.googleapis.com/workloadIdentityPools.update",
    "iam.googleapis.com/workloadIdentityPools.updatePolicyBinding",
    "cloudkms.googleapis.com/cryptoKeys.create",
    "cloudkms.googleapis.com/cryptoKeys.delete",
    "cloudkms.googleapis.com/cryptoKeys.setIamPolicy",
    "cloudkms.googleapis.com/cryptoKeys.update",
    "cloudkms.googleapis.com/cryptoKeyVersions.create",
    "cloudkms.googleapis.com/cryptoKeyVersions.delete",
    "cloudkms.googleapis.com/cryptoKeyVersions.destroy",
    "cloudkms.googleapis.com/cryptoKeyVersions.restore",
    "cloudkms.googleapis.com/cryptoKeyVersions.update",
    "cloudkms.googleapis.com/importJobs.create",
    "cloudkms.googleapis.com/keyRings.create",
    "cloudkms.googleapis.com/keyRings.delete",
    "cloudkms.googleapis.com/keyRings.setIamPolicy",
    "storage.googleapis.com/buckets.create",
    "storage.googleapis.com/buckets.createTagBinding",
    "storage.googleapis.com/buckets.delete",
    "storage.googleapis.com/buckets.deleteTagBinding",
    "storage.googleapis.com/buckets.enableObjectRetention",
    "storage.googleapis.com/buckets.relocate",
    "storage.googleapis.com/buckets.restore",
    "storage.googleapis.com/buckets.setIamPolicy",
    "storage.googleapis.com/buckets.setIpFilter",
    "storage.googleapis.com/buckets.update",
    # HMAC keys are long-lived Cloud Storage credentials for a service account, outside WIF and
    # outside the service-account key policy; managed folders and object policies set access
    # without touching the bucket's policy.
    "storage.googleapis.com/hmacKeys.create",
    "storage.googleapis.com/hmacKeys.update",
    "storage.googleapis.com/managedFolders.create",
    "storage.googleapis.com/managedFolders.delete",
    "storage.googleapis.com/managedFolders.setIamPolicy",
    "storage.googleapis.com/managedFolders.update",
    "storage.googleapis.com/objects.setIamPolicy",
    # The audit trail of the seed: sinks, exclusions and log buckets could drop or reroute it.
    "logging.googleapis.com/buckets.delete",
    "logging.googleapis.com/buckets.update",
    "logging.googleapis.com/exclusions.create",
    "logging.googleapis.com/exclusions.update",
    "logging.googleapis.com/links.create",
    "logging.googleapis.com/logs.delete",
    "logging.googleapis.com/sinks.create",
    "logging.googleapis.com/sinks.delete",
    "logging.googleapis.com/sinks.update",
    "logging.googleapis.com/views.setIamPolicy",
    "serviceusage.googleapis.com/consumerpolicy.update",
    "serviceusage.googleapis.com/services.disable",
    "serviceusage.googleapis.com/services.enable",
    # Other ways to add identities to the pool.
    "iam.googleapis.com/workloadIdentityPoolManagedIdentities.create",
    "iam.googleapis.com/workloadIdentityPoolManagedIdentities.setAttestationRules",
    "iam.googleapis.com/workloadIdentityPoolManagedIdentities.update",
    "iam.googleapis.com/workloadIdentityPoolNamespaces.create",
    "iam.googleapis.com/workloadIdentityPoolNamespaces.update",
    "iam.googleapis.com/workloadIdentityPools.setAttestationRules",
    "orgpolicy.googleapis.com/policies.create",
    "orgpolicy.googleapis.com/policies.delete",
    "orgpolicy.googleapis.com/policies.update",
    "orgpolicy.googleapis.com/policy.set",
    "essentialcontacts.googleapis.com/contacts.create",
    "essentialcontacts.googleapis.com/contacts.delete",
    "essentialcontacts.googleapis.com/contacts.update",
  ])

  # How CI signs in: a federated identity mints a token for the account its gate is bound to.
  token_minting = ["iam.googleapis.com/serviceAccounts.getAccessToken", "iam.googleapis.com/serviceAccounts.getOpenIdToken"]
}

resource "google_iam_deny_policy" "trust_root" {
  parent          = urlencode("cloudresourcemanager.googleapis.com/${google_folder.this["trust-root"].name}")
  name            = "ci-stays-out"
  display_name    = "CI identities can't change the trust root"
  deletion_policy = "PREVENT"

  rules {
    description = "The CI service accounts can't change the trust-root folder, the seed or anything in it (spec 002)."
    deny_rule {
      denied_principals  = sort([for email in values(local.ci_email) : "principal://iam.googleapis.com/projects/-/serviceAccounts/${email}"])
      denied_permissions = local.trust_root_denied_permissions
    }
  }

  rules {
    description = "Nor can any identity of the GitHub pool, even if granted a role directly. It may only mint tokens for the CI accounts, which is how CI signs in."
    deny_rule {
      denied_principals  = ["principalSet://iam.googleapis.com/${module.wif.pool_name}/*"]
      denied_permissions = sort(tolist(setsubtract(local.trust_root_denied_permissions, local.token_minting)))
    }
  }

  # The owner may hold Deny Admin only through this stack's binding (design: first run).
  depends_on = [google_organization_iam_binding.authoritative]
}

# Folder policies on trust-root, which foundation never manages. A folder policy replaces the
# org's, so ci-foundation's org-level Organization Policy Administrator can't loosen these, and the
# deny policy stops it from changing them here. They keep the seed free of networks, service
# account keys, HMAC access, long-lived tokens, identity providers other than GitHub's, and
# contacts outside the identity domain.
locals {
  trust_root_policies = {
    for constraint, rule in {
      "compute.skipDefaultNetworkCreation"                 = { enforce = "TRUE" }
      "iam.disableServiceAccountKeyCreation"               = { enforce = "TRUE" }
      "iam.disableServiceAccountKeyUpload"                 = { enforce = "TRUE" }
      "iam.allowServiceAccountCredentialLifetimeExtension" = { deny_all = "TRUE" }
      "iam.workloadIdentityPoolAwsAccounts"                = { deny_all = "TRUE" }
      "iam.workloadIdentityPoolProviders"                  = { allowed = ["https://token.actions.githubusercontent.com"] }
      "storage.restrictAuthTypes"                          = { denied = ["in:ALL_HMAC_SIGNED_REQUESTS"] }
      "essentialcontacts.allowedContactDomains"            = { allowed = ["@${var.identity_domain}"] }
    } : constraint => merge({ enforce = null, deny_all = null, allowed = null, denied = null }, rule)
  }
}

resource "google_org_policy_policy" "trust_root" {
  for_each = local.trust_root_policies

  name   = "${google_folder.this["trust-root"].name}/policies/${each.key}"
  parent = google_folder.this["trust-root"].name

  spec {
    rules {
      enforce  = each.value.enforce
      deny_all = each.value.deny_all

      dynamic "values" {
        for_each = each.value.allowed == null && each.value.denied == null ? [] : [each.value]
        content {
          allowed_values = values.value.allowed
          denied_values  = values.value.denied
        }
      }
    }
  }

  # The owner may hold Organization Policy Administrator only through this stack's binding.
  depends_on = [google_organization_iam_binding.authoritative]
}

# Data Access logs on the seed, so every CI credential issued, every state object read and every
# state key used is on record per identity. They are a few dozen entries per run.
resource "google_project_iam_audit_config" "seed" {
  for_each = toset(["sts.googleapis.com", "iamcredentials.googleapis.com", "storage.googleapis.com", "cloudkms.googleapis.com"])

  project = module.seed.project_id
  service = each.key

  audit_log_config {
    log_type = "ADMIN_READ"
  }
  audit_log_config {
    log_type = "DATA_READ"
  }
  audit_log_config {
    log_type = "DATA_WRITE"
  }
}
