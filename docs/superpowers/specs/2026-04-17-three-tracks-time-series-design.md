# Three-Track Time-Series Expansion

**Date:** 2026-04-17
**Owner:** wangmm001
**Status:** approved
**Follow-up to:** `2026-04-17-quarterly-time-series-design.md`

## Problem

The unified analysis site at `analysis/web/site/index.html` organizes content
into three research tracks — China / Countries / Network. After the prior
upgrade, only the Countries track fully leverages the six quarterly
snapshots. The China track is pinned to 2026-04, and the Complex-Network
track reflects whatever cache happens to be on disk (currently 2026-01).
The user wants all three tracks to consume the six-snapshot series.

## Goal

Give each research track a first-class **time-series evolution page** that
reflects 2025-01 → 2026-04 quarterly snapshots. Keep the existing deep
analysis pages unchanged — the evolution pages sit alongside them as
complementary viewpoints.

## Non-Goals

- Duplicating the 20 China steps / 13 Network chapters across six snapshots
  (per approach B decided during brainstorming).
- Rebuilding `data_cache/complex_network/` for each snapshot (prohibitively
  expensive: ~100 min per snapshot).
- Changing the site's visual frame, navigation pattern, or deep-page layout.

## Snapshot Set (unchanged)

2025-01 · 2025-04 · 2025-07 · 2025-10 · 2026-01 · 2026-04 — six quarterly
points, all with 180/180 clean metrics JSONs per country in the
`analysis/countries/data/` tree.

## Architecture

Three parallel evolution pages, each owned by its track's source directory
and consumed by the site builder. Data provenance differs:

```
┌─────────────────────────────────────────────────────────────┐
│ analysis/countries/data/{snap}/CN/step*_metrics.json        │
│        (6 snapshots × 20 steps, already on disk)            │
│                         │                                    │
│                         ▼                                    │
│ analysis/china/evolution.py  ── reads only cached JSONs ──▶ │
│ analysis/china/html/evolution.html                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 6 Neo4j swaps × ~8 lightweight Cypher queries                │
│                         │                                    │
│                         ▼                                    │
│ analysis/complex_network/network_evolution.py ─▶            │
│   writes per-snapshot summary to                            │
│   analysis/complex_network_images/evolution_data.json       │
│   then builds                                               │
│   analysis/complex_network_images/evolution.html            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ analysis/countries/html/evolution.html (already built)       │
└─────────────────────────────────────────────────────────────┘

                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ analysis/web/build.py + nav.py                               │
│  · copies each evolution HTML into site/<track>/evolution.html│
│  · adds Evolution tile to each track landing page            │
│  · adds a "时序演化 · Time-Series" section to site/index.html │
│  · updates global TOC and hero leaderboard subtitle          │
└─────────────────────────────────────────────────────────────┘
```

## Component 1 · China Evolution Page

**File:** `analysis/china/evolution.py` → `analysis/china/html/evolution.html`

**Data source:** `analysis/countries/data/{snapshot}/CN/step*_metrics.json`
— reuses the CN slice of the existing countries dataset. No Neo4j calls.

**Five panels** (focus: deep view of one country over time):

1. **20-indicator small-multiples** — one sparkline per key CN metric
   (AS count, v4/v6 prefixes, RPKI%, PageRank rank, k-core depth,
   hegemony edges in/out, DNS sovereignty %, IXP memberships,
   hosted hostnames, Sovereignty Index). Grid 4×5.
2. **Sovereignty Index + 5 components trajectory** — main line + 5
   sub-component lines on a shared 0-1 axis. Answers "which dimension
   drives CN's sovereignty shift?"
