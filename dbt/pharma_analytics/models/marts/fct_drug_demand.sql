{{ config(materialized="table") }}

select
    drug_code,
    region,
    ship_month,
    units_shipped,
    units_sold,
    supply_demand_variance,
    case
        when units_sold = 0 then null
        else round(100.0 * supply_demand_variance / units_sold, 2)
    end as variance_pct_of_sales
from {{ ref("stg_supply_demand") }}
