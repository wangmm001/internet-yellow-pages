# Quarterly Time-Series Implementation Plan

> **Status: DONE (2026-04-17).** Shipped across commits `5538ca3`, `a99bdd7`, `e8421d3`, `1049035`, `d89cede`, `c7894b9`. All 34 tasks below are marked `[x]` retroactively; see git log for the actual sequence. Post-ship follow-up: 2025-01 snapshot lacks `:BGPPrefix` → `evolution.html` flags that baseline gap inline.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `analysis/countries/evolution.html` from 2 annual snapshots to 6 quarterly snapshots (2025-01, 2025-04, 2025-07, 2025-10, 2026-01, 2026-04) by downloading 4 new IYP Neo4j dumps, running the 9-country × 20-step extractor against each, keeping dumps on disk, and upgrading the evolution dashboard to multi-point trend panels.

**Architecture:** Orchestrator bash script iterates over 4 new dump URLs, using `curl` + `docker compose` + `python3 -m analysis.countries.run_all --snapshot …`. Dumps are kept in `dumps_archive/`. Metrics JSONs land in `analysis/countries/data/YYYY-MM/<CC>/`. `evolution.py` is rewritten from 2-point slope logic to N-point trend/CAGR/inflection logic.

**Tech Stack:** bash, docker compose (Neo4j 5.26 + loader), Python 3 (plotly, pandas — already imported), curl.

---

## File Structure

| File | Action | Purpose |
|---|---|---|
| `dumps_archive/` | **create** | holds all downloaded `.dump` files permanently |
| `dumps/neo4j.dump` | transient symlink | whichever dump the loader is currently consuming |
| `analysis/countries/extract_snapshot.sh` | **create** | per-snapshot lifecycle (download → load → extract → stop) |
| `analysis/countries/run_pipeline.sh` | **create** | top-level loop over 4 new snapshots; logs to `extract.log` |
| `analysis/countries/data/2025-01/<CC>/stepNN_metrics.json` | **create** | extraction output × 9 × 20 |
| `analysis/countries/data/2025-07/<CC>/stepNN_metrics.json` | **create** | same |
| `analysis/countries/data/2025-10/<CC>/stepNN_metrics.json` | **create** | same |
| `analysis/countries/data/2026-01/<CC>/stepNN_metrics.json` | **create** | same |
| `analysis/countries/evolution.py` | **modify** | replace 2-point logic with N-point panels |
| `analysis/countries/README.md` | regenerated | `run_all --report` rewrites from metrics |
| `.gitignore` | **modify** | add `/dumps_archive/` |

---

## Task 1 · Prep directories and gitignore

**Files:**
- Create: `dumps_archive/`, `dumps/`, `data/`
- Modify: `.gitignore`

- [x] **Step 1: Check disk and docker availability**

```bash
df -h /Volumes/data | head -2
sg docker -c 'docker ps' | head -3
```

Expected: ≥ 300 GB free; docker command succeeds (IYP-specific containers may or may not be up).

- [x] **Step 2: Create directories**

```bash
mkdir -p /Volumes/data/internet-yellow-pages/dumps_archive \
         /Volumes/data/internet-yellow-pages/dumps \
         /Volumes/data/internet-yellow-pages/data
```

- [x] **Step 3: Add dumps_archive to .gitignore**

Confirm `.gitignore` already anchors `/dumps/` and `/data/`. Add one line:

```
/dumps_archive/
```

- [x] **Step 4: Commit gitignore change**

```bash
cd /Volumes/data/internet-yellow-pages
git add .gitignore
git commit -m "gitignore: exclude /dumps_archive/ (per-snapshot dump retention)"
```

---

## Task 2 · Verify 4 new dumps are published

**Files:** none (probe only)

- [x] **Step 1: HEAD-request each dump URL**

