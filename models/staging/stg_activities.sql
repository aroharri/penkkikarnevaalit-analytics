with source as (
    select * from {{ source('raw', 'activities') }}
),

renamed as (
    select
        id              as activity_id,
        user_id,
        activity_type,
        metadata,
        created_at::timestamp as activity_at,
        created_at::date      as activity_date
    from source
)

select * from renamed
