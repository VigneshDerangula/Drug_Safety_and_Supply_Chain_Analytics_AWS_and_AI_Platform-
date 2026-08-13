# Medallion-style zones: raw (landing) -> staging -> curated, plus a Glue scripts bucket.

resource "aws_s3_bucket" "raw" {
  bucket = "${var.project_name}-${var.environment}-raw"
}

resource "aws_s3_bucket" "staging" {
  bucket = "${var.project_name}-${var.environment}-staging"
}

resource "aws_s3_bucket" "curated" {
  bucket = "${var.project_name}-${var.environment}-curated"
}

resource "aws_s3_bucket" "glue_scripts" {
  bucket = "${var.project_name}-${var.environment}-glue-scripts"
}

resource "aws_s3_bucket_versioning" "raw" {
  bucket = aws_s3_bucket.raw.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw" {
  bucket = aws_s3_bucket.raw.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "raw" {
  bucket                  = aws_s3_bucket.raw.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "raw" {
  bucket = aws_s3_bucket.raw.id
  rule {
    id     = "raw-transition-to-ia"
    status = "Enabled"
    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }
  }
}
