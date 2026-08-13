{{ config(materialized="table") }}

with ae as (
    select distinct drug_code, drug_name
    from {{ ref("stg_adverse_events") }}
),
sd as (
    select distinct drug_code
    from {{ ref("stg_supply_demand") }}
)

select
    coalesce(ae.drug_code, sd.drug_code) as drug_code,
    ae.drug_name
from ae
full outer join sd on ae.drug_code = sd.drug_code
