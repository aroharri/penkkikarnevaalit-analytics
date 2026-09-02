# Penkkikarnevaalit Analytics

End-to-end analytics pipeline for [Penkkikarnevaalit](https://penkkikarnevaalit.fi) — a social bench press tracking app where friend groups compete in collective strength challenges.

This project demonstrates a production-grade analytics engineering workflow: extraction from a live Supabase backend, transformation through a three-layer dbt model architecture, orchestration with Dagster, and a local DuckDB warehouse that anyone can clone and run.

## Architecture

```
Supabase (prod)  →  Python extract  →  DuckDB (raw)  →  dbt  →  DuckDB (staging/intermediate/marts)
                         ↑                                 ↑
                     Dagster orchestrates the full pipeline
```

### Why these tools?

| Tool | Why |
|------|-----|
| **DuckDB** | Local, zero-config warehouse. No cloud account needed. Portable — anyone can clone this repo and query the data. |
| **dbt (dbt-duckdb)** | Industry-standard transformation layer. Schema tests, documentation, and lineage built in. |
| **Dagster** | Modern orchestration with native dbt integration. Asset-based, not task-based — each model is an observable asset. |
| **Python** | Extraction script using Supabase SDK. Handles pagination and logging. |

## Data Lineage

### Full Pipeline

```mermaid
graph LR
    subgraph Source
        SB[(Supabase)]
    end

    subgraph Extract
        PY[supabase_to_duckdb.py]
    end

    subgraph DuckDB
        RAW[(raw schema)]
    end

    SB --> PY --> RAW
    RAW --> STG
    STG --> INT
    INT --> MARTS

    subgraph STG[Staging]
        stg_users
        stg_workouts
        stg_challenges
        stg_challenge_members
        stg_user_profiles
        stg_activities
        stg_kudos
        stg_comments
        stg_comment_reactions
    end

    subgraph INT[Intermediate]
        int_workout_metrics
        int_member_progress
    end

    subgraph MARTS[Marts]
        fct_workouts
        dim_users
        dim_challenges
    end
```

### Model Dependencies

```mermaid
graph TD
    stg_users --> int_workout_metrics
    stg_workouts --> int_workout_metrics
    stg_user_profiles --> int_workout_metrics

    stg_challenge_members --> int_member_progress
    stg_users --> int_member_progress
    stg_workouts --> int_member_progress
    stg_challenges --> int_member_progress

    int_workout_metrics --> fct_workouts

    stg_users --> dim_users
    stg_user_profiles --> dim_users
    int_workout_metrics --> dim_users
    stg_kudos --> dim_users
    stg_activities --> dim_users
    stg_comments --> dim_users
    stg_comment_reactions --> dim_users

    stg_challenges --> dim_challenges
    int_member_progress --> dim_challenges

```

## dbt Model Architecture

### Staging (`models/staging/`)
Raw source cleaning: renames, type casts, filters out invalid data. Materialized as **views**.

| Model | Source | Key Logic |
|-------|--------|-----------|
| `stg_users` | `raw.users` | All users (active + inactive) for FK integrity, renames to analytics-friendly columns |
| `stg_workouts` | `raw.workouts` | Validates Brzycki 1RM formula, filters invalid sets (0 reps, >12 reps) |
| `stg_challenges` | `raw.challenges` | Derives `challenge_duration_days`, `kg_to_gain` |
| `stg_challenge_members` | `raw.challenge_members` | Membership junction table with starting/target 1RM |
| `stg_user_profiles` | `raw.user_profiles` | Body weight, height, experience level |
| `stg_activities` | `raw.activities` | Activity feed events |
| `stg_kudos` | `raw.kudos_reactions` | Emoji reactions on activities |
| `stg_comments` | `raw.comments` | Text comments on activities |
| `stg_comment_reactions` | `raw.comment_reactions` | Emoji reactions on comments |

### Intermediate (`models/intermediate/`)
Business logic and joins. Materialized as **views**.

| Model | Purpose |
|-------|---------|
| `int_workout_metrics` | Each workout enriched with user context, PR detection, relative strength, running best 1RM, training consistency |
| `int_member_progress` | Each challenge member's current state: latest 1RM, progress %, engagement status (active/cooling_off/at_risk) |

### Marts (`models/marts/`)
Consumption-ready tables for BI tools. Materialized as **tables**.

| Model | Purpose |
|-------|---------|
| `fct_workouts` | Fact table: every bench press set with PR flags and running metrics |
| `dim_users` | User dimension: lifetime stats, current rank, social engagement |
| `dim_challenges` | Challenge dimension: goal progress, team composition, engagement health, standout members, and an overall health signal |

## Domain Concepts

### Brzycki 1RM Formula
Estimates one-rep max from submaximal sets:

```
1RM = weight × (36 / (37 - reps))
```

Capped at 12 reps for accuracy. This is the core metric of the entire application.

### Challenge Progress

The app measures progress as the team's combined current 1RM against the goal:

```
progress_% = min(current_total_1rm / goal_total_1rm × 100, 100)
```

`goal_total_1rm` is the sum of members' personal targets, falling back to
`challenges.goal_kg` when no member has set one.

`current_total_1rm` sums each member's **most recent** logged 1RM — not their
best. A lighter session lowers it, which is what the app shows.

Members with no logged workouts contribute nothing to the numerator while
still counting toward the goal.

### What the analytics adds

A few columns have no counterpart in the app. They are prefixed or named so
they cannot be mistaken for something on screen, and they are listed in
[RECONCILIATION.md](RECONCILIATION.md):

| Column | Meaning |
|--------|---------|
| `analytics_engagement_status` | Four inactivity states (7/14-day thresholds). The app shows two. |
| `overall_health` | Challenge scorecard: engagement combined with progress vs. elapsed time. |
| `kudos_received_excl_self` | Kudos count excluding self-reactions. The app counts them. |

There is no rank or tier system. An earlier version of this project computed
one; it was removed because the app has no such concept, and because
`user_profiles` is empty in production so the bodyweight it needed is NULL for
every row.

## Setup

### Prerequisites
- Python 3.10+
- Access to the Penkkikarnevaalit Supabase project (service key)

### Install

```bash
# Clone and install
git clone <repo-url>
cd penkkikarnevaalit-analytics
pip install -e .

# Configure credentials
cp .env.example .env
# Edit .env with your Supabase URL and service key
```

### Run the Pipeline

```bash
# Option 0: No Supabase credentials? Seed synthetic data instead.
python extract/seed_dev_data.py        # Fills raw.* with a production-shaped fixture
dbt build                              # Everything below works from here

# Option 1: Run steps manually against real Supabase
python extract/supabase_to_duckdb.py   # Extract
dbt run                                 # Transform
dbt test                                # Validate

# Option 2: Run via Dagster (recommended)
dagster dev  # reads module_name from pyproject.toml
# Then open http://localhost:3000 and materialize all assets
```

### Explore the Data

```bash
# Query the warehouse directly
duckdb warehouse.duckdb

# Example queries (dbt-duckdb prefixes custom schemas with the target schema)
SELECT * FROM main_marts.fct_workouts LIMIT 10;
SELECT * FROM main_marts.dim_users;
SELECT * FROM main_marts.dim_challenges;
```

## Testing

Two kinds of tests:

**Schema tests** (in YAML files alongside each model layer):
- **Unique + not_null** on all primary keys
- **Relationships** tests (e.g., workouts → users FK integrity)
- **Accepted values** for enums (challenge_status, member_role, experience_level, activity_type, analytics_engagement_status, overall_health)

**Singular tests** (in `tests/`):
- **`assert_raw_schema_matches_production`** — compares every column in `raw.*` against the 74 columns verified in production Supabase. Fails in both directions: a column that disappears upstream, and one that appears unexpectedly. This is the guard that catches an extract or fixture drifting away from the real schema.
- **`assert_brzycki_1rm_accuracy`** (`warn`) — recomputes the Brzycki formula independently and flags any workout where the app's stored `estimated_1rm` disagrees by more than 0.5 kg, or is NULL.
- **`assert_challenge_baseline_is_set`** (`warn`) — flags challenges with no recorded baseline. This is an upstream app defect: `create_challenge` never sets `goal_start_kg`.

Both drift checks run at `warn` on purpose. At `error` a single odd row skipped
31 downstream nodes and produced no marts at all — an upstream signal is not a
reason to leave the warehouse unbuilt.

**Reconciliation** — the check that neither kind of test performs: see
[RECONCILIATION.md](RECONCILIATION.md) and `analyses/ui_reconciliation.sql`.
Tests prove the pipeline runs. Reconciliation proves it computes what the app
computes.

```bash
dbt test                    # Run all tests
dbt test --select staging   # Run only staging tests
dbt test --select test_type:singular  # Run only singular tests
```

## Project Structure

```
penkkikarnevaalit-analytics/
├── extract/
│   ├── supabase_to_duckdb.py      # Supabase → DuckDB extraction
│   └── seed_dev_data.py           # Synthetic fixture — no credentials needed
├── models/
│   ├── staging/
│   │   ├── _sources.yml            # Source definitions + column docs
│   │   ├── _staging__models.yml    # Model docs + tests
│   │   ├── stg_users.sql
│   │   ├── stg_workouts.sql
│   │   ├── stg_challenges.sql
│   │   ├── stg_challenge_members.sql
│   │   ├── stg_user_profiles.sql
│   │   ├── stg_activities.sql
│   │   ├── stg_kudos.sql
│   │   ├── stg_comments.sql
│   │   └── stg_comment_reactions.sql
│   ├── intermediate/
│   │   ├── _intermediate__models.yml
│   │   ├── int_workout_metrics.sql
│   │   └── int_member_progress.sql
│   └── marts/
│       ├── _marts__models.yml
│       ├── fct_workouts.sql
│       ├── dim_users.sql
│       └── dim_challenges.sql
├── orchestration/
│   ├── __init__.py
│   └── assets.py                   # Dagster asset definitions
├── analyses/
│   └── ui_reconciliation.sql       # Model numbers vs. the app, side by side
├── tests/
│   ├── assert_raw_schema_matches_production.sql
│   ├── assert_brzycki_1rm_accuracy.sql
│   └── assert_challenge_baseline_is_set.sql
├── dbt_project.yml
├── profiles.yml
├── pyproject.toml
├── .env.example
├── .gitignore
├── RECONCILIATION.md               # Model ↔ app number map and snapshots
└── README.md
```

## Author

**Harri Aro** — [harriaro.fi](https://harriaro.fi)
