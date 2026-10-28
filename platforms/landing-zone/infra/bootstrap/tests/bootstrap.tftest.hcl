# covers: REQ-LZ-003, REQ-LZ-004, REQ-LZ-009, REQ-LZ-010, REQ-LZ-011
#
# Plan-only: the keys' and bucket's prevent_destroy would make an apply run's clean-up fail.

mock_provider "google" {
  mock_data "google_iam_policy" {
    defaults = {
      policy_data = "{\"bindings\":[]}"
    }
  }

  mock_data "google_storage_project_service_account" {
    defaults = {
      email_address = "service-123456789012@gs-project-accounts.iam.gserviceaccount.com"
    }
  }
}

mock_provider "random" {
  mock_resource "random_id" {
    defaults = {
      hex = "a1b2"
    }
  }
}

override_resource {
  target = module.seed.google_project.this
  values = {
    number = "123456789012"
  }
}

override_resource {
  target = google_folder.this["trust-root"]
  values = {
    name = "folders/1000"
  }
}

override_resource {
  target = google_folder.this["shared"]
  values = {
    name = "folders/2000"
  }
}

override_resource {
  target = google_folder.this["dev"]
  values = {
    name = "folders/3000"
  }
}

override_resource {
  target = google_folder.this["prod"]
  values = {
    name = "folders/4000"
  }
}

override_data {
  target = data.google_iam_policy.folder["trust-root"]
  values = {
    policy_data = "{\"etag\":\"folder-trust-root\"}"
  }
}

override_data {
  target = data.google_iam_policy.folder["shared"]
  values = {
    policy_data = "{\"etag\":\"folder-shared\"}"
  }
}

override_data {
  target = data.google_iam_policy.folder["dev"]
  values = {
    policy_data = "{\"etag\":\"folder-dev\"}"
  }
}

override_data {
  target = data.google_iam_policy.folder["prod"]
  values = {
    policy_data = "{\"etag\":\"folder-prod\"}"
  }
}

override_data {
  target = data.google_iam_policy.state
  values = {
    policy_data = "{\"etag\":\"state-bucket\"}"
  }
}

override_resource {
  target = module.wif.google_iam_workload_identity_pool.github
  values = {
    name = "projects/123456789012/locations/global/workloadIdentityPools/github"
  }
}

variables {
  org_id          = "123456789012"
  customer_id     = "C01abcd2e"
  identity_domain = "example.com"
  billing_account = "012345-6789AB-CDEF01"
  state_bucket    = "gcp-agent-factory-tfstate-a1b2"
  state_key       = "projects/gcp-agent-factory-seed-a1b2/locations/europe-north1/keyRings/tfstate/cryptoKeys/state-trust-root"
}

run "trust_root_layer" {
  command = plan

  assert {
    condition     = module.seed.folder_id == "folders/1000" && module.seed.lien != null
    error_message = "The seed sits in the trust-root folder, with a lien against deletion."
  }

  assert {
    condition     = toset([for folder in google_folder.this : folder.display_name]) == toset(["trust-root", "shared", "dev", "prod"])
    error_message = "bootstrap creates exactly the four top-level folders."
  }

  assert {
    condition     = alltrue([for folder in google_folder.this : folder.parent == "organizations/123456789012" && folder.deletion_protection && folder.deletion_policy == "PREVENT"])
    error_message = "The folders sit under the org and are protected from deletion."
  }

  assert {
    condition     = output.seed_project_id == "gcp-agent-factory-seed-a1b2"
    error_message = "The seed is gcp-agent-factory-seed-<sfx>, with the suffix kept in state."
  }

  assert {
    condition = module.seed.services == sort([
      "billingbudgets.googleapis.com", "cloudbilling.googleapis.com", "cloudkms.googleapis.com",
      "cloudresourcemanager.googleapis.com", "essentialcontacts.googleapis.com", "iam.googleapis.com",
      "iamcredentials.googleapis.com", "orgpolicy.googleapis.com", "serviceusage.googleapis.com",
      "storage.googleapis.com", "sts.googleapis.com",
    ])
    error_message = "The seed enables exactly the allow-listed APIs, so no compute and no VPC network."
  }

  assert {
    condition     = google_storage_bucket.state.labels["component"] == "bootstrap" && google_storage_bucket.state.labels["managed-by"] == "opentofu" && google_storage_bucket.state.labels["repo"] == "gcp-agent-factory"
    error_message = "Labelled resources carry the standard labels from modules/labels."
  }

  assert {
    condition     = google_org_policy_policy.trust_root["compute.skipDefaultNetworkCreation"].spec[0].rules[0].enforce == "TRUE"
    error_message = "trust-root skips default networks, so the seed never gets one."
  }
}

