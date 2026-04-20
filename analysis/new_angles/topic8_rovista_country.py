"""Topic 8 (substitute): ROVISTA country-level enforcement map.

Originally planned as PeeringDB policy_openness geography, but the
2024-10 Neo4j extract for PeeringDB org records returned 0 rows
(schema mismatch on EXTERNAL_ID edge property keys).

Pivots to a country-level view of the ROVISTA ground-truth measurement
that Topic 2 used as an AS-level scatter. The global view is useful:
which countries have the highest share of invalid-route-dropping ASes?
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
    ISO2_TO_ISO3, warning_block,
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
    as_cc = {}
    for r in _read('as_country.csv'):
        try:
            as_cc[int(r['asn'])] = r['cc']
        except (ValueError, KeyError):
            pass
    # asn -> ratio (collapse Validating/Not Validating into one)
    rov = {}
    for r in _read('rovista.csv'):
        try:
            asn = int(r['asn'])
            raw = r.get('ratio') or ''
            if raw.strip():
                rov[asn] = float(raw)
        except (ValueError, KeyError):
            continue
    return as_cc, rov


def build():
    import plotly.graph_objects as go

    as_cc, rov = load()
    # Per-country: (count, mean_ratio, median_ratio, share_enforcing_50pct)
    per_cc = defaultdict(list)
    for asn, ratio in rov.items():
        cc = as_cc.get(asn)
        if cc:
            per_cc[cc].append(ratio)

    # Compute summary rows (min 10 ASes)
    rows = []
    for cc, ratios in per_cc.items():
        if len(ratios) < 10:
            continue
        n = len(ratios)
        mean_r = sum(ratios) / n
        srt = sorted(ratios)
        median_r = srt[n // 2]
        share50 = sum(1 for r in ratios if r >= 0.5) / n * 100
        rows.append({'cc': cc, 'n': n, 'mean': mean_r,
                     'median': median_r, 'share50': share50})
    rows.sort(key=lambda r: -r['mean'])
    print(f'countries with >=10 ROVISTA ASes: {len(rows)}')

    # ---- Panel 1: world choropleth of mean ROVISTA ratio ----
    p1 = go.Figure(data=go.Choropleth(
        locations=[ISO2_TO_ISO3.get(r['cc'], r['cc']) for r in rows],
        z=[r['mean'] * 100 for r in rows],
        text=[f'{r["cc"]}<br>{r["n"]} AS<br>mean {r["mean"]*100:.1f}%<br>'
              f'{r["share50"]:.0f}% enforcing ≥50%' for r in rows],
        hoverinfo='text',
        colorscale=[[0, COLORS['red']], [0.5, COLORS['orange']],
                    [1, COLORS['green']]],
        colorbar=dict(title='mean ROV ratio (%)'),
    ))
    p1.update_layout(
        title='① 全球 ROVISTA 实测执行地图 · Global ROV enforcement by country',
        geo=dict(showframe=False, showcoastlines=True,
                 projection_type='natural earth', bgcolor=DARK_BG,
                 coastlinecolor=DARK_BORDER, landcolor=DARK_PANEL,
                 lakecolor=DARK_BG),
        paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG, height=560,
    )

    # ---- Panel 2: Top-20 + bottom-10 countries by mean ratio ----
    p2 = go.Figure()
    top = rows[:20]
    bot = rows[-10:]
    both = top + bot
    p2.add_trace(go.Bar(
        y=[f'{r["cc"]} ({r["n"]})' for r in both][::-1],
        x=[r['mean'] * 100 for r in both][::-1],
        orientation='h',
        marker_color=[COLORS['green'] if r['mean'] >= 0.5 else COLORS['red']
                      for r in both][::-1],
        text=[f'{r["mean"]*100:.1f}%' for r in both][::-1],
        textposition='outside',
    ))
    p2.update_layout(
        title='② Top-20 + Bottom-10 国家 · 平均 ROV 执行率 '
              '(≥10 AS threshold)',
        xaxis=dict(title='mean ROVISTA ratio (%)', range=[0, 100]),
        height=820, margin=dict(l=100), showlegend=False,
    )

    # ---- Panel 3: 9 target countries head-to-head ----
    p3 = go.Figure()
    tgt_rows = [next((r for r in rows if r['cc'] == cc), None) for cc in TARGET]
    tgt_rows = [r for r in tgt_rows if r]
    tgt_rows.sort(key=lambda r: -r['mean'])
    p3.add_trace(go.Bar(
        x=[f'{COUNTRY_NAME[r["cc"]]} {r["cc"]}' for r in tgt_rows],
        y=[r['mean'] * 100 for r in tgt_rows],
        marker_color=[country_color(r['cc']) for r in tgt_rows],
        text=[f'{r["mean"]*100:.1f}%<br>({r["n"]} AS, '
              f'{r["share50"]:.0f}% enforcing)' for r in tgt_rows],
        textposition='outside',
        name='mean',
    ))
    p3.add_trace(go.Scatter(
        x=[f'{COUNTRY_NAME[r["cc"]]} {r["cc"]}' for r in tgt_rows],
        y=[r['share50'] for r in tgt_rows],
        mode='lines+markers', name='% enforcing ≥50%',
        yaxis='y2', line=dict(color=COLORS['red'], width=2),
        marker=dict(size=10),
    ))
    p3.update_layout(
        title='③ 9 国 ROV 执行对比 · Target-9 mean ratio + % enforcing',
        yaxis=dict(title='mean ratio (%)', range=[0, 100]),
        yaxis2=dict(title='% enforcing ≥50%', overlaying='y', side='right',
                    range=[0, 100]),
        xaxis=dict(title='', tickangle=-20),
        height=520, legend=dict(orientation='h', y=-0.15),
    )

    # ---- Panel 4: distribution histogram by country (3 cohorts) ----
    p4 = go.Figure()
    ratio_by_cohort = {'Top-10': [], 'Middle': [], 'Bottom-10': []}
    for i, r in enumerate(rows):
        if i < 10:
            ratio_by_cohort['Top-10'].extend(per_cc[r['cc']])
        elif i >= len(rows) - 10:
            ratio_by_cohort['Bottom-10'].extend(per_cc[r['cc']])
        else:
            ratio_by_cohort['Middle'].extend(per_cc[r['cc']])
    cohort_colors = {'Top-10': COLORS['green'], 'Middle': COLORS['cyan'],
                     'Bottom-10': COLORS['red']}
    for name, ratios in ratio_by_cohort.items():
        p4.add_trace(go.Histogram(
            x=[r * 100 for r in ratios], nbinsx=25, name=name,
            marker_color=cohort_colors[name], opacity=0.65,
        ))
    p4.update_layout(
        title='④ 三段国家 ROV 分布 · Ratio histogram by cohort',
        barmode='overlay',
        xaxis=dict(title='ROVISTA ratio (%)'), yaxis=dict(title='# AS'),
        height=440,
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

    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>原计划：</b>PeeringDB org 的 <code>policy_general</code> + '
        f'<code>info_ratio</code> + <code>info_traffic</code> 开放度地图。'
        f'<i>2024-10 dump 中 Organization-EXTERNAL_ID-OpaqueID 关系的 '
        f'reference_name 过滤返回 0 行</i>—降级为已有 ROVISTA 数据的国别视图，'
        f'作为 Topic 2 全球 scatter 的国家级补充。'
        f'<br><b>Scope:</b> {len(rov):,} AS with ROVISTA ratio · '
        f'{len(rows)} countries (≥10 AS threshold) · 2024-10 snapshot.'
        f'</p>'
    )
    intro += warning_block(
        '原始计划：PeeringDB org 的 <code>policy_general</code> + '
        '<code>info_ratio</code> + <code>info_traffic</code> 开放度地图。'
        '<br>现状：2026-04-08 dump 里已含 33,366 个 PeeringDB org 记录'
        '（<code>peeringdb_orgs.csv</code>），但本页仍以 ROVISTA-by-country '
        '为主面板——作为 Topic 2 全球散点的国别补充。'
        'Peering 开放度专题面板可在后续迭代中扩展。',
        title='设计说明 · Design note',
    )

    banner = (
        '<div class="step-banner">'
        '<h1>ROVISTA 国别执行图谱 · ROV Enforcement by Country</h1>'
        '<h2>Global + target-9 view of route-validation enforcement · '
        'substitute for PeeringDB openness (data unavailable)</h2>'
        '</div>'
        '<div class="step-footer">topic 8 · 2024-10 snapshot · '
        'Virginia Tech ROVISTA measurement</div>'
    )
    out_path = OUT / 'topic8_rovista_country.html'
    out_path.write_text(
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>ROVISTA 国别执行图谱 · ROV by Country</title>'
        f'{BANNER_CSS}</head><body>'
        f'{banner}<div class="content">{intro}'
        f'{"".join(parts)}</div></body></html>',
        encoding='utf-8',
    )
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    print('top-5 enforcing:', [(r['cc'], f'{r["mean"]*100:.0f}%') for r in rows[:5]])
    print('bottom-5:',
          [(r['cc'], f'{r["mean"]*100:.0f}%') for r in rows[-5:]])


if __name__ == '__main__':
    build()
