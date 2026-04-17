# Quarterly Time-Series Upgrade for `analysis/countries/`

**Date:** 2026-04-17
**Owner:** wangmm001
**Status:** approved

## Problem

The cross-country dashboard (`analysis/countries/`) currently holds only two
IYP snapshots — `2025-04` and `2026-04` — so `evolution.html` is a two-point
"before / after" slope chart. A two-point line carries no trend information:
slope = (Δ/12 months), variance = 0, no inflection, no seasonality. The user
asked to download monthly IYP dumps from 2025-01 onward and re-run the
analysis for higher precision.

## Goal

Go from 2 time points to **6 quarterly snapshots** so that each country ×
metric trajectory has enough degrees of freedom to compute:

- trend slope with residual
- compound annual growth rate (CAGR)
- direction changes / inflection points
- seasonal vs. structural component

## Non-Goals

- Monthly (16-point) or weekly resolution — cost/noise tradeoff rejected
  during brainstorming.
- Re-running the snapshot-specific `analysis/china/` 20-step deep dive for
  every snapshot. It remains pinned to 2026-04.
- Changing crawlers, post-processors, or the IYP Neo4j schema itself.

## Snapshot Set

| # | Snapshot | Dump URL | Status |
|---|---|---|---|
| 1 | 2025-01-08 | `archive.ihr.live/ihr/iyp/2025/01/08/iyp-2025-01-08.dump` | **new** |
| 2 | 2025-04-08 | already committed — reuse `analysis/countries/data/2025-04/` | skip |
| 3 | 2025-07-08 | `archive.ihr.live/ihr/iyp/2025/07/08/iyp-2025-07-08.dump` | **new** |
| 4 | 2025-10-08 | `archive.ihr.live/ihr/iyp/2025/10/08/iyp-2025-10-08.dump` | **new** |
| 5 | 2026-01-08 | `archive.ihr.live/ihr/iyp/2026/01/08/iyp-2026-01-08.dump` | **new** |
| 6 | 2026-04-08 | already committed — reuse `analysis/countries/data/2026-04/` | skip |

Day-of-month `08` chosen for consistency with existing 2025-04-08 and
2026-04-08 anchors.

## Architecture

```
┌──────────────────────────┐
│ dumps_archive/           │ 4 new + 0 existing dumps, never deleted
│  iyp-2025-01-08.dump     │ (gitignored; user wants to keep for reruns)
│  iyp-2025-07-08.dump     │
│  iyp-2025-10-08.dump     │
│  iyp-2026-01-08.dump     │
└──────────────────────────┘
           │ (symlink / copy — one at a time)
           ▼
┌──────────────────────────┐
│ dumps/neo4j.dump         │ whichever snapshot is currently loaded
└──────────────────────────┘
           │ docker compose loader
           ▼
┌──────────────────────────┐
│ data/databases/neo4j/    │ ~184 GB loaded DB
└──────────────────────────┘
           │ Cypher queries via iyp driver
           ▼
┌──────────────────────────────────────────────┐
│ analysis/countries/data/<YYYY-MM>/<CC>/      │ per-country per-snapshot
│  stepNN_metrics.json   × 20                  │ (committed to git, small)
│  ases.csv                                    │
└──────────────────────────────────────────────┘
           │ list_snapshots() picks them up
           ▼
┌──────────────────────────┐
│ analysis/countries/      │
│  evolution.html          │ 6-point trend dashboard (upgraded panels)
│  index.html              │ master navigation
│  README.md               │ auto-regenerated from metrics JSONs
└──────────────────────────┘
```

### Snapshot orchestrator

New helper `analysis/countries/extract_snapshot.sh` (a revised
`snapshot_swap.sh`) performs per-snapshot lifecycle:

1. `curl -C - -o dumps_archive/iyp-$TARGET.dump $URL` (resumeable)
2. `cp dumps_archive/iyp-$TARGET.dump dumps/neo4j.dump`
3. If Neo4j container is up → `docker stop iyp`; purge `data/databases`
   and `data/transactions` so the loader will pick the new dump.