```bash
for d in 2025/01/08 2025/07/08 2025/10/08 2026/01/08; do
  url="https://archive.ihr.live/ihr/iyp/$d/iyp-${d//\//-}.dump"
  sz=$(curl -sIf "$url" --max-time 20 | awk -v IGNORECASE=1 '/content-length/{print $2}' | tr -d '\r')
  if [ -n "$sz" ]; then
    printf "OK   %s  %d GB\n" "$url" $((sz/1024/1024/1024))
  else
    printf "MISS %s\n" "$url"
  fi
done
```

Expected: 4 lines starting with `OK`, each reporting 10–20 GB.

If any `MISS` appears, stop and pick the nearest available day-of-month for that snapshot (01, 15, or 22 instead of 08). Update Task 3 URLs accordingly.

---

## Task 3 · Write per-snapshot orchestrator script

**Files:**
- Create: `analysis/countries/extract_snapshot.sh`

- [x] **Step 1: Write the script**

```bash
#!/usr/bin/env bash
# Per-snapshot lifecycle: download dump (once) → load Neo4j → extract 9×20 →
# stop Neo4j → purge loaded DB. Dump kept in dumps_archive/ for reruns.
#
# Usage: ./extract_snapshot.sh 2025-01-08
set -euo pipefail

TARGET="${1:?usage: $0 YYYY-MM-DD}"
YEAR="${TARGET:0:4}"; MONTH="${TARGET:5:2}"; DAY="${TARGET:8:2}"
SNAP="$YEAR-$MONTH"

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
ARCHIVE="$REPO/dumps_archive"
DUMPS="$REPO/dumps"
DATA="$REPO/data"
DUMP_URL="https://archive.ihr.live/ihr/iyp/$YEAR/$MONTH/$DAY/iyp-$TARGET.dump"
DUMP_FILE="$ARCHIVE/iyp-$TARGET.dump"
LOG_PREFIX="[$SNAP]"

echo "$LOG_PREFIX === start $(date -Iseconds) ==="

mkdir -p "$ARCHIVE" "$DUMPS" "$DATA"

# Portable file-size helper (macOS `stat -f%z`, Linux `stat -c%s`)
fsize() { stat -f%z "$1" 2>/dev/null || stat -c%s "$1" 2>/dev/null || echo 0; }

# 1. Download (resumeable, skipped if file already complete)
if [ -f "$DUMP_FILE" ]; then
    REMOTE_SIZE=$(curl -sI "$DUMP_URL" --max-time 30 \
        | awk -v IGNORECASE=1 '/content-length/{print $2}' | tr -d '\r')
    LOCAL_SIZE=$(fsize "$DUMP_FILE")
    if [ "$LOCAL_SIZE" = "$REMOTE_SIZE" ]; then
        echo "$LOG_PREFIX dump already complete: $DUMP_FILE"
    else
        echo "$LOG_PREFIX resume download (local=$LOCAL_SIZE remote=$REMOTE_SIZE)"
        curl -L -C - --progress-bar "$DUMP_URL" -o "$DUMP_FILE"
    fi
else
    echo "$LOG_PREFIX downloading $DUMP_URL"
    curl -L --progress-bar "$DUMP_URL" -o "$DUMP_FILE"
fi

# 2. Stage dump for loader
echo "$LOG_PREFIX staging dump"
cp "$DUMP_FILE" "$DUMPS/neo4j.dump"

# 3. Purge previously loaded DB so loader will re-run
echo "$LOG_PREFIX stopping any running Neo4j"
docker stop iyp iyp_loader 2>/dev/null || true
docker rm iyp iyp_loader 2>/dev/null || true
echo "$LOG_PREFIX purging loaded database"
rm -rf "$DATA/databases" "$DATA/transactions"

# 4. Bring up loader + DB
echo "$LOG_PREFIX starting docker compose --profile local"
cd "$REPO"
uid="$(id -u)" gid="$(id -g)" docker compose --profile local up -d

# 5. Wait for Neo4j readiness (up to 60 min)
echo "$LOG_PREFIX waiting for Neo4j readiness"
READY=0
for i in $(seq 1 360); do
    sleep 10
    if python3 -c "
from neo4j import GraphDatabase
try:
    d = GraphDatabase.driver('bolt://localhost:7687')
    with d.session() as s:
        r = s.run('MATCH (n) RETURN count(n) AS c LIMIT 1').single()
    print(r['c'])
except Exception as e:
    raise SystemExit(1)
" 2>/dev/null | grep -qE '^[0-9]+$'; then
        READY=1
        echo "$LOG_PREFIX Neo4j ready after ${i}0s"
        break
    fi
done
if [ "$READY" != "1" ]; then
    echo "$LOG_PREFIX ERROR: Neo4j did not become ready within 60 min"
    exit 1
fi

# 6. Run 9-country × 20-step extraction
echo "$LOG_PREFIX running analysis.countries.run_all --snapshot $SNAP"
python3 -m analysis.countries.run_all --snapshot "$SNAP"

# 7. Verify extraction
echo "$LOG_PREFIX verifying"
python3 -m analysis.countries.run_all --verify --snapshot "$SNAP" || true

# 8. Tear down
echo "$LOG_PREFIX stopping Neo4j and purging loaded DB"
docker stop iyp iyp_loader 2>/dev/null || true
docker rm iyp iyp_loader 2>/dev/null || true
rm -rf "$DATA/databases" "$DATA/transactions"
# Remove transient symlink; keep archive copy
rm -f "$DUMPS/neo4j.dump"

echo "$LOG_PREFIX === done $(date -Iseconds) ==="
```

