"""Topic 15: 9×9 country dependency matrix.

Aggregates the 694K AS-level DEPENDS_ON edges (with hege weights) to a
clean country pair matrix among the 9 targets. Shows: for each pair
(A,B), how much do A's ASes depend on B's ASes (weighted by hege).

Reuses cached as_dependency.csv + as_country.csv; no Neo4j.
"""
import csv
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.china.common import (  # noqa: E402
    BANNER_CSS, COLORS, DARK_BG, DARK_BORDER, DARK_PANEL,
    TEXT_PRIMARY, TEXT_SECONDARY, apply_plotly_theme, country_color,
)

REPO = Path(__file__).resolve().parent.parent.parent
CACHE = REPO / 'data_cache' / 'new_angles'
COMPLEX = REPO / 'data_cache' / 'complex_network'
OUT = REPO / 'analysis' / 'new_angles' / 'html'
OUT.mkdir(parents=True, exist_ok=True)

TARGET = ['US', 'CN', 'JP', 'IN', 'DE', 'GB', 'FR', 'NL', 'RU']
COUNTRY_NAME = {
    'US': '美国', 'CN': '中国', 'JP': '日本', 'IN': '印度', 'DE': '德国',
    'GB': '英国', 'FR': '法国', 'NL': '荷兰', 'RU': '俄罗斯',
}


def _read(p):
    return list(csv.DictReader(open(p, encoding='utf-8'))) \
        if p.exists() else []


def load():
    as_cc = {int(r['asn']): r['cc'] for r in _read(CACHE / 'as_country.csv')
             if r.get('asn', '').isdigit()}

    # src depends on dst: flow is src_cc -> dst_cc (weight=hege)
    matrix = defaultdict(float)  # (src_cc, dst_cc) -> weight
    edge_count = defaultdict(int)
    for r in _read(COMPLEX / 'as_dependency.csv'):
        try:
            src = int(r['src']); dst = int(r['dst'])
            h = float(r.get('hege') or 0)
        except (ValueError, KeyError):
            continue
        s = as_cc.get(src); d = as_cc.get(dst)
        if s and d and s in TARGET and d in TARGET:
            matrix[(s, d)] += h
            edge_count[(s, d)] += 1
    return matrix, edge_count


