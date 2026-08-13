# Glue job execution role
resource "aws_iam_role" "glue_role" {
  name = "${var.project_name}-${var.environment}-glue-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "glue.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_s3_access" {
  name = "${var.project_name}-glue-s3-access"
  role = aws_iam_role.glue_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["s3:GetObject", "s3:PutObject", "s3:ListBucket", "s3:DeleteObject"]
      Resource = [
        aws_s3_bucket.raw.arn, "${aws_s3_bucket.raw.arn}/*",
        aws_s3_bucket.staging.arn, "${aws_s3_bucket.staging.arn}/*",
        aws_s3_bucket.curated.arn, "${aws_s3_bucket.curated.arn}/*",
        aws_s3_bucket.glue_scripts.arn, "${aws_s3_bucket.glue_scripts.arn}/*",
      ]
    }]
  })
}

# Lambda execution role for real-time adverse-event triage
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-${var.environment}-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_exec" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_sns_s3" {
  name = "${var.project_name}-lambda-sns-s3"
  role = aws_iam_role.lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["sns:Publish"]
        Resource = aws_sns_topic.adverse_event_alerts.arn
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${aws_s3_bucket.raw.arn}/*"
      }
    ]
  })
}

# Redshift service role for COPY from S3
resource "aws_iam_role" "redshift_role" {
  name = "${var.project_name}-${var.environment}-redshift-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "redshift.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "redshift_s3_read" {
  name = "${var.project_name}-redshift-s3-read"
  role = aws_iam_role.redshift_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:ListBucket"]
      Resource = [aws_s3_bucket.curated.arn, "${aws_s3_bucket.curated.arn}/*"]
    }]
  })
}
