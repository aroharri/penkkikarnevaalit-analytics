-- Singular test: the raw schema must match production Supabase.
--
-- Verified against information_schema on the live project 2026-09-01.
-- 74 columns across 9 tables.
--
-- This is the guard that was missing. Without it, the pipeline referenced a
-- `comments` table and four `user_profiles.target_*` columns that do not
-- exist, and every test still passed because the dev fixture invented them.
--
-- Any row returned means raw and production have diverged: either Supabase
-- changed, or the extract/fixture is wrong. Both need a human.

with expected (table_name, column_name) as (
    values
        -- users
        ('users', 'id'),
        ('users', 'name'),
        ('users', 'email'),
        ('users', 'target_1rm'),
        ('users', 'fcm_token'),
        ('users', 'is_active'),
        ('users', 'created_at'),
        ('users', 'updated_at'),
        ('users', 'is_admin'),
        ('users', 'notifications_enabled'),
        ('users', 'starting_1rm'),
        ('users', 'starting_1rm_date'),
        ('users', 'avatar_url'),
        ('users', 'email_verified'),
        ('users', 'pending_email'),
        -- workouts
        ('workouts', 'id'),
        ('workouts', 'user_id'),
        ('workouts', 'weight_kg'),
        ('workouts', 'reps'),
        ('workouts', 'estimated_1rm'),
        ('workouts', 'comment'),
        ('workouts', 'gym_name'),
        ('workouts', 'logged_at'),
        ('workouts', 'created_at'),
        -- challenges
        ('challenges', 'id'),
        ('challenges', 'name'),
        ('challenges', 'goal_kg'),
        ('challenges', 'goal_start_kg'),
        ('challenges', 'goal_start_date'),
        ('challenges', 'goal_end_date'),
        ('challenges', 'invite_code'),
        ('challenges', 'created_by'),
        ('challenges', 'status'),
        ('challenges', 'max_members'),
        ('challenges', 'created_at'),
        -- challenge_members
        ('challenge_members', 'id'),
        ('challenge_members', 'challenge_id'),
        ('challenge_members', 'user_id'),
        ('challenge_members', 'color'),
        ('challenge_members', 'role'),
        ('challenge_members', 'target_1rm'),
        ('challenge_members', 'starting_1rm'),
        ('challenge_members', 'starting_1rm_date'),
        ('challenge_members', 'joined_at'),
        -- user_profiles
        ('user_profiles', 'id'),
        ('user_profiles', 'user_id'),
        ('user_profiles', 'body_weight_kg'),
        ('user_profiles', 'height_cm'),
        ('user_profiles', 'birth_year'),
        ('user_profiles', 'experience_level'),
        ('user_profiles', 'onboarding_completed'),
        ('user_profiles', 'created_at'),
        ('user_profiles', 'updated_at'),
        -- activities
        ('activities', 'id'),
        ('activities', 'user_id'),
        ('activities', 'activity_type'),
        ('activities', 'metadata'),
        ('activities', 'created_at'),
        -- kudos_reactions
        ('kudos_reactions', 'id'),
        ('kudos_reactions', 'activity_id'),
        ('kudos_reactions', 'user_id'),
        ('kudos_reactions', 'emoji'),
        ('kudos_reactions', 'created_at'),
        -- activity_comments
        ('activity_comments', 'id'),
        ('activity_comments', 'activity_id'),
        ('activity_comments', 'user_id'),
        ('activity_comments', 'content'),
        ('activity_comments', 'is_herra'),
        ('activity_comments', 'created_at'),
        -- comment_reactions
        ('comment_reactions', 'id'),
        ('comment_reactions', 'comment_id'),
        ('comment_reactions', 'user_id'),
        ('comment_reactions', 'emoji'),
        ('comment_reactions', 'created_at')
),

actual as (
    select table_name, column_name
    from information_schema.columns
    where table_schema = 'raw'
      -- weather tulee Open-Meteosta, ei Supabasesta. Sen sarakkeet maarittelee
      -- extract/raw_schema.py, joten tuotantoskeemaan vertaaminen ei koske sita.
      and table_name <> 'weather'
),

missing as (
    select
        e.table_name,
        e.column_name,
        'missing from raw' as problem
    from expected e
    left join actual a
        on e.table_name = a.table_name
       and e.column_name = a.column_name
    where a.column_name is null
),

unexpected as (
    select
        a.table_name,
        a.column_name,
        'unexpected in raw' as problem
    from actual a
    left join expected e
        on a.table_name = e.table_name
       and a.column_name = e.column_name
    where e.column_name is null
)

select * from missing
union all
select * from unexpected
