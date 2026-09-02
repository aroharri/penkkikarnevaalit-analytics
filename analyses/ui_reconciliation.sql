-- Reconciliation harness: every model number that shares a name with something
-- the app puts on screen, in one result set.
--
-- Usage:
--   dbt compile
--   duckdb warehouse.duckdb < target/compiled/penkkikarnevaalit/analyses/ui_reconciliation.sql
--   ...then compare against the app, and record a dated snapshot in
--   RECONCILIATION.md.
--
-- This lives in analyses/ rather than models/ because it is not part of the
-- DAG: dbt compiles it but never materialises it.
--
-- Why it exists: comparing these numbers against the app found a 78 percentage
-- point error in progress_pct that four review passes and 52 schema tests all
-- missed. Tests prove the pipeline runs; only this proves it is right.

with challenges as (
    select * from {{ ref('dim_challenges') }}
),

challenge_level as (
    select challenge_name as scope, 'Tavoite (goal)'        as ui_label, 'ProgressGauge'   as ui_location, round(goal_total_1rm_kg, 2)::varchar    as model_value from challenges
    union all
    select challenge_name, 'Yhteenlaskettu 1RM',  'ProgressGauge',   round(current_total_1rm_kg, 2)::varchar from challenges
    union all
    select challenge_name, 'To go',               'ProgressGauge',   round(kg_remaining, 2)::varchar         from challenges
    union all
    select challenge_name, 'Edistymis-%',         'ProgressGauge',   progress_pct::varchar                   from challenges
    union all
    select challenge_name, 'Time left (d)',       'Time left -kortti', days_remaining::varchar               from challenges
),

user_level as (
    select
        user_name as scope,
        '1RM nyt' as ui_label,
        'ProfilePage / LifterCard' as ui_location,
        round(current_1rm_kg, 2)::varchar as model_value
    from {{ ref('dim_users') }}
    where lifetime_workouts > 0

    union all

    select user_name, 'Suorituksia', 'RosterPage', lifetime_workouts::varchar
    from {{ ref('dim_users') }}
    where lifetime_workouts > 0

    union all

    select user_name, 'Kudoksia saatu', 'ActivityFeed / KudosBar', kudos_received::varchar
    from {{ ref('dim_users') }}
    where lifetime_workouts > 0
)

select 'challenge' as level, * from challenge_level
union all
select 'user', * from user_level
order by level, scope, ui_label