4. `docker compose --profile local up -d` and poll readiness.
5. `python3 -m analysis.countries.run_all --snapshot $YYYY-$MM` (9 × 20
   Cypher jobs; writes metrics JSONs under
   `analysis/countries/data/$YYYY-$MM/`).
6. `docker stop iyp`; `rm -rf data/databases data/transactions` so the
   next iteration starts clean.

The dump **is never deleted** — stays in `dumps_archive/` so reruns can
skip the download.

### `evolution.py` upgrade

Current: `build(snap_old, snap_new)` with a 2-point slope chart.

New: `build(snapshots=list_snapshots())` with five panels:

| Panel | Current (2-pt) | Upgraded (N-pt) |
|---|---|---|
| 1 | Slope chart per sovereignty component | **Trend lines**: 9 countries × 12 metrics small-multiples |
| 2 | YoY delta heatmap | **CAGR heatmap** (country × metric) — more stable than single-period delta |
| 3 | Per-component slope | **Sovereignty Index trajectories**: 6 points per country + variance band |
| 4 | Rank bump chart | **Inflection points**: quarter where each country × metric reversed direction; top movers table |
| 5 | — | **Rank fluctuation**: rank min/max band per country across 4 scale metrics |

All panels use the existing `COLORS`, `DARK_BG`, `apply_plotly_theme()` from
`analysis/countries/common.py`. No new palette.

### Data structures unchanged

`common.list_snapshots()` already scans `DATA_DIR` for `YYYY-MM`
subdirectories, so adding four new directories automatically widens the
time series. `read_country_metrics(snap, cc, n)` returns the same JSON
shape. No schema changes to per-country JSONs.

## Error Handling

- **Dump not yet published:** `curl -sIf` probe at step 1; if 404, skip
  that snapshot, log, continue.
- **Neo4j loader failure:** if loader exits non-zero, leave dump in
  `dumps_archive/` and move on (log to `analysis/countries/extract.log`).
  Partial metrics JSONs are overwritten on retry.
- **Cypher timeout:** individual step queries use existing `step_lib`
  retry logic; a single step failing is logged in its
  `stepNN_metrics.json._error` field and does not block other steps.
- **Disk pressure:** each iteration begins by purging `data/databases`.
  Worst peak is `dump (15 GB) + loaded DB (184 GB)` = ~200 GB. Available:
  1.7 TB. No guard needed beyond the existing `df` check in the script.

## Testing

- **Per-snapshot verify:** after each snapshot, run
  `python3 -m analysis.countries.run_all --verify --snapshot YYYY-MM` —
  prints a 9-country × 20-step OK matrix.
- **Cross-snapshot smoke:** after all 4 snapshots land, run
  `list_snapshots()` → must return 6 entries; `evolution.py` must produce
  a 6-point chart (visual inspection of `evolution.html`).
- **Regression:** 2025-04 and 2026-04 metrics already on disk should not
  be touched. Self-check: `git status analysis/countries/data/2025-04
  analysis/countries/data/2026-04` clean after run.

## Rollback

- All new files live under `analysis/countries/data/YYYY-MM/` and
  `dumps_archive/`. `git clean -fd analysis/countries/data/2025-01
  analysis/countries/data/2025-07 analysis/countries/data/2025-10
  analysis/countries/data/2026-01` reverts the data side.
- `evolution.py` changes are in one file — `git checkout --
  analysis/countries/evolution.py` reverts the code side.
- `dumps_archive/` can be manually deleted to reclaim ~60 GB.

## Execution Mode

User asked for **fully autonomous background execution** — no per-snapshot
confirmation. The orchestrator runs as a single backgrounded bash that
iterates the 4 new snapshots serially, writes to `extract.log`, and the
agent monitors via `Monitor` tool / log tails. Each snapshot takes
~70–120 min. Total wall-clock ~6–8 hours.

## Open Questions

None — all 3 scoping questions resolved:

1. china/ not re-run per snapshot (stays 2026-04).
2. dumps kept in repo-local `dumps_archive/` (gitignored).
3. Fully autonomous, no per-snapshot confirmation gate.
