# Setup & Deployment Guide

## 1. Local run (no AWS account needed)

```bash
git clone <your-repo-url>
cd pharma-aws-data-engineering-ai
python -m venv venv && source venv/bin/activate
pip install -r ai_ml/requirements.txt

# 1. Generate synthetic source data
python data_generation/generate_synthetic_data.py

# 2. Run data-quality tests
pytest tests/ -v

# 3. Train and score the adverse-event severity classifier
python ai_ml/adverse_event_nlp_classifier.py --mode train
python ai_ml/adverse_event_nlp_classifier.py --mode score

# 4. Run the demand forecasting model
python ai_ml/demand_forecasting_model.py --mode score --horizon 3
```

Optional — zero-shot LLM classification instead of the trained model:
```bash
pip install anthropic
export ANTHROPIC_API_KEY=your_key
python ai_ml/adverse_event_nlp_classifier.py --mode score --use-llm
```

## 2. dbt (against a local Postgres, no Redshift needed)

```bash
pip install dbt-postgres
# point DBT_PROFILES_DIR at dbt/pharma_analytics/ci_profiles for a quick local check,
# or create your own ~/.dbt/profiles.yml based on dbt/pharma_analytics/profiles_example.yml
cd dbt/pharma_analytics
dbt build --target ci
```

## 3. Deploying the real AWS infrastructure (optional)

Requires an AWS account and credentials configured locally (`aws configure`).

```bash
cd infrastructure/terraform
terraform init
terraform plan -var="redshift_master_password=<choose-a-strong-password>"
terraform apply -var="redshift_master_password=<choose-a-strong-password>"
```

This provisions:
- 4 S3 buckets (raw / staging / curated / glue-scripts) with encryption + versioning
- 2 AWS Glue jobs (raw_to_staging, staging_to_curated)
- 1 Redshift cluster
- IAM roles for Glue, Lambda, and Redshift
- 1 Lambda function + SNS topic for real-time adverse-event alerting
- An S3 event notification wiring new files under `raw/adverse_events/*.json` to the Lambda

After `apply`, upload the Glue scripts and package the Lambda:
```bash
aws s3 cp etl/glue_jobs/raw_to_staging.py s3://<glue-scripts-bucket>/glue_jobs/
aws s3 cp etl/glue_jobs/staging_to_curated.py s3://<glue-scripts-bucket>/glue_jobs/

cd etl/lambda && zip adverse_event_alert.zip adverse_event_alert.py
# terraform apply again so the Lambda picks up the zip (filename hash triggers redeploy)
```

## 4. Orchestration

`orchestration/airflow/dags/pharma_pipeline_dag.py` assumes:
- Airflow with `apache-airflow-providers-amazon` installed
- An `aws_default` connection with permissions for Glue/S3/SNS
- A `redshift_default` connection to the cluster from step 3
- Variable `pharma_alerts_sns_arn` set to the SNS topic ARN from Terraform output

Drop the DAG file into your Airflow `dags/` folder and it will appear as `pharma_pipeline`,
scheduled daily at 03:00.

## 5. CI/CD

`.github/workflows/ci.yml` runs on every push/PR:
- generates synthetic data, runs the pytest data-quality suite, trains/scores both AI models
- `terraform fmt -check` + `terraform validate` on the infrastructure code
- `dbt compile` against a throwaway Postgres service container to catch SQL/ref errors

No secrets are required for CI to pass — it never touches a real AWS account.
