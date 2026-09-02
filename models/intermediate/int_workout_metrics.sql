{{
    config(
        description="Each workout enriched with user context, PR flags, and running metrics. The workhorse table for all downstream analysis."
    )
}}

with workouts as (
    select * from {{ ref('stg_workouts') }}
),

users as (
    select * from {{ ref('stg_users') }}
),

profiles as (
    select * from {{ ref('stg_user_profiles') }}
),

-- Toinen lähde. Liitos päivämäärällä, ei avaimella: sää on ominaisuus
-- päivällä, ei treenillä. left join, koska säädata voi loppua ennen
-- viimeisintä treeniä (arkistorajapinta laahaa muutaman päivän).
weather as (
    select * from {{ ref('stg_weather') }}
),

workout_with_context as (
    select
        w.workout_id,
        w.user_id,
        u.user_name,
        w.weight_kg,
        w.reps,
        w.estimated_1rm_kg,
        w.workout_comment,
        w.gym_name,
        w.performed_at,
        w.recorded_at,
        w.workout_date,

        -- Profile context. NULL for every row while user_profiles is empty
        -- in production. Bodyweight is not used anywhere in the app, so
        -- nothing is derived from it here.
        p.body_weight_kg,
        p.experience_level,

        -- Sää treenipäivänä (Open-Meteo). NULL viimeisimmiltä päiviltä:
        -- arkistorajapinta laahaa noin kuusi päivää nykyhetkestä.
        wx.temperature_mean_c,
        wx.temperature_band,
        wx.is_freezing,

        -- Is this a personal record at time of logging?
        -- First workout is always a PR. After that, strictly greater than previous best.
        case
            when row_number() over (partition by w.user_id order by w.performed_at) = 1
                then true
            when w.estimated_1rm_kg > max(w.estimated_1rm_kg) over (
                partition by w.user_id
                order by w.performed_at
                rows between unbounded preceding and 1 preceding
            )
                then true
            else false
        end as is_pr,

        -- Running personal best at this point in time
        max(w.estimated_1rm_kg) over (
            partition by w.user_id
            order by w.performed_at
            rows between unbounded preceding and current row
        ) as running_best_1rm_kg,

        -- Days since previous workout (training consistency)
        w.workout_date - lag(w.workout_date) over (
            partition by w.user_id
            order by w.performed_at
        ) as days_since_last_workout,

        -- Workout sequence number per user
        row_number() over (
            partition by w.user_id
            order by w.performed_at
        ) as workout_number,

        -- 1RM change from previous workout
        w.estimated_1rm_kg - lag(w.estimated_1rm_kg) over (
            partition by w.user_id
            order by w.performed_at
        ) as _1rm_change_kg

    from workouts w
    left join users u on w.user_id = u.user_id
    left join profiles p on w.user_id = p.user_id
    left join weather wx on w.workout_date = wx.weather_date
)

select * from workout_with_context
