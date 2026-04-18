"""Topic 12: Global IHR hegemony — which ASes does the world depend on?

Uses `ihr.local_hegemony_v4`-derived DEPENDS_ON edges (hege prop). For
each potential dependency target, sum the hege scores of all ASes
depending on it — this is effectively a global centrality score.
Complements our existing usage of DEPENDS_ON for per-country
step08/step09 analysis.

Input: ihr_hegemony_incoming.csv (top-5000 by incoming hege weight).
"""
import csv
import os
import sys
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


def _read(path):
    return list(csv.DictReader(open(path, encoding='utf-8'))) \
        if path.exists() else []


def load():
    as_cc = {int(r['asn']): r['cc'] for r in _read(CACHE / 'as_country.csv')
             if r.get('asn', '').isdigit()}
    asn_org = {int(r['asn']): r.get('org_name', '')
               for r in _read(COMPLEX / 'as_organization.csv')
               if r.get('asn', '').isdigit()}
    rows = []
    for r in _read(CACHE / 'ihr_hegemony_incoming.csv'):
        try:
            asn = int(r['asn'])
            inc = float(r.get('incoming') or 0)
            n_deps = int(r.get('n_deps') or 0)
            rows.append({
                'asn': asn, 'inc': inc, 'n_deps': n_deps,
                'cc': as_cc.get(asn, '??'),
                'org': asn_org.get(asn, '')[:40],
            })
        except (ValueError, KeyError):
            continue
    rows.sort(key=lambda r: -r['inc'])
    return rows


