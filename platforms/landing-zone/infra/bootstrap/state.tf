# Encrypted, partitioned remote state (REQ-LZ-003, REQ-LZ-004, ADR-0011).

locals {
  # Prefixes each identity may read, and write (writing includes reading and deleting, which
  # locks need). Allow-lists: anything not listed, trust-root/github/ included, is out of reach.
  state_reads = {
    ci-plan       = ["trust-root/bootstrap/", "shared/", "dev/", "prod/"]
    ci-foundation = ["trust-root/bootstrap/"]
    ci-apply-dev  = ["trust-root/bootstrap/", "shared/"]
    ci-apply-prod = ["trust-root/bootstrap/", "shared/"]
  }
  state_writes = {
    ci-foundation = ["shared/"]
    ci-apply-dev  = ["dev/"]
    ci-apply-prod = ["prod/"]
  }
  state_objects = "projects/_/buckets/${google_storage_bucket.state.name}/objects/"

  # One state key per scope, plus the bucket's default key. ci-plan encrypts too, because plans
  # are encrypted. The github stack's state has its own owner-only key, so it takes both a bucket
  # grant and a key grant to read it, as for every other scope.
  state_keys = {
    state-github = {
      encrypters_decrypters = [local.org_admins]
    }
    state-trust-root = {
      encrypters_decrypters = [local.org_admins, local.ci_member["ci-plan"]]
      decrypters            = [local.ci_member["ci-foundation"], local.ci_member["ci-apply-dev"], local.ci_member["ci-apply-prod"]]
    }
    state-shared = {
      encrypters_decrypters = [local.ci_member["ci-foundation"], local.ci_member["ci-plan"]]
      decrypters            = [local.ci_member["ci-apply-dev"], local.ci_member["ci-apply-prod"]]
    }
    state-dev = {
      encrypters_decrypters = [local.ci_member["ci-apply-dev"], local.ci_member["ci-plan"]]
    }
    state-prod = {
      encrypters_decrypters = [local.ci_member["ci-apply-prod"], local.ci_member["ci-plan"]]
    }
    bucket = {
      encrypters_decrypters = ["serviceAccount:${data.google_storage_project_service_account.seed.email_address}"]
    }
  }
}

# The Cloud Storage service agent, which encrypts objects with the bucket's default key. Reading
# it also creates it.
data "google_storage_project_service_account" "seed" {
  project = module.seed.project_id
}

module "kms" {
  source = "../../../../modules/kms"

  project_id = module.seed.project_id
  location   = var.region
  key_ring   = "tfstate"
  labels     = module.labels.labels

  keys = local.state_keys
}

resource "google_storage_bucket" "state" {
  project                     = module.seed.project_id
  name                        = "gcp-agent-factory-tfstate-${random_id.suffix.hex}"
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  labels                      = module.labels.labels

  versioning {
    enabled = true
  }

  soft_delete_policy {
    retention_duration_seconds = 604800 # 7 days
  }

  encryption {
    default_kms_key_name = module.kms.key_ids["bucket"]
  }

  # Keep at most 10 noncurrent versions of each state file, for at most 30 days.
  lifecycle_rule {
    condition {
      num_newer_versions = 10
      with_state         = "ARCHIVED"
    }
    action {
      type = "Delete"
    }
  }

  lifecycle_rule {
    condition {
      days_since_noncurrent_time = 30
      with_state                 = "ARCHIVED"
    }
    action {
      type = "Delete"
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

# The bucket's whole policy is managed, so any other grant shows up as drift. The owner reaches it
# through the seed's Storage Admin. Listing names can't be limited to a prefix, so it's
# bucket-wide; names hold nothing secret.
data "google_iam_policy" "state" {
  binding {
    role    = "roles/storage.legacyBucketReader"
    members = sort(values(local.ci_member))
  }

  dynamic "binding" {
    for_each = local.state_reads
    content {
      role    = "roles/storage.objectViewer"
      members = [local.ci_member[binding.key]]
      condition {
        title       = "${binding.key}-reads"
        description = "State ${binding.key} may read."
        expression  = join(" || ", [for prefix in binding.value : "resource.name.startsWith(\"${local.state_objects}${prefix}\")"])
      }
    }
  }

  dynamic "binding" {
    for_each = local.state_writes
    content {
      role    = "roles/storage.objectUser"
      members = [local.ci_member[binding.key]]
      condition {
        title       = "${binding.key}-writes"
        description = "State ${binding.key} may write, lock and delete."
        expression  = join(" || ", [for prefix in binding.value : "resource.name.startsWith(\"${local.state_objects}${prefix}\")"])
      }
    }
  }
}

resource "google_storage_bucket_iam_policy" "state" {
  bucket      = google_storage_bucket.state.name
  policy_data = data.google_iam_policy.state.policy_data
}
