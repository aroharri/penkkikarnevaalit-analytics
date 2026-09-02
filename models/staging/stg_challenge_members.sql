with source as (
    select * from {{ source('raw', 'challenge_members') }}
),

renamed as (
    select
        id              as membership_id,
        challenge_id,
        user_id,
        color           as display_color,
        role            as member_role,
        target_1rm      as member_target_1rm_kg,
        starting_1rm    as member_starting_1rm_kg,
        starting_1rm_date::date as starting_1rm_date,
        joined_at::timestamp    as joined_at
    from source
)

select * from renamed