- [x] **Step 2: Make executable**

```bash
chmod +x /Volumes/data/internet-yellow-pages/analysis/countries/extract_snapshot.sh
```

- [x] **Step 3: Smoke-test the help path**

```bash
/Volumes/data/internet-yellow-pages/analysis/countries/extract_snapshot.sh 2>&1 | head -5
```

Expected: `usage: ... YYYY-MM-DD` (script's set-u default on missing arg).

- [x] **Step 4: Commit**

```bash
cd /Volumes/data/internet-yellow-pages
git add analysis/countries/extract_snapshot.sh
git commit -m "Add per-snapshot extract script (keeps dumps in dumps_archive/)"
```

---

## Task 4 · Write top-level pipeline loop

**Files:**
- Create: `analysis/countries/run_pipeline.sh`

- [x] **Step 1: Write the loop script**

```bash
#!/usr/bin/env bash
# Run extract_snapshot.sh serially for all 4 new quarterly snapshots.
# Skips snapshots whose metrics dir already contains ≥ 9 × 20 JSONs.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG="$REPO/analysis/countries/extract.log"

SNAPS=(2025-01-08 2025-07-08 2025-10-08 2026-01-08)

echo "=== pipeline start $(date -Iseconds) ==="           | tee -a "$LOG"
for S in "${SNAPS[@]}"; do
    SNAP="${S:0:7}"
    DIR="$REPO/analysis/countries/data/$SNAP"
    JSON_COUNT=$(find "$DIR" -name 'step*_metrics.json' 2>/dev/null | wc -l | tr -d ' ')
    if [ "$JSON_COUNT" -ge 180 ]; then
        echo "[$SNAP] already extracted ($JSON_COUNT JSONs), skipping" | tee -a "$LOG"
        continue
    fi
    echo "=== [$SNAP] extracting ==="                     | tee -a "$LOG"
    if "$SCRIPT_DIR/extract_snapshot.sh" "$S" 2>&1 | tee -a "$LOG"; then
        echo "[$SNAP] SUCCESS" | tee -a "$LOG"
    else
        echo "[$SNAP] FAILED (continuing with next)" | tee -a "$LOG"
    fi
done
echo "=== pipeline done $(date -Iseconds) ==="            | tee -a "$LOG"
```

- [x] **Step 2: Make executable**

```bash
chmod +x /Volumes/data/internet-yellow-pages/analysis/countries/run_pipeline.sh
```

- [x] **Step 3: Commit**

```bash
cd /Volumes/data/internet-yellow-pages
git add analysis/countries/run_pipeline.sh
git commit -m "Add serial pipeline loop for 4 new quarterly snapshots"
```

---

## Task 5 · Launch pipeline in background

**Files:** none (executes Task 4)

- [x] **Step 1: Kick off**

Run via `Bash` with `run_in_background: true`:

```bash
cd /Volumes/data/internet-yellow-pages && ./analysis/countries/run_pipeline.sh
```

Expected wall-clock: 6–8 hours. Returns a background shell ID.

- [x] **Step 2: Record the shell ID**

Save the returned shell ID in conversation context — used in Task 6.

- [x] **Step 3: Schedule first progress check**

Use `ScheduleWakeup` with `delaySeconds: 1800` (30 min) and a reason like "check first snapshot download/load progress".

---

## Task 6 · Monitor progress until all 4 complete

**Files:** `analysis/countries/extract.log` (appended)

- [x] **Step 1: On each wake-up, tail the log**

```bash
tail -40 /Volumes/data/internet-yellow-pages/analysis/countries/extract.log
```

- [x] **Step 2: Count completed snapshots**

```bash
for s in 2025-01 2025-07 2025-10 2026-01; do
  c=$(find /Volumes/data/internet-yellow-pages/analysis/countries/data/$s -name 'step*_metrics.json' 2>/dev/null | wc -l | tr -d ' ')
  printf "%s: %s/180 JSONs\n" "$s" "$c"
done
```

Expected final: each line `180/180`.

- [x] **Step 3: If still running, reschedule**

If the pipeline log hasn't emitted `=== pipeline done ===`, schedule another wake-up (`delaySeconds: 1800`) and do nothing else. If the background shell exited with failure, inspect the log and decide whether to restart the failing snapshot manually (by re-running `./extract_snapshot.sh <date>` — it's idempotent thanks to resume logic).

