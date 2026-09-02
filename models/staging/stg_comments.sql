with source as (
    select * from {{ source('raw', 'activity_comments') }}
),

renamed as (
    select
        id              as comment_id,
        activity_id,
        user_id         as commenter_user_id,
        content         as comment_text,
        is_herra,  -- unused: dead column, not referenced anywhere in the app UI
        created_at::timestamp as commented_at
    from source
)

select * from renamed
