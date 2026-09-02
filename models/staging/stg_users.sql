with source as (
    select * from {{ source('raw', 'users') }}
),

renamed as (
    select
        id              as user_id,
        name            as user_name,
        email,
        email_verified,
        target_1rm      as personal_target_1rm_kg,
        -- Global fallback baseline. The challenge-context baseline lives in
        -- stg_challenge_members.member_starting_1rm_kg. Unused downstream.
        starting_1rm    as personal_starting_1rm_kg,
        starting_1rm_date::date as personal_starting_1rm_date,
        is_active,
        is_admin,
        avatar_url,
        created_at::timestamp as registered_at,
        updated_at::timestamp as updated_at
    from source
    -- Keep all users to preserve FK integrity with workouts/kudos/comments.
    -- Filter on is_active in downstream models where needed.
)

select * from renamed
