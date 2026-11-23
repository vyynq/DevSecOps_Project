# ---------------------------------------------------------------------------
# Détection et alerting : GuardDuty -> EventBridge -> SNS (chiffré) -> email.
# Plus une alerte de budget.
# ---------------------------------------------------------------------------

resource "aws_guardduty_detector" "main" {
  count                        = var.enable_guardduty ? 1 : 0
  enable                       = true
  finding_publishing_frequency = "FIFTEEN_MINUTES"
}

resource "aws_sns_topic" "security_alerts" {
  name              = "${local.name}-security-alerts"
  kms_master_key_id = aws_kms_key.logs.arn
}

# Tu recevras un email "AWS Notification - Subscription Confirmation" : clique pour confirmer.
resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.security_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

data "aws_iam_policy_document" "sns_events" {
  statement {
    sid       = "AllowEventBridgePublish"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.security_alerts.arn]
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
  }
}

resource "aws_sns_topic_policy" "security_alerts" {
  arn    = aws_sns_topic.security_alerts.arn
  policy = data.aws_iam_policy_document.sns_events.json
}

# Sévérité GuardDuty : 1-3.9 faible, 4-6.9 moyenne, 7-8.9 haute, 9-10 critique.
resource "aws_cloudwatch_event_rule" "guardduty_high" {
  name        = "${local.name}-guardduty-high"
  description = "Findings GuardDuty de sévérité haute ou critique"

  event_pattern = jsonencode({
    source      = ["aws.guardduty"]
    detail-type = ["GuardDuty Finding"]
    detail = {
      severity = [{ numeric = [">=", 7] }]
    }
  })
}

resource "aws_cloudwatch_event_target" "guardduty_to_sns" {
  rule      = aws_cloudwatch_event_rule.guardduty_high.name
  target_id = "sns"
  arn       = aws_sns_topic.security_alerts.arn
}

# Bonus de détection maison : alerte si quelqu'un utilise le compte root.
resource "aws_cloudwatch_event_rule" "root_usage" {
  name        = "${local.name}-root-usage"
  description = "Toute action API ou connexion console du compte root"

  event_pattern = jsonencode({
    detail-type = ["AWS API Call via CloudTrail", "AWS Console Sign In via CloudTrail"]
    detail = {
      userIdentity = { type = ["Root"] }
    }
  })
}

resource "aws_cloudwatch_event_target" "root_to_sns" {
  rule      = aws_cloudwatch_event_rule.root_usage.name
  target_id = "sns"
  arn       = aws_sns_topic.security_alerts.arn
}

resource "aws_budgets_budget" "monthly" {
  name         = "${local.name}-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }
}
