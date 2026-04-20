"""Topic 2: routing security reality check (RPKI × ROVISTA).

Intersects RPKI self-declaration (AS signs its own announcements) with
ROVISTA ground-truth measurement (does AS actually drop invalid routes?).

MANRS was planned as a third axis but the 2024-10 IYP dump does not
include MANRS IMPLEMENT relations — the banner flags that gap.

Reads CSVs from data_cache/new_angles/. No Neo4j.
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
    warning_block,
)

REPO = Path(__file__).resolve().parent.parent.parent
CACHE = REPO / 'data_cache' / 'new_angles'
OUT = REPO / 'analysis' / 'new_angles' / 'html'
OUT.mkdir(parents=True, exist_ok=True)

TARGET = ['US', 'CN', 'JP', 'IN', 'DE', 'GB', 'FR', 'NL', 'RU']
COUNTRY_NAME = {
    'US': '美国', 'CN': '中国', 'JP': '日本', 'IN': '印度', 'DE': '德国',
    'GB': '英国', 'FR': '法国', 'NL': '荷兰', 'RU': '俄罗斯',
}


def _read(name):
    p = CACHE / name
    if not p.exists():
        return []
    with open(p, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load():
    # RPKI: asn → (total_prefixes, rpki_valid)
    rpki = {}
    for r in _read('rpki_per_as.csv'):
        try:
            asn = int(r['asn']); total = int(r['total']); valid = int(r['rpki'])
            if total > 0:
                rpki[asn] = (total, valid, valid / total * 100)
        except (ValueError, KeyError):
            continue

    # ROVISTA: asn → ratio (0..1; higher = drops more invalid routes)
    rov = {}
    for r in _read('rovista.csv'):
        try:
            asn = int(r['asn'])
            ratio = r.get('ratio') or ''
            if ratio.strip():
                rov[asn] = float(ratio)
        except (ValueError, KeyError):
            continue

    # AS → Country
    as_cc = {}
    for r in _read('as_country.csv'):
        try:
            as_cc[int(r['asn'])] = r['cc']
        except (ValueError, KeyError):
            continue

    return rpki, rov, as_cc


def build():
    import plotly.graph_objects as go

    rpki, rov, as_cc = load()
    joined = {a: (rpki[a][2], rov[a], as_cc.get(a, '??'))
              for a in rpki if a in rov and rpki[a][0] > 0}
    print(f'joined RPKI × ROVISTA: {len(joined)} ASes', flush=True)

    # ---- Panel 1: RPKI% × ROVISTA scatter with quadrant highlights ----
    xs = [v[0] for v in joined.values()]
    ys = [v[1] * 100 for v in joined.values()]
    ccs = [v[2] for v in joined.values()]

    # Highlight 9 target countries; others grey
    target_pts = {cc: ([], [], []) for cc in TARGET}
    other_x, other_y = [], []
    for (asn, (x, y, cc)) in joined.items():
        if cc in target_pts:
            target_pts[cc][0].append(x)
            target_pts[cc][1].append(y * 100)
            target_pts[cc][2].append(asn)
        else:
            other_x.append(x)
            other_y.append(y * 100)

    p1 = go.Figure()
    # Quadrant background rectangles
    p1.add_shape(type='rect', x0=50, x1=100, y0=0, y1=50,
                 fillcolor='rgba(255,69,58,0.08)', line_width=0, layer='below')
    p1.add_annotation(x=75, y=25, showarrow=False,
                      text='⚠️ Published RPKI but<br>not enforcing ROV<br>(the gap)',
                      font=dict(color=COLORS['red'], size=12))
    p1.add_shape(type='rect', x0=50, x1=100, y0=50, y1=100,
                 fillcolor='rgba(52,199,89,0.06)', line_width=0, layer='below')
    p1.add_annotation(x=75, y=75, showarrow=False,
                      text='✅ signed + enforcing',
                      font=dict(color=COLORS['green'], size=12))
    p1.add_shape(type='rect', x0=0, x1=50, y0=0, y1=50,
                 fillcolor='rgba(142,142,147,0.05)', line_width=0, layer='below')
    p1.add_annotation(x=25, y=25, showarrow=False,
                      text='🟤 laggards<br>(neither side deployed)',
                      font=dict(color='#a0a0a8', size=11))
    p1.add_shape(type='rect', x0=0, x1=50, y0=50, y1=100,
                 fillcolor='rgba(0,113,227,0.05)', line_width=0, layer='below')
    p1.add_annotation(x=25, y=75, showarrow=False,
                      text='🔵 enforcing others<br>but not signing own',
                      font=dict(color=COLORS['cyan'], size=11))

    p1.add_trace(go.Scatter(
        x=other_x, y=other_y, mode='markers', name='other',
        marker=dict(size=3, color='rgba(142,142,147,0.35)', line_width=0),
        hoverinfo='skip',
    ))
    for cc in TARGET:
        x, y, aa = target_pts[cc]
        if x:
            p1.add_trace(go.Scatter(
                x=x, y=y, mode='markers',
                name=f'{cc} ({len(x)})',
                marker=dict(size=6, color=country_color(cc),
                            line=dict(color='#fff', width=0.5)),
                customdata=aa,
                hovertemplate=('AS%{customdata} · '
                               f'{cc}<br>RPKI=%{{x:.1f}}%%<br>'
                               'ROV=%{y:.1f}%<extra></extra>'),
            ))
    p1.update_layout(
        title=f'① RPKI 宣告 × ROVISTA 实测 · 信任与实行的落差（{len(joined):,} AS）',
        xaxis=dict(title='RPKI coverage (% of AS prefixes with ROA)',
                   range=[-2, 102]),
        yaxis=dict(title='ROVISTA enforcement ratio (%)', range=[-2, 102]),
        height=620, legend=dict(orientation='h', y=-0.12),
    )

    # ---- Panel 2: per-country quadrant share ----
    quads = {cc: {'gap': 0, 'good': 0, 'laggard': 0, 'enforcing': 0, 'total': 0}
             for cc in TARGET}
    for (asn, (x, y, cc)) in joined.items():
        if cc not in quads:
            continue
        q = quads[cc]
        q['total'] += 1
        y_pct = y * 100
        if x >= 50 and y_pct >= 50:
            q['good'] += 1
        elif x >= 50 and y_pct < 50:
            q['gap'] += 1
        elif x < 50 and y_pct >= 50:
            q['enforcing'] += 1
        else:
            q['laggard'] += 1

    order = sorted(TARGET,
                   key=lambda c: (-quads[c]['gap'] / max(quads[c]['total'], 1)))
    p2 = go.Figure()
    categories = [('good', '✅ RPKI+ROV', COLORS['green']),
                  ('enforcing', '🔵 ROV only', COLORS['cyan']),
                  ('gap', '⚠️ Gap', COLORS['red']),
                  ('laggard', '🟤 Neither', '#8e8e93')]
    for key, label, col in categories:
        p2.add_trace(go.Bar(
            x=[f'{COUNTRY_NAME[c]} {c}' for c in order],
            y=[quads[c][key] / max(quads[c]['total'], 1) * 100 for c in order],
            name=label, marker_color=col,
            text=[f'{quads[c][key]}' for c in order], textposition='inside',
        ))
    p2.update_layout(
        title='② 各国 AS 的 4 象限占比 · Country breakdown of the 2×2 matrix',
        barmode='stack', height=480,
        yaxis=dict(title='% of joined ASes', range=[0, 100]),
        xaxis=dict(title='', tickangle=-25),
    )

    # ---- Panel 3: Top-15 "worst gap" ASes (high RPKI, low ROV) ----
    gap_scored = []
    for asn, (x, y, cc) in joined.items():
        if x >= 70 and y <= 0.3:
            gap_scored.append((asn, cc, x, y, x - y * 100))
    gap_scored.sort(key=lambda t: -t[4])
    gap_scored = gap_scored[:15]
    p3 = go.Figure()
    if gap_scored:
        p3.add_trace(go.Bar(
            orientation='h',
            y=[f'AS{a} ({c})' for a, c, _, _, _ in gap_scored][::-1],
            x=[d for _, _, _, _, d in gap_scored][::-1],
            marker_color=[country_color(c) for _, c, _, _, _ in gap_scored][::-1],
            text=[f'RPKI {x:.0f}% · ROV {y*100:.0f}%'
                  for _, _, x, y, _ in gap_scored][::-1],
            textposition='outside',
        ))
    p3.update_layout(
        title='③ 最大落差 AS Top-15 · "Signed but not enforcing" champions',
        xaxis=dict(title='gap = RPKI% − ROV%'), height=520,
        showlegend=False, margin=dict(l=180),
    )

    # ---- Panel 4: histogram comparison ----
    import numpy as np
    p4 = go.Figure()
    p4.add_trace(go.Histogram(
        x=[v[0] for v in joined.values()], nbinsx=30,
        name='RPKI coverage %', marker_color=COLORS['green'],
        opacity=0.7,
    ))
    p4.add_trace(go.Histogram(
        x=[v[1] * 100 for v in joined.values()], nbinsx=30,
        name='ROVISTA enforcement %', marker_color=COLORS['cyan'],
        opacity=0.7,
    ))
    p4.update_layout(
        title='④ 全球 AS 的 RPKI 覆盖率 vs ROVISTA 实测分布对比',
        barmode='overlay',
        xaxis=dict(title='%'), yaxis=dict(title='# of ASes'),
        height=420,
    )

    from plotly.io import to_html
    for fig in (p1, p2, p3, p4):
        apply_plotly_theme(fig)
    parts = []
    first = True
    for fig in (p1, p2, p3, p4):
        parts.append(to_html(fig, include_plotlyjs=('inline' if first else False),
                             full_html=False, default_height='560px'))
        first = False

    signed = sum(1 for v in joined.values() if v[0] >= 50)
    gap = sum(1 for v in joined.values() if v[0] >= 50 and v[1] < 0.5)
    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>问题：</b>把路由安全看作三层——<b>宣告（RPKI ROA）</b>、'
        f'<b>实行（ROVISTA 实测 drop）</b>、<b>承诺（MANRS 声明）</b>。'
        f'RPKI 很高不代表真的 drop 无效路由；本页对比前两层。'
        f'<br><b>Scope:</b> {len(joined):,} AS intersected · '
        f'2024-10 snapshot · "signed" threshold = RPKI ≥ 50%, '
        f'"enforcing" threshold = ROV ≥ 50%.'
        f'<br><b>全球数字：</b>{signed:,} AS 有过半前缀签了 RPKI '
        f'({signed/len(joined)*100:.1f}% of joined)，其中 <b>{gap:,}</b> AS '
        f'实测 ROV 低于 50%（签了但不执行的"落差 AS"占已签的 '
        f'{gap/max(signed,1)*100:.1f}%）</p>'
    )
    intro += warning_block(
        'MANRS 维度缺失：2024-10 dump 的 IYP graph 未包含 '
        '<code>[:IMPLEMENT]</code> 到 MANRS Action 的关系（crawler 未在 '
        '该快照运行或已改路径）。3D 散点降级为 2D。待未来快照含 MANRS '
        '后自动启用第三轴。'
        '<br>MANRS dimension missing in this snapshot — falls back to '
        '2-axis RPKI × ROVISTA view.',
        title='MANRS 维度缺失 · MANRS dimension missing',
    )

    banner = (
        '<div class="step-banner">'
        '<h1>路由安全真身 · Routing Security Reality</h1>'
        '<h2>RPKI self-declaration × ROVISTA measured enforcement · '
        '"signed vs enforced" gap map</h2>'
        '</div>'
        '<div class="step-footer">topic 2 · 2024-10 snapshot · 2-axis view '
        '(MANRS unavailable)</div>'
    )
    out_path = OUT / 'topic2_routing_security.html'
    out_path.write_text(
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>路由安全真身 · Routing Security Reality</title>'
        f'{BANNER_CSS}</head><body>'
        f'{banner}<div class="content">{intro}'
        f'{"".join(parts)}</div></body></html>',
        encoding='utf-8',
    )
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    print(f'summary: total={len(joined):,}  signed={signed:,}  '
          f'gap={gap:,} ({gap/max(signed,1)*100:.1f}% of signed)')


if __name__ == '__main__':
    build()
