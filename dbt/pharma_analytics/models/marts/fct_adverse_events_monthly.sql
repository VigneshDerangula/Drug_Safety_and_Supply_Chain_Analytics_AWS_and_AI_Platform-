{{ config(materialized="table") }}

select
    drug_code,
    region,
    date_trunc("month", report_date)::date as report_month,
    count(*)                                        as total_events,
    sum(case when serious_flag then 1 else 0 end)   as serious_events,
    sum(case when severity_label = "life-threatening" then 1 else 0 end) as life_threatening_events,
    round(100.0 * sum(case when serious_flag then 1 else 0 end) / nullif(count(*), 0), 2) as pct_serious
from {{ ref("stg_adverse_events") }}
group by 1, 2, 3
