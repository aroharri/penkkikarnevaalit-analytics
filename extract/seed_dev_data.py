"""
Seed the DuckDB raw schema with synthetic development data.

Lets anyone clone this repo and run `dbt build` without Supabase credentials.

Column definitions come from extract/raw_schema.py — the same source the
extract uses when a table returns zero rows. This file holds only rows, in
that module's column order. An earlier version restated the schema here and
got it wrong: it invented a `comments` table and four `user_profiles.target_*`
columns that do not exist, and `dbt build` passed green against a pipeline
that could never have run against production.

Usage:
    python extract/seed_dev_data.py
    dbt build
"""

import logging
import os

import duckdb

try:
    # when imported as a package, e.g. from Dagster
    from extract.raw_schema import RAW_SCHEMA
except ModuleNotFoundError:
    # when run directly as a script, sys.path[0] is extract/ itself
    from raw_schema import RAW_SCHEMA

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DUCKDB_PATH = os.environ.get("DUCKDB_PATH", "warehouse.duckdb")

# Keksityt nimet. Oikeat jasenet ovat vain tuotantodatassa, joka ei ole repossa.
AINO, EERO, SANNI, VAINO, TESTI = "u1", "u2", "u3", "u4", "u5"
CH_MAIN, CH_NEW = "c1", "c2"

# One entry per table in RAW_SCHEMA. Values are rows in RAW_SCHEMA column order.
#
# Brzycki: 1RM = weight * (36 / (37 - reps)). Every estimated_1rm below is
# consistent with the formula so assert_brzycki_1rm_accuracy passes.
# Change one to watch the singular test fire.
FIXTURES = {
    "users": [
        (AINO, "Aino", "aino@example.fi", 140.0, None, True,
         "2026-01-05", "2026-01-05", True, True, 120.0, "2026-01-05", None, True, None),
        (EERO, "Eero", "eero@example.fi", 160.0, None, True,
         "2026-01-06", "2026-01-06", False, True, None, None, None, True, None),
        (SANNI, "Sanni", "sanni@example.fi", 140.0, None, True,
         "2026-01-07", "2026-01-07", False, True, None, None, None, True, None),
        # Member with zero workouts — must not break challenge aggregation
        (VAINO, "Väinö", "vaino@example.fi", 160.0, None, True,
         "2026-01-08", "2026-01-08", False, True, None, None, None, False, None),
        # Inactive user who still has workouts — FK integrity check
        (TESTI, "Testi", "testi@example.fi", 0.0, None, False,
         "2026-01-09", "2026-01-09", False, True, None, None, None, False, None),
    ],
    "workouts": [
        # The apostrophe guards against SQL string-interpolation regressions
        ("w1", AINO, 100.0, 5, 112.5, "hyvä fiilis, ei PR'ää", "Fressi", "2026-02-01", "2026-02-01"),
        ("w2", AINO, 105.0, 5, 118.1, None, "Fressi", "2026-05-10", "2026-05-10"),
        ("w3", AINO, 90.0, 10, 120.0, "kympin sarja", "Fressi", "2026-09-01", "2026-09-01"),
        ("w4", EERO, 80.0, 8, 99.3, None, "SATS", "2026-02-05", "2026-02-05"),
        ("w5", EERO, 130.0, 5, 146.3, None, "SATS", "2026-03-10", "2026-03-10"),
        ("w6", SANNI, 110.0, 7, 132.0, None, "Kotitreeni", "2026-05-03", "2026-05-03"),
        # VAINO has none, deliberately
        ("w7", TESTI, 140.0, 1, 140.0, None, "Fressi", "2026-08-28", "2026-08-28"),
        # reps > 12: allowed by the DB (check is reps <= 100) but outside the
        # Brzycki reliability range, so stg_workouts must filter it out.
        ("w8", AINO, 60.0, 15, 98.2, "korkeatoistoinen", "Fressi", "2026-08-30", "2026-08-30"),
    ],
    "challenges": [
        # Mirrors production: goal_start_kg was set by seed data, not by the app
        (CH_MAIN, "Penkkikarnevaalit 600", 600.0, 530.0, "2026-01-01", "2026-12-27",
         "ABC123", AINO, "active", 10, "2026-01-01"),
        # New-challenge reality: create_challenge never sets goal_start_kg, so
        # it stays at the column default of 0. Its member has a NULL target_1rm,
        # which forces progress_pct onto its goal_kg fallback.
        (CH_NEW, "Uusi haaste", 600.0, 0.0, "2026-06-01", "2026-12-27",
         "XYZ789", TESTI, "active", 10, "2026-06-01"),
    ],
    "challenge_members": [
        # Targets sum to 600, matching CH_MAIN.goal_kg. Only one member has a
        # starting_1rm — same sparsity as production.
        ("m1", CH_MAIN, AINO, "#e63946", "admin", 140.0, 120.0, "2026-01-01", "2026-01-01"),
        ("m2", CH_MAIN, EERO, "#2a9d8f", "member", 160.0, None, None, "2026-01-02"),
        ("m3", CH_MAIN, SANNI, "#457b9d", "member", 140.0, None, None, "2026-01-03"),
        ("m4", CH_MAIN, VAINO, "#f4a261", "member", 160.0, None, None, "2026-01-04"),
        # NULL target — exercises the goal_kg fallback in progress_pct
        ("m5", CH_NEW, TESTI, "#888888", "admin", None, None, None, "2026-06-01"),
    ],
    # Empty in production: profilesService never persists what the onboarding
    # wizard collects. Everything joined from here is NULL.
    "user_profiles": [],
    "activities": [
        ("a1", AINO, "workout_logged", '{"weight_kg": 100, "reps": 5}', "2026-02-01"),
        ("a2", AINO, "pr_achieved", '{"estimated_1rm": 120.0}', "2026-09-01"),
        ("a3", EERO, "workout_logged", '{"weight_kg": 130, "reps": 5}', "2026-03-10"),
        ("a4", SANNI, "milestone", '{"milestone": "first_workout"}', "2026-05-03"),
    ],
    "kudos_reactions": [
        ("k1", "a1", EERO, "fire", "2026-02-01"),
        # Exactly one self-reaction, as in production. The app counts it, so
        # kudos_received must too. kudos_received_excl_self must not.
        ("k2", "a1", AINO, "fire", "2026-02-01"),
        ("k3", "a2", EERO, "clap", "2026-09-01"),
        ("k4", "a3", AINO, "fire", "2026-03-10"),
    ],
    "activity_comments": [
        ("cm1", "a1", EERO, "Hyvä veto!", False, "2026-02-01"),
        ("cm2", "a3", AINO, "Kova suoritus", True, "2026-03-10"),
    ],
    # Empty in production
    "comment_reactions": [],
    # Toinen lahde (Open-Meteo). Kattaa fixturen treenipaivat seka yhden
    # paivan jolta treenia ei ole - liitoksen pitaa kestaa molemmat.
    "weather": [
        ("2026-02-01",  -8.4, -12.1,  0.4, 1.2, 60.29, 25.26),
        ("2026-02-05",  -2.1,  -5.0,  1.1, 0.8, 60.29, 25.26),
        ("2026-03-10",   1.7,  -1.2,  3.2, 0.0, 60.29, 25.26),
        ("2026-05-03",  11.9,   6.4,  0.0, 0.0, 60.29, 25.26),
        ("2026-05-10",  14.2,   8.1,  2.7, 0.0, 60.29, 25.26),
        ("2026-06-15",  18.0,  11.3,  0.0, 0.0, 60.29, 25.26),  # ei treenia
        ("2026-08-28",  16.4,  10.2,  5.1, 0.0, 60.29, 25.26),
        ("2026-08-30",  15.1,   9.7,  0.0, 0.0, 60.29, 25.26),
        ("2026-09-01",  17.2,  11.0,  0.2, 0.0, 60.29, 25.26),
    ],
}


