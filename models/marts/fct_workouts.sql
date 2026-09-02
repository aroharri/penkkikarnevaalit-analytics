{{
    config(
        description="Fact table: every valid bench press set with full context. One row per set. The primary table for BI tools and ad-hoc analysis."
    )
}}

-- Grain: one row per logged bench press set that passes stg_workouts filters.

with workout_metrics as (
    select * from {{ ref('int_workout_metrics') }}
)

select
    workout_id,
    user_id,
    user_name,
    weight_kg,
    reps,
    estimated_1rm_kg,
    experience_level,
    is_pr,
    running_best_1rm_kg,
    round(_1rm_change_kg, 1) as _1rm_change_kg,
    days_since_last_workout,
    workout_number,
    workout_comment,
    gym_name,
    performed_at,
    recorded_at,
    workout_date
from workout_metrics
