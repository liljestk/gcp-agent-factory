# covers: REQ-LZ-003, REQ-LZ-009

mock_provider "google" {}

override_resource {
  target = google_project.this
  values = {
    number = "123456789012"
  }
}

variables {
  project_id      = "gcp-agent-factory-seed-k3x9"
  name            = "gcp-agent-factory seed"
  folder_id       = "folders/111"
  billing_account = "012345-6789AB-CDEF01"
  services        = ["cloudkms.googleapis.com", "storage.googleapis.com"]
  labels = {
    env          = "shared"
    platform     = "landing-zone"
    component    = "seed"
    owner        = "platform-team"
    "managed-by" = "opentofu"
    repo         = "gcp-agent-factory"
  }
  lien_reason = "Holds the OpenTofu state for every stack."
}

run "seed_project" {
  command = plan

  assert {
    condition     = google_project.this.auto_create_network == true
    error_message = "By default the provider must not turn compute on just to delete a default network that only compute creates."
  }

  assert {
    condition     = google_project.this.deletion_policy == "PREVENT" && google_project.this.labels == tomap(var.labels)
    error_message = "The project must refuse deletion by default and carry the given labels."
  }

  assert {
    condition     = output.services == tolist(["cloudkms.googleapis.com", "storage.googleapis.com"])
    error_message = "The listed APIs must be enabled and managed."
  }

  assert {
    condition     = alltrue([for service in google_project_service.this : service.disable_on_destroy == false])
    error_message = "Removing an API from the list must not disable it."
  }

  assert {
    condition     = google_resource_manager_lien.this[0].parent == "projects/123456789012" && google_resource_manager_lien.this[0].restrictions == tolist(["resourcemanager.projects.delete"])
    error_message = "The lien must block deleting the project."
  }
}

run "no_lien" {
  command = plan

  variables {
    lien_reason            = null
    services               = []
    delete_default_network = true
  }

  assert {
    condition     = google_project.this.auto_create_network == false
    error_message = "delete_default_network asks the provider to delete the default network."
  }

  assert {
    condition     = length(google_resource_manager_lien.this) == 0 && length(output.services) == 0
    error_message = "Without a reason there is no lien, and an empty list enables no API."
  }
}

run "rejects_invalid_project_id" {
  command = plan

  variables {
    project_id = "Gcp-agent-factory-"
  }

  expect_failures = [var.project_id]
}

run "rejects_invalid_name" {
  command = plan

  variables {
    name = "gcp/agent"
  }

  expect_failures = [var.name]
}

run "rejects_invalid_folder" {
  command = plan

  variables {
    folder_id = "organizations/1"
  }

  expect_failures = [var.folder_id]
}

run "rejects_invalid_billing_account" {
  command = plan

  variables {
    billing_account = "billingAccounts/012345-6789AB-CDEF01"
  }

  expect_failures = [var.billing_account]
}

run "rejects_invalid_service" {
  command = plan

  variables {
    services = ["kms"]
  }

  expect_failures = [var.services]
}

run "rejects_hand_written_labels" {
  command = plan

  variables {
    labels = { env = "dev" }
  }

  expect_failures = [var.labels]
}

run "rejects_unknown_deletion_policy" {
  command = plan

  variables {
    deletion_policy = "KEEP"
  }

  expect_failures = [var.deletion_policy]
}

run "rejects_empty_lien_reason" {
  command = plan

  variables {
    lien_reason = ""
  }

  expect_failures = [var.lien_reason]
}
