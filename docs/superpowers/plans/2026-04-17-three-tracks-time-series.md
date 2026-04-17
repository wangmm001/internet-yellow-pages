# Three-Track Time-Series Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an `evolution.html` page to each of the three tracks (China · Countries · Network) so the unified site at `analysis/web/site/index.html` surfaces the six-quarter time-series data coherently. Countries already has one from the prior project.

**Architecture:** One time-series page per track with distinct data provenance. China reuses `analysis/countries/data/<snap>/CN/` JSONs (no Neo4j). Network runs ~10 lightweight Cypher aggregates per snapshot via a `run_network_evolution.sh` orchestrator (~12 min total Neo4j). Countries evolution.html already exists. A single site-builder pass rewires nav + emits three evolution pages.

**Tech Stack:** Python (plotly, json), bash, docker compose, Neo4j 5.26, Jinja2 (via existing `analysis/web/build.py`).

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `analysis/china/evolution.py` | **create** | reads CN JSONs across 6 snapshots → renders china/html/evolution.html |
| `analysis/china/html/evolution.html` | **create** | 5-panel CN time-series |
| `analysis/complex_network/network_evolution.py` | **create** | `--extract --snapshot SNAP` (Cypher) + `--render` (html builder) |
| `analysis/complex_network/run_network_evolution.sh` | **create** | 6-snapshot Neo4j-swap orchestrator |
| `analysis/complex_network_images/evolution_data.json` | **create** | snapshot → {metrics} cache, written by --extract |
| `analysis/complex_network_images/evolution.html` | **create** | 5-panel global-network time-series |
| `analysis/web/nav.py` | **modify** | register Evolution page in each track; update SNAPSHOT constants; extend leaderboard delta baseline |
| `analysis/web/build.py` | **modify** | emit site/china/evolution/index.html + site/network/evolution/index.html (countries evolution already emitted) |
| `analysis/web/templates/index.html.j2` | **modify** | new "时序演化 · Time-Series" section |
| `analysis/web/templates/track_landing.html.j2` | **modify** | add Evolution tile at top of each track landing (or whatever template name exists) |

---

## Task 1 · China evolution page (no Neo4j)

**Files:**
- Create: `analysis/china/evolution.py`
- Create (output): `analysis/china/html/evolution.html`

- [ ] **Step 1: Draft the module skeleton**

```python
# analysis/china/evolution.py
"""CN time-series evolution across 6 quarterly snapshots.

Reuses per-snapshot CN metrics already extracted into
analysis/countries/data/{snap}/CN/step*_metrics.json. No Neo4j calls.
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.countries.common import (  # noqa: E402
    COLORS, DARK_BG, DARK_BORDER, DARK_PANEL, TEXT_PRIMARY, TEXT_SECONDARY,
    apply_plotly_theme, country_color, list_snapshots, plotly_inline_once,
    read_country_metrics, save_consolidated_html, save_placeholder_html,
)

CC = 'CN'

METRICS_TRACKED = [
    ('AS 数',        1, 'total_ases'),
    ('IPv4 前缀',   4, 'v4_prefixes'),
    ('IPv6 前缀',   4, 'v6_prefixes'),
    ('总前缀',      4, 'total_prefixes'),
    ('RPKI %',      4, 'rpki_rate_pct'),
    ('Anycast',     4, 'anycast_prefixes'),
    ('Best PR',     6, ('best_ranks', 'pagerank')),
    ('Best deg',    6, ('best_ranks', 'degree')),
    ('Max k-core',  7, 'deepest_k_in_country'),
    ('出向依赖',    8, 'outbound_edges'),
    ('入向依赖',    9, 'inbound_edges'),
    ('IXP 成员',   11, 'ixp_memberships_domestic'),
    ('托管主机',   14, 'total_hosted_hostnames'),
    ('DNS 主权 %', 15, 'domestic_pct'),
    ('审查 AS',    18, 'censoring_ases'),
    ('主权指数',   20, 'composite_sovereignty_index'),
]

SOV_COMPONENTS = [
    ('hosting_sovereignty', '托管 Hosting'),
    ('dns_sovereignty',     'DNS'),
    ('rpki_adoption',       'RPKI'),
    ('ixp_domesticization', 'IXP 本地化'),
    ('hub_ratio',           'Hub ratio'),
]

RANK_METRICS = [
    ('AS count',  3, ('as_count',       'rank')),
    ('Prefix',    3, ('prefix_count',   'rank')),
    ('IXP',       3, ('ixp_count',      'rank')),
    ('Facility',  3, ('facility_count', 'rank')),
    ('Best PR',   6, ('best_ranks',     'pagerank')),
    ('k-core',    7, 'cn_deepest_coreness'),
]


def _get(step_map, step, key):
    s = (step_map or {}).get(step, {}) or {}
    if isinstance(key, tuple):
        cur = s
        for k in key:
            cur = (cur or {}).get(k, None)
            if cur is None:
                return None
        return cur
    return s.get(key, None)


def load_cn_series(snapshots):
    out = {}
    for s in snapshots:
        per_step = {}
        for n in range(1, 21):
            m = read_country_metrics(s, CC, n)
            per_step[n] = (m or {}).get('metrics', {}) or {}
        out[s] = per_step
    return out
```

- [ ] **Step 2: Add the `build()` function with 5 panels**

Append to `analysis/china/evolution.py`:

