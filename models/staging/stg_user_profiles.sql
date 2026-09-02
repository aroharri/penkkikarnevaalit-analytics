with source as (
    select * from {{ source('raw', 'user_profiles') }}
),

renamed as (
    select
        user_id,
        -- body_weight_kg and height_cm have no downstream reader since the
        -- cathedral rank was removed. Kept because they exist in the source.
        body_weight_kg,
        height_cm,
        birth_year,
        experience_level,
        onboarding_completed,
        created_at::timestamp as created_at,
        updated_at::timestamp as updated_at
    from source
)

select * from renamed
