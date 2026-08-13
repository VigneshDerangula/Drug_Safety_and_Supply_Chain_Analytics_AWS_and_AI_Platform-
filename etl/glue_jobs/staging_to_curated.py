"""
AWS Glue Job: staging_to_curated

Joins the staged pharma datasets into curated, analytics-ready tables
(one row per adverse event enriched with drug/trial context, one row per
shipment enriched with sales context) and writes them to the curated S3
zone in Parquet, ready for Redshift COPY / Spectrum and for dbt sources.
"""
import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F

args = getResolvedOptions(sys.argv, ["JOB_NAME", "STAGING_BUCKET", "CURATED_BUCKET"])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

STAGING_BUCKET = args["STAGING_BUCKET"]
CURATED_BUCKET = args["CURATED_BUCKET"]


def read_staging(name: str):
    return spark.read.parquet(f"s3://{STAGING_BUCKET}/{name}/")


adverse_events = read_staging("adverse_events")
clinical_trials = read_staging("clinical_trials")
drug_shipments = read_staging("drug_shipments")
drug_sales = read_staging("drug_sales")

# --- curated_adverse_events: safety events enriched with active-trial context ---
active_trials_by_drug = (
    clinical_trials.filter(F.col("status").isin("Active", "Recruiting"))
    .groupBy("drug_code")
    .agg(F.count("trial_id").alias("active_trial_count"))
)

curated_adverse_events = (
    adverse_events.join(active_trials_by_drug, on="drug_code", how="left")
    .withColumn("active_trial_count", F.coalesce(F.col("active_trial_count"), F.lit(0)))
    .withColumn("is_pediatric", F.col("patient_age") < 18)
    .withColumn("is_geriatric", F.col("patient_age") >= 65)
)

curated_adverse_events.write.mode("overwrite").partitionBy("region").parquet(
    f"s3://{CURATED_BUCKET}/adverse_events/"
)

# --- curated_supply_demand: shipments joined to same-month sales for supply/demand variance ---
shipments_monthly = drug_shipments.withColumn(
    "ship_month", F.date_trunc("month", F.col("ship_date"))
).groupBy("drug_code", "region", "ship_month").agg(
    F.sum("quantity_units").alias("units_shipped")
)

sales_renamed = drug_sales.withColumnRenamed("sales_month", "ship_month")

curated_supply_demand = shipments_monthly.join(
    sales_renamed, on=["drug_code", "region", "ship_month"], how="outer"
).withColumn(
    "units_shipped", F.coalesce(F.col("units_shipped"), F.lit(0))
).withColumn(
    "units_sold", F.coalesce(F.col("units_sold"), F.lit(0))
).withColumn(
    "supply_demand_variance", F.col("units_shipped") - F.col("units_sold")
)

curated_supply_demand.write.mode("overwrite").partitionBy("region").parquet(
    f"s3://{CURATED_BUCKET}/supply_demand/"
)

print(f"curated_adverse_events rows: {curated_adverse_events.count()}")
print(f"curated_supply_demand rows: {curated_supply_demand.count()}")

job.commit()
