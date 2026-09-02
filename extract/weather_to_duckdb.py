"""
Toinen lähde: säähavainnot Open-Meteon avoimesta rajapinnasta.

Vastaa kysymykseen, johon sovelluksen oma data ei yksin riitä: vaikuttaako
sää siihen, kuinka usein treenataan?

Poiminta lukee treenien päivämääräalueen DuckDB:stä ja hakee säädatan
täsmälleen siltä väliltä. Se tarkoittaa aitoa riippuvuutta: tämä ajetaan
vasta kun raw.workouts on olemassa.

Sijainti on kiinteä, koska sovellus ei tallenna treenin koordinaatteja —
vain vapaan tekstikentän salin nimelle. Sipoo on lähin yhteinen nimittäjä
tuotannon saleille; se on approksimaatio ja se on dokumentoitu sellaisena.

Ei vaadi API-avainta.

Usage:
    python extract/weather_to_duckdb.py
"""

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import date, timedelta

import duckdb

try:
    from extract.raw_schema import RAW_SCHEMA
except ModuleNotFoundError:
    from raw_schema import RAW_SCHEMA

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DUCKDB_PATH = os.environ.get("DUCKDB_PATH", "warehouse.duckdb")

API = "https://archive-api.open-meteo.com/v1/archive"
LATITUDE = 60.29   # Sipoo
LONGITUDE = 25.26
TIMEZONE = "Europe/Helsinki"

# Arkistorajapinta on noin viisi päivää jäljessä nykyhetkeä.
ARCHIVE_LAG_DAYS = 6


def workout_date_range(con: duckdb.DuckDBPyConnection) -> tuple[date, date]:
    """Treenien ensimmäinen ja viimeinen päivä. Määrää haettavan jakson."""
    row = con.execute(
        "select min(logged_at::date), max(logged_at::date) from raw.workouts"
    ).fetchone()

    if not row or row[0] is None:
        raise RuntimeError(
            "raw.workouts on tyhjä tai puuttuu. Aja extract/supabase_to_duckdb.py ensin."
        )

    first, last = row
    latest_available = date.today() - timedelta(days=ARCHIVE_LAG_DAYS)
    return first, min(last, latest_available)


def fetch_weather(start: date, end: date) -> list[dict]:
    """Hae päivittäiset säähavainnot. Palauttaa rivit, ei sarakkeita."""
    params = (
        f"?latitude={LATITUDE}&longitude={LONGITUDE}"
        f"&start_date={start.isoformat()}&end_date={end.isoformat()}"
        "&daily=temperature_2m_mean,temperature_2m_min,precipitation_sum,snowfall_sum"
        f"&timezone={TIMEZONE}"
    )

    try:
        with urllib.request.urlopen(API + params, timeout=60) as response:
            payload = json.load(response)
    except urllib.error.URLError as e:
        raise RuntimeError(f"Open-Meteo ei vastannut: {e}") from e

    daily = payload.get("daily")
    if not daily or not daily.get("time"):
        raise RuntimeError(f"Open-Meteo palautti tyhjän vastauksen jaksolle {start}..{end}")

    # Rajapinta palauttaa rinnakkaisia listoja. Käännetään ne riveiksi,
    # koska raw-kerroksen pitää näyttää taululta eikä API-vastaukselta.
    return [
        {
            "weather_date": d,
            "temperature_mean_c": daily["temperature_2m_mean"][i],
            "temperature_min_c": daily["temperature_2m_min"][i],
            "precipitation_mm": daily["precipitation_sum"][i],
            "snowfall_cm": daily["snowfall_sum"][i],
            "latitude": payload["latitude"],
            "longitude": payload["longitude"],
        }
        for i, d in enumerate(daily["time"])
    ]


def load_to_duckdb(con: duckdb.DuckDBPyConnection, rows: list[dict]):
    """Kirjoita raw.weather. Sarakkeet RAW_SCHEMAsta, kuten muillakin tauluilla."""
    columns = RAW_SCHEMA["weather"]
    column_ddl = ", ".join(f"{name} {sql_type}" for name, sql_type in columns)

    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute(f"CREATE OR REPLACE TABLE raw.weather ({column_ddl})")

    if rows:
        placeholders = ", ".join("?" * len(columns))
        con.executemany(
            f"INSERT INTO raw.weather VALUES ({placeholders})",
            [tuple(r[name] for name, _ in columns) for r in rows],
        )

    logger.info(f"  raw.weather: {len(rows)} rows")


def extract_and_load():
    con = duckdb.connect(DUCKDB_PATH)
    try:
        start, end = workout_date_range(con)
        logger.info(f"Haetaan säädata jaksolle {start} .. {end}")

        rows = fetch_weather(start, end)
        if not rows:
            raise RuntimeError("Open-Meteo palautti nolla riviä — ei kirjoiteta tyhjää taulua.")

        load_to_duckdb(con, rows)

        temps = [r["temperature_mean_c"] for r in rows if r["temperature_mean_c"] is not None]
        if temps:
            logger.info(f"  lämpötila {min(temps):.1f} .. {max(temps):.1f} °C")
    finally:
        con.close()


if __name__ == "__main__":
    extract_and_load()