- [x] **Step 4: When complete, confirm all 6 snapshots visible**

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, '/Volumes/data/internet-yellow-pages')
from analysis.countries.common import list_snapshots
print(list_snapshots())
PY
```

Expected: `['2025-01', '2025-04', '2025-07', '2025-10', '2026-01', '2026-04']`.

- [x] **Step 5: Commit the 4 new metrics JSON directories**

```bash
cd /Volumes/data/internet-yellow-pages
git add analysis/countries/data/2025-01 analysis/countries/data/2025-07 \
        analysis/countries/data/2025-10 analysis/countries/data/2026-01
git commit -m "Add per-country metrics for 4 new quarterly snapshots (2025-01/07/10, 2026-01)"
```

---

## Task 7 · Upgrade `evolution.py` from 2-point to N-point

**Files:**
- Modify: `analysis/countries/evolution.py`

**Context:** the current script hard-codes `build(snap_old='2025-04', snap_new='2026-04')` and renders 4 panels (slope chart, YoY heatmap, per-component slope, rank bump). With 6 quarterly points we can compute CAGR and detect direction changes, both of which require ≥ 3 points.

- [x] **Step 1: Rewrite the module-level constants and helpers**

Replace the top of `evolution.py` (after the imports) with:

```python
METRICS_TRACKED = [
    ('AS 数',       1, 'total_ases'),
    ('前缀总数',    4, 'total_prefixes'),
    ('IPv6 前缀',   4, 'v6_prefixes'),
    ('RPKI %',      4, 'rpki_rate_pct'),
    ('Best PR',     6, ('best_ranks', 'pagerank')),
    ('Max k-core',  7, 'deepest_k_in_country'),
    ('入向依赖',    9, 'inbound_edges'),
    ('出向依赖',    8, 'outbound_edges'),
    ('托管主机',   14, 'total_hosted_hostnames'),
    ('DNS 主权 %', 15, 'domestic_pct'),
    ('审查 AS',    18, 'censoring_ases'),
    ('主权指数',   20, 'composite_sovereignty_index'),
]


