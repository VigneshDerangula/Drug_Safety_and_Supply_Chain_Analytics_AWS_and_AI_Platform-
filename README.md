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

Every day, a pharma company generates clinical trial results, adverse-event reports, shipment
records, and sales data — in different shapes, different systems, different urgency levels. This
is a portfolio build of the platform that pulls all of it together: raw files land in S3, Glue
reshapes them through a medallion pipeline into Redshift, dbt turns curated tables into trusted
marts, and two ML models — an adverse-event severity classifier and a demand forecaster — sit on
top and turn the data into decisions. A parallel Lambda path triages new safety reports the moment
they land, because drug-safety signals can't wait for the nightly batch.

## Why this project exists

Pharma data platforms live under three constraints that shaped every design decision here:

1. **Regulated and auditable.** Every transformation is versioned (dbt), tested (dbt tests +
   pytest), and traceable raw → staging → curated through medallion-style S3 zones — nothing
   moves without a paper trail.
2. **Safety can't wait for batch.** Adverse-event signals get a real-time path: a Lambda function
   triages severity and fires an SNS alert the moment a new report lands, independent of the
   nightly Airflow run.
3. **Clinical, safety, and commercial data don't share a shape.** Trial data, FAERS-style adverse
   events, ERP shipments, and sales all land in different formats and cadences and get unified
   into one Redshift warehouse for cross-functional analysis.

## Architecture

<img width="1760" height="1000" alt="architecture_diagram" src="https://github.com/user-attachments/assets/ba407e5e-c1cf-478d-a020-f8599c38c000" />


Two paths, one warehouse:

- **Batch (daily, Airflow-orchestrated):** `S3 raw → Glue (raw→staging) → S3 staging → Glue
  (staging→curated) → S3 curated → Redshift (COPY) → dbt (staging + marts) → AI/ML scoring → BI`
- **Real-time (event-driven):** a new adverse-event file landing in the raw zone triggers `Lambda
  → severity triage → SNS` straight to the safety team, no batch wait.

A plain-text/Mermaid version of this diagram (handy for diffing in PRs) lives in
[`architecture/architecture_diagram.md`](architecture/architecture_diagram.md).

## Repo layout

| Path | What's in it |
|---|---|
| `data_generation/` | Synthetic pharma datasets — clinical trials, FAERS adverse events, shipments, sales |
| `infrastructure/` | Terraform for S3, Glue, Redshift, IAM, Lambda |
| `etl/glue_jobs/` | PySpark Glue jobs: raw → staging → curated |
| `etl/lambda/` | Real-time adverse-event severity triage (Lambda + SNS) |
| `orchestration/` | Airflow DAG orchestrating the full daily pipeline |
| `dbt/pharma_analytics/` | dbt project — staging models, marts, schema tests |
| `ai_ml/` | Adverse-event NLP severity classifier + demand forecasting model |
| `.github/workflows/` | CI — dbt build/test + pytest on every PR |
| `tests/` | Data-quality pytest suite |
| `docs/SETUP.md` | Step-by-step deploy guide |
| `architecture/` | Architecture diagram (SVG + Mermaid source) |

## Datasets

All synthetic, generated locally — **no real patient or company data**.

| Dataset | Grain | Modeled after |
|---|---|---|
| `clinical_trials.csv` | One row per trial site/phase | ClinicalTrials.gov structure |
| `adverse_events.csv` | One row per reported event | FDA FAERS report structure |
| `drug_shipments.csv` | One row per shipment | ERP / logistics feed |
| `drug_sales.csv` | One row per drug/region/month | Commercial data warehouse |

Regenerate with `python data_generation/generate_synthetic_data.py`.

## AI/ML components

1. **Adverse Event Severity Classifier** (`ai_ml/adverse_event_nlp_classifier.py`) — TF-IDF +
   logistic regression baseline that reads free-text adverse-event narratives and tags a severity
   tier (mild / moderate / severe / life-threatening). Includes a documented swap-in point for an
   LLM-based zero-shot classifier (Claude/Bedrock) for cases with no labeled training data.
2. **Drug Demand Forecasting** (`ai_ml/demand_forecasting_model.py`) — per-drug/region time-series
   forecast (statsmodels exponential smoothing) for supply chain planning, with a backtesting
   harness (MAPE/RMSE) to evaluate accuracy before it's trusted.

## Getting started

Full walkthrough in [`docs/SETUP.md`](docs/SETUP.md). Quick version:

```bash
python -m venv venv && source venv/bin/activate
pip install -r ai_ml/requirements.txt
python data_generation/generate_synthetic_data.py
python ai_ml/adverse_event_nlp_classifier.py
python ai_ml/demand_forecasting_model.py
cd dbt/pharma_analytics && dbt build   # requires a configured Redshift/local Postgres target
```

Terraform (`infrastructure/terraform/`) stands up the real AWS resources — S3 buckets, Glue jobs,
Redshift cluster, IAM roles, Lambda. It's written to `plan` cleanly but isn't applied as part of
this repo (no AWS account attached).

## Tech stack

AWS S3 · AWS Glue (PySpark) · AWS Lambda · Amazon Redshift · IAM · Apache Airflow · dbt · Python
(pandas, scikit-learn, statsmodels) · Terraform · GitHub Actions · pytest

## License

MIT — see [`LICENSE`](LICENSE).
