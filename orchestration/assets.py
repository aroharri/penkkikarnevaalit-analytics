"""
Dagster asset definitions for the Penkkikarnevaalit analytics pipeline.

Asset graph:
  extract_supabase → dbt_models (staging → intermediate → marts)

Each asset is observable and materialized independently.
"""

import os
import subprocess
from pathlib import Path

from dagster import (
    asset,
    AssetExecutionContext,
    MaterializeResult,
    MetadataValue,
    Definitions,
    define_asset_job,
    ScheduleDefinition,
    AssetSelection,
)
from dagster_dbt import DbtCliResource, dbt_assets, DbtProject

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_DIR = Path(__file__).resolve().parent.parent
DBT_PROJECT_DIR = PROJECT_DIR
EXTRACT_SCRIPT = PROJECT_DIR / "extract" / "supabase_to_duckdb.py"
PROFILES_DIR = PROJECT_DIR

# ---------------------------------------------------------------------------
# dbt project setup
# ---------------------------------------------------------------------------
dbt_project = DbtProject(
    project_dir=DBT_PROJECT_DIR,
    profiles_dir=PROFILES_DIR,
)

# Parse the dbt project to generate the manifest
# (run `dbt parse` or `dbt compile` first, or let Dagster handle it)
dbt_project.prepare_if_dev()

dbt_resource = DbtCliResource(
    project_dir=DBT_PROJECT_DIR,
    profiles_dir=PROFILES_DIR,
)


# ---------------------------------------------------------------------------
# Asset: Extract from Supabase to DuckDB
# ---------------------------------------------------------------------------
@asset(
    group_name="extract",
    compute_kind="python",
    description="Pull all tables from Supabase into the DuckDB raw schema via paginated API calls.",
)
def extract_supabase(context: AssetExecutionContext) -> MaterializeResult:
    """Run the extraction script: Supabase → DuckDB raw schema."""

    result = subprocess.run(
        ["python", str(EXTRACT_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_DIR),
        env={**os.environ},  # inherits .env vars if loaded
    )

    if result.returncode != 0:
        context.log.error(f"Extraction failed:\n{result.stderr}")
        raise Exception(f"Extraction script failed with code {result.returncode}")

    context.log.info(result.stdout)

    return MaterializeResult(
        metadata={
            "stdout": MetadataValue.text(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout),
        }
    )


# ---------------------------------------------------------------------------
# Asset: dbt models (staging → intermediate → marts)
# ---------------------------------------------------------------------------
@dbt_assets(
    manifest=dbt_project.manifest_path,
    project=dbt_project,
)
def penkkikarnevaalit_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    """
    All dbt models as Dagster assets.

    Dagster-dbt integration automatically:
    - Maps each dbt model to a Dagster asset
    - Respects the dbt DAG (staging → intermediate → marts)
    - Runs dbt tests after materialization
    """
    yield from dbt.cli(["build"], context=context).stream()


# ---------------------------------------------------------------------------
# Job: full pipeline refresh
# ---------------------------------------------------------------------------
full_refresh_job = define_asset_job(
    name="full_pipeline_refresh",
    description="Extract from Supabase, then build all dbt models and run tests.",
    selection=AssetSelection.all(),
)


# ---------------------------------------------------------------------------
# Schedule: daily refresh (optional, for production use)
# ---------------------------------------------------------------------------
daily_refresh_schedule = ScheduleDefinition(
    job=full_refresh_job,
    cron_schedule="0 6 * * *",  # 06:00 UTC daily
    default_status=None,  # disabled by default — enable in Dagster UI
)


# ---------------------------------------------------------------------------
# Definitions
# ---------------------------------------------------------------------------
defs = Definitions(
    assets=[extract_supabase, penkkikarnevaalit_dbt_assets],
    resources={"dbt": dbt_resource},
    jobs=[full_refresh_job],
    schedules=[daily_refresh_schedule],
)
