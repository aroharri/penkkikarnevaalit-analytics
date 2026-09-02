"""
Build reports/haastemittaristo.html from the warehouse.

Reads the marts, computes the dashboard payload and substitutes it into
reports/_template.html. Every number on the page comes from main_marts —
nothing is typed by hand, so the page cannot drift from the pipeline.

Usage:
    python reports/build_dashboard.py
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DUCKDB_PATH = os.environ.get("DUCKDB_PATH", "warehouse.duckdb")
HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "_template.html"
OUTPUT = HERE / "haastemittaristo.html"

# The challenge the dashboard reports on. Ordering by member count keeps the
# page pointed at the real one rather than a test challenge.
CHALLENGE_SQL = """
select challenge_name, current_total_1rm_kg, goal_total_1rm_kg, progress_pct,
       kg_remaining, days_remaining, member_count, active_members,
       total_workouts, challenge_end_date
from main_marts.dim_challenges
order by member_count desc, current_total_1rm_kg desc
limit 1
"""

MEMBERS_SQL = """
select user_name, current_1rm_kg, all_time_best_1rm_kg, member_target_1rm_kg,
       total_workouts, last_workout_date, days_inactive
from main_intermediate.int_member_progress
where challenge_name = ?
order by current_1rm_kg desc nulls last
"""

# Kaikki nostot uusin ensin. Yksi rivi per kirjattu sarja.
WORKOUTS_SQL = """
select performed_at, user_name, reps, weight_kg, estimated_1rm_kg, is_pr,
       max(estimated_1rm_kg) over (
           partition by user_id order by performed_at
           rows between unbounded preceding and 1 preceding
       ) as prev_best
from main_marts.fct_workouts
order by performed_at desc
"""

# Team total on each day a workout was logged: every member's most recent 1RM
# as of that date, summed. Members with no workout yet contribute nothing —
# the same rule the app applies.
TREND_SQL = """
with days as (select distinct workout_date as d from main_staging.stg_workouts),
members as (
    select user_id from main_intermediate.int_member_progress
    where challenge_name = ?
),
snapshot as (
    select days.d, members.user_id,
        (select w.estimated_1rm_kg
         from main_staging.stg_workouts w
         where w.user_id = members.user_id and w.workout_date <= days.d
         order by w.performed_at desc limit 1) as rm
    from days cross join members
)
select d, round(sum(coalesce(rm, 0)), 2) as total
from snapshot group by d having sum(coalesce(rm, 0)) > 0 order by d
"""


def fi_date(d) -> str:
    return f"{d.day}.{d.month}.{d.year}"


def build_payload(con: duckdb.DuckDBPyConnection) -> dict:
    row = con.execute(CHALLENGE_SQL).fetchone()
    if row is None:
        raise RuntimeError(
            "main_marts.dim_challenges is empty. Run the extract and `dbt build` first."
        )
    (name, current, goal, pct, remaining, days, members, active, workouts, end_date) = row

    member_rows = con.execute(MEMBERS_SQL, [name]).fetchall()
    if not member_rows:
        raise RuntimeError(f"No members found for challenge {name!r}.")

    trend = con.execute(TREND_SQL, [name]).fetchall()
    if not trend:
        raise RuntimeError(f"No workout history found for challenge {name!r}.")

    workout_rows = con.execute(WORKOUTS_SQL).fetchall()

    payload = {
        "generated": datetime.now().strftime("%-d.%-m.%Y %H:%M")
        if os.name != "nt"
        else datetime.now().strftime("%d.%m.%Y %H:%M").lstrip("0").replace(".0", "."),
        "challenge": {
            "name": name,
            "current": float(current),
            "goal": float(goal),
            "pct": float(pct),
            "remaining": float(remaining),
            "days": int(days),
            "members": int(members),
            "active": int(active),
            "workouts": int(workouts),
            "end_date": fi_date(end_date),
        },
        # What the team has already demonstrated, as opposed to their latest set.
        "best_total": round(sum(float(m[2] or 0) for m in member_rows), 2),
        "members": [
            {
                "n": m[0],
                "cur": float(m[1] or 0),
                "best": float(m[2] or 0),
                "tgt": float(m[3] or 0),
                "w": int(m[4] or 0),
                "last": fi_date(m[5]) if m[5] else "—",
                "idle": int(m[6]) if m[6] is not None else 9999,
            }
            for m in member_rows
        ],
        "trend": [[d.isoformat(), float(t)] for d, t in trend],
        "workouts": [
            {
                "ts": w[0].strftime("%-d.%-m.%Y %H:%M")
                if os.name != "nt"
                else f"{w[0].day}.{w[0].month}.{w[0].year} {w[0]:%H:%M}",
                "who": w[1],
                "reps": int(w[2]),
                "kg": float(w[3]),
                "rm": float(w[4]),
                "pr": bool(w[5]),
                # Mika ennatys oli ennen tata nostoa. None = ensimmainen kirjattu.
                "prev": float(w[6]) if w[6] is not None else None,
                # ISO-muoto lajittelua varten, ei nayteta
                "sort": w[0].isoformat(),
            }
            for w in workout_rows
        ],
    }
    return payload


def main():
    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    try:
        payload = build_payload(con)
    finally:
        con.close()

    template = TEMPLATE.read_text(encoding="utf-8")
    if "__PK_DATA__" not in template:
        raise RuntimeError(f"{TEMPLATE.name} has no __PK_DATA__ placeholder.")

    # </script> inside the JSON would close the block early
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    OUTPUT.write_text(template.replace("__PK_DATA__", data), encoding="utf-8")

    c = payload["challenge"]
    logger.info(f"{OUTPUT.name}: {c['name']}")
    logger.info(f"  {c['current']} / {c['goal']} kg = {c['pct']} %")
    logger.info(f"  paras koskaan {payload['best_total']} kg")
    logger.info(f"  {len(payload['members'])} jäsentä, {len(payload['trend'])} trendipistettä")
    logger.info(f"  {len(payload['workouts'])} nostoa taulukossa")
    logger.info(f"  {c['active']}/{c['members']} aktiivista, {c['days']} päivää jäljellä")


if __name__ == "__main__":
    main()
