output "raw_bucket" {
  value = aws_s3_bucket.raw.bucket
}

output "staging_bucket" {
  value = aws_s3_bucket.staging.bucket
}

output "curated_bucket" {
  value = aws_s3_bucket.curated.bucket
}

output "redshift_endpoint" {
  value = aws_redshift_cluster.pharma_dwh.endpoint
}

output "sns_alert_topic_arn" {
  value = aws_sns_topic.adverse_event_alerts.arn
}