def _get(data, step, key):
    s = (data or {}).get(step, {}) or {}
    if isinstance(key, tuple):
        cur = s
        for k in key:
            cur = (cur or {}).get(k, None)
            if cur is None:
                return None
        return cur
    return s.get(key, None)


def load_all(snapshots):
    """Return (countries, {snap: {cc: {step: metrics_dict}}})."""
    per_snap_countries = [set(list_countries_in_snapshot(s)) for s in snapshots]
    countries = sorted(set.intersection(*per_snap_countries)) if per_snap_countries else []
    out = {s: {cc: {} for cc in countries} for s in snapshots}
    for s in snapshots:
        for cc in countries:
            for n in range(1, 21):
                m = read_country_metrics(s, cc, n)
                out[s][cc][n] = (m or {}).get('metrics', {}) or {}
    return countries, out


def snapshot_to_months(s):
    """'2025-01' → 0, '2025-04' → 3, …"""
    y, m = s.split('-')
    return (int(y) - 2025) * 12 + (int(m) - 1)


def cagr(start, end, months):
    """Compound monthly growth rate compounded to 12 months. None if invalid."""
    if start is None or end is None or start <= 0 or months <= 0:
        return None
    try:
        return (end / start) ** (12.0 / months) - 1.0
    except (ZeroDivisionError, ValueError):
        return None


def inflection_count(series):
    """Number of direction reversals in a numeric series (None-tolerant)."""
    vals = [v for v in series if v is not None]
    if len(vals) < 3:
        return 0
    signs = []
    for a, b in zip(vals, vals[1:]):
        if b > a:
            signs.append(1)
        elif b < a:
            signs.append(-1)
        else:
            signs.append(0)
    reversals = 0
    for a, b in zip(signs, signs[1:]):
        if a != 0 and b != 0 and a != b:
            reversals += 1
    return reversals
