{{
    config(
        description="Challenge dimension: goal progress, team composition, engagement health, and standout members. One row per challenge."
    )
}}

-- Grain: one row per challenge.
--
-- This model absorbs what used to be three models at this same grain
-- (int_challenge_progress -> dim_challenges -> metrics_challenge_health).
-- They chained directly into each other and each added only a couple of
-- derived columns, so they earned one model between them, not three.

with challenges as (
    select * from {{ ref('stg_challenges') }}
),

member_progress as (
    select * from {{ ref('int_member_progress') }}
),

-- Team aggregates.
--
-- current_total_1rm_kg sums each member's latest workout 1RM. Members with no
-- workouts contribute nothing, which is exactly what the app does: they never
-- enter the userLatest map in getTeamStats.
team as (
    select
        challenge_id,
        count(membership_id) as member_count,
        count(case when member_role = 'admin' then 1 end) as admin_count,
        coalesce(sum(current_1rm_kg), 0) as current_total_1rm_kg,
        sum(member_target_1rm_kg)        as member_target_total_kg,

        count(case when analytics_engagement_status = 'active' then 1 end)        as active_members,
        count(case when analytics_engagement_status = 'cooling_off' then 1 end)   as cooling_off_members,
        count(case when analytics_engagement_status = 'at_risk' then 1 end)       as at_risk_members,
        count(case when analytics_engagement_status = 'never_trained' then 1 end) as never_trained_members,

        sum(total_workouts)              as total_workouts,
        avg(avg_days_between_workouts)   as avg_training_frequency_days
    from member_progress
    group by challenge_id
),

member_ranked as (
    select
        challenge_id,
        user_name,
        current_1rm_kg,
        _1rm_gained_kg,
        row_number() over (
            partition by challenge_id
            order by current_1rm_kg desc nulls last, user_name
        ) as rank_by_1rm,
        row_number() over (
            partition by challenge_id
            order by _1rm_gained_kg desc nulls last, user_name
        ) as rank_by_improvement
    from member_progress
),

top_performers as (
    select challenge_id, user_name as top_performer_name, current_1rm_kg as top_performer_1rm_kg
    from member_ranked
    where rank_by_1rm = 1
),

most_improved as (
    select challenge_id, user_name as most_improved_name, round(_1rm_gained_kg, 1) as most_improved_kg
    from member_ranked
    where rank_by_improvement = 1
),

-- The goal mirrors the app: the sum of members' personal targets, falling
-- back to challenges.goal_kg when no member has one. In the app this is
-- `members.reduce(...) || challenge.goal_kg` in ChallengeContext.
scored as (
    select
        c.challenge_id,
        c.challenge_name,
        c.challenge_status,
        c.challenge_start_date,
        c.challenge_end_date,
        c.challenge_duration_days,

        coalesce(nullif(t.member_target_total_kg, 0), c.goal_total_1rm_kg) as goal_total_1rm_kg,
        coalesce(t.current_total_1rm_kg, 0)                                as current_total_1rm_kg,

        -- Recorded baseline. Unreliable: create_challenge never sets it, so
        -- it is 0 on every challenge created through the app. Carried for
        -- visibility only — no metric here is derived from it.
        c.baseline_total_1rm_kg,

        coalesce(t.member_count, 0) as member_count,
        coalesce(t.admin_count, 0)  as admin_count,
        coalesce(t.active_members, 0)        as active_members,
        coalesce(t.cooling_off_members, 0)   as cooling_off_members,
        coalesce(t.at_risk_members, 0)       as at_risk_members,
        coalesce(t.never_trained_members, 0) as never_trained_members,

        coalesce(t.total_workouts, 0) as total_workouts,
        round(t.avg_training_frequency_days, 1) as avg_training_frequency_days,

        c.challenge_end_date - current_date as days_remaining,

        case
            when c.challenge_duration_days > 0
            then round((current_date - c.challenge_start_date)::float
                       / c.challenge_duration_days * 100, 1)
        end as time_elapsed_pct
    from challenges c
    left join team t on c.challenge_id = t.challenge_id
),

derived as (
    select
        s.*,

        -- Matches the app's ProgressGauge: current / goal, capped at 100.
        case
            when s.goal_total_1rm_kg is null or s.goal_total_1rm_kg = 0 then null
            else round(least(s.current_total_1rm_kg / s.goal_total_1rm_kg * 100, 100), 1)
        end as progress_pct,

        round(s.goal_total_1rm_kg - s.current_total_1rm_kg, 1) as kg_remaining,

        case
            when s.member_count > 0
            then round(s.active_members::float / s.member_count * 100, 0)
            else 0
        end as engagement_health_pct
    from scored s
)

select
    d.challenge_id,
    d.challenge_name,
    d.challenge_status,
    d.challenge_start_date,
    d.challenge_end_date,
    d.challenge_duration_days,

    -- Goal and progress (app-faithful)
    d.goal_total_1rm_kg,
    d.current_total_1rm_kg,
    d.progress_pct,
    d.kg_remaining,
    d.baseline_total_1rm_kg,

    -- Time
    d.days_remaining,
    d.time_elapsed_pct,

    -- Team
    d.member_count,
    d.admin_count,
    d.active_members,
    d.cooling_off_members,
    d.at_risk_members,
    d.never_trained_members,
    d.engagement_health_pct,

    -- Activity
    d.total_workouts,
    d.avg_training_frequency_days,

    -- Standouts
    tp.top_performer_name,
    tp.top_performer_1rm_kg,
    mi.most_improved_name,
    mi.most_improved_kg,

    -- Analytics-owned scorecard, NOT a UI concept. Compares progress against
    -- elapsed time, which needs only the goal and the dates — deliberately
    -- avoiding the broken goal_start_kg baseline.
    case
        when d.challenge_status = 'archived' then 'ARCHIVED'
        when d.progress_pct is null or d.time_elapsed_pct is null then 'NO_DATA'
        when d.engagement_health_pct >= 70 and d.progress_pct >= d.time_elapsed_pct then 'HEALTHY'
        when d.engagement_health_pct >= 50 or d.progress_pct >= d.time_elapsed_pct then 'WATCH'
        else 'CRITICAL'
    end as overall_health

from derived d
left join top_performers tp on d.challenge_id = tp.challenge_id
left join most_improved mi on d.challenge_id = mi.challenge_id
