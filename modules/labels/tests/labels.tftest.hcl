# covers: REQ-REPO-006

variables {
  env       = "dev"
  platform  = "agents"
  component = "orchestrator"
  owner     = "platform-team"
}

run "standard_labels" {
  command = plan

  assert {
    condition = output.labels == tomap({
      env           = "dev"
      platform      = "agents"
      component     = "orchestrator"
      owner         = "platform-team"
      "cost-center" = "demo"
      "managed-by"  = "opentofu"
      repo          = "gcp-agent-factory"
    })
    error_message = "Standard labels did not match the expected set."
  }
}

run "optional_and_extra_labels" {
  command = plan

  variables {
    agent        = "finops-analyst"
    app          = "todo"
    data_product = "dp_finops"
    extra        = { tier = "gold" }
  }

  assert {
    condition     = output.labels["agent"] == "finops-analyst" && output.labels["app"] == "todo" && output.labels["data-product"] == "dp_finops"
    error_message = "Optional labels were not added."
  }

  assert {
    condition     = output.labels["tier"] == "gold" && length(output.labels) == 11
    error_message = "Extra labels were not merged."
  }
}

run "rejects_unknown_env" {
  command = plan

  variables {
    env = "staging"
  }

  expect_failures = [var.env]
}

run "rejects_unknown_platform" {
  command = plan

  variables {
    platform = "mainframe"
  }

  expect_failures = [var.platform]
}

run "rejects_invalid_component" {
  command = plan

  variables {
    component = "Orchestrator"
  }

  expect_failures = [var.component]
}

run "rejects_invalid_owner" {
  command = plan

  variables {
    owner = "Platform Team"
  }

  expect_failures = [var.owner]
}

run "rejects_invalid_cost_center" {
  command = plan

  variables {
    cost_center = "1demo"
  }

  expect_failures = [var.cost_center]
}

run "rejects_invalid_repo" {
  command = plan

  variables {
    repo = "liljestk/gcp-agent-factory"
  }

  expect_failures = [var.repo]
}

run "rejects_invalid_agent" {
  command = plan

  variables {
    agent = "FinOps_Analyst"
  }

  expect_failures = [var.agent]
}

run "rejects_invalid_app" {
  command = plan

  variables {
    app = "my app"
  }

  expect_failures = [var.app]
}

run "rejects_invalid_data_product" {
  command = plan

  variables {
    data_product = "dp.finops"
  }

  expect_failures = [var.data_product]
}

run "rejects_invalid_extra_label" {
  command = plan

  variables {
    extra = { Tier = "gold" }
  }

  expect_failures = [var.extra]
}

run "rejects_overriding_standard_labels" {
  command = plan

  variables {
    extra = { env = "prod" }
  }

  expect_failures = [var.extra]
}
