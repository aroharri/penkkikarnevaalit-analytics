"""
Dagster-orkestrointi Penkkikarnevaalit-analytiikalle.

    raw_supabase  ->  raw_weather  ->  dbt_models  ->  haastemittaristo

Nelja assettia ketjussa. Jokainen ajaa oman komentonsa PipesSubprocessClientilla,
joka on Dagsterin dokumentoitu tapa ajaa työtä tämän prosessin ulkopuolella.

Miksi ei dagster-dbt:

    dagster-dbt antaisi jokaisesta dbt-mallista oman assetin ja dbt-testeistä
    asset checkit. Se ei kuitenkaan asennu Python 3.14:lle: paketin metadata
    rajaa `Requires-Python >=3.10,<3.14` (dagster-dbt 0.29.20, 27.8.2026).
    Rajaus on peräisin ajalta jolloin dbt-core ei tukenut 3.14:ää — dbt-core
    1.12 tukee sitä nykyään, mutta Dagsterin kattoa ei ole päivitetty.
    Seurattavana GitHub-issuessa dagster-io/dagster#33903.

    Hinta: dbt-ajo näkyy yhtenä assettina eikä neljänätoista. Riippuvuudet
    mallien välillä hoitaa dbt itse, joten ajojärjestys on silti oikea.

Ajaminen:

    dagster dev                     käyttöliittymä selaimessa
    dagster asset materialize --select "*"      koko ketju kerralla
"""

import sys
from pathlib import Path

import dagster as dg

PROJECT_DIR = Path(__file__).resolve().parent.parent

# sys.executable osoittaa siihen Pythoniin joka ajaa Dagsteria. Pelkkä "python"
# osuisi järjestelmän tulkkiin, jossa ei ole tämän projektin riippuvuuksia.
PYTHON = sys.executable
DBT = str(Path(PYTHON).parent / "dbt.exe") if sys.platform == "win32" else "dbt"


@dg.asset(
    group_name="penkkikarnevaalit",
    compute_kind="python",
    description="Poiminta Supabasesta DuckDB:n raw-skeemaan. Ei muunnoksia.",
)
def raw_supabase(
    context: dg.AssetExecutionContext,
    pipes: dg.PipesSubprocessClient,
) -> dg.MaterializeResult:
    return pipes.run(
        command=[PYTHON, str(PROJECT_DIR / "extract" / "supabase_to_duckdb.py")],
        cwd=str(PROJECT_DIR),
        context=context,
    ).get_materialize_result()


@dg.asset(
    deps=[raw_supabase],
    group_name="penkkikarnevaalit",
    compute_kind="python",
    description=(
        "Toinen lahde: saahavainnot Open-Meteosta. Riippuu raw_supabasesta, "
        "koska haettava jakso johdetaan treenien paivamaarista."
    ),
)
def raw_weather(
    context: dg.AssetExecutionContext,
    pipes: dg.PipesSubprocessClient,
) -> dg.MaterializeResult:
    return pipes.run(
        command=[PYTHON, str(PROJECT_DIR / "extract" / "weather_to_duckdb.py")],
        cwd=str(PROJECT_DIR),
        context=context,
    ).get_materialize_result()


@dg.asset(
    deps=[raw_weather],
    group_name="penkkikarnevaalit",
    compute_kind="dbt",
    description=(
        "dbt build: 15 mallia kolmessa kerroksessa ja 48 testiä. "
        "Ajojärjestyksen päättelee dbt itse ref()-viittauksista."
    ),
)
def dbt_models(
    context: dg.AssetExecutionContext,
    pipes: dg.PipesSubprocessClient,
) -> dg.MaterializeResult:
    return pipes.run(
        command=[DBT, "build", "--profiles-dir", "."],
        cwd=str(PROJECT_DIR),
        context=context,
    ).get_materialize_result()


@dg.asset(
    deps=[dbt_models],
    group_name="penkkikarnevaalit",
    compute_kind="python",
    description="Mittaristo marteista: reports/haastemittaristo.html.",
)
def haastemittaristo(
    context: dg.AssetExecutionContext,
    pipes: dg.PipesSubprocessClient,
) -> dg.MaterializeResult:
    return pipes.run(
        command=[PYTHON, str(PROJECT_DIR / "reports" / "build_dashboard.py")],
        cwd=str(PROJECT_DIR),
        context=context,
    ).get_materialize_result()


paivitys = dg.define_asset_job(
    name="paivitys",
    description="Koko ketju: poiminta, mallit ja testit, mittaristo.",
    selection=dg.AssetSelection.all(),
)

# Pois päältä oletuksena. Tuotannossa tämä ajaisi putken joka aamu kuudelta.
aamuajo = dg.ScheduleDefinition(
    job=paivitys,
    cron_schedule="0 6 * * *",
    default_status=dg.DefaultScheduleStatus.STOPPED,
)

defs = dg.Definitions(
    assets=[raw_supabase, raw_weather, dbt_models, haastemittaristo],
    jobs=[paivitys],
    schedules=[aamuajo],
    resources={"pipes": dg.PipesSubprocessClient()},
)
