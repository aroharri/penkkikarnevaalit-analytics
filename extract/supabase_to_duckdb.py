"""
Extract data from Supabase (Postgres) and load into DuckDB raw schema.

Full extract-load — no transformations. That's dbt's job.
"""

import json
import logging
import os
import tempfile
from datetime import datetime, timezone

import duckdb
from dotenv import load_dotenv
from supabase import create_client

try:
    # when imported as a package, e.g. from Dagster
    from extract.raw_schema import RAW_SCHEMA
except ModuleNotFoundError:
    # when run directly as a script, sys.path[0] is extract/ itself
    from raw_schema import RAW_SCHEMA

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
DUCKDB_PATH = os.environ.get("DUCKDB_PATH", "warehouse.duckdb")

# Tables to extract — order matters for foreign keys but not for EL
TABLES = [
    "users",
    "workouts",
    "challenges",
    "challenge_members",
    "user_profiles",
    "activities",
    "kudos_reactions",
    "activity_comments",
    "comment_reactions",
]


def extract_table(supabase, table_name: str) -> list[dict]:
    """Pull all rows from a Supabase table. Handles pagination."""
    all_rows = []
    page_size = 1000
    offset = 0

    while True:
        response = (
            supabase.table(table_name)
            .select("*")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = response.data
        all_rows.extend(rows)

        if len(rows) < page_size:
            break
        offset += page_size

    return all_rows


def _json_to_duckdb(con: duckdb.DuckDBPyConnection, data: list[dict], target_table: str):
    """Write JSON data to a DuckDB table via temp file (avoids SQL injection)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        tmp_path = f.name

    # Normalize path separators for Windows compatibility
    tmp_path = tmp_path.replace("\\", "/")

    try:
        con.execute(f"""
            CREATE OR REPLACE TABLE {target_table} AS
            SELECT * FROM read_json_auto('{tmp_path}')
        """)
    finally:
        os.unlink(tmp_path)


def create_empty_table(con: duckdb.DuckDBPyConnection, table_name: str):
    """Create an empty raw table with the production column list.

    A source table can legitimately have zero rows (user_profiles and
    comment_reactions both do). read_json_auto cannot infer columns from an
    empty result, so the table has to be declared explicitly — otherwise it is
    never created and every downstream model referencing it fails.

    CREATE OR REPLACE matters here: it also clears a table left behind by an
    earlier run, so an empty source can never be masked by stale rows.
    """
    columns = RAW_SCHEMA.get(table_name)
    if not columns:
        raise RuntimeError(
            f"{table_name} returned no rows and has no entry in RAW_SCHEMA, "
            "so the empty table cannot be created. Add it to extract/raw_schema.py."
        )

    column_ddl = ", ".join(f"{name} {sql_type}" for name, sql_type in columns)
    con.execute(f"CREATE OR REPLACE TABLE raw.{table_name} ({column_ddl})")


def load_to_duckdb(con: duckdb.DuckDBPyConnection, table_name: str, rows: list[dict]):
    """Load rows into DuckDB raw schema. Full replace on each run."""
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")

    if not rows:
        create_empty_table(con, table_name)
        logger.warning(f"  raw.{table_name}: 0 rows — empty table created")
        return

    _json_to_duckdb(con, rows, f"raw.{table_name}")

    count = con.execute(f"SELECT count(*) FROM raw.{table_name}").fetchone()[0]
    logger.info(f"  raw.{table_name}: {count} rows")


def extract_and_load():
    """Run the full extract-load pipeline."""
    started_at = datetime.now(timezone.utc)
    logger.info(f"Starting extract at {started_at.isoformat()}")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    con = duckdb.connect(DUCKDB_PATH)

    # Track extraction metadata
    extraction_log = []

    for table_name in TABLES:
        try:
            logger.info(f"Extracting {table_name}...")
            rows = extract_table(supabase, table_name)
            load_to_duckdb(con, table_name, rows)
            extraction_log.append({
                "table_name": table_name,
                "row_count": len(rows),
                "status": "success",
                "extracted_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as e:
            logger.error(f"  FAILED: {table_name} — {e}")
            extraction_log.append({
                "table_name": table_name,
                "row_count": 0,
                "status": f"error: {e}",
                "extracted_at": datetime.now(timezone.utc).isoformat(),
            })

    # Write extraction metadata to DuckDB for observability
    con.execute("CREATE SCHEMA IF NOT EXISTS meta")
    _json_to_duckdb(con, extraction_log, "meta.extraction_log")

    con.close()

    elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
    logger.info(f"Done in {elapsed:.1f}s — {len(extraction_log)} tables extracted")

    # Fail loudly so Dagster marks the asset as failed
    failed = [e for e in extraction_log if e["status"] != "success"]
    if failed:
        raise RuntimeError(
            f"Extract failed for {len(failed)} table(s): "
            f"{[e['table_name'] for e in failed]}"
        )


if __name__ == "__main__":
    extract_and_load()
