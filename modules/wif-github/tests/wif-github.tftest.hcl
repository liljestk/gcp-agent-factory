# covers: REQ-LZ-001, REQ-LZ-002

mock_provider "google" {
  mock_data "google_iam_policy" {
    defaults = {
      policy_data = "{\"bindings\":[]}"
    }
  }
}

override_resource {
  target = google_iam_workload_identity_pool.github
  values = {
    name = "projects/123456789012/locations/global/workloadIdentityPools/github"
  }
}

variables {
  project_id          = "gcp-agent-factory-seed-k3x9"
  repository          = "liljestk/gcp-agent-factory"
  repository_id       = "1431415117"
  repository_owner_id = "4373495"
  service_accounts = {
    ci-plan = {
      email = "ci-plan@gcp-agent-factory-seed-k3x9.iam.gserviceaccount.com"
      gate  = "plan"
    }
    ci-apply-prod = {
      email       = "ci-apply-prod@gcp-agent-factory-seed-k3x9.iam.gserviceaccount.com"
      gate        = "deploy"
      environment = "prod"
    }
  }
}

run "pinned_trust_and_gates" {
  command = plan

  assert {
    condition     = startswith(google_iam_workload_identity_pool_provider.github.attribute_condition, "assertion.repository_id == '1431415117' && assertion.repository_owner_id == '4373495' && ")
    error_message = "Trust must be pinned to the immutable repository and owner IDs."
  }

  assert {
    condition     = endswith(google_iam_workload_identity_pool_provider.github.attribute_condition, "(attribute.plan == 'allowed' || attribute.deploy != 'none')")
    error_message = "Tokens that pass neither gate must be refused at the token exchange."
  }

  assert {
    condition     = !strcontains(google_iam_workload_identity_pool_provider.github.attribute_condition, "gcp-agent-factory")
    error_message = "The trust condition must not use the repository name."
  }

  assert {
    condition     = google_iam_workload_identity_pool_provider.github.oidc[0].issuer_uri == "https://token.actions.githubusercontent.com"
    error_message = "Only GitHub Actions tokens are accepted."
  }

  assert {
    condition     = strcontains(google_iam_workload_identity_pool_provider.github.attribute_mapping["attribute.deploy"], "'liljestk/gcp-agent-factory/.github/workflows/tofu.yml@refs/heads/main'")
    error_message = "The deploy gate must pin the apply workflow on main."
  }

  assert {
    condition     = strcontains(google_iam_workload_identity_pool_provider.github.attribute_mapping["attribute.deploy"], "assertion.event_name == 'push'") && strcontains(google_iam_workload_identity_pool_provider.github.attribute_mapping["attribute.deploy"], "assertion.workflow_ref == assertion.job_workflow_ref")
    error_message = "The deploy gate must only accept push runs of the apply workflow itself, not other events or callers."
  }

  assert {
    condition     = strcontains(google_iam_workload_identity_pool_provider.github.attribute_mapping["attribute.plan"], "assertion.actor_id == '4373495'")
    error_message = "The plan gate must default to the repository owner."
  }

  assert {
    condition     = output.principal_sets["ci-plan"] == "principalSet://iam.googleapis.com/projects/123456789012/locations/global/workloadIdentityPools/github/attribute.plan/allowed"
    error_message = "ci-plan must trust only the plan gate's allowed runs."
  }

  assert {
    condition     = output.principal_sets["ci-apply-prod"] == "principalSet://iam.googleapis.com/projects/123456789012/locations/global/workloadIdentityPools/github/attribute.deploy/prod"
    error_message = "An apply identity must trust only its own environment's deploy gate."
  }

  assert {
    condition = alltrue([
      for name, policy in data.google_iam_policy.service_account :
      length(policy.binding) == 1 && one(policy.binding).role == "roles/iam.workloadIdentityUser" && one(policy.binding).members == toset([output.principal_sets[name]])
    ])
    error_message = "Each account's whole policy grants only Workload Identity User, to its own gate: no Token Creator or Service Account User for anyone."
  }

  assert {
    condition     = google_service_account_iam_policy.this["ci-apply-prod"].service_account_id == "projects/gcp-agent-factory-seed-k3x9/serviceAccounts/ci-apply-prod@gcp-agent-factory-seed-k3x9.iam.gserviceaccount.com"
    error_message = "The policy is set on the account itself."
  }
}

run "separate_plan_actor" {
  command = plan

  variables {
    owner_actor_id = "42"
  }

  assert {
    condition     = strcontains(output.gates.plan, "assertion.actor_id == '42'")
    error_message = "owner_actor_id overrides the plan gate's actor."
  }
}

run "rejects_invalid_project" {
  command = plan

  variables {
    project_id = "Seed"
  }

  expect_failures = [var.project_id]
}

run "rejects_invalid_pool" {
  command = plan

  variables {
    pool_id = "gh"
  }

  expect_failures = [var.pool_id]
}

run "rejects_reserved_pool_prefix" {
  command = plan

  variables {
    pool_id = "gcp-github"
  }

  expect_failures = [var.pool_id]
}

run "rejects_reserved_provider_prefix" {
  command = plan

  variables {
    provider_id = "gcp-actions"
  }

  expect_failures = [var.provider_id]
}

run "rejects_the_refusal_value_as_environment" {
  command = plan

  variables {
    service_accounts = {
      ci-apply-dev = { email = "ci-apply-dev@gcp-agent-factory-seed-k3x9.iam.gserviceaccount.com", gate = "deploy", environment = "none" }
    }
  }

  expect_failures = [var.service_accounts]
}

run "rejects_invalid_provider" {
  command = plan

  variables {
    provider_id = "GitHub"
  }

  expect_failures = [var.provider_id]
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

run "rejects_non_numeric_actor" {
  command = plan

  variables {
    owner_actor_id = "liljestk"
  }

  expect_failures = [var.owner_actor_id]
}

run "rejects_workflow_outside_workflows" {
  command = plan

  variables {
    apply_workflow = "scripts/apply.yml"
  }

  expect_failures = [var.apply_workflow]
}

run "rejects_invalid_email" {
  command = plan

  variables {
    service_accounts = {
      ci-plan = { email = "someone@example.com", gate = "plan" }
    }
  }

  expect_failures = [var.service_accounts]
}

run "rejects_deploy_without_environment" {
  command = plan

  variables {
    service_accounts = {
      ci-apply-dev = { email = "ci-apply-dev@gcp-agent-factory-seed-k3x9.iam.gserviceaccount.com", gate = "deploy" }
    }
  }

  expect_failures = [var.service_accounts]
}

run "rejects_unknown_gate" {
  command = plan

  variables {
    service_accounts = {
      ci-plan = { email = "ci-plan@gcp-agent-factory-seed-k3x9.iam.gserviceaccount.com", gate = "any" }
    }
  }

  expect_failures = [var.service_accounts]
}