run "state_is_protected" {
  command = plan

  assert {
    condition     = output.state_bucket == "gcp-agent-factory-tfstate-a1b2" && google_storage_bucket.state.location == "europe-north1"
    error_message = "The state bucket is gcp-agent-factory-tfstate-<sfx> in europe-north1."
  }

  assert {
    condition     = google_storage_bucket.state.versioning[0].enabled && google_storage_bucket.state.uniform_bucket_level_access && google_storage_bucket.state.public_access_prevention == "enforced"
    error_message = "The bucket is versioned, with uniform access and public access prevention."
  }

  assert {
    condition     = google_storage_bucket.state.soft_delete_policy[0].retention_duration_seconds == 604800 && !google_storage_bucket.state.force_destroy
    error_message = "The bucket keeps deleted objects for 7 days and can't be force-destroyed."
  }

  assert {
    condition     = google_storage_bucket.state.encryption[0].default_kms_key_name == module.kms.key_ids["bucket"]
    error_message = "The bucket's default key is tfstate/bucket."
  }

  assert {
    condition = length(google_storage_bucket.state.lifecycle_rule) == 2 && anytrue([for rule in google_storage_bucket.state.lifecycle_rule : one(rule.condition).num_newer_versions == 10]) && anytrue([for rule in google_storage_bucket.state.lifecycle_rule : one(rule.condition).days_since_noncurrent_time == 30]) && alltrue([
      for rule in google_storage_bucket.state.lifecycle_rule : one(rule.action).type == "Delete" && one(rule.condition).with_state == "ARCHIVED"
    ])
    error_message = "Noncurrent versions go once 10 newer ones exist or after 30 days; current state is never touched."
  }

  assert {
    condition     = keys(output.state_keys) == ["dev", "github", "prod", "shared", "trust-root"]
    error_message = "Each scope has its own state key, and the github stack has one of its own."
  }
}

