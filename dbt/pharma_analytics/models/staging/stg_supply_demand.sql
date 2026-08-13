with source as (
    select * from {{ source("raw", "supply_demand") }}
)

select
    drug_code,
    region,
    ship_month,
    coalesce(units_shipped, 0) as units_shipped,
    coalesce(units_sold, 0)    as units_sold,
    supply_demand_variance
from source
where drug_code is not null
