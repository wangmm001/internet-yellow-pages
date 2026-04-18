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
    BANNER_CSS, COLORS, DARK_BG, DARK_BORDER, DARK_PANEL,
    TEXT_PRIMARY, TEXT_SECONDARY, apply_plotly_theme,
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
    # Prefix label varies across snapshots: 2025-04+ uses BGPPrefix,
    # older snapshots sometimes only carry the generic Prefix label.
    # Try specific first, fallback to generic.
    metrics['prefix_count'] = (
        _q1('MATCH (p:BGPPrefix) RETURN count(p) AS c')
        or _q1('MATCH (p:Prefix) RETURN count(p) AS c'))
    metrics['rpki_valid_prefixes'] = (
        _q1("MATCH (p:BGPPrefix)-[:CATEGORIZED]->(t:Tag {label:'RPKI Valid'}) "
            'RETURN count(DISTINCT p) AS c')
        or _q1("MATCH (p:Prefix)-[:CATEGORIZED]->(t:Tag {label:'RPKI Valid'}) "
               'RETURN count(DISTINCT p) AS c'))
    if metrics['prefix_count'] and metrics['rpki_valid_prefixes'] is not None:
        metrics['rpki_pct'] = round(
            metrics['rpki_valid_prefixes'] / metrics['prefix_count'] * 100, 2)

    if metrics['peering_edges'] and metrics['as_count']:
        metrics['mean_peering_degree'] = round(
            2 * metrics['peering_edges'] / metrics['as_count'], 3)

    top_recs = (
        _q1('MATCH (a:AS)-[:ORIGINATE]->(p:BGPPrefix) '
            'WITH a, count(DISTINCT p) AS pfx '
            'ORDER BY pfx DESC LIMIT 10 '
            'RETURN collect(pfx) AS counts')
        or _q1('MATCH (a:AS)-[:ORIGINATE]->(p:Prefix) '
               'WITH a, count(DISTINCT p) AS pfx '
               'ORDER BY pfx DESC LIMIT 10 '
               'RETURN collect(pfx) AS counts'))
    if isinstance(top_recs, list):
        top10 = sum(top_recs)
        if metrics['prefix_count']:
            metrics['top10_prefix_share_pct'] = round(
                top10 / metrics['prefix_count'] * 100, 2)
            metrics['top10_prefix_counts'] = top_recs

    cc_counts = {}
    for cc in TARGET_COUNTRIES:
        cc_counts[cc] = _q1(
            'MATCH (a:AS)-[:COUNTRY]->(c:Country {country_code:$cc}) '
            'RETURN count(DISTINCT a) AS c', cc=cc)
    metrics['as_by_country'] = cc_counts

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


def _banner(title_zh, title_en, subtitle=''):
    sub = f'<div class="step-footer">{subtitle}</div>' if subtitle else ''
    return (
        '<div class="step-banner">'
        f'<h1>{title_zh}</h1>'
        f'<h2>{title_en}</h2>'
        '</div>' + sub
    )


def _plotly_inline(figs):
    from plotly.io import to_html
    out = []
    first = True
    for fig in figs:
        apply_plotly_theme(fig)
        out.append(to_html(
            fig,
            include_plotlyjs=('inline' if first else False),
            full_html=False,
            default_height='560px',
        ))
        first = False
    return '\n'.join(out)


def render():
    import plotly.graph_objects as go
    import plotly.subplots as sp

    out_path = IMG_DIR / 'evolution.html'
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    def _write_placeholder(msg_zh, msg_en):
        html = (
            '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
            '<title>网络时序演化</title>'
            f'{BANNER_CSS}</head><body>'
            f'{_banner("网络时序演化", "Global Network Time-Series", "")}'
            f'<div class="content"><p>{msg_zh}</p><p>{msg_en}</p></div>'
            '</body></html>'
        )
        out_path.write_text(html, encoding='utf-8')
        print(f'[placeholder] wrote {out_path}')

    if not DATA_FILE.exists():
        _write_placeholder(
            '缺少 evolution_data.json，请先跑 --extract',
            'Missing evolution_data.json, run --extract first')
        return
    store = json.loads(DATA_FILE.read_text())
    snapshots = sorted(store.keys())
    if len(snapshots) < 2:
        _write_placeholder(
            f'需要 ≥ 2 个快照，目前 {snapshots}',
            f'Need ≥ 2 snapshots, found {snapshots}')
        return

    def series(key):
        return [store[s].get(key) for s in snapshots]

    # Panel 1: scale
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

    # Panel 2: topology
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

    # Panel 3: concentration
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

    # Panel 4: RPKI
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

    # Panel 5: regional shift (9 target countries stacked)
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

    incomplete = [
        s for s in snapshots
        if (store[s].get('rpki_pct') in (None, 0)
            and store[s].get('dependency_edges') in (None, 0))
    ]
    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'快照区间：<b>{snapshots[0]} → {snapshots[-1]}</b>'
        f'（{len(snapshots)} 季度）。'
        f'每个快照抽取 ~10 个全局汇总指标。'
        f'<br>Global network time-series: ~10 aggregate Cypher metrics '
        f'per snapshot ({len(snapshots)} quarters).'
        f'</p>'
    )
    if incomplete:
        joined = ', '.join(incomplete)
        intro += (
            f'<p style="margin:4px 16px 12px;padding:10px 14px;'
            f'border-left:3px solid #ff9f0a;background:rgba(255,159,10,0.08);'
            f'color:{TEXT_PRIMARY};font-size:13px;border-radius:4px">'
            f'⚠️ <b>Baseline 数据空洞 · Incomplete baseline:</b> 快照 '
            f'<code>{joined}</code> 早于 IYP <code>:BGPPrefix</code> 标签 '
            f'+ <code>AS_DEPENDS_ON</code> 关系的引入，'
            f'③ Top-10 prefix share、④ RPKI% 及 ① Dependency edges '
            f'在该点读作 0 — 非真实下跌。'
            f'<br>Snapshot(s) <code>{joined}</code> predate the '
            f'<code>:BGPPrefix</code> label and <code>AS_DEPENDS_ON</code> '
            f'edges; panels ③ ④ and dependency-edge series of ① show 0 '
            f'at those points — not a real drop.</p>'
        )
    body = intro + _plotly_inline(
        [panel1, panel2, panel3, panel4, panel5])

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
        f'{_banner(title_zh, title_en, subtitle)}'
        f'<div class="content">{body}</div>'
        '</body></html>'
    )
    out_path.write_text(html, encoding='utf-8')
    print(f'[render] wrote {out_path} ({out_path.stat().st_size // 1024} KB)')


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