run "state_access_by_prefix" {
  command = plan

  assert {
    condition     = length(one([for binding in data.google_iam_policy.state.binding : binding if binding.role == "roles/storage.legacyBucketReader"]).condition) == 0
    error_message = "Listing names is the only bucket-wide grant."
  }

  assert {
    condition = alltrue([
      for binding in data.google_iam_policy.state.binding :
      binding.role == "roles/storage.legacyBucketReader" || (contains(["roles/storage.objectViewer", "roles/storage.objectUser"], binding.role) && length(binding.condition) == 1 && length(binding.members) == 1)
    ])
    error_message = "Object access is only ever granted per identity, under a prefix condition."
  }

  assert {
    condition = toset([
      for binding in data.google_iam_policy.state.binding : one(binding.members) if binding.role == "roles/storage.objectUser"
      ]) == toset([
      "serviceAccount:ci-foundation@gcp-agent-factory-seed-a1b2.iam.gserviceaccount.com",
      "serviceAccount:ci-apply-dev@gcp-agent-factory-seed-a1b2.iam.gserviceaccount.com",
      "serviceAccount:ci-apply-prod@gcp-agent-factory-seed-a1b2.iam.gserviceaccount.com",
    ])
    error_message = "Only the apply identities write state; ci-plan writes nothing."
  }

  assert {
    condition = alltrue([
      for binding in data.google_iam_policy.state.binding :
      !strcontains(one(binding.condition).expression, "/objects/trust-root/") if binding.role == "roles/storage.objectUser"
    ])
    error_message = "No CI identity can write or delete anything under trust-root/."
  }

  assert {
    condition = alltrue([
      for binding in data.google_iam_policy.state.binding :
      !strcontains(one(binding.condition).expression, "/objects/trust-root/github/") && !strcontains(one(binding.condition).expression, "/objects/trust-root/\")") if binding.role != "roles/storage.legacyBucketReader"
    ])
    error_message = "No CI identity can read trust-root/github/."
  }

  assert {
    condition = local.state_reads == {
      ci-plan       = ["trust-root/bootstrap/", "shared/", "dev/", "prod/"]
      ci-foundation = ["trust-root/bootstrap/"]
      ci-apply-dev  = ["trust-root/bootstrap/", "shared/"]
      ci-apply-prod = ["trust-root/bootstrap/", "shared/"]
    }
    error_message = "Each identity reads exactly the state it plans or consumes."
  }

  assert {
    condition = alltrue([
      for prefix in flatten(concat(values(local.state_reads), values(local.state_writes))) :
      endswith(prefix, "/") && !startswith("trust-root/github/", prefix)
    ])
    error_message = "Every prefix is a whole directory, and none covers trust-root/github/."
  }

  assert {
    condition     = google_storage_bucket_iam_policy.state.policy_data == data.google_iam_policy.state.policy_data && google_storage_bucket_iam_policy.state.bucket == "gcp-agent-factory-tfstate-a1b2"
    error_message = "The prefix policy is the state bucket's whole policy."
  }

  assert {
    condition     = local.state_writes == { ci-foundation = ["shared/"], ci-apply-dev = ["dev/"], ci-apply-prod = ["prod/"] }
    error_message = "Each apply identity writes only its own scope: dev can't write prod, prod can't write dev, foundation writes neither."
  }

  assert {
    condition     = one([for binding in data.google_iam_policy.state.binding : binding.condition[0].expression if binding.role == "roles/storage.objectUser" && contains(binding.members, "serviceAccount:ci-apply-dev@gcp-agent-factory-seed-a1b2.iam.gserviceaccount.com")]) == "resource.name.startsWith(\"projects/_/buckets/gcp-agent-factory-tfstate-a1b2/objects/dev/\")"
    error_message = "Prefix conditions match whole object names in this bucket."
  }

  assert {
    condition = (
      local.state_keys["state-dev"].encrypters_decrypters == ["serviceAccount:ci-apply-dev@gcp-agent-factory-seed-a1b2.iam.gserviceaccount.com", "serviceAccount:ci-plan@gcp-agent-factory-seed-a1b2.iam.gserviceaccount.com"]
      && local.state_keys["state-prod"].encrypters_decrypters == ["serviceAccount:ci-apply-prod@gcp-agent-factory-seed-a1b2.iam.gserviceaccount.com", "serviceAccount:ci-plan@gcp-agent-factory-seed-a1b2.iam.gserviceaccount.com"]
      && !can(local.state_keys["state-dev"].decrypters) && !can(local.state_keys["state-prod"].decrypters)
    )
    error_message = "dev and prod state keys are usable only by their own apply identity and ci-plan."
  }

  assert {
    condition     = !contains(local.state_keys["state-trust-root"].encrypters_decrypters, "serviceAccount:ci-foundation@gcp-agent-factory-seed-a1b2.iam.gserviceaccount.com") && contains(local.state_keys["state-trust-root"].decrypters, "serviceAccount:ci-apply-dev@gcp-agent-factory-seed-a1b2.iam.gserviceaccount.com")
    error_message = "Apply identities may only decrypt trust-root state."
  }

  assert {
    condition     = contains(local.state_keys["state-shared"].encrypters_decrypters, "serviceAccount:ci-foundation@gcp-agent-factory-seed-a1b2.iam.gserviceaccount.com") && local.state_keys["bucket"].encrypters_decrypters == ["serviceAccount:service-123456789012@gs-project-accounts.iam.gserviceaccount.com"]
    error_message = "ci-foundation writes shared state; only the Cloud Storage agent uses the bucket key."
  }

  assert {
    condition     = local.state_keys["state-github"].encrypters_decrypters == ["group:gcp-org-admins@example.com"] && !can(local.state_keys["state-github"].decrypters)
    error_message = "Only the owner can use the github stack's state key."
  }
}

