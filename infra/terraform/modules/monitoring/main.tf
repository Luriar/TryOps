/**
 * Monitoring Module
 * 
 * Cloud Monitoring 대시보드 + Billing 알람 + 알람 채널
 * 사용자 요구사항: 실시간 비용 추적
 */

locals {
  module_labels = merge(var.common_labels, {
    module      = "monitoring"
    cost_center = "core"
  })
}

# ===================================================================
# 알람 채널 (이메일)
# ===================================================================

resource "google_monitoring_notification_channel" "email" {
  project      = var.project_id
  display_name = "TryOps ${var.environment} Email Alerts"
  type         = "email"
  
  labels = {
    email_address = var.alert_email
  }
  
  user_labels = local.module_labels
}

# Slack 알람 채널 (선택, 환경변수 통해 webhook 주입)
# resource "google_monitoring_notification_channel" "slack" {
#   ...
# }

# ===================================================================
# 비용 알람 (Billing Budget)
# ===================================================================

resource "google_billing_budget" "monthly_budget" {
  billing_account = var.billing_account_id
  display_name    = "TryOps ${var.environment} Monthly Budget"
  
  budget_filter {
    projects = ["projects/${var.project_id}"]
    
    labels = {
      project = "tryops"
    }
  }
  
  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.monthly_budget_usd)
    }
  }
  
  # 50% 도달 알람
  threshold_rules {
    threshold_percent = 0.5
    spend_basis       = "CURRENT_SPEND"
  }
  
  # 80% 도달 알람
  threshold_rules {
    threshold_percent = 0.8
    spend_basis       = "CURRENT_SPEND"
  }
  
  # 100% 도달 긴급 알람
  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "CURRENT_SPEND"
  }
  
  # 예측치 100% 도달 시 알람 (월 중간이라도 트렌드로 초과 예측)
  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "FORECASTED_SPEND"
  }
  
  all_updates_rule {
    monitoring_notification_channels = [
      google_monitoring_notification_channel.email.id
    ]
    
    disable_default_iam_recipients = true
  }
}

# ===================================================================
# 알람 정책 — 핵심 메트릭 모니터링
# ===================================================================

# 매장 게이트웨이 → Ingest 실패율 알람
resource "google_monitoring_alert_policy" "ingest_error_rate" {
  project      = var.project_id
  display_name = "Ingest Error Rate > 5%"
  combiner     = "OR"
  
  conditions {
    display_name = "Cloud Run Ingest 5xx errors"
    
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"tryops-${var.environment}-ingest\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.labels.response_code_class=\"5xx\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
  
  notification_channels = [google_monitoring_notification_channel.email.id]
  
  user_labels = local.module_labels
}

# BigQuery 일 비용 알람
resource "google_monitoring_alert_policy" "bigquery_daily_cost" {
  project      = var.project_id
  display_name = "BigQuery Daily Cost > $20"
  combiner     = "OR"
  
  conditions {
    display_name = "BigQuery slot ms exceed budget"
    
    condition_threshold {
      filter          = "resource.type=\"bigquery_project\" AND metric.type=\"bigquery.googleapis.com/query/scanned_bytes\""
      duration        = "3600s"  # 1시간
      comparison      = "COMPARISON_GT"
      threshold_value = 4000000000000  # 4TB scanned in 1시간 = 약 $20
      
      aggregations {
        alignment_period   = "3600s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }
  
  notification_channels = [google_monitoring_notification_channel.email.id]
  
  user_labels = local.module_labels
}

# ===================================================================
# 비용 대시보드
# ===================================================================

resource "google_monitoring_dashboard" "cost" {
  project = var.project_id
  
  dashboard_json = jsonencode({
    displayName = "TryOps ${var.environment} Cost Dashboard"
    
    mosaicLayout = {
      columns = 12
      tiles = [
        {
          width  = 6
          height = 4
          xPos   = 0
          yPos   = 0
          widget = {
            title = "Daily Cost (Last 30 Days)"
            
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesQueryLanguage = "fetch consumer_quota | metric 'billing.googleapis.com/cost/total' | every 1d"
                }
                plotType = "STACKED_BAR"
              }]
            }
          }
        },
        {
          width  = 6
          height = 4
          xPos   = 6
          yPos   = 0
          widget = {
            title = "Cost by Service"
            
            pieChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesQueryLanguage = "fetch consumer_quota | metric 'billing.googleapis.com/cost/total' | group_by [service.description], sum(value.cost)"
                }
              }]
            }
          }
        },
        {
          width  = 12
          height = 4
          xPos   = 0
          yPos   = 4
          widget = {
            title = "Pub/Sub Throughput"
            
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"pubsub_topic\" AND resource.labels.topic_id=\"tryops-${var.environment}-store-events\" AND metric.type=\"pubsub.googleapis.com/topic/byte_cost\""
                  }
                }
              }]
            }
          }
        }
      ]
    }
  })
}

# ===================================================================
# Billing Export 안내 (Terraform으로 직접 활성화 불가)
# ===================================================================

# Outputs
