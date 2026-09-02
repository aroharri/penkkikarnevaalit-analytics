{{
    config(
        description="Each challenge member's current progress — latest 1RM, total workouts, consistency metrics, and distance to personal target."
    )
}}

with members as (
    select * from {{ ref('stg_challenge_members') }}
),

users as (
    select * from {{ ref('stg_users') }}
),

workouts as (
    select * from {{ ref('stg_workouts') }}
),

challenges as (
    select * from {{ ref('stg_challenges') }}
),

-- Latest workout per member (current 1RM)
latest_workout as (
    select
        user_id,
        estimated_1rm_kg as current_1rm_kg,
        workout_date     as last_workout_date,
        performed_at     as last_workout_at
    from (
        select
            *,
            row_number() over (partition by user_id order by performed_at desc) as rn
        from workouts
    )
    where rn = 1
),

-- Workout stats per member
workout_stats as (
    select
        user_id,
        count(*)                    as total_workouts,
        max(estimated_1rm_kg)       as all_time_best_1rm_kg,
        min(workout_date)           as first_workout_date,
        max(workout_date)           as last_workout_date,
        avg(estimated_1rm_kg)       as avg_1rm_kg,
        -- Consistency: avg days between workouts
        case
            when count(*) > 1
            then (max(workout_date) - min(workout_date))::float / (count(*) - 1)
            else null
        end as avg_days_between_workouts
    from workouts
    group by user_id
),

member_progress as (
    select
        m.membership_id,
        m.challenge_id,
        m.user_id,
        u.user_name,
        m.member_role,
        m.display_color,
        m.member_starting_1rm_kg,
        m.member_target_1rm_kg,
        m.joined_at,

        -- Challenge context
        c.challenge_name,
        c.challenge_end_date,

        -- Current state
        lw.current_1rm_kg,
        lw.last_workout_date,
        lw.last_workout_at,

        -- Progress
        coalesce(lw.current_1rm_kg, 0) - coalesce(m.member_starting_1rm_kg, 0) as _1rm_gained_kg,

        case
            when m.member_target_1rm_kg > 0 and m.member_starting_1rm_kg > 0
            then round(
                (coalesce(lw.current_1rm_kg, 0) - m.member_starting_1rm_kg)::float
                / nullif(m.member_target_1rm_kg - m.member_starting_1rm_kg, 0)
                * 100, 1
            )
            else null
        end as progress_pct,

        -- Activity stats
        coalesce(ws.total_workouts, 0) as total_workouts,
        ws.all_time_best_1rm_kg,
        ws.avg_1rm_kg,
        ws.avg_days_between_workouts,

        -- Days since last activity
        current_date - lw.last_workout_date as days_inactive,

        -- Risk flag: no workout in 14+ days
        case
            when lw.last_workout_date is null then 'never_trained'
            when current_date - lw.last_workout_date > 14 then 'at_risk'
            when current_date - lw.last_workout_date > 7 then 'cooling_off'
            else 'active'
        -- Analytics-owned, NOT a UI concept. The app's WeeklyRecap shows a
        -- two-state split over a 7-day window ("Palvellut" / "Kadonneet
        -- lampaat"); this is a richer four-state view.
        end as analytics_engagement_status

    from members m
    left join users u on m.user_id = u.user_id
    left join latest_workout lw on m.user_id = lw.user_id
    left join workout_stats ws on m.user_id = ws.user_id
    left join challenges c on m.challenge_id = c.challenge_id
)

select * from member_progress
