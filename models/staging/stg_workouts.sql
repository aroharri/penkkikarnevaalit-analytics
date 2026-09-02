with source as (
    select * from {{ source('raw', 'workouts') }}
),

renamed as (
    select
        id                  as workout_id,
        user_id,
        weight_kg,
        reps,
        estimated_1rm       as estimated_1rm_kg,
        comment             as workout_comment,
        gym_name,
        logged_at::timestamp as performed_at,
        created_at::timestamp as recorded_at,

        -- Derived: validate Brzycki formula
        -- weight_kg * (36.0 / (37.0 - reps)) = estimated_1rm
        round(weight_kg * (36.0 / (37.0 - reps)), 1) as calculated_1rm_kg,

        -- Workout date (without time) for daily aggregations
        logged_at::date     as workout_date
    from source
    where reps > 0 and reps <= 12  -- Brzycki formula reliable range
      and weight_kg > 0
)

select * from renamed
