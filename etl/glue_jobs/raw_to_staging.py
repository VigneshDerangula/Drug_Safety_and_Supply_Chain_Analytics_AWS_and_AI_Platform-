"""
AWS Glue Job: raw_to_staging

Reads the four raw pharma feeds landed in S3 (clinical_trials, adverse_events,
drug_shipments, drug_sales), applies schema enforcement + basic data-quality
rules, and writes partitioned Parquet to the staging zone.

Run as a Glue 4.0 PySpark job. Locally, the same logic can be exercised with
`spark-submit` against local CSVs by setting RAW_BUCKET/STAGING_BUCKET to
local paths instead of s3:// URIs.
"""
import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql.types import (
    BooleanType,
    DateType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

args = getResolvedOptions(sys.argv, ["JOB_NAME", "RAW_BUCKET", "STAGING_BUCKET"])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

RAW_BUCKET = args["RAW_BUCKET"]
STAGING_BUCKET = args["STAGING_BUCKET"]


def read_csv(name: str, schema: StructType):
    path = f"s3://{RAW_BUCKET}/{name}/"
    return spark.read.option("header", True).schema(schema).csv(path)


# ---- schemas mirror data_generation/generate_synthetic_data.py ----

clinical_trials_schema = StructType(
    [
        StructField("trial_id", StringType()),
        StructField("drug_code", StringType()),
        StructField("drug_name", StringType()),
        StructField("therapeutic_area", StringType()),
        StructField("phase", StringType()),
        StructField("status", StringType()),
        StructField("site_country", StringType()),
        StructField("region", StringType()),
        StructField("start_date", DateType()),
        StructField("estimated_completion_date", DateType()),
        StructField("enrolled_patients", IntegerType()),
        StructField("primary_endpoint_met", BooleanType()),
    ]
)

adverse_events_schema = StructType(
    [
        StructField("case_id", StringType()),
        StructField("drug_code", StringType()),
        StructField("drug_name", StringType()),
        StructField("report_date", DateType()),
        StructField("patient_age", IntegerType()),
        StructField("patient_sex", StringType()),
        StructField("country", StringType()),
        StructField("region", StringType()),
        StructField("reporter_type", StringType()),
        StructField("narrative", StringType()),
        StructField("severity_label", StringType()),
        StructField("outcome", StringType()),
        StructField("serious_flag", BooleanType()),
    ]
)

drug_shipments_schema = StructType(
    [
        StructField("shipment_id", StringType()),
        StructField("drug_code", StringType()),
        StructField("drug_name", StringType()),
        StructField("origin_facility", StringType()),
        StructField("destination_country", StringType()),
        StructField("region", StringType()),
        StructField("ship_date", DateType()),
        StructField("quantity_units", IntegerType()),
        StructField("batch_id", StringType()),
        StructField("cold_chain_required", BooleanType()),
        StructField("delivery_status", StringType()),
    ]
)

drug_sales_schema = StructType(
    [
        StructField("sales_month", DateType()),
        StructField("drug_code", StringType()),
        StructField("drug_name", StringType()),
        StructField("region", StringType()),
        StructField("units_sold", IntegerType()),
        StructField("revenue_usd", DoubleType()),
    ]
)


def clean_and_write(df, name: str, required_cols, dedup_key):
    """Drop rows missing required fields, dedupe on business key, write partitioned parquet."""
    before = df.count()
    df = df.dropna(subset=required_cols)
    df = df.dropDuplicates([dedup_key])
    after = df.count()
    print(f"[{name}] rows in={before} rows out={after} dropped={before - after}")

    df = df.withColumn("_ingested_at", F.current_timestamp())
    out_path = f"s3://{STAGING_BUCKET}/{name}/"
    df.write.mode("overwrite").partitionBy("region").parquet(out_path)


clinical_trials = read_csv("clinical_trials", clinical_trials_schema)
clean_and_write(clinical_trials, "clinical_trials", ["trial_id", "drug_code"], "trial_id")

adverse_events = read_csv("adverse_events", adverse_events_schema)
clean_and_write(adverse_events, "adverse_events", ["case_id", "drug_code", "report_date"], "case_id")

drug_shipments = read_csv("drug_shipments", drug_shipments_schema)
clean_and_write(drug_shipments, "drug_shipments", ["shipment_id", "drug_code"], "shipment_id")

drug_sales = read_csv("drug_sales", drug_sales_schema)
clean_and_write(drug_sales, "drug_sales", ["drug_code", "sales_month"], "drug_code")

job.commit()