run "ci_roles_are_an_allow_list" {
  command = plan

  assert {
    condition     = toset([for role, binding in google_organization_iam_binding.authoritative : role if contains(binding.members, "serviceAccount:ci-plan@gcp-agent-factory-seed-a1b2.iam.gserviceaccount.com")]) == toset(["roles/browser", "roles/iam.securityReviewer", "roles/iam.denyReviewer", "roles/orgpolicy.policyViewer", "roles/resourcemanager.folderViewer", "roles/resourcemanager.tagViewer"])
    error_message = "ci-plan holds exactly its org viewer roles."
  }

  assert {
    condition     = toset([for role, binding in google_organization_iam_binding.authoritative : role if contains(binding.members, "serviceAccount:ci-foundation@gcp-agent-factory-seed-a1b2.iam.gserviceaccount.com")]) == toset(["roles/orgpolicy.policyAdmin", "roles/resourcemanager.tagAdmin", "roles/essentialcontacts.admin"])
    error_message = "ci-foundation holds exactly Organization Policy Administrator, Tag Admin and Essential Contacts Admin at org level."
  }

  assert {
    condition     = alltrue([for binding in google_organization_iam_binding.authoritative : !strcontains(join(",", binding.members), "ci-apply-")])
    error_message = "The apply identities hold nothing at org level."
  }

  assert {
    condition     = alltrue([for name, policy in data.google_iam_policy.folder : name == "trust-root" ? length(policy.binding) == 0 : toset([for binding in policy.binding : binding.role]) == toset(["roles/resourcemanager.folderAdmin", "roles/resourcemanager.projectCreator", "roles/billing.projectManager", "roles/resourcemanager.tagUser"])])
    error_message = "trust-root's whole policy is empty; shared, dev and prod grant ci-foundation exactly its four folder roles."
  }

  assert {
    condition     = alltrue([for name, policy in data.google_iam_policy.folder : alltrue([for binding in policy.binding : binding.members == toset(["serviceAccount:ci-foundation@gcp-agent-factory-seed-a1b2.iam.gserviceaccount.com"])])])
    error_message = "Only ci-foundation holds folder roles."
  }

  assert {
    condition = alltrue([
      for name, number in { trust-root = "1000", shared = "2000", dev = "3000", prod = "4000" } :
      google_folder_iam_policy.this[name].folder == "folders/${number}" && google_folder_iam_policy.this[name].policy_data == data.google_iam_policy.folder[name].policy_data
    ])
    error_message = "Each folder gets its own policy: the empty one lands on trust-root."
  }

  assert {
    condition     = toset([for role, binding in google_project_iam_binding.seed : role if contains(binding.members, "serviceAccount:ci-plan@gcp-agent-factory-seed-a1b2.iam.gserviceaccount.com")]) == toset(["roles/serviceusage.serviceUsageConsumer", "roles/cloudkms.viewer", "roles/iam.workloadIdentityPoolViewer", "roles/iam.serviceAccountViewer", "roles/serviceusage.serviceUsageViewer"])
    error_message = "On the seed, ci-plan holds only Service Usage Consumer and its viewer roles."
  }

  assert {
    condition = alltrue([
      for name in ["ci-foundation", "ci-apply-dev", "ci-apply-prod"] :
      toset([for role, binding in google_project_iam_binding.seed : role if contains(binding.members, "serviceAccount:${name}@gcp-agent-factory-seed-a1b2.iam.gserviceaccount.com")]) == toset(["roles/serviceusage.serviceUsageConsumer"])
    ])
    error_message = "On the seed, the apply identities hold only Service Usage Consumer."
  }

  assert {
    condition     = toset([for role, binding in google_billing_account_iam_binding.authoritative : role if contains(binding.members, "serviceAccount:ci-foundation@gcp-agent-factory-seed-a1b2.iam.gserviceaccount.com")]) == toset(["roles/billing.user", "roles/billing.costsManager"]) && google_billing_account_iam_binding.authoritative["roles/billing.viewer"].members == toset(["serviceAccount:ci-plan@gcp-agent-factory-seed-a1b2.iam.gserviceaccount.com"])
    error_message = "On the billing account, ci-foundation holds exactly Billing Account User and Costs Manager, and ci-plan only Billing Account Viewer."
  }

  assert {
    condition = alltrue(flatten([
      for bindings in [google_organization_iam_binding.authoritative, google_project_iam_binding.seed, google_billing_account_iam_binding.authoritative] : [
        for role, binding in bindings :
        !(contains(["roles/owner", "roles/editor", "roles/viewer", "roles/resourcemanager.organizationAdmin", "roles/iam.securityAdmin"], role) && strcontains(join(",", binding.members), "serviceAccount:ci-"))
      ]
    ]))
    error_message = "No CI identity holds Organization Administrator, Security Admin or a basic role."
  }

  assert {
    condition     = google_project_iam_binding.seed["roles/editor"].members == toset(["serviceAccount:123456789012@cloudservices.gserviceaccount.com"])
    error_message = "Editor on the seed is held only by Google's APIs service agent."
  }
}