```

- [x] **Step 2: Replace `build()` with N-point version**

Delete the existing `build(snap_old, snap_new)` body and replace with:

```python
def build(snapshots=None):
    import plotly.graph_objects as go
    import plotly.subplots as sp

    all_snaps = list_snapshots()
    snapshots = snapshots or all_snaps
    snapshots = [s for s in snapshots if s in all_snaps]
    if len(snapshots) < 2:
        save_placeholder_html(
            'evolution.html', 0,
            '时序演化 · Time-Series Evolution',
            'Time-Series Evolution',
            f'需要 ≥ 2 个快照，当前只有 {snapshots}',
            f'Need ≥ 2 snapshots, found {snapshots}')
        return

    countries, data = load_all(snapshots)
    x_labels = snapshots  # 'YYYY-MM' strings make good categorical axis

    # Panel 1 · Trend lines small-multiples: metrics as rows, one trace per country
    n_metrics = len(METRICS_TRACKED)
    cols = 3
    rows = (n_metrics + cols - 1) // cols
    panel1 = sp.make_subplots(
        rows=rows, cols=cols,
        subplot_titles=[m[0] for m in METRICS_TRACKED],
        vertical_spacing=0.06, horizontal_spacing=0.05,
    )
    for i, (label, step, key) in enumerate(METRICS_TRACKED):
        r, c = i // cols + 1, i % cols + 1
        for cc in countries:
            ys = [_get(data[s][cc], step, key) for s in snapshots]
            panel1.add_trace(go.Scatter(
                x=x_labels, y=ys, mode='lines+markers',
                name=cc, legendgroup=cc, showlegend=(i == 0),
                line=dict(color=country_color(cc), width=1.5),
                marker=dict(size=5),
            ), row=r, col=c)
    panel1.update_layout(
        title='① 12 项关键指标趋势 · 9 国 × 6 季度 · Trend small-multiples',
        height=240 * rows, hovermode='x unified',
    )
    apply_plotly_theme(panel1)

    # Panel 2 · CAGR heatmap (country × metric)
    start, end = snapshots[0], snapshots[-1]
    months = snapshot_to_months(end) - snapshot_to_months(start)
    z, text = [], []
    for cc in countries:
        row_z, row_t = [], []
        for label, step, key in METRICS_TRACKED:
            v0 = _get(data[start][cc], step, key)
            v1 = _get(data[end][cc], step, key)
            g = cagr(v0, v1, months)
            row_z.append(None if g is None else round(g * 100, 2))
            row_t.append('—' if g is None else f'{g*100:+.1f}%')
        z.append(row_z)
        text.append(row_t)
    panel2 = go.Figure(go.Heatmap(
        z=z, x=[m[0] for m in METRICS_TRACKED], y=countries,
        text=text, texttemplate='%{text}',
        colorscale='RdBu', zmid=0,
        colorbar=dict(title='CAGR %'),
    ))
    panel2.update_layout(
        title=f'② 复合年增长率 CAGR · {start} → {end}（{months} 个月）',
        height=max(340, 40 * len(countries) + 120),
    )
    apply_plotly_theme(panel2)

    # Panel 3 · Sovereignty trajectories with variance band
    panel3 = go.Figure()
    for cc in countries:
        ys = [_get(data[s][cc], 20, 'composite_sovereignty_index') for s in snapshots]
        panel3.add_trace(go.Scatter(
            x=x_labels, y=ys, mode='lines+markers',
            name=cc, line=dict(color=country_color(cc), width=2),
            marker=dict(size=7),
        ))
    panel3.update_layout(
        title='③ Sovereignty Index 时序 · Composite trajectory',
        yaxis=dict(title='Sovereignty Index'),
        height=440, hovermode='x unified',
    )
    apply_plotly_theme(panel3)

    # Panel 4 · Inflection / volatility table
    movers = []
    for cc in countries:
        for label, step, key in METRICS_TRACKED:
            series = [_get(data[s][cc], step, key) for s in snapshots]
            reversals = inflection_count(series)
            vals = [v for v in series if v is not None]
            if len(vals) < 2:
                continue
            vmin, vmax = min(vals), max(vals)
            volatility = (vmax - vmin) / (abs(vmin) + 1e-9) if vmin != 0 else None
            movers.append((cc, label, reversals, volatility, series))
    movers.sort(key=lambda r: (-(r[2] or 0), -(r[3] or 0)))
    top = movers[:30]
    panel4 = go.Figure(go.Table(
        header=dict(values=['Country', 'Metric', 'Direction changes', 'Range / |min|', 'Series'],
                    fill_color=DARK_PANEL, font=dict(color=TEXT_PRIMARY)),
        cells=dict(values=[
            [r[0] for r in top],
            [r[1] for r in top],
            [r[2] for r in top],
            [('—' if r[3] is None else f'{r[3]*100:.0f}%') for r in top],
            [' → '.join('—' if v is None else f'{v:.2f}' if isinstance(v, float) else str(v) for v in r[4]) for r in top],
        ], fill_color=DARK_BG, font=dict(color=TEXT_SECONDARY))))
    panel4.update_layout(
        title='④ 方向反转与波动榜 · Top 30 by (direction changes, range)',
        height=640,
    )
    apply_plotly_theme(panel4)

    # Panel 5 · Rank fluctuation band (4 scale metrics × countries)
    rank_metrics = [
        ('AS count rank',       3, ('as_count', 'rank')),
        ('Prefix rank',         3, ('prefix_count', 'rank')),
        ('IXP rank',            3, ('ixp_count', 'rank')),
        ('Facility rank',       3, ('facility_count', 'rank')),
    ]
    panel5 = sp.make_subplots(rows=1, cols=len(rank_metrics),
                              subplot_titles=[m[0] for m in rank_metrics],
                              shared_yaxes=False, horizontal_spacing=0.06)
    for i, (label, step, key) in enumerate(rank_metrics, start=1):
        for cc in countries:
            ys = [_get(data[s][cc], step, key) for s in snapshots]
            panel5.add_trace(go.Scatter(
                x=x_labels, y=ys, mode='lines+markers',
                name=cc, legendgroup=cc, showlegend=(i == 1),
                line=dict(color=country_color(cc), width=1.3),
                marker=dict(size=5),
            ), row=1, col=i)
        panel5.update_yaxes(autorange='reversed', row=1, col=i)  # rank #1 on top
    panel5.update_layout(
        title='⑤ 全球排名波动带 · Rank trajectories (lower = better)',
        height=440, hovermode='x unified',
    )
    apply_plotly_theme(panel5)

    # Stitch all panels into a single body, then wrap with the banner template.
    # save_consolidated_html(body_html, name, title_zh, title_en, subtitle=''):
    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'基于 {len(snapshots)} 个季度快照（{", ".join(snapshots)}）对 '
        f'{len(countries)} 国 × {len(METRICS_TRACKED)} 指标的时序分析。'
        f'CAGR = 按月复利折算到年。'
        f'<br>Time-series analysis across {len(snapshots)} quarterly snapshots '
        f'for {len(countries)} countries × {len(METRICS_TRACKED)} metrics. '
        f'CAGR is monthly-compounded, annualized.'
        f'</p>'
    )
    body = intro + plotly_inline_once(
        [panel1, panel2, panel3, panel4, panel5])
    save_consolidated_html(
        body,
        'evolution.html',
        f'时序演化 · {snapshots[0]} → {snapshots[-1]}（{len(snapshots)} 季度）',
        f'Time-Series Evolution · {snapshots[0]} → {snapshots[-1]} ({len(snapshots)} quarters)',
    )