3. **Global rank trajectory** — AS count / prefix / IXP / facility /
   best PageRank / deepest k-core. Y-axis reversed (rank #1 top).
4. **Outbound dependency composition** — stacked bar across 6
   snapshots showing CN's top-5 destination countries. From
   `step08.top_destination_countries`. Reveals shifts in who CN
   depends on.
5. **Inbound dependency composition** — stacked bar of CN's top-5
   source countries. From `step09.top_source_countries`. Reveals
   shifts in who depends on CN.

**Narrative block** above panels — 4-5 bullet summary of biggest CN
movers derived programmatically from the data (auto-regenerated).

## Component 2 · Network Evolution Page

**File:** `analysis/complex_network/network_evolution.py` →
`analysis/complex_network_images/evolution.html` +
`analysis/complex_network_images/evolution_data.json`

**Data source:** 6 Neo4j snapshot swaps, each running a set of
lightweight aggregate Cypher queries. Metrics cached in
`evolution_data.json` so the HTML rebuild is fast and offline.

### Extracted metrics per snapshot (~8 numbers)

| Category | Metric | Source |
|---|---|---|
| Scale | total ASes | `MATCH (a:AS) RETURN count(a)` |
| Scale | BGP peering edges | `MATCH ()-[r:PEERS_WITH]->() RETURN count(r)` |
| Scale | Dependency edges | `MATCH ()-[r:DEPENDS_ON]->() RETURN count(r)` |
| Scale | IXP count | `MATCH (i:IXP) RETURN count(i)` |
| Scale | Facility count | `MATCH (f:Facility) RETURN count(f)` |
| Topology | Mean peering degree | Cypher aggregate |
| Topology | Top-10 AS prefix share | aggregate + total |
| Topology | HHI over prefix distribution | aggregate |
| Security | Global RPKI % | tag-based count |
| Regional | AS count for 9 target countries | per-country aggregate |

### Five panels

1. **Scale trajectory** — AS / peering / dependency / IXP / facility
   counts across 6 snapshots (normalized or dual-axis).
2. **Topology** — mean degree + max k-core + connected-component ratio.
3. **Concentration** — HHI (prefix distribution) + top-10 AS share.
4. **Security** — global RPKI % coverage trajectory.
5. **Regional shift** — AS count per target country over time
   (stacked area of 9 countries + "rest of world" residual).

### Orchestration

New script `analysis/complex_network/run_network_evolution.sh` (mirrors
`analysis/countries/extract_snapshot.sh` pattern):

1. For each snapshot in dumps_archive/: swap Neo4j, run
   `network_evolution.py --extract --snapshot <date>`, teardown.
2. After all 6 captures, run `network_evolution.py --render` to build
   the HTML from `evolution_data.json` without Neo4j.

Results are idempotent: re-running with the same snapshot overwrites
that snapshot's entry in `evolution_data.json`.

Expected wall-clock: 6 × (~30s load + ~1 min queries + ~30s teardown)
≈ 12 min Neo4j + 1 min render.

## Component 3 · Site Integration

**Files modified:**

- `analysis/web/build.py` — add evolution page emission for each track;
  copy HTML from source tree into `site/<track>/evolution.html`.
- `analysis/web/nav.py` — register evolution sub-pages in each track's
  nav array; register a "时序演化 · Time-Series" section in global TOC.
- `analysis/web/templates/*.html.j2` — add tile on each track landing
  page, add section on `index.html`, update hero leaderboard subtitle
  from `Δ vs 2025-04` → `Δ vs 2025-01` (15-month baseline).

**Hero changes:** leaderboard "Δ" column now spans 15 months instead
of 12, showing larger absolute deltas. Add `snapshot=2026-04, baseline=2025-01`
clarifier in the subtitle.

**No changes** to the dark-theme palette, the existing 53 deep pages,
iframe scaffolding, or the search / TOC JS.

## Data Flow

```
Countries JSONs (on disk)
  ─▶ china/evolution.py
       reads analysis/countries/data/{snap}/CN/step*_metrics.json
       writes analysis/china/html/evolution.html

Neo4j dumps (in dumps_archive/)
  ─▶ for snap in snapshots:
       swap Neo4j + run network_evolution.py --extract
       appends to analysis/complex_network_images/evolution_data.json
  ─▶ network_evolution.py --render
       reads evolution_data.json
       writes analysis/complex_network_images/evolution.html

analysis/web/build.py
  ─▶ copies both new HTMLs into site/<track>/evolution.html
  ─▶ adds cards on index + track landings
  ─▶ rebuilds site/ in place
```

## Error Handling

- **Missing CN metrics for a snapshot:** `china/evolution.py` skips that
  snapshot in the series (records `—` in tables). Logged at info level.
- **Neo4j not available during extraction:** `network_evolution.py
  --extract` fails loud, the snapshot stays absent from
  `evolution_data.json`. `--render` displays whatever snapshots are
  present; the HTML notes incomplete coverage in the subtitle.
- **Site build iframe probe:** `build.py` already verifies iframe
  sources exist before emission. New evolution pages inherit that
  contract.

## Testing

- **Component 1:** run `python -m analysis.china.evolution`; manually
  open `analysis/china/html/evolution.html`; verify all 5 panels render
  with 6 x-axis points and no empty traces.
- **Component 2:** run `analysis/complex_network/run_network_evolution.sh`;
  verify `evolution_data.json` has 6 entries keyed by snapshot;
  open the HTML.
- **Component 3:** run `python -m analysis.web.build`; verify new tiles
  on `site/index.html`, three track landings; verify no broken iframe
  references.

## Rollback

- All new files are additive. `git rm analysis/china/html/evolution.html
  analysis/complex_network/network_evolution.py
  analysis/complex_network_images/evolution.html
  analysis/complex_network_images/evolution_data.json` reverts the data
  side.
- `git checkout -- analysis/web/build.py analysis/web/nav.py
  analysis/web/templates/` reverts the site side.

## Execution Mode

User continues the fully-autonomous "纯后台" preference from the prior
session. No per-snapshot confirmation for component 2's Neo4j swaps.
Pipeline monitor + scheduled wake-ups cover long-running phases as
before.

## Open Questions

None resolved — all three components accepted during brainstorming.
