with source as (
    select * from {{ source('raw', 'challenges') }}
),

renamed as (
    select
        id                  as challenge_id,
        name                as challenge_name,
        goal_kg             as goal_total_1rm_kg,
        goal_start_kg       as baseline_total_1rm_kg,
        goal_start_date::date as challenge_start_date,
        goal_end_date::date   as challenge_end_date,
        invite_code,
        created_by          as creator_user_id,
        status              as challenge_status,
        max_members,
        created_at::timestamp as created_at,

        -- Derived
        goal_end_date::date - goal_start_date::date as challenge_duration_days,
        goal_kg - goal_start_kg as kg_to_gain
    from source
)

select * from renamed
