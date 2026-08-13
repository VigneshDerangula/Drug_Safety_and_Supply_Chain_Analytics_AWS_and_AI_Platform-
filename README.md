# PharmaPulse

**An end-to-end AWS data platform for pharma — clinical, safety & commercial data in, AI-driven insight out.**

<img width="1760" height="1000" alt="architecture_diagram" src="https://github.com/user-attachments/assets/7af19da6-fd9f-49e8-aedb-a8ffbd75a849" />


Every day, a pharma company generates clinical trial results, adverse-event reports, shipment
records, and sales data — in different shapes, different systems, different urgency levels. This
is a portfolio build of the platform that pulls all of it together: raw files land in S3, Glue
reshapes them through a medallion pipeline into Redshift, dbt turns curated tables into trusted
marts, and two ML models — an adverse-event severity classifier and a demand forecaster — sit on
top and turn the data into decisions. A parallel Lambda path triages new safety reports the moment
they land, because drug-safety signals can't wait for the nightly batch.

Built to mirror the kind of data engineering work behind pharma analytics teams — the AWS stack,
orchestration, and governed-data practices referenced in Merck & Co.–style Data Engineer job
descriptions: **S3, Glue, Lambda, Redshift, IAM, Airflow, dbt, CI/CD, and applied ML on top of it
all.**

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
# PharmaPulse

**An end-to-end AWS data platform for pharma — clinical, safety & commercial data in, AI-driven insight out.**

<img width="264" height="150" alt="architecture_diagram" src="https://github.com/user-attachments/assets/19900544-7029-4dbe-bab3-0c9e92a47f4a" />


Every day, a pharma company generates clinical trial results, adverse-event reports, shipment
records, and sales data — in different shapes, different systems, different urgency levels. This
is a portfolio build of the platform that pulls all of it together: raw files land in S3, Glue
reshapes them through a medallion pipeline into Redshift, dbt turns curated tables into trusted
marts, and two ML models — an adverse-event severity classifier and a demand forecaster — sit on
top and turn the data into decisions. A parallel Lambda path triages new safety reports the moment
they land, because drug-safety signals can't wait for the nightly batch.

Built to mirror the kind of data engineering work behind pharma analytics teams — the AWS stack,
orchestration, and governed-data practices referenced in Merck & Co.–style Data Engineer job
descriptions: **S3, Glue, Lambda, Redshift, IAM, Airflow, dbt, CI/CD, and applied ML on top of it
all.**

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

<p align="center">
  <img src="architecture/assets/architecture_diagram.svg" alt="PharmaPulse architecture diagram: source systems flow into an S3 raw zone, through AWS Glue PySpark jobs into staging and curated S3 zones, into Redshift, through dbt into an AI/ML layer (adverse event NLP classifier and demand forecasting), and out to a BI layer. A parallel Lambda and SNS path handles real-time adverse-event triage. Apache Airflow orchestrates the daily batch DAG, and GitHub Actions runs CI." width="100%">
</p>

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
