{{ config(severity='warn') }}

-- Singular test: verify that the app's estimated_1rm matches
-- our independent Brzycki calculation within 0.5 kg tolerance.
--
-- Any rows returned here indicate a mismatch between the app's
-- 1RM calculation and the Brzycki formula. This could signal
-- a formula change in the app or data corruption.
--
-- severity: warn. Formula drift is a signal, not a reason to leave every
-- downstream mart unbuilt: at severity error a single bad row skipped 31
-- nodes and produced no marts at all.

select
    workout_id,
    weight_kg,
    reps,
    estimated_1rm_kg,
    calculated_1rm_kg,
    abs(estimated_1rm_kg - calculated_1rm_kg) as drift_kg
from {{ ref('stg_workouts') }}
where abs(estimated_1rm_kg - calculated_1rm_kg) > 0.5
   or estimated_1rm_kg is null
