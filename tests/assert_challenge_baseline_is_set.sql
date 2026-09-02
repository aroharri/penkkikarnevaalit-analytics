{{ config(severity='warn') }}

-- Warns when a challenge has no recorded baseline.
--
-- This is an APP bug, not an analytics one: create_challenge never sets
-- goal_start_kg, and the admin UI exposes no field for it, so every challenge
-- created through the app keeps the column default of 0. Only the original
-- seeded challenge has a real value.
--
-- severity: warn on purpose. A broken input upstream is a signal worth
-- surfacing, not a reason to stop building the marts. No metric in
-- dim_challenges depends on this column.

select
    challenge_id,
    challenge_name,
    baseline_total_1rm_kg
from {{ ref('stg_challenges') }}
where baseline_total_1rm_kg is null
   or baseline_total_1rm_kg = 0
