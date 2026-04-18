"""Topic 1: user-weighted vs equal-weight view of the 9-country sovereignty.

Reads cached CSVs from data_cache/new_angles/ and existing per-country
metrics under analysis/countries/data/2026-04/. No Neo4j.

Renders analysis/new_angles/html/topic1_eyeball_weighted.html with 4 panels:
  ① per-country top-10 AS eyeball-share HHI (market concentration)
  ② sovereignty vs AS-per-million scatter (size vs independence)
  ③ equal-weight vs user-weighted rank shift heatmap
  ④ per-country eyeball-HHI Gini curve
"""
import csv
import json
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
OUT = REPO / 'analysis' / 'new_angles' / 'html'
OUT.mkdir(parents=True, exist_ok=True)
METRICS = REPO / 'analysis' / 'countries' / 'data' / '2026-04'

TARGET = ['US', 'CN', 'JP', 'IN', 'DE', 'GB', 'FR', 'NL', 'RU']
COUNTRY_NAME = {
    'US': '美国', 'CN': '中国', 'JP': '日本', 'IN': '印度', 'DE': '德国',
    'GB': '英国', 'FR': '法国', 'NL': '荷兰', 'RU': '俄罗斯',
}

# Fallback populations (Worldbank 2024, Nov release) used when the live
# CSV is empty — the 2024-10 Neo4j extract hit a schema-property mismatch
# (the crawler stored population on edge.value, not edge.population).
# extract_data.py has been corrected; this dict keeps the analysis
# working until the next full re-extract.
POP_FALLBACK_2024 = {
    'US': 336_810_000,  'CN': 1_410_710_000,  'JP': 123_750_000,
    'IN': 1_428_630_000, 'DE': 84_480_000,   'GB': 68_350_000,
    'FR': 68_170_000,   'NL': 17_880_000,   'RU': 143_830_000,
}


def _read_csv(name):
    path = CACHE / name
    if not path.exists():
        return []
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _gini(xs):
    """Classical Gini on a non-negative numeric list."""
    xs = sorted(float(x) for x in xs if x is not None)
    n = len(xs)
    if n == 0 or sum(xs) == 0:
        return 0.0
    cum = 0.0
    for i, x in enumerate(xs, start=1):
        cum += i * x
    return (2 * cum) / (n * sum(xs)) - (n + 1) / n


def load_data():
    eyeball = _read_csv('eyeball_as_country.csv')
    pop_rows = _read_csv('country_population.csv')
    pop = {}
    for r in pop_rows:
        v = r.get('population') or ''
        if v.strip():
            try:
                pop[r['cc']] = float(v)
            except ValueError:
                pass
    # Fill in 9 target countries from static fallback if empty
    for cc, v in POP_FALLBACK_2024.items():
        pop.setdefault(cc, v)

    per_cc = defaultdict(list)
    for r in eyeball:
        try:
            per_cc[r['cc']].append((int(r['asn']), float(r['pct_users'])))
        except (KeyError, ValueError):
            continue
    for cc in per_cc:
        per_cc[cc].sort(key=lambda t: -t[1])

    sov = {}
    ases = {}
    for cc in TARGET:
        p = METRICS / cc / 'step20_metrics.json'
        if p.exists():
            m = json.loads(p.read_text()).get('metrics') or {}
            sov[cc] = m.get('composite_sovereignty_index')
        p1 = METRICS / cc / 'step01_metrics.json'
        if p1.exists():
            m = json.loads(p1.read_text()).get('metrics') or {}
            ases[cc] = m.get('total_ases')
    return per_cc, pop, sov, ases


