resource "aws_glue_catalog_database" "pharma_catalog" {
  name = "${var.project_name}_${var.environment}_catalog"
}

resource "aws_glue_job" "raw_to_staging" {
  name              = "${var.project_name}-${var.environment}-raw-to-staging"
  role_arn          = aws_iam_role.glue_role.arn
  glue_version      = "4.0"
  worker_type       = "G.1X"
  number_of_workers = 4
  timeout           = 60

  command {
    name            = "glueetl"
    script_location = "s3://${aws_s3_bucket.glue_scripts.bucket}/glue_jobs/raw_to_staging.py"
    python_version  = "3"
  }

  default_arguments = {
    "--RAW_BUCKET"     = aws_s3_bucket.raw.bucket
    "--STAGING_BUCKET" = aws_s3_bucket.staging.bucket
    "--job-language"   = "python"
    "--enable-metrics" = "true"
  }
}

resource "aws_glue_job" "staging_to_curated" {
  name              = "${var.project_name}-${var.environment}-staging-to-curated"
  role_arn          = aws_iam_role.glue_role.arn
  glue_version      = "4.0"
  worker_type       = "G.1X"
  number_of_workers = 4
  timeout           = 60

  command {
    name            = "glueetl"
    script_location = "s3://${aws_s3_bucket.glue_scripts.bucket}/glue_jobs/staging_to_curated.py"
    python_version  = "3"
  }

  default_arguments = {
    "--STAGING_BUCKET" = aws_s3_bucket.staging.bucket
    "--CURATED_BUCKET" = aws_s3_bucket.curated.bucket
    "--job-language"   = "python"
    "--enable-metrics" = "true"
  }
}
