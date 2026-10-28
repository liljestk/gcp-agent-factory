# A billing-account budget from the first apply (REQ-LZ-011, PLAN §9.2). It measures gross cost:
# with credits subtracted, spend would read €0 for the whole trial.

locals {
  budget_eur        = 85
  budget_thresholds = [0.25, 0.5, 0.75, 0.9, 1.0]
}

resource "google_billing_budget" "account" {
  billing_account = var.billing_account
  display_name    = "gcp-agent-factory billing account (gross)"
  deletion_policy = "PREVENT"

  amount {
    specified_amount {
      currency_code = "EUR"
      units         = tostring(local.budget_eur)
    }
  }

  budget_filter {
    calendar_period        = "MONTH"
    credit_types_treatment = "EXCLUDE_ALL_CREDITS"
  }

  dynamic "threshold_rules" {
    for_each = local.budget_thresholds
    content {
      threshold_percent = threshold_rules.value
      spend_basis       = "CURRENT_SPEND"
    }
  }

  # No all_updates_rule: alerts go by email to the billing account's administrators and users,
  # which is the default. Notification channels arrive with the ops platform (Phase 2).
}
