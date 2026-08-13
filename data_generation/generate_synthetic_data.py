"""
generate_synthetic_data.py

Generates synthetic (non-real) pharma datasets that mirror the shape of common
industry sources, so the rest of the pipeline (Glue -> Redshift -> dbt -> AI/ML)
has something realistic to run against:

  - clinical_trials.csv   : trial/site/phase records, ClinicalTrials.gov-like
  - adverse_events.csv    : FAERS-like individual case safety reports (ICSRs)
  - drug_shipments.csv    : logistics/ERP shipment records
  - drug_sales.csv        : monthly commercial sales by drug/region

Usage:
    python generate_synthetic_data.py [--rows-multiplier 1] [--seed 42]

Output: writes CSVs to ./data/
"""
import argparse
import os
import random
from datetime import datetime, timedelta

import pandas as pd

DRUGS = [
    ("MRK-1001", "Cardiozin", "Cardiology"),
    ("MRK-1002", "Oncavera", "Oncology"),
    ("MRK-1003", "Immunext", "Immunology"),
    ("MRK-1004", "Glucostat", "Endocrinology"),
    ("MRK-1005", "Neuroplex", "Neurology"),
    ("MRK-1006", "Vaxishield", "Vaccines"),
    ("MRK-1007", "Pulmocare", "Respiratory"),
    ("MRK-1008", "Dermalyx", "Dermatology"),
]

REGIONS = ["North America", "EMEA", "APAC", "Latin America"]
COUNTRIES = {
    "North America": ["USA", "Canada", "Mexico"],
    "EMEA": ["Germany", "UK", "France", "South Africa"],
    "APAC": ["Japan", "India", "Australia", "South Korea"],
    "Latin America": ["Brazil", "Argentina", "Chile"],
}
TRIAL_PHASES = ["Phase I", "Phase II", "Phase III", "Phase IV"]
TRIAL_STATUS = ["Recruiting", "Active", "Completed", "Terminated", "Suspended"]

SEVERITY_TERMS = {
    "mild": [
        "patient reported mild headache after dose, resolved without treatment",
        "slight nausea noted, self-limiting, no intervention required",
        "minor injection site redness, resolved within 24 hours",
    ],
    "moderate": [
        "patient experienced moderate dizziness requiring dose adjustment",
        "elevated liver enzymes observed, drug temporarily paused, monitored",
        "moderate rash across forearms, antihistamine administered",
    ],
    "severe": [
        "patient hospitalized for severe allergic reaction, drug discontinued",
        "severe cardiac arrhythmia reported, emergency care administered",
        "significant drop in blood pressure requiring ICU observation",
    ],
    "life-threatening": [
        "patient experienced anaphylaxis, life-threatening, emergency resuscitation performed",
        "life-threatening respiratory failure reported, patient intubated",
        "cardiac arrest reported shortly after administration, resuscitated, drug withdrawn",
    ],
}
SEVERITY_WEIGHTS = {"mild": 0.55, "moderate": 0.28, "severe": 0.13, "life-threatening": 0.04}


def _rand_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))


def gen_clinical_trials(n: int) -> pd.DataFrame:
    rows = []
    start_range = datetime(2019, 1, 1)
    end_range = datetime(2026, 6, 1)
    for i in range(n):
        drug = random.choice(DRUGS)
        region = random.choice(REGIONS)
        country = random.choice(COUNTRIES[region])
        start_date = _rand_date(start_range, end_range)
        enrolled = random.randint(20, 1200)
        rows.append(
            {
                "trial_id": f"NCT{100000 + i}",
                "drug_code": drug[0],
                "drug_name": drug[1],
                "therapeutic_area": drug[2],
                "phase": random.choice(TRIAL_PHASES),
                "status": random.choice(TRIAL_STATUS),
                "site_country": country,
                "region": region,
                "start_date": start_date.date().isoformat(),
                "estimated_completion_date": (start_date + timedelta(days=random.randint(180, 1500))).date().isoformat(),
                "enrolled_patients": enrolled,
                "primary_endpoint_met": random.choice([True, False, None]),
            }
        )
    return pd.DataFrame(rows)