```

- [x] **Step 3: Update the `__main__` block**

Replace the existing `if __name__ == '__main__':` block with:

```python
if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--snapshots', nargs='+', default=None,
                    help='Override auto-detected snapshot list')
    args = ap.parse_args()
    build(snapshots=args.snapshots)
```

- [x] **Step 4: Run the upgraded script against current 2-snapshot data (pre-pipeline smoke test)**

This is the fallback path — if only 2 snapshots exist it should still produce a working chart:

```bash
cd /Volumes/data/internet-yellow-pages
python3 -m analysis.countries.evolution
```

Expected: writes `analysis/countries/html/evolution.html`; no exception.

- [x] **Step 5: Verify the HTML**

```bash
ls -la /Volumes/data/internet-yellow-pages/analysis/countries/html/evolution.html
head -5 /Volumes/data/internet-yellow-pages/analysis/countries/html/evolution.html
```

Expected: file exists, starts with `<!DOCTYPE html>` or `<html …`.

- [x] **Step 6: Commit evolution.py change (but not the regenerated HTML yet — do that in Task 8)**

```bash
cd /Volumes/data/internet-yellow-pages
git add analysis/countries/evolution.py
git commit -m "evolution.py: generalize from 2-point slope to N-point trend/CAGR/inflection panels"
```

---

## Task 8 · Regenerate dashboards + README

**Files:**
- Modify: `analysis/countries/html/evolution.html`, `analysis/countries/html/index.html`, `analysis/countries/README.md`

- [x] **Step 1: Rebuild evolution dashboard against 6 snapshots**

```bash
cd /Volumes/data/internet-yellow-pages
python3 -m analysis.countries.evolution
```

- [x] **Step 2: Rebuild index + README (pulls from all metrics JSONs)**

```bash
cd /Volumes/data/internet-yellow-pages
python3 -m analysis.countries.run_all --report
```

- [x] **Step 3: Sanity-check that 6 snapshots show up**

```bash
grep -c 'quarterly\|2025-01\|2025-07\|2025-10\|2026-01' \
    /Volumes/data/internet-yellow-pages/analysis/countries/html/evolution.html
