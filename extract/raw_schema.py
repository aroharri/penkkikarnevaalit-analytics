"""
Column definitions for the raw schema, matching production Supabase.

Used when a source table returns zero rows. DuckDB's read_json_auto infers
columns from the data, so an empty result gives it nothing to work with —
without this the table would simply not be created, and every downstream
model referencing it would fail with "Table does not exist".

Verified against information_schema on 2026-09-01. Types are approximate:
they only need to be compatible with the casts in the staging models, since
any table that actually has rows gets its real types inferred from the data.

Note that tests/assert_raw_schema_matches_production.sql keeps its own
independent copy of the expected column list on purpose. It is the check on
this file, not a consumer of it — a test that reads its expectations from the
code it is testing cannot fail.
"""

RAW_SCHEMA = {
    "users": [
        ("id", "VARCHAR"), ("name", "VARCHAR"), ("email", "VARCHAR"),
        ("target_1rm", "DOUBLE"), ("fcm_token", "VARCHAR"), ("is_active", "BOOLEAN"),
        ("created_at", "TIMESTAMP"), ("updated_at", "TIMESTAMP"), ("is_admin", "BOOLEAN"),
        ("notifications_enabled", "BOOLEAN"), ("starting_1rm", "DOUBLE"),
        ("starting_1rm_date", "DATE"), ("avatar_url", "VARCHAR"),
        ("email_verified", "BOOLEAN"), ("pending_email", "VARCHAR"),
    ],
    "workouts": [
        ("id", "VARCHAR"), ("user_id", "VARCHAR"), ("weight_kg", "DOUBLE"),
        ("reps", "INTEGER"), ("estimated_1rm", "DOUBLE"), ("comment", "VARCHAR"),
        ("gym_name", "VARCHAR"), ("logged_at", "TIMESTAMP"), ("created_at", "TIMESTAMP"),
    ],
    "challenges": [
        ("id", "VARCHAR"), ("name", "VARCHAR"), ("goal_kg", "DOUBLE"),
        ("goal_start_kg", "DOUBLE"), ("goal_start_date", "DATE"),
        ("goal_end_date", "DATE"), ("invite_code", "VARCHAR"), ("created_by", "VARCHAR"),
        ("status", "VARCHAR"), ("max_members", "INTEGER"), ("created_at", "TIMESTAMP"),
    ],
    "challenge_members": [
        ("id", "VARCHAR"), ("challenge_id", "VARCHAR"), ("user_id", "VARCHAR"),
        ("color", "VARCHAR"), ("role", "VARCHAR"), ("target_1rm", "DOUBLE"),
        ("starting_1rm", "DOUBLE"), ("starting_1rm_date", "DATE"),
        ("joined_at", "TIMESTAMP"),
    ],
    "user_profiles": [
        ("id", "VARCHAR"), ("user_id", "VARCHAR"), ("body_weight_kg", "DOUBLE"),
        ("height_cm", "DOUBLE"), ("birth_year", "INTEGER"),
        ("experience_level", "VARCHAR"), ("onboarding_completed", "BOOLEAN"),
        ("created_at", "TIMESTAMP"), ("updated_at", "TIMESTAMP"),
    ],
    "activities": [
        ("id", "VARCHAR"), ("user_id", "VARCHAR"), ("activity_type", "VARCHAR"),
        ("metadata", "VARCHAR"), ("created_at", "TIMESTAMP"),
    ],
    "kudos_reactions": [
        ("id", "VARCHAR"), ("activity_id", "VARCHAR"), ("user_id", "VARCHAR"),
        ("emoji", "VARCHAR"), ("created_at", "TIMESTAMP"),
    ],
    "activity_comments": [
        ("id", "VARCHAR"), ("activity_id", "VARCHAR"), ("user_id", "VARCHAR"),
        ("content", "VARCHAR"), ("is_herra", "BOOLEAN"), ("created_at", "TIMESTAMP"),
    ],
    "comment_reactions": [
        ("id", "VARCHAR"), ("comment_id", "VARCHAR"), ("user_id", "VARCHAR"),
        ("emoji", "VARCHAR"), ("created_at", "TIMESTAMP"),
    ],
    # Toinen lahde: Open-Meteo. Ei Supabasesta, joten skeemadriftin vahti
    # ei koske tata - sen sarakkeet maaraa tama tiedosto, ei tuotantokanta.
    "weather": [
        ("weather_date", "DATE"), ("temperature_mean_c", "DOUBLE"),
        ("temperature_min_c", "DOUBLE"), ("precipitation_mm", "DOUBLE"),
        ("snowfall_cm", "DOUBLE"), ("latitude", "DOUBLE"), ("longitude", "DOUBLE"),
    ],
}
