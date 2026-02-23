# FlowyML GCP — Budget Alerts
# Automatic cost monitoring with email notifications

# ============================================================================
# Budget with Email Alerts
# ============================================================================

data "google_billing_account" "account" {
  count           = var.billing_account_id != "" ? 1 : 0
  billing_account = var.billing_account_id
}

data "google_project" "project" {
  project_id = var.project_id
}

resource "google_billing_budget" "flowyml_budget" {
  count           = var.billing_account_id != "" ? 1 : 0
  billing_account = data.google_billing_account.account[0].id
  display_name    = "FlowyML (€${var.budget_amount}/mo)"

  budget_filter {
    projects = ["projects/${data.google_project.project.number}"]
  }

  amount {
    specified_amount {
      currency_code = var.budget_currency
      units         = var.budget_amount
    }
  }

  # Alert at 25%, 50%, 75%, 90%, 100%, and 120% of budget
  dynamic "threshold_rules" {
    for_each = [0.25, 0.5, 0.75, 0.9, 1.0, 1.2]
    content {
      threshold_percent = threshold_rules.value
      spend_basis       = "CURRENT_SPEND"
    }
  }

  # Also alert on forecasted overspend
  dynamic "threshold_rules" {
    for_each = [0.9, 1.0]
    content {
      threshold_percent = threshold_rules.value
      spend_basis       = "FORECASTED_SPEND"
    }
  }

  all_updates_rule {
    monitoring_notification_channels = []
    schema_version                   = 1
    enable_project_level_recipients  = true
    disable_default_iam_recipients   = false
  }

  depends_on = [google_project_service.apis]
}

# ============================================================================
# Budget Variables
# ============================================================================

variable "billing_account_id" {
  description = "GCP Billing Account ID (format: XXXXXX-XXXXXX-XXXXXX). Leave empty to skip budget alerts."
  type        = string
  default     = ""
}

variable "budget_amount" {
  description = "Monthly budget amount in whole units (e.g., 10 = €10/month)"
  type        = number
  default     = 10
}

variable "budget_currency" {
  description = "Budget currency code"
  type        = string
  default     = "EUR"
}