```python
def build(snapshots=None):
    import plotly.graph_objects as go
    import plotly.subplots as sp

    all_snaps = list_snapshots()
    snapshots = snapshots or all_snaps
    snapshots = [s for s in snapshots if s in all_snaps]
    # only keep snaps where CN metrics exist
    snapshots = [s for s in snapshots
                 if (read_country_metrics(s, CC, 1) or {}).get('metrics')]
    if len(snapshots) < 2:
        save_placeholder_html(
            'evolution.html', 0,
            '中国时序演化', 'China Time-Series Evolution',
            f'需要 ≥ 2 个快照，当前只有 {snapshots}',
            f'Need ≥ 2 snapshots, found {snapshots}')
        return

    data = load_cn_series(snapshots)
    x = snapshots
    red = COLORS['red']
    cyan = COLORS['cyan']

    # ---- Panel 1: 16-indicator sparkline grid 4×4 ----
    panel1 = sp.make_subplots(
        rows=4, cols=4,
        subplot_titles=[m[0] for m in METRICS_TRACKED],
        vertical_spacing=0.08, horizontal_spacing=0.05,
    )
    for i, (label, step, key) in enumerate(METRICS_TRACKED):
        r, c = i // 4 + 1, i % 4 + 1
        ys = [_get(data[s], step, key) for s in snapshots]
        panel1.add_trace(go.Scatter(
            x=x, y=ys, mode='lines+markers',
            line=dict(color=red, width=1.7),
            marker=dict(size=5), showlegend=False,
        ), row=r, col=c)
    panel1.update_layout(
        title='① CN 16 项关键指标趋势 · Per-metric trajectory',
        height=780, hovermode='x unified',
    )

    # ---- Panel 2: Sovereignty Index + 5 components ----
    panel2 = go.Figure()
    main = [_get(data[s], 20, 'composite_sovereignty_index') for s in snapshots]
    panel2.add_trace(go.Scatter(
        x=x, y=main, mode='lines+markers',
        name='Sovereignty Index',
        line=dict(color=red, width=3),
        marker=dict(size=9),
    ))
    comp_colors = [cyan, COLORS['orange'], COLORS['purple'],
                   COLORS['green'], COLORS['yellow']]
    for (ckey, clabel), color in zip(SOV_COMPONENTS, comp_colors):
        ys = [(data[s].get(20, {}).get('components') or {}).get(ckey)
              for s in snapshots]
        panel2.add_trace(go.Scatter(
            x=x, y=ys, mode='lines+markers',
            name=clabel,
            line=dict(color=color, width=1.5, dash='dot'),
            marker=dict(size=6),
        ))
    panel2.update_layout(
        title='② 主权指数 + 5 分项 · Composite vs components',
        yaxis=dict(title='0 – 1', range=[0, 1]),
        height=500, hovermode='x unified',
    )

    # ---- Panel 3: Global rank trajectory (y reversed, rank #1 top) ----
    panel3 = go.Figure()
    rank_colors = [COLORS['red'], COLORS['orange'], COLORS['purple'],
                   COLORS['cyan'], COLORS['green'], COLORS['yellow']]
    for (label, step, key), color in zip(RANK_METRICS, rank_colors):
        ys = [_get(data[s], step, key) for s in snapshots]
        panel3.add_trace(go.Scatter(
            x=x, y=ys, mode='lines+markers',
            name=label,
            line=dict(color=color, width=2),
            marker=dict(size=7),
        ))
    panel3.update_layout(
        title='③ CN 全球排名轨迹 · Global rank trajectory (lower=better)',
        yaxis=dict(title='rank', autorange='reversed'),
        height=500, hovermode='x unified',
    )

    # ---- Panel 4: Outbound dependency composition (stacked bar) ----
    def top5_shift(step, key):
        cat = {}
        for s in snapshots:
            d = (data[s].get(step, {}) or {}).get(key, {}) or {}
            for k, v in d.items():
                cat.setdefault(k, {})[s] = v
        # pick top 5 by total across snapshots
        totals = [(k, sum(vs.values())) for k, vs in cat.items()]
        top = [k for k, _ in sorted(totals, key=lambda t: -t[1])[:5]]
        return top, {k: cat[k] for k in top}

    out_top, out_data = top5_shift(8, 'top_destination_countries')
    panel4 = go.Figure()
    out_colors = [COLORS['cyan'], COLORS['blue'], COLORS['purple'],
                  COLORS['orange'], COLORS['red']]
    for cc, color in zip(out_top, out_colors):
        ys = [out_data[cc].get(s, 0) for s in snapshots]
        panel4.add_trace(go.Bar(
            x=x, y=ys, name=cc, marker_color=color,
        ))
    panel4.update_layout(
        title='④ CN 出向依赖 Top-5 国家组成 · Outbound dependency mix',
        barmode='stack',
        yaxis=dict(title='edges'),
        height=440, hovermode='x unified',
    )

    # ---- Panel 5: Inbound dependency composition ----
    in_top, in_data = top5_shift(9, 'top_source_countries')
    panel5 = go.Figure()
    in_colors = [COLORS['yellow'], COLORS['green'], COLORS['cyan'],
                 COLORS['purple'], COLORS['red']]
    for cc, color in zip(in_top, in_colors):
        ys = [in_data[cc].get(s, 0) for s in snapshots]
        panel5.add_trace(go.Bar(
            x=x, y=ys, name=cc, marker_color=color,
        ))
    panel5.update_layout(
        title='⑤ CN 入向依赖 Top-5 国家组成 · Inbound dependency mix',
        barmode='stack',
        yaxis=dict(title='edges'),
        height=440, hovermode='x unified',
    )

    # ---- Narrative ----
    start_sov = main[0] if main[0] is not None else float('nan')
    end_sov = main[-1] if main[-1] is not None else float('nan')
    delta = (end_sov - start_sov) if main[0] is not None and main[-1] is not None else 0.0
    narrative = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'快照区间：<b>{snapshots[0]} → {snapshots[-1]}</b>（{len(snapshots)} 季度）。'
        f'综合主权指数：<b>{start_sov:.3f} → {end_sov:.3f}</b>（Δ {delta:+.3f}）。'
        f'本页聚焦 <b>CN</b> 单一国家跨 6 快照的深度视角——由 '
        f'analysis/countries/data/ 缓存直接装配，无需新 Neo4j 查询。'
        f'<br>Six quarterly snapshots focused on <b>CN</b>, rebuilt from the '
        f'existing per-country cache.'
        f'</p>'
    )

    body = narrative + plotly_inline_once(
        [panel1, panel2, panel3, panel4, panel5])
    save_consolidated_html(
        body,
        'evolution.html',
        f'中国时序演化 · {snapshots[0]} → {snapshots[-1]}（{len(snapshots)} 季度）',
        f'China Time-Series · {snapshots[0]} → {snapshots[-1]} '
        f'({len(snapshots)} quarters)',
        subtitle='CN-only deep view · reuses countries/ per-snapshot JSONs',
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--snapshots', nargs='+', default=None)
    args = ap.parse_args()
    build(snapshots=args.snapshots)


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: `save_consolidated_html` resolves to china/html/evolution.html?**

Check which `HTML_DIR` the import chain uses. The import is from
`analysis.countries.common`, so `save_consolidated_html` writes to
`analysis/countries/html/`. That's wrong — we want `analysis/china/html/`.

Fix: import from `analysis.china.common` instead where possible:

Replace the import block in `analysis/china/evolution.py` with:

```python
from analysis.china.common import (  # noqa: E402
    COLORS, DARK_BG, DARK_BORDER, DARK_PANEL, TEXT_PRIMARY, TEXT_SECONDARY,
    apply_plotly_theme, plotly_inline_once, save_consolidated_html,
    save_placeholder_html,
)
from analysis.countries.common import (  # noqa: E402
    list_snapshots, read_country_metrics,
)
```

- [ ] **Step 4: Run it**

```bash
cd /Volumes/data/internet-yellow-pages
.venv/bin/python -m analysis.china.evolution
```

Expected output: `[html] wrote /Volumes/data/internet-yellow-pages/analysis/china/html/evolution.html (NNNN KB)`

- [ ] **Step 5: Sanity-check the HTML**

```bash
grep -oE 'CN 16 项|主权指数 \+ 5 分项|CN 全球排名|CN 出向依赖|CN 入向依赖' \
  analysis/china/html/evolution.html | sort -u
