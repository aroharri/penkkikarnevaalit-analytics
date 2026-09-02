# Reconciliation: analytics vs. the app

The app is the source of truth. Any number here that shares a name with
something on screen must produce the same value.

This file has two parts. The **map** is permanent: which model column
corresponds to which UI element, and the formula on each side. The
**snapshots** are point-in-time — they age as soon as someone logs a set.

Run `analyses/ui_reconciliation.sql` to produce the model side:

```bash
dbt compile
```

Then execute `target/compiled/penkkikarnevaalit/analyses/ui_reconciliation.sql`
against the warehouse and compare against the app.

## Why this file exists

Comparing these numbers against the running app found a 78 percentage point
error in `progress_pct`. Four code review passes and 52 schema tests had all
passed over it. Schema tests prove the pipeline runs; only this proves it
computes the right thing.

## The map

### Challenge level — `dim_challenges`

| UI element | Model column | App formula | Model formula |
|---|---|---|---|
| Tavoite | `goal_total_1rm_kg` | `members.reduce(sum target_1rm) \|\| challenge.goal_kg` | same, via `coalesce(nullif(sum(target),0), goal_kg)` |
| Yhteenlaskettu 1RM | `current_total_1rm_kg` | sum of each member's latest workout `estimated_1rm` | same; members with no workouts contribute nothing |
| To go | `kg_remaining` | `goal − current` | same |
| Edistymis-% | `progress_pct` | `min(current / goal × 100, 100)` | same |
| Time left | `days_remaining` | `goal_end_date − today` | same |

### User level — `dim_users`

| UI element | Model column | Note |
|---|---|---|
| 1RM nyt | `current_1rm_kg` | Latest logged set, **not** the all-time best. `all_time_best_1rm_kg` holds the PR the app shows in RmProgressModal. |
| Suorituksia | `lifetime_workouts` | |
| Kudoksia | `kudos_received` | Self-reactions included, as the app counts them. |

## Analytics-owned metrics

These have no UI counterpart. They are named so they cannot be mistaken for
one, and nothing here needs to reconcile against anything.

| Column | Model | Note |
|---|---|---|
| `analytics_engagement_status` | `int_member_progress` | Four states over 7/14-day thresholds. The app's WeeklyRecap shows two states over a 7-day window. |
| `overall_health` | `dim_challenges` | Scorecard combining engagement with progress vs. elapsed time. |
| `kudos_received_excl_self` | `dim_users` | Variant that drops self-reactions. Deliberately not the number on screen. |

## Known upstream defect

`challenges.goal_start_kg` is carried into `baseline_total_1rm_kg` for
visibility, but **no metric is derived from it**. `create_challenge` never
sets it and the admin UI exposes no field for it, so every challenge created
through the app keeps the column default of 0. Only the original seeded
challenge has a real value (530).

`assert_challenge_baseline_is_set` warns when it is 0. Severity is `warn`, not
`error`: an upstream defect is worth surfacing, not worth leaving the marts
unbuilt over.

## Snapshots

### 2026-09-01 13:54 — "Penkkikarnevaalit 600"

Verified end to end: `extract/supabase_to_duckdb.py` against live Supabase,
then `dbt build` from an empty warehouse. `PASS=61 ERROR=0 SKIP=0`.

| Metric | App | Model | |
|---|---|---|---|
| Yhteenlaskettu 1RM | 538,3 kg | 538,31 | ✅ |
| Tavoite | 600 kg | 600,0 | ✅ |
| To go | 61,7 kg | 61,7 | ✅ |
| **Edistymis-%** | **89,7 %** | **89,7** | ✅ |
| Time left | 117 d | 117 | ✅ |
| 1RM nyt — jäsen A | 120 kg | 120,03 | ✅ |
| Suorituksia — jäsenet A / B / C / D | 31 / 7 / 5 / 1 | 31 / 7 / 5 / 1 | ✅ |

Context at the time: 5 users (one unused test account outside the challenge),
44 workouts, 44 activities, 8 kudos, 8 comments. `user_profiles` and
`comment_reactions` were empty — the extract now creates them as empty tables
rather than skipping them, which is what makes a clean run possible at all.

The `relative_strength` column was removed after this snapshot: bodyweight is
not used anywhere in the app, and `user_profiles` being empty made it NULL for
every row regardless.

Before this snapshot `progress_pct` returned **11,9 %** against the same data,
because it divided the gain by `kg_to_gain` instead of dividing the total by
the goal.

## Known upstream defect: Dagster path

`orchestration/assets.py` launches the extract with
`subprocess.run(["python", ...])`, which resolves the interpreter from PATH
rather than the project's virtualenv. With dependencies installed in `.venv`
this picks the system Python, which has no `supabase` module.

The fix is `sys.executable`. Deliberately deferred — the dbt pipeline does not
need Dagster to run, and the orchestration layer has not been exercised yet.
`pip install -e .` is likewise still untested.
