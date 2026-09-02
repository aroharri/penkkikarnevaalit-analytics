with source as (
    select * from {{ source('raw', 'kudos_reactions') }}
),

renamed as (
    select
        id              as kudos_id,
        activity_id,
        user_id         as reactor_user_id,
        emoji,
        created_at::timestamp as reacted_at
    from source
)

select * from renamed