run "org_iam_has_one_owner" {
  command = plan

  assert {
    condition     = google_organization_iam_binding.authoritative["roles/resourcemanager.projectCreator"].members == toset(["group:gcp-org-admins@example.com"])
    error_message = "Project Creator at org level is held only by gcp-org-admins."
  }

  assert {
    condition     = google_organization_iam_binding.authoritative["roles/iam.denyAdmin"].members == toset(["group:gcp-org-admins@example.com"])
    error_message = "Deny Admin is authoritative and held only by gcp-org-admins: deny-policy changes can't be denied, so its holders must show up as drift."
  }

  assert {
    condition     = length(google_organization_iam_binding.authoritative["roles/billing.creator"].members) == 0
    error_message = "Billing Account Creator is held by nobody."
  }

  assert {
    condition = length(setintersection(
      toset([for binding in google_organization_iam_binding.authoritative : binding.role]),
      toset([for member in google_organization_iam_member.additive : member.role]),
      )) == 0 && length(setintersection(
      toset([for binding in google_billing_account_iam_binding.authoritative : binding.role]),
      toset([for member in google_billing_account_iam_member.additive : member.role]),
    )) == 0
    error_message = "No role is managed both authoritatively and additively, so an extra member always shows up as drift."
  }

  assert {
    condition     = toset([for member in google_organization_iam_member.additive : member.role]) == toset(["roles/resourcemanager.organizationAdmin", "roles/resourcemanager.folderCreator"]) && alltrue([for member in google_organization_iam_member.additive : member.member == "group:gcp-org-admins@example.com"])
    error_message = "Only roles no CI identity holds are additive, all for gcp-org-admins."
  }

  assert {
    condition     = google_billing_account_iam_member.additive["roles/billing.admin"].member == "group:gcp-billing-admins@example.com"
    error_message = "Billing Account Administrator stays additive, so the personal owner can't be locked out."
  }

  assert {
    condition = alltrue([
      for role in ["roles/owner", "roles/storage.admin", "roles/cloudkms.admin", "roles/iam.workloadIdentityPoolAdmin", "roles/iam.serviceAccountAdmin"] :
      google_project_iam_binding.seed[role].members == toset(["group:gcp-org-admins@example.com"])
    ])
    error_message = "The seed's Owner and storage, KMS, WIF and service-account admin roles are held only by gcp-org-admins."
  }

  assert {
    condition = alltrue(flatten([
      for bindings in [google_organization_iam_binding.authoritative, google_project_iam_binding.seed] : [
        for role in ["roles/iam.serviceAccountTokenCreator", "roles/iam.serviceAccountOpenIdTokenCreator", "roles/iam.serviceAccountUser", "roles/iam.workloadIdentityUser"] :
        length(bindings[role].members) == 0
      ]
    ])) && length(google_project_iam_binding.seed["roles/iam.serviceAccountKeyAdmin"].members) == 0
    error_message = "Nobody holds Token Creator, OpenID Token Creator, Service Account User or Workload Identity User at org level or on the seed, so no grant reaches a CI identity from above."
  }

  assert {
    condition     = toset(keys(module.wif.principal_sets)) == toset(keys(local.ci)) && module.wif.principal_sets["ci-plan"] == "principalSet://iam.googleapis.com/projects/123456789012/locations/global/workloadIdentityPools/github/attribute.plan/allowed" && module.wif.principal_sets["ci-foundation"] == "principalSet://iam.googleapis.com/projects/123456789012/locations/global/workloadIdentityPools/github/attribute.deploy/foundation"
    error_message = "Each CI identity is reachable only through its own gate."
  }
}

