{{
    config(
        description="User dimension with lifetime stats and social engagement. One row per user, active and inactive."
    )
}}

-- Grain: one row per row in stg_users.

with users as (
    select * from {{ ref('stg_users') }}
),

profiles as (
    select * from {{ ref('stg_user_profiles') }}
),

workout_stats as (
    select
        user_id,
        count(*)              as lifetime_workouts,
        min(workout_date)     as first_workout_date,
        max(workout_date)     as last_workout_date,
        max(estimated_1rm_kg) as all_time_best_1rm_kg,
        avg(estimated_1rm_kg) as avg_1rm_kg,
        count(case when is_pr then 1 end) as total_prs,
        -- Current 1RM = most recent workout's 1RM. This matches the app:
        -- "1RM nyt" is the latest logged set, not the all-time best.
        last(estimated_1rm_kg order by performed_at) as current_1rm_kg
    from {{ ref('int_workout_metrics') }}
    group by user_id
),

kudos_given as (
    select reactor_user_id as user_id, count(*) as kudos_given_count
    from {{ ref('stg_kudos') }}
    group by reactor_user_id
),

-- Kudos received = reactions on activities this user owns.
-- Self-reactions ARE counted, because the app counts them: toggle_kudos has
-- no self-check and KudosBar renders every reaction. A "cleaner" number that
-- disagrees with the screen is the wrong number.
kudos_received as (
    select
        a.user_id,
        count(*) as kudos_received_count,
        count(case when k.reactor_user_id != a.user_id then 1 end) as kudos_received_excl_self_count
    from {{ ref('stg_kudos') }} k
    inner join {{ ref('stg_activities') }} a on k.activity_id = a.activity_id
    group by a.user_id
),

comments_written as (
    select commenter_user_id as user_id, count(*) as comments_count
    from {{ ref('stg_comments') }}
    group by commenter_user_id
),

comment_reactions_given as (
    select reactor_user_id as user_id, count(*) as comment_reactions_count
    from {{ ref('stg_comment_reactions') }}
    group by reactor_user_id
)

select
    u.user_id,
    u.user_name,
    -- email intentionally excluded from marts (PII)
    u.is_active,
    u.registered_at,
    u.avatar_url,

    -- Profile attributes. NULL for every user while user_profiles is empty
    -- in production; they populate if onboarding starts persisting them.
    p.body_weight_kg,
    p.height_cm,
    p.experience_level,

    -- Strength
    coalesce(ws.current_1rm_kg, 0)           as current_1rm_kg,
    ws.all_time_best_1rm_kg,
    round(ws.avg_1rm_kg, 1)                  as avg_1rm_kg,

    -- Activity
    coalesce(ws.lifetime_workouts, 0) as lifetime_workouts,
    ws.total_prs,
    ws.first_workout_date,
    ws.last_workout_date,
    current_date - ws.last_workout_date as days_since_last_workout,

    -- Tenure
    current_date - u.registered_at::date as days_since_registration,

    -- Social engagement
    coalesce(kg.kudos_given_count, 0)    as kudos_given,
    coalesce(kr.kudos_received_count, 0) as kudos_received,
    coalesce(kr.kudos_received_excl_self_count, 0) as kudos_received_excl_self,
    coalesce(cw.comments_count, 0)       as comments_written,
    coalesce(cr.comment_reactions_count, 0) as comment_reactions_given,
    coalesce(kg.kudos_given_count, 0)
        + coalesce(cw.comments_count, 0)
        + coalesce(cr.comment_reactions_count, 0) as total_social_actions

from users u
left join profiles p on u.user_id = p.user_id
left join workout_stats ws on u.user_id = ws.user_id
left join kudos_given kg on u.user_id = kg.user_id
left join kudos_received kr on u.user_id = kr.user_id
left join comments_written cw on u.user_id = cw.user_id
left join comment_reactions_given cr on u.user_id = cr.user_id
