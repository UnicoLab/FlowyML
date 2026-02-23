# FlowyML GCP — Alerting
# Scale-to-zero–aware alert policies using passive Cloud Run metrics.
#
# DESIGN DECISION (Feb 2026):
# We do NOT use GCP Uptime Checks by default because they wake
# Cloud Run services, preventing scale-to-zero and generating
# false-positive latency alerts from cold starts. Instead we use Cloud Run's
# native metrics (request_count, request_latencies) which are reported
# passively without generating traffic.

# ============================================================================
# Notification Channel (Email)
# ============================================================================

resource "google_monitoring_notification_channel" "alert_email" {
  count        = var.alert_email != "" ? 1 : 0
  display_name = "FlowyML Alerts"
  type         = "email"
  project      = var.project_id

  labels = {
    email_address = var.alert_email
  }

  depends_on = [google_project_service.apis]
}

locals {
  notification_channels = var.alert_email != "" ? [google_monitoring_notification_channel.alert_email[0].name] : []
}

# ============================================================================
# Alert: Sustained Error Rate (5xx) — passive, scale-to-zero safe
# ============================================================================

resource "google_monitoring_alert_policy" "high_error_rate" {
  count        = var.alert_email != "" ? 1 : 0
  display_name = "🟡 FlowyML High Error Rate (5xx)"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Cloud Run 5xx error rate elevated for 10 min"
    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_count\" AND metric.labels.response_code_class = \"5xx\""
      comparison      = "COMPARISON_GT"
      threshold_value = 5
      duration        = "600s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }

      trigger {
        count = 1
      }
    }
  }

  notification_channels = local.notification_channels

  alert_strategy {
    auto_close = "3600s"
  }

  documentation {
    content   = "Sustained 5xx error rate on FlowyML (10+ min).\n\n**Check logs:**\n```bash\nmake gcp-logs\n```\n\n**Note:** Single cold-start errors are filtered by the 10-min duration window."
    mime_type = "text/markdown"
  }
}

# ============================================================================
# Alert: High Latency (p99 > 10s for 15 min) — cold-start tolerant
# ============================================================================

resource "google_monitoring_alert_policy" "high_latency" {
  count        = var.alert_email != "" ? 1 : 0
  display_name = "🟡 FlowyML High Latency (p99 > 10s)"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Cloud Run p99 latency > 10 seconds for 15 min"
    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_latencies\""
      comparison      = "COMPARISON_GT"
      threshold_value = 10000
      duration        = "900s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_PERCENTILE_99"
      }

      trigger {
        count = 1
      }
    }
  }

  notification_channels = local.notification_channels

  alert_strategy {
    auto_close = "3600s"
  }

  documentation {
    content   = "Sustained latency above 10s (p99) for 15+ min on FlowyML.\n\nPossible causes: database bottleneck, resource limits, heavy ML pipeline.\n\n**Note:** Single cold-start requests (2-8s) do NOT trigger this alert."
    mime_type = "text/markdown"
  }
}

# ============================================================================
# Alert: Cloud SQL High CPU
# ============================================================================

resource "google_monitoring_alert_policy" "cloudsql_cpu" {
  count        = var.alert_email != "" ? 1 : 0
  display_name = "🟡 FlowyML Cloud SQL High CPU"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Cloud SQL CPU > 80% for 10 min"
    condition_threshold {
      filter          = "resource.type = \"cloudsql_database\" AND metric.type = \"cloudsql.googleapis.com/database/cpu/utilization\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0.8
      duration        = "600s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_MEAN"
      }

      trigger {
        count = 1
      }
    }
  }

  notification_channels = local.notification_channels

  alert_strategy {
    auto_close = "3600s"
  }

  documentation {
    content   = "Cloud SQL CPU > 80% for FlowyML.\n\nUpgrade `tier` from `db-f1-micro` to `db-custom-1-3840` in main.tf."
    mime_type = "text/markdown"
  }
}

# ============================================================================
# Alert: Unexpected Traffic Spike (cost guard)
# ============================================================================

resource "google_monitoring_alert_policy" "traffic_spike" {
  count        = var.alert_email != "" ? 1 : 0
  display_name = "🟠 FlowyML Unexpected Traffic"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Cloud Run request count > 100/5min for 10 min"
    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_count\""
      comparison      = "COMPARISON_GT"
      threshold_value = 100
      duration        = "600s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }

      trigger {
        count = 1
      }
    }
  }

  notification_channels = local.notification_channels

  alert_strategy {
    auto_close = "3600s"
  }

  documentation {
    content   = "Unexpected traffic spike on FlowyML (>100 req/5min sustained).\n\n**Investigate:**\n```bash\nmake flowyml-traffic-audit\n```"
    mime_type = "text/markdown"
  }
}

# ============================================================================
# Alerting Variables
# ============================================================================

variable "alert_email" {
  description = "Email for monitoring alerts. Leave empty to disable alerting."
  type        = string
  default     = ""
}