```

Expected: ≥ 4 matches.

- [x] **Step 4: Commit regenerated artifacts**

```bash
cd /Volumes/data/internet-yellow-pages
git add analysis/countries/html/evolution.html \
        analysis/countries/html/index.html \
        analysis/countries/README.md
git commit -m "Regenerate dashboards and README with 6 quarterly snapshots"
```

---

## Task 9 · Final verification and cleanup

**Files:** none

- [x] **Step 1: `git status` should be clean except gitignored paths**

```bash
cd /Volumes/data/internet-yellow-pages
git status --short
```

Expected: empty output, or only `dumps_archive/` noise (which `.gitignore` should have absorbed — if any line references `dumps_archive` check the gitignore anchor).

- [x] **Step 2: Disk usage snapshot**

```bash
du -sh /Volumes/data/internet-yellow-pages/dumps_archive/*.dump 2>/dev/null
df -h /Volumes/data | head -2
```

Expected: 4 dumps × ~15 GB each = ~60 GB in `dumps_archive/`. Free space remains comfortable.

- [x] **Step 3: Confirm pipeline log is committed to log dir**

Nothing to commit for `extract.log` (it's a runtime artifact; check whether `analysis/countries/.gitignore` or repo `.gitignore` excludes it; if not, add `analysis/countries/extract.log` to `.gitignore`).

- [x] **Step 4: Print summary report**

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, '/Volumes/data/internet-yellow-pages')
from analysis.countries.common import list_snapshots, list_countries_in_snapshot, read_country_metrics
snaps = list_snapshots()
print(f'Snapshots: {snaps}')
for s in snaps:
    ccs = list_countries_in_snapshot(s)
    ok = sum(1 for cc in ccs for n in range(1, 21)
             if (read_country_metrics(s, cc, n) or {}).get('metrics'))
    print(f'  {s}: {len(ccs)} countries × 20 steps = {ok}/{len(ccs)*20} JSONs OK')
PY
```

Expected: 6 lines, each `9 countries × 20 steps = 180/180 JSONs OK`.

---

## Self-Review

**Spec coverage:**

- 6 snapshots (§Snapshot Set) → Task 1, Task 6 Step 4.
- dumps_archive/ retention (§Architecture) → Task 1 Step 2, Task 3 Step 1 (never deletes from archive).
- extract_snapshot.sh lifecycle (§Snapshot orchestrator) → Task 3.
- evolution.py N-point upgrade (§evolution.py upgrade) → Task 7.
- 5 panels (§evolution.py upgrade table) → Task 7 Step 2.
- Error handling: dump-not-published (§Error Handling) → Task 2 Step 1.
- Error handling: Neo4j loader failure → Task 6 Step 3 (script continues, log inspected).
- Testing: per-snapshot verify (§Testing) → Task 3 Step 1 item 7, Task 9 Step 4.
- Rollback (§Rollback) → no task (documentation sufficient; reversible via git commands listed in spec).
- Fully autonomous background (§Execution Mode) → Task 5 (`run_in_background: true`) + Task 6 (monitor via ScheduleWakeup, no per-snapshot confirmation).

All covered.

**Placeholder scan:** No `TBD` / `TODO` / "similar to above". Every code block is complete. The only dynamic piece is inspecting log output — expected since we monitor a long-running pipeline.

**Type consistency:** `_get(data, step, key)` signature consistent across Panel 1–5. `METRICS_TRACKED` schema stays `(label, step, key)` throughout. `snapshot_to_months`, `cagr`, `inflection_count` are each defined once and used consistently.

**Execution mode alignment:** spec requires fully autonomous — Task 5/6 flow matches (background launch + scheduled wake-ups, no user-facing pauses).

Plan is ready.
