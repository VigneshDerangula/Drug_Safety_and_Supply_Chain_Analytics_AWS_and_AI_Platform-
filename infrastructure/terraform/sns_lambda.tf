resource "aws_sns_topic" "adverse_event_alerts" {
  name = "${var.project_name}-${var.environment}-severe-ae-alerts"
}

resource "aws_sns_topic_subscription" "alert_email" {
  topic_arn = aws_sns_topic.adverse_event_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_lambda_function" "adverse_event_alert" {
  function_name = "${var.project_name}-${var.environment}-ae-triage"
  role          = aws_iam_role.lambda_role.arn
  runtime       = "python3.12"
  handler       = "adverse_event_alert.lambda_handler"
  filename      = "${path.module}/../../etl/lambda/adverse_event_alert.zip"
  timeout       = 30

  environment {
    variables = {
      SNS_TOPIC_ARN = aws_sns_topic.adverse_event_alerts.arn
    }
  }
}

resource "aws_s3_bucket_notification" "raw_ae_trigger" {
  bucket = aws_s3_bucket.raw.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.adverse_event_alert.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "adverse_events/"
    filter_suffix       = ".json"
  }

  depends_on = [aws_lambda_permission.allow_s3]
}

resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.adverse_event_alert.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.raw.arn
}
