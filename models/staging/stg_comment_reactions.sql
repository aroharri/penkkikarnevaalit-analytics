with source as (
    select * from {{ source('raw', 'comment_reactions') }}
),

renamed as (
    select
        id              as comment_reaction_id,
        comment_id,
        user_id         as reactor_user_id,
        emoji,
        created_at::timestamp as reacted_at
    from source
)

select * from renamed
