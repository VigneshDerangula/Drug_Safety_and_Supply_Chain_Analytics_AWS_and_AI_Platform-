{{ config(materialized="table") }}

select
    case_id,
    drug_code,
    report_date,
    date_trunc("month", report_date)::date as report_month,
    region,
    country,
    severity_label,
    serious_flag,
    is_pediatric,
    is_geriatric,
    active_trial_count,
    outcome
from {{ ref("stg_adverse_events") }}