def build():
    import plotly.graph_objects as go
    rows = load()
    print(f'rows: {len(rows)}')

    # ---- Panel 1: Top-30 global hegemony ----
    top30 = rows[:30]
    p1 = go.Figure()
    p1.add_trace(go.Bar(
        orientation='h',
        y=[f'AS{r["asn"]} ({r["cc"]}) {r["org"]}' for r in top30][::-1],
        x=[r['inc'] for r in top30][::-1],
        marker_color=[country_color(r['cc']) if r['cc'] in TARGET
                      else COLORS['purple'] for r in top30][::-1],
        text=[f'{r["inc"]:,.0f} · {r["n_deps"]:,} deps' for r in top30][::-1],
        textposition='outside',
    ))
    p1.update_layout(
        title='① 全球 Top-30 hegemony AS · Whom does the world depend on?',
        xaxis=dict(title='sum of hege (incoming dependency weight)'),
        height=720, margin=dict(l=320), showlegend=False,
    )

    # ---- Panel 2: Country share of top-100 ----
    top100 = rows[:100]
    from collections import Counter
    cc_in_top = Counter(r['cc'] for r in top100)
    cc_weight = Counter()
    for r in top100:
        cc_weight[r['cc']] += r['inc']
    top_ccs = sorted(cc_in_top, key=lambda c: -cc_weight[c])
    p2 = go.Figure()
    p2.add_trace(go.Bar(
        x=top_ccs[:15],
        y=[cc_in_top[c] for c in top_ccs[:15]],
        marker_color=[country_color(c) if c in TARGET else COLORS['purple']
                      for c in top_ccs[:15]],
        text=[str(cc_in_top[c]) for c in top_ccs[:15]],
        textposition='outside', name='# in top-100',
    ))
    p2.add_trace(go.Scatter(
        x=top_ccs[:15], y=[cc_weight[c] for c in top_ccs[:15]],
        mode='lines+markers', name='sum(hege)', yaxis='y2',
        line=dict(color=COLORS['red'], width=2),
        marker=dict(size=9),
    ))
    p2.update_layout(
        title='② Top-100 全球 hegemony 的国家分布 · '
              'Country share of the top-100 most-depended-on ASes',
        yaxis=dict(title='# of AS in top-100'),
        yaxis2=dict(title='sum hege weight',
                    overlaying='y', side='right'),
        xaxis=dict(title='country'),
        height=480, legend=dict(orientation='h', y=-0.15),
    )

    # ---- Panel 3: 9-country presence in top-5000 ----
    p3 = go.Figure()
    per_cc_rows = []
    for cc in TARGET:
        cc_rows = [r for r in rows if r['cc'] == cc]
        if not cc_rows:
            continue
        per_cc_rows.append({
            'cc': cc, 'n': len(cc_rows),
            'total_inc': sum(r['inc'] for r in cc_rows),
            'best_asn': cc_rows[0]['asn'],
            'best_inc': cc_rows[0]['inc'],
        })
    per_cc_rows.sort(key=lambda r: -r['total_inc'])
    p3.add_trace(go.Bar(
        x=[f'{COUNTRY_NAME[r["cc"]]} {r["cc"]}' for r in per_cc_rows],
        y=[r['total_inc'] for r in per_cc_rows],
        marker_color=[country_color(r['cc']) for r in per_cc_rows],
        text=[f'{r["total_inc"]:,.0f}<br>({r["n"]} AS in top-5k)<br>'
              f'best AS{r["best_asn"]}' for r in per_cc_rows],
        textposition='outside',
    ))
    p3.update_layout(
        title='③ 9 国 hegemony 总权重 · Target-9 total hege weight '
              'in global top-5000',
        yaxis=dict(title='sum hege weight'),
        xaxis=dict(title='', tickangle=-20),
        height=480, showlegend=False,
    )

    # ---- Panel 4: distribution curve (log-log) ----
    import math
    p4 = go.Figure()
    xs = list(range(1, len(rows) + 1))
    ys = [r['inc'] for r in rows]
    p4.add_trace(go.Scatter(
        x=xs, y=ys, mode='lines',
        line=dict(color=COLORS['cyan'], width=2),
        fill='tozeroy', fillcolor='rgba(0,208,201,0.08)',
    ))
    p4.update_layout(
        title='④ Global hegemony 分布曲线 · heavy-tailed by design '
              '(log-log)',
        xaxis=dict(title='rank', type='log'),
        yaxis=dict(title='incoming hege weight', type='log'),
        height=440, showlegend=False,
    )

    from plotly.io import to_html
    for fig in (p1, p2, p3, p4):
        apply_plotly_theme(fig)
    parts = []; first = True
    for fig in (p1, p2, p3, p4):
        parts.append(to_html(
            fig, include_plotlyjs=('inline' if first else False),
            full_html=False, default_height='540px'))
        first = False

    top1 = rows[0]; top3 = rows[:3]
    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>数据：</b>IHR local-hegemony-v4 把 AS 之间的依赖量化为 '
        f'<code>hege ∈ [0,1]</code>。这里对每个 AS 聚合 <b>incoming hege</b>'
        f'（多少别的 AS 依赖它，加权求和）—得到全球依赖中心性。'
        f'<br><b>Scope:</b> top-{len(rows):,} AS by incoming hege. '
        f'No.1 = <b>AS{top1["asn"]}</b> ({top1["org"]}, {top1["cc"]}) '
        f'incoming={top1["inc"]:,.0f} 来自 {top1["n_deps"]:,} 个依赖方。'
        f'<br><b>Top-3:</b> '
        + ' · '.join(f'AS{r["asn"]} {r["cc"]} ({r["inc"]:,.0f})'
                     for r in top3) +
        f'</p>'
    )

    banner = (
        '<div class="step-banner">'
        '<h1>全球依赖中心性 · Global IHR Hegemony</h1>'
        '<h2>Top ASes the world depends on · incoming hege weight aggregate</h2>'
        '</div>'
        '<div class="step-footer">topic 12 · 2024-10 snapshot · '
        'ihr.local_hegemony_v4</div>'
    )
    out_path = OUT / 'topic12_ihr_hegemony.html'
    out_path.write_text(
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>全球依赖中心性 · Global IHR Hegemony</title>'
        f'{BANNER_CSS}</head><body>'
        f'{banner}<div class="content">{intro}'
        f'{"".join(parts)}</div></body></html>',
        encoding='utf-8',
    )
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    for r in rows[:5]:
        print(f'  AS{r["asn"]} ({r["cc"]}) {r["org"]}: '
              f'incoming={r["inc"]:,.0f} n_deps={r["n_deps"]:,}')


if __name__ == '__main__':
    build()
