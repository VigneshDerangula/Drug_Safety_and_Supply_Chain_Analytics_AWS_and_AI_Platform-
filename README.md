# PharmaPulse

**An end-to-end AWS data platform for pharma — clinical, safety & commercial data in, AI-driven insight out.**

<p>
  <img alt="AWS" src="https://img.shields.io/badge/AWS-S3%20%7C%20Glue%20%7C%20Lambda%20%7C%20Redshift-E8853B?style=flat-square&logo=amazonaws&logoColor=white">
  <img alt="dbt" src="https://img.shields.io/badge/dbt-transformations-EA6B4B?style=flat-square&logo=dbt&logoColor=white">
  <img alt="Airflow" src="https://img.shields.io/badge/Airflow-orchestration-017CEE?style=flat-square&logo=apacheairflow&logoColor=white">
  <img alt="Terraform" src="https://img.shields.io/badge/Terraform-IaC-5C4EE5?style=flat-square&logo=terraform&logoColor=white">
  <img alt="Python" src="https://img.shields.io/badge/Python-pandas%20%7C%20scikit--learn-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="CI" src="https://img.shields.io/badge/CI-GitHub%20Actions-24292E?style=flat-square&logo=githubactions&logoColor=white">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-1B8A5A?style=flat-square">
</p>

## What this is

PharmaPulse is a portfolio project that simulates the data platform behind a pharma company's
safety and supply chain teams. It takes four kinds of data a real pharma company deals with —
clinical trial records, adverse-event reports, drug shipments, and sales — and moves them through
a full pipeline: **land the raw files → clean and join them → load a warehouse → model them with
dbt → score them with two AI models → hand them to BI tools.** Everything is built and tested
end to end, from the Terraform that provisions the AWS resources down to the CI pipeline that
validates every change.

It's designed to demonstrate the specific skill set behind pharma data engineering roles (the kind
referenced in Merck & Co.–style Data Engineer job postings): **AWS (S3, Glue, Lambda, Redshift,
IAM), Airflow orchestration, dbt-based transformation, Terraform IaC, CI/CD, and applied ML on top
of governed data.**

All data in this repo is **synthetic and generated locally** — no real patient, trial, or company
data is used anywhere.

## The architecture, at a glance

<img width="1760" height="1000" alt="architecture_diagram" src="https://github.com/user-attachments/assets/e23e189c-606f-4297-b4e3-0e74f10fdc1e" />

There are two paths through the system, and understanding the difference is the key to
understanding the whole design:

- **The daily batch path** (solid arrows, orchestrated by Airflow) — handles everything that can
  wait a few hours: cleaning data, joining it, loading the warehouse, refreshing dbt models,
  scoring the ML models.
- **The real-time path** (dashed red arrows) — handles the one thing that *can't* wait: a brand
  new adverse-event report. The moment one lands in S3, a Lambda function fires and pages the
  safety team within seconds, completely independent of the nightly batch run.

A plain-text/Mermaid version of this same diagram (easier to read in a PR diff) lives in
[`architecture/architecture_diagram.md`](architecture/architecture_diagram.md).

## Walking through a single day

This is the whole pipeline, step by step, in the order it actually runs:

1. **Synthetic source data lands.** `data_generation/generate_synthetic_data.py` produces four
   CSVs that mimic real pharma feeds: `clinical_trials.csv` (ClinicalTrials.gov-style),
   `adverse_events.csv` (FDA FAERS-style individual case safety reports), `drug_shipments.csv`
   (ERP/logistics), and `drug_sales.csv` (commercial data warehouse). In production these would be
   the actual upstream feeds landing in S3's **raw zone**.

2. **AWS Glue job `raw_to_staging` cleans and enforces structure** (`etl/glue_jobs/raw_to_staging.py`).
   For each of the four datasets it enforces a strict schema (so a malformed column fails loudly
   instead of silently corrupting downstream tables), drops rows missing required fields, removes
   duplicate records by business key (e.g. `case_id` for adverse events), and writes the result as
   partitioned Parquet to the **staging zone**. It logs how many rows came in vs. survived, so data
   loss is visible, not hidden.

