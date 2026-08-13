with source as (
    select * from {{ source("raw", "adverse_events") }}
)

select
    case_id,
    drug_code,
    drug_name,
    report_date,
    patient_age,
    patient_sex,
    country,
    region,
    reporter_type,
    narrative,
    severity_label,
    outcome,
    serious_flag,
    active_trial_count,
    is_pediatric,
    is_geriatric
from source
where case_id is not null