run "deny_policy_keeps_ci_out" {
  command = plan

  assert {
    condition     = google_iam_deny_policy.trust_root.parent == "cloudresourcemanager.googleapis.com%2Ffolders%2F1000" && google_iam_deny_policy.trust_root.deletion_policy == "PREVENT"
    error_message = "The deny policy sits on the trust-root folder and can't be destroyed by accident."
  }

  assert {
    condition = toset(google_iam_deny_policy.trust_root.rules[0].deny_rule[0].denied_principals) == toset([
      for name in keys(local.ci) : "principal://iam.googleapis.com/projects/-/serviceAccounts/${name}@gcp-agent-factory-seed-a1b2.iam.gserviceaccount.com"
    ])
    error_message = "The first rule names every CI service account."
  }

  assert {
    condition = alltrue([
      for permission in [
        "cloudresourcemanager.googleapis.com/folders.setIamPolicy",
        "cloudresourcemanager.googleapis.com/projects.setIamPolicy",
        "cloudresourcemanager.googleapis.com/projects.delete",
        "cloudresourcemanager.googleapis.com/projects.move",
        "cloudresourcemanager.googleapis.com/projects.updateLiens",
        "cloudresourcemanager.googleapis.com/projects.deleteBillingAssignment",
        "iam.googleapis.com/serviceAccounts.setIamPolicy",
        "iam.googleapis.com/serviceAccounts.getAccessToken",
        "iam.googleapis.com/serviceAccountKeys.create",
        "iam.googleapis.com/workloadIdentityPoolProviders.update",
        "iam.googleapis.com/workloadIdentityPoolProviders.create",
        "cloudkms.googleapis.com/cryptoKeys.setIamPolicy",
        "cloudkms.googleapis.com/cryptoKeyVersions.destroy",
        "storage.googleapis.com/buckets.setIamPolicy",
        "storage.googleapis.com/buckets.delete",
        "orgpolicy.googleapis.com/policies.update",
        "storage.googleapis.com/hmacKeys.create",
        "storage.googleapis.com/managedFolders.setIamPolicy",
        "storage.googleapis.com/objects.setIamPolicy",
        "logging.googleapis.com/sinks.create",
        "logging.googleapis.com/exclusions.create",
        "iam.googleapis.com/workloadIdentityPoolNamespaces.create",
      ] : contains(google_iam_deny_policy.trust_root.rules[0].deny_rule[0].denied_permissions, permission)
    ])
    error_message = "CI may not change trust-root IAM, tokens, keys, HMAC keys, the pool, KMS keys, the bucket or its folders, the audit trail, org policies, or the seed's existence, location, liens or billing."
  }

  assert {
    condition = length(setintersection(google_iam_deny_policy.trust_root.rules[0].deny_rule[0].denied_permissions, [
      "storage.googleapis.com/objects.get",
      "storage.googleapis.com/objects.list",
      "storage.googleapis.com/objects.create",
      "storage.googleapis.com/objects.delete",
      "storage.googleapis.com/objects.update",
      "cloudkms.googleapis.com/cryptoKeyVersions.useToEncrypt",
      "cloudkms.googleapis.com/cryptoKeyVersions.useToDecrypt",
      "serviceusage.googleapis.com/services.use",
    ])) == 0
    error_message = "CI can still read and write its state, use its keys and charge quota to the seed."
  }

  assert {
    condition     = google_iam_deny_policy.trust_root.rules[1].deny_rule[0].denied_principals == tolist(["principalSet://iam.googleapis.com/projects/123456789012/locations/global/workloadIdentityPools/github/*"])
    error_message = "The second rule covers every identity of the GitHub pool."
  }

  assert {
    condition = (
      !contains(google_iam_deny_policy.trust_root.rules[1].deny_rule[0].denied_permissions, "iam.googleapis.com/serviceAccounts.getAccessToken")
      && length(google_iam_deny_policy.trust_root.rules[1].deny_rule[0].denied_permissions) == length(google_iam_deny_policy.trust_root.rules[0].deny_rule[0].denied_permissions) - 2
    )
    error_message = "Pool identities keep only token minting, which is how CI signs in."
  }

  assert {
    condition     = google_org_policy_policy.trust_root["iam.workloadIdentityPoolProviders"].spec[0].rules[0].values[0].allowed_values == tolist(["https://token.actions.githubusercontent.com"]) && google_org_policy_policy.trust_root["iam.workloadIdentityPoolAwsAccounts"].spec[0].rules[0].deny_all == "TRUE"
    error_message = "The seed's pool can only ever hold GitHub providers."
  }

  assert {
    condition = (
      google_org_policy_policy.trust_root["iam.disableServiceAccountKeyCreation"].spec[0].rules[0].enforce == "TRUE"
      && google_org_policy_policy.trust_root["iam.disableServiceAccountKeyUpload"].spec[0].rules[0].enforce == "TRUE"
      && google_org_policy_policy.trust_root["iam.allowServiceAccountCredentialLifetimeExtension"].spec[0].rules[0].deny_all == "TRUE"
      && google_org_policy_policy.trust_root["storage.restrictAuthTypes"].spec[0].rules[0].values[0].denied_values == tolist(["in:ALL_HMAC_SIGNED_REQUESTS"])
      && google_org_policy_policy.trust_root["essentialcontacts.allowedContactDomains"].spec[0].rules[0].values[0].allowed_values == tolist(["@example.com"])
    )
    error_message = "trust-root pins its own key, token-lifetime, HMAC and contact policies, so loosening them at org level never reaches the seed."
  }

  assert {
    condition     = alltrue([for name, policy in google_org_policy_policy.trust_root : policy.parent == "folders/1000" && policy.name == "folders/1000/policies/${name}"])
    error_message = "Every one of these policies sits on the trust-root folder."
  }

  assert {
    condition     = toset(keys(google_project_iam_audit_config.seed)) == toset(["sts.googleapis.com", "iamcredentials.googleapis.com", "storage.googleapis.com", "cloudkms.googleapis.com"]) && alltrue([for config in google_project_iam_audit_config.seed : toset([for log in config.audit_log_config : log.log_type]) == toset(["ADMIN_READ", "DATA_READ", "DATA_WRITE"])])
    error_message = "Every token exchange, minted token, state read and key use is logged."
  }
}