3. **AWS Glue job `staging_to_curated` joins the data into analytics-ready tables**
   (`etl/glue_jobs/staging_to_curated.py`). Two curated tables come out of this step:
   - `curated_adverse_events` — every adverse event enriched with how many active clinical trials
     exist for that drug, plus derived flags like `is_pediatric` and `is_geriatric`.
   - `curated_supply_demand` — shipments and sales joined by drug/region/month, with a computed
     `supply_demand_variance` (units shipped minus units sold) that flags over- or under-supply.

   Both land in the **curated zone**, ready for Redshift or dbt to pick up directly.

4. **In parallel, real-time safety triage runs independently of all of the above.** The instant a
   new adverse-event file lands under `raw/adverse_events/*.json`, an S3 event triggers the
   `adverse_event_alert` Lambda (`etl/lambda/adverse_event_alert.py`). It runs a cheap keyword-rules
   check — looking for terms like *anaphylaxis*, *cardiac arrest*, *respiratory failure*, or a
   `fatal` outcome — and if the case looks severe or life-threatening, it publishes straight to an
   SNS topic that pages the pharmacovigilance team. This is deliberately simple and fast: it's a
   tripwire, not a diagnosis. The fuller, more accurate classification happens in step 6 during the
   nightly batch, and the two are designed to reconcile.

5. **Redshift COPY loads the warehouse.** Airflow's `S3ToRedshiftOperator` copies the curated
   Parquet straight into two Redshift tables (`raw.adverse_events`, `raw.supply_demand`).

6. **dbt transforms raw warehouse tables into trusted marts** (`dbt/pharma_analytics/`). Staging
   models (`stg_adverse_events`, `stg_supply_demand`) do light cleanup and null-filtering. Mart
   models build the tables BI tools actually query:
   - `dim_drugs` — one row per drug seen in either the safety or supply/demand data.
   - `fct_adverse_events` — one row per case, BI-ready.
   - `fct_adverse_events_monthly` — monthly event counts and % serious, by drug and region.
   - `fct_drug_demand` — monthly shipped-vs-sold variance, by drug and region.

   Every model has dbt tests attached (uniqueness, not-null, accepted-value checks on
   `severity_label`) so a broken upstream feed fails the build instead of silently corrupting a
   dashboard.

7. **Two AI models score the freshly-built marts:**
   - **Adverse-event severity classifier** (`ai_ml/adverse_event_nlp_classifier.py`) — TF-IDF +
     logistic regression trained on labeled narratives, classifying each case into
     mild / moderate / severe / life-threatening. It also supports `--use-llm`, which swaps in
     zero-shot classification via an LLM (Claude, or Bedrock in a real AWS deployment) for
     situations with no labeled history yet — a new drug launch, for instance.
   - **Demand forecaster** (`ai_ml/demand_forecasting_model.py`) — Holt-Winters exponential
     smoothing, fit per drug/region, forecasting units needed months ahead. It backtests on the
     last 3 months of real history before trusting the forecast, reporting MAPE and RMSE per
     series so accuracy is measured, not assumed.

8. **Looker/QuickSight-style BI sits on top** of the marts and model outputs for self-serve
   analysis by safety and commercial teams.

9. **Apache Airflow ties steps 2, 3, 5, 6, and 7 together** in one DAG
   (`orchestration/airflow/dags/pharma_pipeline_dag.py`), running daily at 03:00 with retries,
   sensors that wait for each Glue job to actually finish, and an SNS notification on success or
   failure — using the same alert topic the real-time Lambda uses.

## Why it's built this way

Pharma data platforms live under three constraints that shaped every decision in this repo:

1. **Regulated and auditable.** Every transformation is versioned (dbt), tested (dbt tests +
   pytest), and traceable raw → staging → curated through medallion-style S3 zones. If a number in
   a dashboard looks wrong, you can trace it back to the exact row and the exact transformation
   that produced it.
2. **Safety can't wait for batch.** A life-threatening adverse event reported at 9am shouldn't sit
   in a queue until the 3am batch run. The Lambda/SNS path exists specifically so severity triage
   happens in seconds, not hours.
3. **Clinical, safety, and commercial data don't share a shape.** Trial data, FAERS-style events,
   ERP shipments, and sales all arrive in different formats and cadences. Glue's schema
   enforcement and the staging/curated split exist to force them into a single, consistent shape
   before anyone tries to join them.

## Testing & CI — what actually gets checked

Nothing in this repo ships untested. `.github/workflows/ci.yml` runs three jobs on every push and
PR, and none of them need real AWS credentials:

