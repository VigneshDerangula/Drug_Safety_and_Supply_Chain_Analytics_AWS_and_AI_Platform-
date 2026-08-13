# PharmaPulse — AWS Data Engineering & AI Platform for Drug Safety and Supply Chain Analytics

A portfolio project simulating an end-to-end data platform for a pharmaceutical company: it ingests
clinical trial, adverse-event (FAERS-style), drug shipment, and sales data, moves it through an
AWS-native pipeline, models it with dbt, and layers two AI components on top — an adverse-event
severity classifier (pharmacovigilance) and a drug demand forecasting model (supply chain).

Built to demonstrate the skill set relevant to a Data Engineer role supporting pharma
analytics (clinical, safety, and commercial data) — the kind of work referenced in Merck & Co.
data engineering job descriptions: AWS (S3, Glue, Lambda, Redshift, IAM), orchestration (Airflow),
dbt-based transformation, CI/CD, and applied ML/AI on top of governed data.

## Why this project

Pharma data platforms have three defining constraints this repo is designed around:
1. **Regulated, auditable data** — every transformation is versioned (dbt), tested (dbt tests +
   pytest), and traceable from raw → staging → curated (medallion-style zones in S3).
2. **Safety-critical latency** — adverse event signals need near-real-time triage, not just
   nightly batch (Lambda-based alerting sits alongside the batch Glue/Airflow pipeline).
3. **Cross-functional data** — clinical, safety, and commercial (sales/supply chain) data live in
   different shapes and cadences and get unified into a single Redshift warehouse.

## Architecture

```
┌─────────────┐   ┌──────────────┐   ┌───────────────┐   ┌─────────────┐   ┌────────────────┐
│ Source data │──▶│ S3 raw zone   │──▶│ AWS Glue (PySpark)│──▶│ S3 curated  │──▶│ Redshift        │
│ (trials,    │   │ (landing)     │   │ raw→staging→curated│   │ zone        │   │ (COPY from S3)  │
│ FAERS, ERP) │   └──────────────┘   └───────────────┘   └─────────────┘   └────────────────┘
└─────────────┘          │                                                        │
                          │ new adverse event                                     │
                          ▼                                                       ▼
                 ┌────────────────┐                                     ┌──────────────────┐
                 │ Lambda: real-  │                                     │ dbt (staging +    │
                 │ time severity  │                                     │ marts) on Redshift │
                 │ triage + SNS   │                                     └──────────────────┘
                 └────────────────┘                                               │
                                                                                   ▼
                                                                     ┌──────────────────────────┐
                                                                     │ AI/ML layer:              │
                                                                     │ - adverse event NLP model │
                                                                     │ - demand forecasting model│
                                                                     └──────────────────────────┘
                                                                                   │
                                                                                   ▼
                                                                     ┌──────────────────────────┐
                                                                     │ BI (Looker/QuickSight)    │
                                                                     └──────────────────────────┘
```

Orchestration: an **Airflow DAG** (`orchestration/airflow/dags/pharma_pipeline_dag.py`) runs the
Glue jobs, triggers the Redshift COPY, runs `dbt build`, then scores the AI models — end to end,
scheduled daily, with retries and SLAs.

## Repo layout

```
data_generation/     synthetic pharma datasets (clinical trials, FAERS adverse events, shipments, sales)
infrastructure/       Terraform for S3, Glue, Redshift, IAM, Lambda
etl/glue_jobs/        PySpark Glue jobs: raw → staging → curated
etl/lambda/           real-time adverse-event severity triage (Lambda + SNS)
orchestration/         Airflow DAG orchestrating the full pipeline
dbt/pharma_analytics/  dbt project: staging models, marts, schema tests
ai_ml/                 adverse-event NLP severity classifier + demand forecasting model
.github/workflows/     CI: dbt build/test + pytest on every PR
tests/                 data-quality pytest suite
docs/SETUP.md          step-by-step deploy guide
```

## Datasets (synthetic, generated locally — no real patient/company data)

| Dataset | Grain | Analogous real source |
|---|---|---|
| `clinical_trials.csv` | one row per trial site/phase | ClinicalTrials.gov structure |
| `adverse_events.csv` | one row per reported event | FDA FAERS report structure |
| `drug_shipments.csv` | one row per shipment | ERP / logistics feed |
| `drug_sales.csv` | one row per drug/region/month | Commercial data warehouse |

Run `python data_generation/generate_synthetic_data.py` to regenerate them under `data/`.

## AI/ML components

1. **Adverse Event Severity Classifier** (`ai_ml/adverse_event_nlp_classifier.py`) — TF-IDF +
   logistic regression baseline that classifies free-text adverse-event narratives into
   severity tiers (mild/moderate/severe/life-threatening), with a documented swap-in point for
   an LLM-based zero-shot classifier (Claude/Bedrock) for cases with no labeled training data.
2. **Drug Demand Forecasting** (`ai_ml/demand_forecasting_model.py`) — time-series forecast
   (statsmodels exponential smoothing) per drug/region to support supply chain planning, with
   an evaluation harness (MAPE/RMSE backtesting).

## Getting started

See `docs/SETUP.md` for the full walkthrough. Quick version:

```bash
python -m venv venv && source venv/bin/activate
pip install -r ai_ml/requirements.txt
python data_generation/generate_synthetic_data.py
python ai_ml/adverse_event_nlp_classifier.py
python ai_ml/demand_forecasting_model.py
cd dbt/pharma_analytics && dbt build   # requires a configured Redshift/local Postgres target
```

Terraform (`infrastructure/terraform/`) is provided to stand up the real AWS resources
(S3 buckets, Glue jobs, Redshift cluster, IAM roles, Lambda) — it's written to `plan` cleanly
but is not applied as part of this repo (no AWS account attached).

## Tech stack

AWS S3 · AWS Glue (PySpark) · AWS Lambda · Amazon Redshift · IAM · Apache Airflow · dbt ·
Python (pandas, scikit-learn, statsmodels) · Terraform · GitHub Actions · pytest

## License

MIT — see `LICENSE`.
