"""
Airflow DAG: pharma_pipeline

Daily orchestration of the full PharmaPulse pipeline:

  1. raw_to_staging (Glue)          — schema-enforced, deduped staging parquet
  2. staging_to_curated (Glue)      — joined, analytics-ready curated parquet
  3. redshift_copy                  — COPY curated parquet into Redshift
  4. dbt_build                      — staging + mart models, with dbt tests
  5. score_adverse_event_severity   — batch-score new narratives with the NLP model
  6. score_demand_forecast          — refresh the drug demand forecast

Each Glue step waits for job completion via a sensor; dbt and the ML scoring
steps run as BashOperators inside a dedicated virtualenv/image. Alerting on
failure goes to the same SNS topic used by the real-time Lambda triage.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator
from airflow.providers.amazon.aws.sensors.glue import GlueJobSensor
from airflow.providers.amazon.aws.transfers.s3_to_redshift import S3ToRedshiftOperator
from airflow.providers.amazon.aws.operators.sns import SnsPublishOperator

default_args = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": None,  # wire to a shared alert helper in a real deployment
}

with DAG(
    dag_id="pharma_pipeline",
    description="Ingest -> transform -> warehouse -> AI scoring for pharma safety & supply data",
    schedule_interval="0 3 * * *",  # daily at 03:00
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["pharma", "aws", "dbt", "ai"],
    max_active_runs=1,
) as dag:

    raw_to_staging = GlueJobOperator(
        task_id="raw_to_staging",
        job_name="pharmapulse-dev-raw-to-staging",
        aws_conn_id="aws_default",
        region_name="us-east-1",
    )

    wait_raw_to_staging = GlueJobSensor(
        task_id="wait_raw_to_staging",
        job_name="pharmapulse-dev-raw-to-staging",
        run_id="{{ ti.xcom_pull(task_ids='raw_to_staging') }}",
        aws_conn_id="aws_default",
    )

    staging_to_curated = GlueJobOperator(
        task_id="staging_to_curated",
        job_name="pharmapulse-dev-staging-to-curated",
        aws_conn_id="aws_default",
        region_name="us-east-1",
    )

    wait_staging_to_curated = GlueJobSensor(
        task_id="wait_staging_to_curated",
        job_name="pharmapulse-dev-staging-to-curated",
        run_id="{{ ti.xcom_pull(task_ids='staging_to_curated') }}",
        aws_conn_id="aws_default",
    )

    redshift_copy_adverse_events = S3ToRedshiftOperator(
        task_id="redshift_copy_adverse_events",
        schema="raw",
        table="adverse_events",
        s3_bucket="pharmapulse-dev-curated",
        s3_key="adverse_events/",
        copy_options=["FORMAT AS PARQUET"],
        redshift_conn_id="redshift_default",
        aws_conn_id="aws_default",
        method="REPLACE",
    )

    redshift_copy_supply_demand = S3ToRedshiftOperator(
        task_id="redshift_copy_supply_demand",
        schema="raw",
        table="supply_demand",
        s3_bucket="pharmapulse-dev-curated",
        s3_key="supply_demand/",
        copy_options=["FORMAT AS PARQUET"],
        redshift_conn_id="redshift_default",
        aws_conn_id="aws_default",
        method="REPLACE",
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command="cd /opt/dbt/pharma_analytics && dbt build --target prod",
    )

    score_adverse_event_severity = BashOperator(
        task_id="score_adverse_event_severity",
        bash_command="python /opt/ai_ml/adverse_event_nlp_classifier.py --mode score",
    )

    score_demand_forecast = BashOperator(
        task_id="score_demand_forecast",
        bash_command="python /opt/ai_ml/demand_forecasting_model.py --mode score",
    )

    notify_success = SnsPublishOperator(
        task_id="notify_success",
        target_arn="{{ var.value.pharma_alerts_sns_arn }}",
        message="pharma_pipeline completed successfully for {{ ds }}",
        subject="[PharmaPulse] Daily pipeline succeeded",
        aws_conn_id="aws_default",
    )

    (
        raw_to_staging
        >> wait_raw_to_staging
        >> staging_to_curated
        >> wait_staging_to_curated
        >> [redshift_copy_adverse_events, redshift_copy_supply_demand]
        >> dbt_build
        >> [score_adverse_event_severity, score_demand_forecast]
        >> notify_success
    )