- **`python-tests`** — regenerates the synthetic data, runs the full `tests/test_data_quality.py`
  suite (uniqueness of IDs, valid severity labels, plausible patient ages, no orphaned drug codes
  between shipments and sales, non-negative revenue, etc.), then trains and scores both AI models
  to make sure the ML code actually runs end to end.
- **`terraform-validate`** — runs `terraform fmt -check` and `terraform validate` against
  `infrastructure/terraform/` to catch broken or malformed infrastructure code before it's ever
  applied.
- **`dbt-build`** — spins up a throwaway Postgres container and runs `dbt compile` against it, so
  every dbt model's SQL and `ref()`/`source()` graph is validated on every PR without touching a
  real Redshift cluster.

## Repo layout

| Path | What's in it |
|---|---|
| `data_generation/` | Generates the four synthetic pharma datasets |
| `infrastructure/terraform/` | Terraform for S3, Glue, Redshift, IAM, Lambda, SNS |
| `etl/glue_jobs/` | PySpark Glue jobs: `raw_to_staging`, `staging_to_curated` |
| `etl/lambda/` | Real-time adverse-event severity triage (Lambda + SNS) |
| `orchestration/airflow/dags/` | The Airflow DAG that runs the daily pipeline end to end |
| `dbt/pharma_analytics/` | dbt project — staging models, marts, schema tests |
| `ai_ml/` | Adverse-event NLP severity classifier + demand forecasting model |
| `.github/workflows/` | CI — pytest, terraform validate, dbt compile on every push/PR |
| `tests/` | Data-quality pytest suite |
| `docs/SETUP.md` | Full step-by-step guide: local run, dbt, Terraform deploy, Airflow, CI |
| `architecture/` | Architecture diagram (SVG + Mermaid source) |

## What's in each dataset

All synthetic, generated locally — **no real patient or company data**.

| Dataset | Grain | Modeled after |
|---|---|---|
| `clinical_trials.csv` | One row per trial site/phase | ClinicalTrials.gov structure |
| `adverse_events.csv` | One row per reported event | FDA FAERS report structure |
| `drug_shipments.csv` | One row per shipment | ERP / logistics feed |
| `drug_sales.csv` | One row per drug/region/month | Commercial data warehouse |

Regenerate any time with `python data_generation/generate_synthetic_data.py`.

## The AWS infrastructure (Terraform)

`infrastructure/terraform/` provisions everything the pipeline needs, and `terraform validate`
runs in CI on every PR — it's written to `plan` cleanly, though it isn't `apply`'d as part of this
repo (no AWS account attached). It stands up:

- **4 S3 buckets** — raw, staging, curated, and glue-scripts, each with versioning, server-side
  encryption, and public access blocked.
- **2 Glue jobs** — `raw_to_staging` and `staging_to_curated`, plus a Glue Catalog database.
- **1 Redshift cluster** — with a dedicated subnet group.
- **IAM roles** scoped per service — Glue (S3 access), Lambda (SNS publish + S3 read), Redshift
  (S3 read for COPY) — nothing gets broader permissions than it needs.
- **1 Lambda function + SNS topic** for real-time alerting, wired to fire automatically on new S3
  objects under `raw/adverse_events/*.json`.

## Getting started

The full walkthrough — including how to run dbt locally, deploy the real AWS infrastructure, and
wire up Airflow — is in [`docs/SETUP.md`](docs/SETUP.md). Fastest path to seeing it work, no AWS
account required:

```bash
python -m venv venv && source venv/bin/activate
pip install -r ai_ml/requirements.txt

python data_generation/generate_synthetic_data.py   # generate the 4 source datasets
pytest tests/ -v                                     # data-quality checks

python ai_ml/adverse_event_nlp_classifier.py --mode train
python ai_ml/adverse_event_nlp_classifier.py --mode score

python ai_ml/demand_forecasting_model.py --mode score --horizon 3

cd dbt/pharma_analytics && dbt build --target ci     # runs against a local Postgres target
```

## Tech stack

AWS S3 · AWS Glue (PySpark) · AWS Lambda · Amazon SNS · Amazon Redshift · IAM · Apache Airflow ·
dbt · Python (pandas, scikit-learn, statsmodels) · Terraform · GitHub Actions · pytest

## License

MIT — see [`LICENSE`](LICENSE).