```

Expected: 5 distinct matches, one per panel.

```bash
grep -oE '2025-01|2025-04|2025-07|2025-10|2026-01|2026-04' \
  analysis/china/html/evolution.html | sort -u
```

Expected: all 6 snapshot labels appear.

- [ ] **Step 6: Commit**

```bash
cd /Volumes/data/internet-yellow-pages
git add analysis/china/evolution.py analysis/china/html/evolution.html
git commit -m "china/evolution.py: 5-panel CN time-series (reuses countries/CN data)"
```

---

## Task 2 · Network evolution extractor + renderer

**Files:**
- Create: `analysis/complex_network/network_evolution.py`

- [ ] **Step 1: Write the module**

```python
# analysis/complex_network/network_evolution.py
"""Global network-level time-series.

Two modes:
  --extract --snapshot YYYY-MM : run lightweight Cypher aggregates
      against the currently-loaded Neo4j, merge into
      complex_network_images/evolution_data.json.
  --render : read evolution_data.json, render evolution.html.
      No Neo4j needed.
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.complex_network.utils import run_query  # noqa: E402
from analysis.china.common import (  # noqa: E402
    COLORS, DARK_BG, DARK_BORDER, DARK_PANEL, TEXT_PRIMARY, TEXT_SECONDARY,
    apply_plotly_theme, plotly_inline_once, save_consolidated_html,
    save_placeholder_html,
)

IMG_DIR = Path(__file__).resolve().parent.parent / 'complex_network_images'
DATA_FILE = IMG_DIR / 'evolution_data.json'

TARGET_COUNTRIES = ['US', 'CN', 'JP', 'IN', 'DE', 'GB', 'FR', 'NL', 'RU']


def _q1(cypher, **params):
    """Run a Cypher that returns one scalar row; return the scalar or None."""
    try:
        rec = run_query(cypher, params)
        if rec and len(rec) > 0:
            row = rec[0]
            # Return the first value
            return list(row.values())[0]
    except Exception as e:
        print(f'    ! cypher failed: {type(e).__name__}: {str(e)[:120]}',
              flush=True)
    return None


def extract_snapshot(snapshot):
    print(f'[extract {snapshot}] starting', flush=True)
    metrics = {}

    metrics['as_count'] = _q1('MATCH (a:AS) RETURN count(a) AS c')
    metrics['ixp_count'] = _q1('MATCH (i:IXP) RETURN count(i) AS c')
    metrics['facility_count'] = _q1('MATCH (f:Facility) RETURN count(f) AS c')
    metrics['peering_edges'] = _q1(
        'MATCH ()-[r:PEERS_WITH]->() RETURN count(r) AS c')
    metrics['dependency_edges'] = _q1(
        'MATCH ()-[r:DEPENDS_ON]->() RETURN count(r) AS c')
    metrics['prefix_count'] = _q1(
        'MATCH (p:BGPPrefix) RETURN count(p) AS c')
    metrics['rpki_valid_prefixes'] = _q1(
        "MATCH (p:BGPPrefix)-[:CATEGORIZED]->(t:Tag {label:'RPKI Valid'}) "
        'RETURN count(DISTINCT p) AS c')
    if metrics['prefix_count'] and metrics['rpki_valid_prefixes'] is not None:
        metrics['rpki_pct'] = round(
            metrics['rpki_valid_prefixes'] / metrics['prefix_count'] * 100, 2)

    # Mean peering degree = 2 * peering_edges / as_count
    if metrics['peering_edges'] and metrics['as_count']:
        metrics['mean_peering_degree'] = round(
            2 * metrics['peering_edges'] / metrics['as_count'], 3)

    # Top-10 AS prefix origination share
    top_recs = _q1(
        'MATCH (a:AS)-[:ORIGINATE]->(p:BGPPrefix) '
        'WITH a, count(DISTINCT p) AS pfx '
        'ORDER BY pfx DESC LIMIT 10 '
        'RETURN collect(pfx) AS counts')
    if isinstance(top_recs, list):
        top10 = sum(top_recs)
        if metrics['prefix_count']:
            metrics['top10_prefix_share_pct'] = round(
                top10 / metrics['prefix_count'] * 100, 2)
            metrics['top10_prefix_counts'] = top_recs

    # Per-country AS count (for regional shift panel)
    cc_counts = {}
    for cc in TARGET_COUNTRIES:
        cc_counts[cc] = _q1(
            'MATCH (a:AS)-[:COUNTRY]->(c:Country {country_code:$cc}) '
            'RETURN count(DISTINCT a) AS c', cc=cc)
    metrics['as_by_country'] = cc_counts

    # Merge into JSON file
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    store = {}
    if DATA_FILE.exists():
        try:
            store = json.loads(DATA_FILE.read_text())
        except json.JSONDecodeError:
            store = {}
    store[snapshot] = metrics
    DATA_FILE.write_text(json.dumps(store, indent=2, ensure_ascii=False))
    print(f'[extract {snapshot}] done: {len(metrics)} fields → {DATA_FILE}',
          flush=True)


def render():
    import plotly.graph_objects as go
    import plotly.subplots as sp

    if not DATA_FILE.exists():
        save_placeholder_html(
            'evolution.html', 0,
            '网络时序演化', 'Network Time-Series',
            '缺少 evolution_data.json，请先跑 --extract',
            'Missing evolution_data.json, run --extract first')
        return
    store = json.loads(DATA_FILE.read_text())
    snapshots = sorted(store.keys())
    if len(snapshots) < 2:
        save_placeholder_html(
            'evolution.html', 0,
            '网络时序演化', 'Network Time-Series',
            f'需要 ≥ 2 个快照，目前 {snapshots}',
            f'Need ≥ 2 snapshots, found {snapshots}')
        return

    def series(key):
        return [store[s].get(key) for s in snapshots]

    # Panel 1: scale (AS / peering / dependency / IXP / facility)
    panel1 = sp.make_subplots(
        rows=1, cols=5,
        subplot_titles=['AS', 'Peering edges', 'Dependency edges',
                        'IXP', 'Facility'],
        shared_yaxes=False, horizontal_spacing=0.05)
    scale_colors = [COLORS['red'], COLORS['cyan'], COLORS['purple'],
                    COLORS['orange'], COLORS['green']]
    for i, k in enumerate(['as_count', 'peering_edges', 'dependency_edges',
                           'ixp_count', 'facility_count']):
        panel1.add_trace(go.Scatter(
            x=snapshots, y=series(k), mode='lines+markers',
            line=dict(color=scale_colors[i], width=2),
            marker=dict(size=7),
            showlegend=False,
        ), row=1, col=i + 1)
    panel1.update_layout(
        title='① 规模轨迹 · Global scale across quarters',
        height=340, hovermode='x unified',
    )

    # Panel 2: topology (mean degree, rpki_pct)
    panel2 = go.Figure()
    panel2.add_trace(go.Scatter(
        x=snapshots, y=series('mean_peering_degree'),
        mode='lines+markers', name='Mean peering degree',
        line=dict(color=COLORS['cyan'], width=2.3),
        marker=dict(size=8),
    ))
    panel2.update_layout(
        title='② 拓扑形态 · Mean peering degree',
        yaxis=dict(title='mean degree'),
        height=380, hovermode='x unified',
    )

    # Panel 3: concentration (top-10 prefix share)
    panel3 = go.Figure()
    panel3.add_trace(go.Scatter(
        x=snapshots, y=series('top10_prefix_share_pct'),
        mode='lines+markers',
        line=dict(color=COLORS['orange'], width=2.3),
        marker=dict(size=8),
    ))
    panel3.update_layout(
        title='③ 权力集中 · Top-10 AS prefix share (%)',
        yaxis=dict(title='% of global prefixes'),
        height=380, hovermode='x unified',
    )

    # Panel 4: RPKI security
    panel4 = go.Figure()
    panel4.add_trace(go.Scatter(
        x=snapshots, y=series('rpki_pct'),
        mode='lines+markers',
        line=dict(color=COLORS['green'], width=2.3),
        marker=dict(size=8),
    ))
    panel4.update_layout(
        title='④ 路由安全 · Global RPKI Valid prefix share (%)',
        yaxis=dict(title='%'),
        height=380, hovermode='x unified',
    )

    # Panel 5: regional shift (AS count for 9 target countries stacked)
    cc_series = {cc: [] for cc in TARGET_COUNTRIES}
    for s in snapshots:
        m = (store[s].get('as_by_country') or {})
        for cc in TARGET_COUNTRIES:
            cc_series[cc].append(m.get(cc) or 0)
    panel5 = go.Figure()
    region_colors = [COLORS['red'], COLORS['orange'], COLORS['yellow'],
                     COLORS['green'], COLORS['cyan'], COLORS['blue'],
                     COLORS['purple'], COLORS['pink'], '#888']
    for cc, color in zip(TARGET_COUNTRIES, region_colors):
        panel5.add_trace(go.Scatter(
            x=snapshots, y=cc_series[cc],
            mode='lines+markers', name=cc, stackgroup='one',
            line=dict(color=color, width=1),
        ))
    panel5.update_layout(
        title='⑤ 区域 AS 分布 · AS count for 9 target countries',
        yaxis=dict(title='AS count'),
        height=460, hovermode='x unified',
    )

    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'快照区间：<b>{snapshots[0]} → {snapshots[-1]}</b>（{len(snapshots)} 季度）。'
        f'每个快照抽取 ~10 个全局汇总指标。'
        f'<br>Global network time-series: ~10 aggregate Cypher metrics '
        f'per snapshot ({len(snapshots)} quarters).'
        f'</p>'
    )
    body = intro + plotly_inline_once(
        [panel1, panel2, panel3, panel4, panel5])

    # write to complex_network_images/ directly (bypasses save_consolidated_html
    # which assumes the analysis/china HTML_DIR)
    from analysis.china.common import build_banner, BANNER_CSS
    title_zh = (f'网络时序演化 · {snapshots[0]} → {snapshots[-1]}'
                f'（{len(snapshots)} 季度）')
    title_en = (f'Global Network Time-Series · {snapshots[0]} → {snapshots[-1]} '
                f'({len(snapshots)} quarters)')
    subtitle = (f'{len(snapshots)} snapshots · 10 aggregate metrics · '
                f'no cache dependencies')
    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        f'<title>{title_zh}</title>'
        f'{BANNER_CSS}</head><body>'
        f'{build_banner(title_zh, title_en, subtitle)}'
        f'<div class="content">{body}</div>'
        '</body></html>'
    )
    out = IMG_DIR / 'evolution.html'
    out.write_text(html, encoding='utf-8')
    print(f'[render] wrote {out} ({out.stat().st_size // 1024} KB)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--extract', action='store_true',
                    help='run Cypher aggregates against current Neo4j')
    ap.add_argument('--render', action='store_true',
                    help='build evolution.html from evolution_data.json')
    ap.add_argument('--snapshot', default=None,
                    help='YYYY-MM tag for this snapshot')
    args = ap.parse_args()
    if args.extract:
        if not args.snapshot:
            raise SystemExit('--extract requires --snapshot YYYY-MM')
        extract_snapshot(args.snapshot)
    if args.render:
        render()


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Syntax-check**

```bash
cd /Volumes/data/internet-yellow-pages
.venv/bin/python -c "import analysis.complex_network.network_evolution"
```

Expected: silent (import succeeds).

- [ ] **Step 3: Commit (before the orchestrator + execution)**

```bash
cd /Volumes/data/internet-yellow-pages
git add analysis/complex_network/network_evolution.py
git commit -m "network_evolution: lightweight global Cypher aggregates + render"
```

---

## Task 3 · Orchestrator script

**Files:**
- Create: `analysis/complex_network/run_network_evolution.sh`

- [ ] **Step 1: Write the shell script**

```bash
#!/usr/bin/env bash
# Run network_evolution.py --extract against each of the 6 quarterly dumps,
# then a single --render pass. Reuses analysis/countries/extract_snapshot.sh's
# docker + Neo4j lifecycle pattern.
set -uo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
ARCHIVE="$REPO/dumps_archive"
DUMPS="$REPO/dumps"
DATA="$REPO/data"
VENV_PY="$REPO/.venv/bin/python"
LOG="$REPO/analysis/complex_network/network_evolution.log"

SNAPS=(
  "2025-01:2025-01-08"
  "2025-04:2025-04-08"
  "2025-07:2025-07-08"
  "2025-10:2025-10-08"
  "2026-01:2026-01-15"
  "2026-04:2026-04-08"
)

# Portable file-size helper (macOS stat -f%z, Linux stat -c%s)
fsize() { stat -f%z "$1" 2>/dev/null || stat -c%s "$1" 2>/dev/null || echo 0; }

wait_neo4j() {
    for i in $(seq 1 180); do
        sleep 5
        if "$VENV_PY" -c "
from neo4j import GraphDatabase
try:
    d = GraphDatabase.driver('bolt://localhost:7687')
    with d.session() as s:
        r = s.run('MATCH (n) RETURN count(n) AS c').single()
    print(r['c'])
except Exception:
    raise SystemExit(1)
" 2>/dev/null | grep -qE '^[0-9]+$'; then
            echo "  Neo4j ready (${i}x5s)"
            return 0
        fi
    done
    return 1
}

echo "=== network-evolution pipeline start $(date -Iseconds) ===" | tee -a "$LOG"
for entry in "${SNAPS[@]}"; do
    SNAP="${entry%:*}"
    DATE="${entry#*:}"
    DUMP="$ARCHIVE/iyp-$DATE.dump"
    echo "=== [$SNAP] ===" | tee -a "$LOG"

    # Download if missing (2025-04 / 2026-04 may not be on disk)
    if [ ! -f "$DUMP" ]; then
        URL="https://archive.ihr.live/ihr/iyp/${DATE:0:4}/${DATE:5:2}/${DATE:8:2}/iyp-$DATE.dump"
        echo "  downloading $URL" | tee -a "$LOG"
        if ! curl -L --no-progress-meter "$URL" -o "$DUMP"; then
            echo "  FAIL download; skipping $SNAP" | tee -a "$LOG"
            continue
        fi
        echo "  dump size: $(($(fsize "$DUMP")/1024/1024)) MB" | tee -a "$LOG"
    fi

    echo "  staging $DUMP → $DUMPS/neo4j.dump" | tee -a "$LOG"
    cp "$DUMP" "$DUMPS/neo4j.dump"

    echo "  resetting containers + data" | tee -a "$LOG"
    docker stop iyp iyp_loader 2>/dev/null || true
    docker rm iyp iyp_loader 2>/dev/null || true
    rm -rf "$DATA/databases" "$DATA/transactions"

    echo "  docker compose up" | tee -a "$LOG"
    cd "$REPO"
    uid="$(id -u)" gid="$(id -g)" docker compose --profile local up -d

    if ! wait_neo4j; then
        echo "  ERROR Neo4j not ready; skipping $SNAP" | tee -a "$LOG"
        continue
    fi

    echo "  running --extract --snapshot $SNAP" | tee -a "$LOG"
    "$VENV_PY" -m analysis.complex_network.network_evolution \
        --extract --snapshot "$SNAP" 2>&1 | tee -a "$LOG"

    echo "  teardown" | tee -a "$LOG"
    docker stop iyp iyp_loader 2>/dev/null || true
    docker rm iyp iyp_loader 2>/dev/null || true
    rm -rf "$DATA/databases" "$DATA/transactions"
    rm -f "$DUMPS/neo4j.dump"
done

echo "=== render $(date -Iseconds) ===" | tee -a "$LOG"
"$VENV_PY" -m analysis.complex_network.network_evolution --render 2>&1 | tee -a "$LOG"
echo "=== network-evolution pipeline done $(date -Iseconds) ===" | tee -a "$LOG"
```

- [ ] **Step 2: Make executable**

```bash
chmod +x /Volumes/data/internet-yellow-pages/analysis/complex_network/run_network_evolution.sh
```

- [ ] **Step 3: Commit**

```bash
cd /Volumes/data/internet-yellow-pages
git add analysis/complex_network/run_network_evolution.sh
git commit -m "run_network_evolution.sh: 6-snapshot Neo4j-swap orchestrator"
```

---

## Task 4 · Execute the network-evolution pipeline

**Files:** none (runs Task 3 script)

- [ ] **Step 1: Launch in background**

```bash
cd /Volumes/data/internet-yellow-pages
./analysis/complex_network/run_network_evolution.sh
```

(agentic worker: use `run_in_background: true`)

Expected wall-clock: ~12 min of Neo4j work + ~1 min render.

- [ ] **Step 2: Arm a Monitor**

```bash
tail -n 0 -F /Volumes/data/internet-yellow-pages/analysis/complex_network/network_evolution.log \
  | grep -E --line-buffered "=== |Neo4j ready|--extract|done:|FAIL|ERROR|Traceback"
```

(agentic worker: use Monitor tool with persistent=true.)

- [ ] **Step 3: Wait for `=== network-evolution pipeline done ===`**

Use `ScheduleWakeup(delaySeconds=1500)` heartbeats if running autonomously.

- [ ] **Step 4: Sanity-check `evolution_data.json` has 6 entries**

```bash
.venv/bin/python -c "
import json
from pathlib import Path
p = Path('analysis/complex_network_images/evolution_data.json')
store = json.loads(p.read_text())
print('snapshots:', sorted(store.keys()))
for s in sorted(store.keys()):
    m = store[s]
    print(f'  {s}: as={m.get(\"as_count\"):,} peering={m.get(\"peering_edges\"):,} rpki%={m.get(\"rpki_pct\")}')"
```

Expected: 6 lines showing snapshot → as_count / peering_edges / rpki_pct.

- [ ] **Step 5: Sanity-check the rendered HTML**

```bash
ls -la analysis/complex_network_images/evolution.html
grep -oE '规模轨迹|拓扑形态|权力集中|路由安全|区域 AS 分布' \
  analysis/complex_network_images/evolution.html | sort -u
```

Expected: 5 distinct matches.

- [ ] **Step 6: Commit the data + HTML**

```bash
cd /Volumes/data/internet-yellow-pages
git add analysis/complex_network_images/evolution_data.json \
        analysis/complex_network_images/evolution.html
git commit -m "Add global network time-series: 6 snapshots × 10 aggregates + rendered HTML"
```

---

## Task 5 · Register Evolution pages in site nav

**Files:**
- Modify: `analysis/web/nav.py`

- [ ] **Step 1: Update snapshot constants**

In `analysis/web/nav.py:31-32`, change:

```python
SNAPSHOT_LATEST = '2026-04'
SNAPSHOT_PREV = '2025-04'
```

to:

```python
SNAPSHOT_LATEST = '2026-04'
SNAPSHOT_PREV = '2025-04'  # retained for leaderboard Δ-1y display
SNAPSHOT_BASELINE = '2025-01'  # 15-month baseline for "Δ since launch"
```

- [ ] **Step 2: Add Evolution page to China track**

Find `_build_china_track()` (around line 136). After the `phases` loop,
prepend a "Dashboards" phase containing an Evolution page. Replace the
`return Track(...)` block with:

```python
    # Prepend a Dashboards phase with the cross-snapshot evolution page
    dash_pages = [Page(
        slug='evolution',
        url='/china/evolution/',
        track='china',
        title_zh='时序演化',
        title_en='Time-Series Evolution',
        kind='plotly',
        src='../../../../china/html/evolution.html',
        phase='dashboards',
        kpis=['6 季度', 'CN 深度'],
    )]
    phases.insert(0, Phase('dashboards', '综合仪表板', 'Dashboards', dash_pages))
    return Track(
        slug='china',
        title_zh='中国互联网全球位置',
        title_en='China in the Global Internet Hierarchy',
        tagline_zh='20 步系统性考察中国在全球互联网分层中的位置与依赖',
        tagline_en='20 analytical steps examining China across BGP · DNS · IXP · content · sovereignty.',
        accent='#ff453a',
        phases=phases,
        hub_url='/china/',
    )
```

- [ ] **Step 3: Add Evolution page to Network track**

Find `_build_network_track()` (around line 329). Similar to Task 5 Step 2,
prepend a dashboards phase:

```python
    dash_pages = [Page(
        slug='evolution',
        url='/network/evolution/',
        track='network',
        title_zh='时序演化',
        title_en='Network Time-Series',
        kind='plotly',
        src='../../../../complex_network_images/evolution.html',
        phase='dashboards',
        kpis=['6 季度', '10 指标'],
    )]
    phases.insert(0, Phase('dashboards', '综合仪表板', 'Dashboards', dash_pages))
    return Track(
        slug='network',
        title_zh='全球复杂网络分析',
        title_en='Global Complex-Network Analysis',
        tagline_zh='把互联网视为 BGP × DNS × 物理 × 组织 四层多重网络的全栈拓扑体检',
        tagline_en='The Internet as a four-layer multiplex — a full-stack complex-network audit.',
        accent='#30d158',
        phases=phases,
        hub_url='/network/',
    )
```

- [ ] **Step 4: Update leaderboard baseline**

In `build_site_model()` (around line 380-396), replace the leaderboard
loop with a version that computes both 1y and 15-month deltas:

```python
    # Sovereignty leaderboard for home-page footer
    leaderboard: list[dict] = []
    for cc, zh, en in COUNTRY_NAMES:
        sov_now = _country_sov(cc, SNAPSHOT_LATEST)
        sov_prev = _country_sov(cc, SNAPSHOT_PREV)
        sov_base = _country_sov(cc, SNAPSHOT_BASELINE)
        if sov_now is None:
            continue
        leaderboard.append({
            'cc': cc,
            'zh': zh,
            'en': en,
            'sov_now': sov_now,
            'sov_prev': sov_prev,
            'sov_base': sov_base,
            'delta': (sov_now - sov_prev) if sov_prev is not None else None,
            'delta_baseline': (sov_now - sov_base) if sov_base is not None else None,
            'url': f'/countries/{cc}/',
        })
    leaderboard.sort(key=lambda r: r['sov_now'], reverse=True)
```

And add `'snapshot_baseline': SNAPSHOT_BASELINE,` to the returned dict
(alongside `snapshot_latest` and `snapshot_prev`).

- [ ] **Step 5: Smoke-test the site model loads**

```bash
cd /Volumes/data/internet-yellow-pages
.venv/bin/python -c "
from analysis.web.nav import build_site_model
m = build_site_model()
print('tracks:', list(m['tracks'].keys()))
for t in m['tracks_list']:
    dash = [p for p in t.all_pages() if p.phase == 'dashboards']
    print(f'  {t.slug}: {len(t.all_pages())} pages, {len(dash)} dashboards')
print('baseline:', m['snapshot_baseline'])
print('leaderboard first:', m['leaderboard'][0])"
```

Expected:
- china has at least 1 dashboard (evolution)
- network has at least 1 dashboard (evolution)
- countries has its existing 4 dashboards
- baseline = 2025-01
- leaderboard[0] has `delta_baseline` key

- [ ] **Step 6: Commit**

```bash
cd /Volumes/data/internet-yellow-pages
git add analysis/web/nav.py
git commit -m "web/nav: register evolution pages on China + Network; add 15-month baseline"
```

---

## Task 6 · Site build + templates

**Files:**
- Modify: `analysis/web/build.py` (minimal, if any)
- Modify: `analysis/web/templates/index.html.j2` — add Time-Series section
- Modify: track landing templates if exist (probe first)

- [ ] **Step 1: Probe the template directory**

```bash
ls analysis/web/templates/ 2>/dev/null
```

- [ ] **Step 2: Find the index template**

```bash
grep -l '三条研究路径\|track_card\|leaderboard' analysis/web/templates/*.j2
```

Record the filename. For the remaining steps, call it `<INDEX_TPL>`.

- [ ] **Step 3: Add Time-Series section to index template**

Edit `<INDEX_TPL>` — after the `<div class="grid-3">` (three track cards)
closing `</div>`, add (before the leaderboard section):

```jinja
<div class="section-head">
    <h2>时序演化 · Time-Series</h2>
    <span class="en">{{ snapshot_baseline }} → {{ snapshot_latest }} ({{ totals.quarters or 6 }} quarters)</span>
    <span class="rule"></span>
</div>

<div class="grid-3">
    <a class="track-card" href="china/evolution/" style="--track-accent: #ff453a;">
        <span class="num">China · CN 深度</span>
        <div>
            <h3>中国 15 个月轨迹</h3>
            <p class="en">CN across 6 quarterly snapshots</p>
        </div>
        <p class="desc">主权指数、依赖结构、全球排名的季度演化</p>
        <span class="cta">查看 → View</span>
    </a>
    <a class="track-card" href="countries/evolution.html" style="--track-accent: #0071e3;">
        <span class="num">Countries · 九国对比</span>
        <div>
            <h3>九国趋势 + CAGR</h3>
            <p class="en">9 countries × 12 metrics × 6 quarters</p>
        </div>
        <p class="desc">趋势线、CAGR 热图、拐点榜、排名波动带</p>
        <span class="cta">查看 → View</span>
    </a>
    <a class="track-card" href="network/evolution/" style="--track-accent: #30d158;">
        <span class="num">Network · 全球拓扑</span>
        <div>
            <h3>网络规模 + 集中度演化</h3>
            <p class="en">10 global aggregates across 6 quarters</p>
        </div>
        <p class="desc">规模、拓扑、集中度、RPKI、区域分布</p>
        <span class="cta">查看 → View</span>
    </a>
</div>
```

- [ ] **Step 4: Update the leaderboard subtitle**

Search for `Δ vs 2025-04` in `<INDEX_TPL>`. Replace with:

```jinja
Δ vs {{ snapshot_baseline }} (15 months)
```

And update the leaderboard row rendering to prefer `delta_baseline` over
`delta`. Find the `<div class="d ...">` block and change the variable
reference.

- [ ] **Step 5: Run build**

```bash
cd /Volumes/data/internet-yellow-pages
.venv/bin/python -m analysis.web.build
```

Expected: builds complete; prints written pages; no errors.

- [ ] **Step 6: Verify outputs**

```bash
ls -la analysis/web/site/china/evolution/ 2>/dev/null
ls -la analysis/web/site/network/evolution/ 2>/dev/null
grep -c '时序演化 · Time-Series' analysis/web/site/index.html
```

Expected: both evolution dirs exist with `index.html` inside, and
index.html contains at least 1 "时序演化 · Time-Series" heading.

- [ ] **Step 7: Commit**

```bash
cd /Volumes/data/internet-yellow-pages
git add analysis/web/templates/ analysis/web/build.py analysis/web/site/
git commit -m "web: surface evolution pages on home + track landings, 15-month baseline"
```

---

## Task 7 · Final verification

**Files:** none

- [ ] **Step 1: Open the three new pages in order**

```bash
for f in analysis/china/html/evolution.html \
         analysis/countries/html/evolution.html \
         analysis/complex_network_images/evolution.html \
         analysis/web/site/index.html \
         analysis/web/site/china/evolution/index.html \
         analysis/web/site/network/evolution/index.html; do
    if [ -f "$f" ]; then
        echo "OK   $f ($(stat -f%z "$f") bytes)"
    else
        echo "MISS $f"
    fi
done
```

Expected: 6 × OK.

- [ ] **Step 2: Confirm git status clean for data artifacts**

```bash
cd /Volumes/data/internet-yellow-pages
git status --short | grep -v '^?? \.DS\|^?? \.claude\|^?? analysis/web' | head
```

Expected: empty (all intended changes committed).

- [ ] **Step 3: Print summary**

```bash
cd /Volumes/data/internet-yellow-pages
.venv/bin/python <<'PY'
import json
from pathlib import Path
d = json.loads(Path('analysis/complex_network_images/evolution_data.json').read_text())
print(f'Network evolution: {len(d)} snapshots')
for s in sorted(d):
    m = d[s]
    print(f'  {s}: AS={m.get("as_count"):,} Peering={m.get("peering_edges"):,} RPKI%={m.get("rpki_pct")}')
PY
```

Expected: 6 rows with realistic values.

---

## Self-Review

**Spec coverage:**

- Component 1 (China evolution page) → Task 1.
- Component 2 (Network evolution extractor + renderer) → Tasks 2, 3, 4.
- Component 3 (site integration) → Tasks 5, 6.
- Final verification → Task 7.
- Scope "5 panels per page" → Tasks 1 Step 2 (5 panels) and 2 Step 1 (5 panels) match.
- Snapshot set 2025-01 … 2026-04 → Task 3 SNAPS array lists all 6.
- dumps-archive reuse → Task 3 Step 1 reuses existing dumps when present and
  only downloads missing ones (2025-04 + 2026-04 may not be cached).
- Error handling (missing CN JSONs, Neo4j unavailable, incomplete snapshot
  coverage) → Task 1 Step 2 (placeholder), Task 2 Step 1 (`wait_neo4j`
  returns non-zero, orchestrator skips), Task 2 Step 1 (`render` placeholder
  when data file missing or < 2 snapshots).
- Rollback → no dedicated task but spec's `git rm` and `git checkout --`
  instructions are single-line operations.
- Autonomous execution → Task 4 Step 1 directs `run_in_background: true` for
  agentic execution, matches the user's "纯后台" preference.

**Placeholder scan:** No `TBD` / `TODO`. One phrase to fix:
"minimal, if any" for build.py in Task 6 file list — kept intentionally
because build.py may need zero edits once nav.py supplies the pages
(the build system already iframes any Page with `src`). If build.py
does need edits they will be discovered during Task 6 Step 5 when
running `python -m analysis.web.build` and diagnosing errors.

**Type consistency:** `SNAPSHOT_BASELINE`, `SNAPSHOT_LATEST`, `SNAPSHOT_PREV`
used consistently in nav.py (Task 5). `snapshot` vs `snap` naming: scripts
use `snapshot` for the string-typed argument and `store[snapshot]` as the
dict key. `evolution_data.json` schema is flat `{snapshot: metrics_dict}`,
consistent between `extract_snapshot()` and `render()`.

Plan is ready.