def build():
    import plotly.graph_objects as go
    matrix, edge_count = load()

    # ---- Panel 1: weighted heatmap (hege) ----
    z = []
    for src in TARGET:
        row = []
        for dst in TARGET:
            row.append(matrix.get((src, dst), 0))
        z.append(row)

    p1 = go.Figure(data=go.Heatmap(
        z=z, x=TARGET, y=TARGET,
        colorscale=[[0, '#0d1117'], [0.25, COLORS['purple']],
                    [0.6, COLORS['orange']], [1, COLORS['red']]],
        colorbar=dict(title='sum(hege)'),
        text=[[f'{cell:.1f}' if cell else '' for cell in row]
              for row in z],
        texttemplate='%{text}',
        textfont=dict(color=TEXT_PRIMARY, size=12),
    ))
    p1.update_layout(
        title='① 依赖权重矩阵 · Row depends on column (hege sum)',
        xaxis=dict(title='depends on →', side='top'),
        yaxis=dict(title='← from', autorange='reversed'),
        height=520,
    )

    # ---- Panel 2: row-normalized matrix (what % of each country's outbound
    #                goes to each target)
    p2 = go.Figure()
    z_norm = []
    for src in TARGET:
        total = sum(matrix.get((src, d), 0) for d in TARGET)
        row = []
        for dst in TARGET:
            v = matrix.get((src, dst), 0)
            row.append(v / total * 100 if total > 0 else 0)
        z_norm.append(row)
    p2.add_trace(go.Heatmap(
        z=z_norm, x=TARGET, y=TARGET,
        colorscale=[[0, '#0d1117'], [0.25, COLORS['cyan']],
                    [0.5, COLORS['green']], [1, COLORS['yellow']]],
        colorbar=dict(title='% of row'),
        text=[[f'{cell:.0f}%' if cell >= 1 else '' for cell in row]
              for row in z_norm],
        texttemplate='%{text}',
        textfont=dict(color=TEXT_PRIMARY, size=12),
    ))
    p2.update_layout(
        title='② 行内占比矩阵 · % of each country\'s target-9 dependency '
              'going to each column (rows sum to 100%)',
        xaxis=dict(title='depends on →', side='top'),
        yaxis=dict(title='← from', autorange='reversed'),
        height=520,
    )

    # ---- Panel 3: per-country outbound total + inbound total ----
    p3 = go.Figure()
    out_total = {src: sum(matrix.get((src, d), 0) for d in TARGET
                          if d != src)
                 for src in TARGET}
    in_total = {dst: sum(matrix.get((s, dst), 0) for s in TARGET
                         if s != dst)
                for dst in TARGET}
    ordered = sorted(TARGET, key=lambda c: -(out_total[c] + in_total[c]))
    p3.add_trace(go.Bar(
        x=[f'{COUNTRY_NAME[c]} {c}' for c in ordered],
        y=[out_total[c] for c in ordered],
        name='outbound (deps on others)', marker_color=COLORS['red'],
        text=[f'{out_total[c]:.1f}' for c in ordered],
        textposition='inside',
    ))
    p3.add_trace(go.Bar(
        x=[f'{COUNTRY_NAME[c]} {c}' for c in ordered],
        y=[in_total[c] for c in ordered],
        name='inbound (others depend on)', marker_color=COLORS['green'],
        text=[f'{in_total[c]:.1f}' for c in ordered],
        textposition='inside',
    ))
    p3.update_layout(
        title='③ 9 国出入向依赖总权重 · Total hege weight '
              'in/out of each target country',
        barmode='group', yaxis=dict(title='sum hege'),
        xaxis=dict(title='', tickangle=-20),
        height=480, legend=dict(orientation='h', y=-0.18),
    )

    # ---- Panel 4: Net dependency balance ----
    p4 = go.Figure()
    rows = []
    for cc in TARGET:
        rows.append({
            'cc': cc,
            'balance': in_total[cc] - out_total[cc],
            'in': in_total[cc], 'out': out_total[cc],
        })
    rows.sort(key=lambda r: -r['balance'])
    p4.add_trace(go.Bar(
        x=[f'{COUNTRY_NAME[r["cc"]]} {r["cc"]}' for r in rows],
        y=[r['balance'] for r in rows],
        marker_color=[COLORS['green'] if r['balance'] > 0 else COLORS['red']
                      for r in rows],
        text=[f'net={r["balance"]:+.1f}<br>in={r["in"]:.1f} · '
              f'out={r["out"]:.1f}' for r in rows],
        textposition='outside',
    ))
    p4.add_hline(y=0, line=dict(color='#8e8e93', width=1, dash='dash'))
    p4.update_layout(
        title='④ 净依赖平衡 · Net hege balance (inbound − outbound) '
              '— + = exporter, − = importer',
        yaxis=dict(title='net hege weight'),
        xaxis=dict(title='', tickangle=-20),
        height=460, showlegend=False,
    )

    from plotly.io import to_html
    for fig in (p1, p2, p3, p4):
        apply_plotly_theme(fig)
    parts = []; first = True
    for fig in (p1, p2, p3, p4):
        parts.append(to_html(
            fig, include_plotlyjs=('inline' if first else False),
            full_html=False, default_height='520px'))
        first = False

    exporter = max(rows, key=lambda r: r['balance'])
    importer = min(rows, key=lambda r: r['balance'])
    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>数据：</b>IHR local-hegemony-v4 的 AS 依赖图，按国家聚合成 9×9 矩阵。'
        f'每格单元值 = 起源国 AS 对目标国 AS 的 hege 加权依赖。'
        f'<br><b>最大净出口国（others depend on）：</b>'
        f'{COUNTRY_NAME[exporter["cc"]]} {exporter["cc"]}'
        f'（net={exporter["balance"]:+.1f}）· '
        f'<b>最大净进口国（depends on others）：</b>'
        f'{COUNTRY_NAME[importer["cc"]]} {importer["cc"]}'
        f'（net={importer["balance"]:+.1f}）</p>'
    )

    banner = (
        '<div class="step-banner">'
        '<h1>9×9 国家依赖矩阵 · 9×9 Country Dependency Matrix</h1>'
        '<h2>Hege-weighted country-to-country dependency · '
        'net importer vs exporter</h2>'
        '</div>'
        '<div class="step-footer">topic 15 · offline · '
        'ihr.local_hegemony_v4 aggregated</div>'
    )
    out_path = OUT / 'topic15_country_dep_matrix.html'
    out_path.write_text(
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>9×9 国家依赖矩阵 · Country Dependency Matrix</title>'
        f'{BANNER_CSS}</head><body>'
        f'{banner}<div class="content">{intro}'
        f'{"".join(parts)}</div></body></html>',
        encoding='utf-8',
    )
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    print(f'balance ranking:')
    for r in rows:
        print(f'  {r["cc"]}: net={r["balance"]:+.1f}  '
              f'in={r["in"]:.1f} out={r["out"]:.1f}')


if __name__ == '__main__':
    build()