run "gross_cost_budget" {
  command = plan

  assert {
    condition     = google_billing_budget.account.billing_account == "012345-6789AB-CDEF01" && google_billing_budget.account.amount[0].specified_amount[0].currency_code == "EUR" && google_billing_budget.account.amount[0].specified_amount[0].units == "85"
    error_message = "The billing-account budget is 85 EUR per month."
  }

  assert {
    condition     = google_billing_budget.account.budget_filter[0].credit_types_treatment == "EXCLUDE_ALL_CREDITS" && google_billing_budget.account.budget_filter[0].calendar_period == "MONTH" && google_billing_budget.account.budget_filter[0].projects == null
    error_message = "It measures gross monthly cost across the whole billing account."
  }

  assert {
    condition     = [for rule in google_billing_budget.account.threshold_rules : rule.threshold_percent] == [0.25, 0.5, 0.75, 0.9, 1.0]
    error_message = "It alerts at 25, 50, 75, 90 and 100%."
  }

  assert {
    condition     = length(google_billing_budget.account.all_updates_rule) == 0 && google_billing_budget.account.deletion_policy == "PREVENT"
    error_message = "Alerts go to the billing account's administrators and users by default, and the budget can't be destroyed by accident."
  }
}

run "state_settings_may_be_unset" {
  command = plan

  variables {
    state_bucket = null
    state_key    = null
  }

  assert {
    condition     = output.seed_project_id == "gcp-agent-factory-seed-a1b2"
    error_message = "An unset state bucket and key pass validation. tofu test never builds the backend or the key provider; the first-run sequence itself is rehearsed in task 9."
  }
}