def gen_adverse_events(n: int) -> pd.DataFrame:
    rows = []
    start_range = datetime(2022, 1, 1)
    end_range = datetime(2026, 8, 1)
    for i in range(n):
        drug = random.choice(DRUGS)
        region = random.choice(REGIONS)
        country = random.choice(COUNTRIES[region])
        severity = random.choices(list(SEVERITY_WEIGHTS.keys()), weights=list(SEVERITY_WEIGHTS.values()))[0]
        narrative = random.choice(SEVERITY_TERMS[severity])
        report_date = _rand_date(start_range, end_range)
        rows.append(
            {
                "case_id": f"AE{200000 + i}",
                "drug_code": drug[0],
                "drug_name": drug[1],
                "report_date": report_date.date().isoformat(),
                "patient_age": random.randint(2, 92),
                "patient_sex": random.choice(["M", "F", "U"]),
                "country": country,
                "region": region,
                "reporter_type": random.choice(["Physician", "Pharmacist", "Consumer", "Other HCP"]),
                "narrative": narrative,
                "severity_label": severity,  # ground truth, used to train/eval the classifier
                "outcome": random.choice(
                    ["Recovered", "Recovering", "Not Recovered", "Recovered with Sequelae", "Fatal", "Unknown"]
                ),
                "serious_flag": severity in ("severe", "life-threatening"),
            }
        )
    return pd.DataFrame(rows)


def gen_drug_shipments(n: int) -> pd.DataFrame:
    rows = []
    start_range = datetime(2024, 1, 1)
    end_range = datetime(2026, 8, 1)
    for i in range(n):
        drug = random.choice(DRUGS)
        region = random.choice(REGIONS)
        country = random.choice(COUNTRIES[region])
        ship_date = _rand_date(start_range, end_range)
        qty = random.randint(500, 50000)
        rows.append(
            {
                "shipment_id": f"SHP{300000 + i}",
                "drug_code": drug[0],
                "drug_name": drug[1],
                "origin_facility": random.choice(["NJ-Plant-01", "Ireland-Plant-02", "Singapore-Plant-03"]),
                "destination_country": country,
                "region": region,
                "ship_date": ship_date.date().isoformat(),
                "quantity_units": qty,
                "batch_id": f"BATCH-{random.randint(10000,99999)}",
                "cold_chain_required": drug[2] in ("Vaccines", "Immunology"),
                "delivery_status": random.choice(["Delivered", "In Transit", "Delayed", "Customs Hold"]),
            }
        )
    return pd.DataFrame(rows)


def gen_drug_sales(n_months: int = 30) -> pd.DataFrame:
    rows = []
    base_month = datetime(2024, 1, 1)
    for m in range(n_months):
        month = (base_month + timedelta(days=30 * m)).strftime("%Y-%m-01")
        for drug in DRUGS:
            for region in REGIONS:
                seasonal = 1 + 0.15 * ((m % 12) / 12)
                trend = 1 + 0.01 * m
                noise = random.uniform(0.85, 1.15)
                base_units = random.randint(8000, 60000)
                units = int(base_units * seasonal * trend * noise)
                rows.append(
                    {
                        "sales_month": month,
                        "drug_code": drug[0],
                        "drug_name": drug[1],
                        "region": region,
                        "units_sold": units,
                        "revenue_usd": round(units * random.uniform(12.0, 220.0), 2),
                    }
                )
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows-multiplier", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)

    trials = gen_clinical_trials(300 * args.rows_multiplier)
    events = gen_adverse_events(2000 * args.rows_multiplier)
    shipments = gen_drug_shipments(1500 * args.rows_multiplier)
    sales = gen_drug_sales(30)

    trials.to_csv(os.path.join(out_dir, "clinical_trials.csv"), index=False)
    events.to_csv(os.path.join(out_dir, "adverse_events.csv"), index=False)
    shipments.to_csv(os.path.join(out_dir, "drug_shipments.csv"), index=False)
    sales.to_csv(os.path.join(out_dir, "drug_sales.csv"), index=False)

    print(f"Wrote {len(trials)} clinical trial rows")
    print(f"Wrote {len(events)} adverse event rows")
    print(f"Wrote {len(shipments)} shipment rows")
    print(f"Wrote {len(sales)} sales rows")
    print(f"Output directory: {os.path.abspath(out_dir)}")


if __name__ == "__main__":
    main()
