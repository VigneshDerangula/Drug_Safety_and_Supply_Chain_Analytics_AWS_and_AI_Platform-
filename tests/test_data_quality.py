"""
Data-quality checks for the synthetic pharma datasets. These stand in for
the kind of contract tests you'd run in CI before data ever reaches Glue —
catch schema drift and obviously bad rows before they cost a pipeline run.

Run with: pytest tests/ -v
(Assumes data_generation/generate_synthetic_data.py has already been run.)
"""
import os

import pandas as pd
import pytest

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

VALID_SEVERITIES = {"mild", "moderate", "severe", "life-threatening"}
VALID_REGIONS = {"North America", "EMEA", "APAC", "Latin America"}


@pytest.fixture(scope="module")
def clinical_trials():
    return pd.read_csv(os.path.join(DATA_DIR, "clinical_trials.csv"))


@pytest.fixture(scope="module")
def adverse_events():
    return pd.read_csv(os.path.join(DATA_DIR, "adverse_events.csv"))


@pytest.fixture(scope="module")
def drug_shipments():
    return pd.read_csv(os.path.join(DATA_DIR, "drug_shipments.csv"))


@pytest.fixture(scope="module")
def drug_sales():
    return pd.read_csv(os.path.join(DATA_DIR, "drug_sales.csv"))


class TestClinicalTrials:
    def test_trial_id_unique_and_present(self, clinical_trials):
        assert clinical_trials["trial_id"].notna().all()
        assert clinical_trials["trial_id"].is_unique

    def test_enrolled_patients_non_negative(self, clinical_trials):
        assert (clinical_trials["enrolled_patients"] >= 0).all()

    def test_region_values_valid(self, clinical_trials):
        assert set(clinical_trials["region"].unique()).issubset(VALID_REGIONS)


class TestAdverseEvents:
    def test_case_id_unique_and_present(self, adverse_events):
        assert adverse_events["case_id"].notna().all()
        assert adverse_events["case_id"].is_unique

    def test_severity_label_in_allowed_set(self, adverse_events):
        assert set(adverse_events["severity_label"].unique()).issubset(VALID_SEVERITIES)

    def test_patient_age_in_plausible_range(self, adverse_events):
        assert adverse_events["patient_age"].between(0, 120).all()

    def test_serious_flag_consistent_with_severity(self, adverse_events):
        serious_rows = adverse_events[adverse_events["severity_label"].isin(["severe", "life-threatening"])]
        assert serious_rows["serious_flag"].all()


class TestDrugShipments:
    def test_shipment_id_unique(self, drug_shipments):
        assert drug_shipments["shipment_id"].is_unique

    def test_quantity_units_positive(self, drug_shipments):
        assert (drug_shipments["quantity_units"] > 0).all()

    def test_no_orphan_drug_codes(self, drug_shipments, drug_sales):
        shipped_codes = set(drug_shipments["drug_code"].unique())
        sold_codes = set(drug_sales["drug_code"].unique())
        # every drug that shipped should also appear in the commercial sales feed
        assert shipped_codes.issubset(sold_codes)


class TestDrugSales:
    def test_no_negative_revenue(self, drug_sales):
        assert (drug_sales["revenue_usd"] >= 0).all()

    def test_units_sold_non_negative(self, drug_sales):
        assert (drug_sales["units_sold"] >= 0).all()

    def test_sales_month_is_month_start(self, drug_sales):
        months = pd.to_datetime(drug_sales["sales_month"])
        assert (months.dt.day == 1).all()
