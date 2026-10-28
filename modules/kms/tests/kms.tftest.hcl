# covers: REQ-LZ-003, REQ-LZ-004

mock_provider "google" {
  # The real data source renders JSON; the policy resources reject anything else at plan.
  mock_data "google_iam_policy" {
    defaults = {
      policy_data = "{\"bindings\":[]}"
    }
  }
}

override_resource {
  target = google_kms_key_ring.this
  values = {
    id = "projects/seed/locations/europe-north1/keyRings/tfstate"
  }
}

override_resource {
  target = google_kms_crypto_key.this["state-dev"]
  values = {
    id = "projects/seed/locations/europe-north1/keyRings/tfstate/cryptoKeys/state-dev"
  }
}

variables {
  project_id = "gcp-agent-factory-seed-k3x9"
  location   = "europe-north1"
  key_ring   = "tfstate"
  keys = {
    state-dev = {
      encrypters_decrypters = ["serviceAccount:ci-apply-dev@gcp-agent-factory-seed-k3x9.iam.gserviceaccount.com"]
      decrypters            = ["serviceAccount:ci-plan@gcp-agent-factory-seed-k3x9.iam.gserviceaccount.com"]
    }
    bucket = {
      encrypters_decrypters = ["serviceAccount:service-123456789012@gs-project-accounts.iam.gserviceaccount.com"]
    }
    spare = {}
  }
  labels = {
    env          = "shared"
    platform     = "landing-zone"
    component    = "tfstate"
    owner        = "platform-team"
    "managed-by" = "opentofu"
    repo         = "gcp-agent-factory"
  }
}

run "state_keys" {
  command = plan

  assert {
    condition     = google_kms_crypto_key.this["state-dev"].rotation_period == "7776000s" && google_kms_crypto_key.this["state-dev"].purpose == "ENCRYPT_DECRYPT"
    error_message = "Keys must rotate every 90 days by default and encrypt and decrypt."
  }

  assert {
    condition     = google_kms_crypto_key.this["bucket"].version_template[0].protection_level == "SOFTWARE"
    error_message = "Keys must be software keys; HSM keys cost more and aren't needed here."
  }

  assert {
    condition     = google_kms_crypto_key.this["bucket"].labels == tomap(var.labels)
    error_message = "Keys must carry the standard labels."
  }

  assert {
    condition = toset([for binding in data.google_iam_policy.key["state-dev"].binding : binding.role]) == toset([
      "roles/cloudkms.cryptoKeyEncrypterDecrypter",
      "roles/cloudkms.cryptoKeyDecrypter",
    ])
    error_message = "Each listed role becomes one binding in the key's policy."
  }

  assert {
    condition     = one([for binding in data.google_iam_policy.key["state-dev"].binding : binding.members if binding.role == "roles/cloudkms.cryptoKeyEncrypterDecrypter"]) == toset(["serviceAccount:ci-apply-dev@gcp-agent-factory-seed-k3x9.iam.gserviceaccount.com"])
    error_message = "Only the listed identities may encrypt and decrypt."
  }

  assert {
    condition     = length(data.google_iam_policy.key["spare"].binding) == 0 && length(google_kms_crypto_key_iam_policy.this) == 3
    error_message = "A key without members still gets a managed, empty policy."
  }

  assert {
    condition     = length(data.google_iam_policy.key_ring.binding) == 0
    error_message = "The key ring's policy stays empty."
  }

  assert {
    condition     = output.key_ring_id == "projects/seed/locations/europe-north1/keyRings/tfstate" && output.key_ids["state-dev"] == "projects/seed/locations/europe-north1/keyRings/tfstate/cryptoKeys/state-dev"
    error_message = "The outputs expose the key ring and key IDs."
  }
}

run "rejects_invalid_project" {
  command = plan

  variables {
    project_id = "Seed"
  }

  expect_failures = [var.project_id]
}

run "rejects_invalid_location" {
  command = plan

  variables {
    location = "Europe North"
  }

  expect_failures = [var.location]
}

run "rejects_invalid_key_ring" {
  command = plan

  variables {
    key_ring = "tf state"
  }

  expect_failures = [var.key_ring]
}

run "rejects_invalid_key_name" {
  command = plan

  variables {
    keys = { "bad key" = {} }
  }

  expect_failures = [var.keys]
}

run "rejects_no_keys" {
  command = plan

  variables {
    keys = {}
  }

  expect_failures = [var.keys]
}

run "rejects_short_rotation" {
  command = plan

  variables {
    keys = { state = { rotation_period = "3600s" } }
  }

  expect_failures = [var.keys]
}

run "rejects_public_members" {
  command = plan

  variables {
    keys = { state = { decrypters = ["allUsers"] } }
  }

  expect_failures = [var.keys]
}

run "rejects_principal_sets" {
  command = plan

  variables {
    keys = { state = { decrypters = ["principalSet://iam.googleapis.com/projects/1/locations/global/workloadIdentityPools/github/*"] } }
  }

  expect_failures = [var.keys]
}

run "rejects_users" {
  command = plan

  variables {
    keys = { state = { encrypters_decrypters = ["user:someone@gmail.com"] } }
  }

  expect_failures = [var.keys]
}

run "rejects_hand_written_labels" {
  command = plan

  variables {
    labels = { env = "shared" }
  }

  expect_failures = [var.labels]
}