def check_fixtures():
    """Fail loudly if the fixtures have drifted from RAW_SCHEMA.

    Catches the two mistakes this file has actually made: a table that exists
    in one place but not the other, and a row whose field count no longer
    matches the column list.
    """
    missing = set(RAW_SCHEMA) - set(FIXTURES)
    extra = set(FIXTURES) - set(RAW_SCHEMA)
    if missing or extra:
        raise RuntimeError(
            f"FIXTURES and RAW_SCHEMA disagree — missing: {sorted(missing)}, "
            f"unexpected: {sorted(extra)}"
        )

    for table_name, rows in FIXTURES.items():
        expected = len(RAW_SCHEMA[table_name])
        for i, row in enumerate(rows):
            if len(row) != expected:
                raise RuntimeError(
                    f"raw.{table_name} row {i} has {len(row)} values, "
                    f"but RAW_SCHEMA declares {expected} columns"
                )


def create_fixture(con: duckdb.DuckDBPyConnection, table_name: str, rows: list):
    """Create raw.<table_name> from RAW_SCHEMA and insert the fixture rows."""
    columns = RAW_SCHEMA[table_name]
    column_ddl = ", ".join(f"{name} {sql_type}" for name, sql_type in columns)

    con.execute(f"CREATE OR REPLACE TABLE raw.{table_name} ({column_ddl})")

    if rows:
        placeholders = ", ".join("?" * len(columns))
        con.executemany(f"INSERT INTO raw.{table_name} VALUES ({placeholders})", rows)

    logger.info(f"  raw.{table_name}: {len(rows)} rows")


def seed():
    """Replace the raw schema with synthetic development data."""
    check_fixtures()
    logger.info(f"Seeding development data into {DUCKDB_PATH}")

    con = duckdb.connect(DUCKDB_PATH)
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")

    for table_name, rows in FIXTURES.items():
        create_fixture(con, table_name, rows)

    con.close()
    logger.info(f"Done - {len(FIXTURES)} tables seeded. Run `dbt build` next.")


if __name__ == "__main__":
    seed()
