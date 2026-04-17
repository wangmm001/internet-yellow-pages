"""Cross-country AS-dependency matrix.

Reads as_dependency.csv + as_country.csv and aggregates per (src_cc, dst_cc)
pair, then produces:
  - 9×9 heatmap of aggregated hegemony
  - Sankey of top 30 inter-country flows
  - Per-country donut of dependencies-by-destination-country
"""
import argparse
import csv
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.countries.common import (  # noqa: E402
    COLORS, DARK_BG, DARK_BORDER, DARK_PANEL, HTML_DIR, TEXT_PRIMARY,
    TARGET_COUNTRIES, apply_plotly_theme, bilingual, country_color, en,
    load_country_as_map, plotly_inline_once, save_consolidated_html, zh,
)
from analysis.complex_network.utils import DATA_DIR as CACHE_DIR


def aggregate_matrix(hege_min=0.03, include=None):
    """Build (src_cc, dst_cc) → aggregated hegemony and edge-count matrices."""
    include = include or set(TARGET_COUNTRIES)
    # Reverse: asn → primary country
    cmap = load_country_as_map()
    as_cc = {}
    for cc, asns in cmap.items():
        for a in asns:
            as_cc.setdefault(a, cc)  # first-seen wins (registration priority)

    path = os.path.join(CACHE_DIR, 'as_dependency.csv')
    agg = defaultdict(lambda: {'sum_h': 0.0, 'count': 0})
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                s = int(r['src'])
                d = int(r['dst'])
                h = float(r['hege'])
            except Exception:
                continue
            if s == d or h < hege_min:
                continue
            scc = as_cc.get(s)
            dcc = as_cc.get(d)
            if not scc or not dcc:
                continue
            if scc not in include or dcc not in include:
                continue
            agg[(scc, dcc)]['sum_h'] += h
            agg[(scc, dcc)]['count'] += 1
    return agg


def build(snapshot='2026-04'):
    agg = aggregate_matrix()
    countries = TARGET_COUNTRIES
    # Build matrices
    h_mat = [[0.0 for _ in countries] for _ in countries]  # src → dst mean hege
    c_mat = [[0 for _ in countries] for _ in countries]
    for i, src in enumerate(countries):
        for j, dst in enumerate(countries):
            if src == dst:
                continue
            entry = agg.get((src, dst))
            if entry and entry['count']:
                h_mat[i][j] = entry['sum_h'] / entry['count']
                c_mat[i][j] = entry['count']

    import plotly.graph_objects as go
    import plotly.subplots as sp

    # Heatmap (mean hegemony)
    hm_hege = go.Figure(go.Heatmap(
        z=h_mat, x=countries, y=countries, colorscale='Reds',
        colorbar=dict(title='mean hegemony'),
        text=[[f'{v:.3f}' for v in row] for row in h_mat],
        hovertemplate='%{y} → %{x}<br>mean hege=%{z:.3f}<extra></extra>',
    ))
    hm_hege.update_layout(
        title='① 跨国 AS 依赖矩阵 (均值 Hegemony)',
        xaxis=dict(title='依赖对象 Destination'),
        yaxis=dict(title='依赖主体 Source', autorange='reversed'),
        height=520,
    )

    # Heatmap (edge count)
    hm_count = go.Figure(go.Heatmap(
        z=c_mat, x=countries, y=countries, colorscale='Blues',
        colorbar=dict(title='edge count'),
        text=[[str(v) for v in row] for row in c_mat],
        hovertemplate='%{y} → %{x}<br>edges=%{z}<extra></extra>',
    ))
    hm_count.update_layout(
        title='② 跨国依赖边数矩阵 (原始计数)',
        xaxis=dict(title='依赖对象 Destination'),
        yaxis=dict(title='依赖主体 Source', autorange='reversed'),
        height=520,
    )

    # Sankey of top 30 inter-country flows (by edge count)
    flows = sorted(
        [((s, d), v['count']) for (s, d), v in agg.items()],
        key=lambda t: -t[1])[:30]
    nodes = []
    node_idx = {}
    for pair, _ in flows:
        for x in pair:
            if x not in node_idx:
                node_idx[x] = len(nodes)
                nodes.append(x)
    link_s = [node_idx[p[0][0]] for p in flows]
    link_d = [node_idx[p[0][1]] for p in flows]
    link_v = [p[1] for p in flows]
    sankey = go.Figure(go.Sankey(
        node=dict(
            label=[f'{bilingual(cc)}' for cc in nodes],
            color=[country_color(cc) for cc in nodes],
            pad=14, thickness=20),
        link=dict(
            source=link_s, target=link_d, value=link_v,
            color='rgba(69,183,209,0.3)',
            label=[f'{flows[i][1]} edges' for i in range(len(flows))]),
    ))
    sankey.update_layout(
        title=f'③ Top-30 跨国依赖流 · Top-30 inter-country flows', height=620)

    # Per-country donut grid (3×3)
    donut = sp.make_subplots(
        rows=3, cols=3,
        specs=[[{'type': 'pie'}] * 3] * 3,
        subplot_titles=[f'{cc} · {zh(cc)}' for cc in countries])
    for idx, cc in enumerate(countries):
        row = idx // 3 + 1
        col = idx % 3 + 1
        # Aggregate outbound dependencies for this country
        destinations = {}
        for (src, dst), v in agg.items():
            if src == cc and dst != cc:
                destinations[dst] = v['count']
        if not destinations:
            continue
        top_d = sorted(destinations.items(), key=lambda t: -t[1])[:8]
        donut.add_trace(go.Pie(
            labels=[d[0] for d in top_d],
            values=[d[1] for d in top_d],
            marker_colors=[country_color(d[0]) for d in top_d],
            textinfo='label+percent', hole=0.4, showlegend=False,
        ), row=row, col=col)
    donut.update_layout(
        title='④ 各国出向依赖构成 · Outbound dependency breakdown per country',
        height=720)

    narr = '''
    <div class="sidebar-note">
    <b>跨国依赖矩阵 · Cross-country Dependency Matrix</b><br><br>
    基于 IHR AS Hegemony (as_dependency.csv)；过滤 hege ≥ 0.03；按源/目的 AS 所属注册国聚合。<br>
    Matrix cell <i>row → column</i> = 行国家的 AS 依赖 列国家的 AS 的边数或均值 hegemony 强度；
    对角线为国内依赖（灰出）。<br>
    Source IYP IHR country-level hegemony, aggregated from AS-level edges by
    registered country_code (NRO delegated stats).
    </div>
    '''

    figs = [hm_hege, hm_count, sankey, donut]
    for f in figs:
        apply_plotly_theme(f)
    body = narr + plotly_inline_once(figs)
    save_consolidated_html(
        body, 'dependency_matrix.html',
        title_zh='跨国 AS 依赖矩阵',
        title_en=f'Cross-Country AS Dependency Matrix · {snapshot}',
        subtitle=f'9 countries · mean hegemony + edge count · {snapshot}',
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--snapshot', default='2026-04')
    args = ap.parse_args()
    build(args.snapshot)


if __name__ == '__main__':
    main()
