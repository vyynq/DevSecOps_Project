output "vpc_id" {
  value = aws_vpc.main.id
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}

output "logs_bucket" {
  value = aws_s3_bucket.logs.id
}

output "cloudtrail_name" {
  value = aws_cloudtrail.main.name
}

output "auditor_role_arn" {
  description = "aws sts assume-role --role-arn <ARN> --role-session-name test --serial-number <MFA_ARN> --token-code <CODE>"
  value       = aws_iam_role.auditor.arn
}

output "security_alerts_topic" {
  value = aws_sns_topic.security_alerts.arn
}