def build():
    import plotly.graph_objects as go
    import plotly.subplots as sp

    per_cc, pop, sov, ases = load_data()

    have = [cc for cc in TARGET if cc in per_cc]
    missing = [cc for cc in TARGET if cc not in per_cc]

    # ---- Panel 1: top-10 AS eyeball share per country ----
    p1 = go.Figure()
    top10_share = {}
    for cc in have:
        top = per_cc[cc][:10]
        share = sum(t[1] for t in top)
        top10_share[cc] = share
    # sorted bars
    order = sorted(have, key=lambda c: -top10_share.get(c, 0))
    p1.add_trace(go.Bar(
        x=[f'{COUNTRY_NAME[c]} {c}' for c in order],
        y=[top10_share[c] for c in order],
        marker_color=[country_color(c) for c in order],
        text=[f'{top10_share[c]:.1f}%' for c in order],
        textposition='outside',
    ))
    p1.update_layout(
        title='① 各国 Top-10 AS 占用户比例（市场集中度）· Top-10 AS eyeball share',
        yaxis=dict(title='% of national internet users', range=[0, 100]),
        xaxis=dict(title='', tickangle=-25),
        height=480, showlegend=False,
    )

    # ---- Panel 2: AS-per-million scatter vs sovereignty ----
    p2 = go.Figure()
    xs, ys, labels, colors, sizes = [], [], [], [], []
    for cc in TARGET:
        if cc not in ases or cc not in pop:
            continue
        ppm = ases[cc] / max(pop[cc] / 1e6, 1)
        xs.append(ppm)
        ys.append(sov.get(cc, 0) or 0)
        labels.append(f'{cc} {COUNTRY_NAME[cc]}')
        colors.append(country_color(cc))
        sizes.append(max(12, min(40, (pop[cc] / 1e7) ** 0.5 * 6 + 12)))
    p2.add_trace(go.Scatter(
        x=xs, y=ys, mode='markers+text', text=labels, textposition='top center',
        marker=dict(size=sizes, color=colors, line=dict(color='#fff', width=1)),
        textfont=dict(color=TEXT_PRIMARY, size=13),
    ))
    p2.update_layout(
        title='② AS 密度 × 主权指数 · AS per million residents vs Sovereignty',
        xaxis=dict(title='AS per million residents', type='log'),
        yaxis=dict(title='Sovereignty Index (0–1)', range=[0, 1]),
        height=500, showlegend=False,
    )

    # ---- Panel 3: rank shift (equal-weight vs user-weighted) ----
    # Equal-weight: rank by sovereignty_index
    # User-weighted: sovereignty × sqrt(eyeball-users) to co-weight size
    rows = []
    for cc in TARGET:
        s = sov.get(cc) or 0
        users = pop.get(cc, 0)
        rows.append((cc, s, s * (users / 1e8) ** 0.5))
    by_equal = sorted(rows, key=lambda r: -r[1])
    by_weight = sorted(rows, key=lambda r: -r[2])
    eq_rank = {r[0]: i + 1 for i, r in enumerate(by_equal)}
    wt_rank = {r[0]: i + 1 for i, r in enumerate(by_weight)}

    order3 = sorted(TARGET, key=lambda c: eq_rank[c])
    p3 = go.Figure()
    p3.add_trace(go.Scatter(
        x=['等权排名', '用户加权排名'], y=[[eq_rank[c] for c in order3], []][0],
        mode='lines+markers', line=dict(color='#888', width=0.5), showlegend=False,
    ))
    # Use slope chart
    p3 = go.Figure()
    for cc in order3:
        p3.add_trace(go.Scatter(
            x=['Equal-weight', 'User-weighted'],
            y=[eq_rank[cc], wt_rank[cc]],
            mode='lines+markers+text',
            line=dict(color=country_color(cc), width=2),
            marker=dict(size=9),
            text=[f'#{eq_rank[cc]} {cc}', f'#{wt_rank[cc]} {cc}'],
            textposition=['middle left', 'middle right'],
            textfont=dict(color=country_color(cc), size=12),
            name=cc, showlegend=False,
        ))
    p3.update_layout(
        title='③ 排名漂移 · Rank under equal-weight vs population-weighted',
        yaxis=dict(title='rank', autorange='reversed', tickmode='linear', dtick=1),
        height=520, margin=dict(l=80, r=80),
    )

    # ---- Panel 4: eyeball Gini per country ----
    p4 = go.Figure()
    gini_rows = []
    for cc in have:
        shares = [t[1] for t in per_cc[cc]]
        g = _gini(shares)
        gini_rows.append((cc, g, len(shares)))
    gini_rows.sort(key=lambda r: -r[1])
    p4.add_trace(go.Bar(
        x=[f'{COUNTRY_NAME.get(c, c)} {c}' for c, _, _ in gini_rows],
        y=[g for _, g, _ in gini_rows],
        marker_color=[country_color(c) for c, _, _ in gini_rows],
        text=[f'{g:.3f}<br>({n} ASes)' for _, g, n in gini_rows],
        textposition='outside',
    ))
    p4.update_layout(
        title='④ 用户在 AS 中的 Gini 系数 · Eyeball concentration (higher = fewer ISPs rule)',
        yaxis=dict(title='Gini (0=uniform, 1=monopoly)', range=[0, 1]),
        xaxis=dict(title='', tickangle=-25),
        height=480, showlegend=False,
    )

    from plotly.io import to_html
    for fig in (p1, p2, p3, p4):
        apply_plotly_theme(fig)
    body_parts = []
    first = True
    for fig in (p1, p2, p3, p4):
        body_parts.append(to_html(
            fig, include_plotlyjs=('inline' if first else False),
            full_html=False, default_height='520px'))
        first = False

    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>问题：</b>现有 IYP 分析把每个 AS 视为等权，'
        f'1 个服务 10 个用户的企业网 = 1 个服务 3 亿人的 ISP。'
        f'本页引入 <b>APNIC Eyeball</b>（每 AS 在该国用户份额）+ '
        f'<b>Worldbank</b> 人口作为新维度。'
        f'<br><b>Scope:</b> 9 target countries · 2024-10 snapshot · '
        f'{sum(len(per_cc[c]) for c in have):,} eyeball AS entries across '
        f'{len(have)} countries.</p>'
    )
    if missing:
        intro += (
            f'<p style="color:#ff9f0a;padding:0 16px;font-size:13px">'
            f'⚠️ 缺 eyeball 数据的国家：<code>{", ".join(missing)}</code>'
            f' (APNIC 未覆盖或数据缺失)</p>'
        )

    banner = (
        '<div class="step-banner">'
        '<h1>用户加权视角 · User-weighted Sovereignty</h1>'
        '<h2>Equal-weight vs population-weighted view · '
        'APNIC Eyeball + Worldbank population</h2>'
        '</div>'
        '<div class="step-footer">topic 1 · 2024-10 snapshot · no double-counting</div>'
    )
    out_path = OUT / 'topic1_eyeball_weighted.html'
    out_path.write_text(
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>用户加权视角 · User-weighted Sovereignty</title>'
        f'{BANNER_CSS}</head><body>'
        f'{banner}<div class="content">{intro}'
        f'{"".join(body_parts)}</div></body></html>',
        encoding='utf-8',
    )
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')


if __name__ == '__main__':
    build()
