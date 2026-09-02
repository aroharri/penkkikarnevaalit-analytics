with source as (
    select * from {{ source('open_meteo', 'weather') }}
),

renamed as (
    select
        weather_date::date  as weather_date,
        temperature_mean_c,
        temperature_min_c,
        precipitation_mm,
        snowfall_cm,

        -- Johdetut luokat. Rajat ovat analytiikan omia, eivät sovelluksen:
        -- sovelluksessa ei ole säätä lainkaan.
        case
            when temperature_mean_c < -10 then 'kova pakkanen'
            when temperature_mean_c <   0 then 'pakkanen'
            when temperature_mean_c <  10 then 'viileä'
            when temperature_mean_c <  20 then 'leuto'
            else                               'lämmin'
        end as temperature_band,

        temperature_mean_c < 0 as is_freezing
    from source
)

select * from renamed