run "rejects_invalid_org_id" {
  command = plan

  variables {
    org_id = "organizations/123"
  }

  expect_failures = [var.org_id]
}

run "rejects_invalid_customer_id" {
  command = plan

  variables {
    customer_id = "my-company"
  }

  expect_failures = [var.customer_id]
}

run "rejects_invalid_identity_domain" {
  command = plan

  variables {
    identity_domain = "gcp-org-admins@example.com"
  }

  expect_failures = [var.identity_domain]
}

run "rejects_invalid_billing_account" {
  command = plan

  variables {
    billing_account = "billingAccounts/012345-6789AB-CDEF01"
  }

  expect_failures = [var.billing_account]
}

run "rejects_regions_outside_europe" {
  command = plan

  variables {
    region = "us-central1"
  }

  expect_failures = [var.region]
}

run "rejects_invalid_repository" {
  command = plan

  variables {
    repository = "gcp-agent-factory"
  }

  expect_failures = [var.repository]
}

run "rejects_non_numeric_repository_id" {
  command = plan

  variables {
    repository_id = "liljestk/gcp-agent-factory"
  }

  expect_failures = [var.repository_id]
}

run "rejects_non_numeric_owner_id" {
  command = plan

  variables {
    repository_owner_id = "liljestk"
  }

  expect_failures = [var.repository_owner_id]
}

run "rejects_invalid_state_bucket" {
  command = plan

  variables {
    state_bucket = "gs://gcp-agent-factory-tfstate-a1b2"
  }

  expect_failures = [var.state_bucket]
}

run "rejects_invalid_state_key" {
  command = plan

  variables {
    state_key = "tfstate/state-trust-root"
  }

  expect_failures = [var.state_key]
}

run "rejects_invalid_quota_project" {
  command = plan

  variables {
    quota_project = "Seed Project"
  }

  expect_failures = [var.quota_project]
}
