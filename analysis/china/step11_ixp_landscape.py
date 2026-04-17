"""Step 11 · Chinese IXP Landscape.

Dimensions: AS -[:MEMBER_OF]- IXP + IXP -[:COUNTRY]- Country
Data: cached as_ixp_membership.csv + ixp_stats.csv
Output: cn_ixp_memberships.csv + geo-bubble + domestic/foreign bars
"""
import csv
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.china.common import (  # noqa: E402
    COLORS, DATA_DIR, TEXT_PRIMARY, country_color, iso2_to_iso3,
    load_cn_ases, save_multi_plotly_html, write_csv,
    write_step_metrics, writeup,
)
from analysis.complex_network.utils import DATA_DIR as GLOBAL_DATA_DIR

STEP = 11
TITLE_ZH = '中国 IXP 互联生态'
TITLE_EN = 'China IXP Landscape'


def main():
    cn = load_cn_ases()

    # Load CN AS memberships + per-IXP country
    ixp_cn_members = Counter()       # ixp_name -> # CN members
    ixp_country = {}                 # ixp_name -> country_code
    cn_ixp_rows = []                 # (asn, ixp, country)
    path = os.path.join(GLOBAL_DATA_DIR, 'as_ixp_membership.csv')
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            try:
                asn = int(row['asn'])
            except Exception:
                continue
            ixp = row['ixp_name']
            ccs = (row.get('ixp_countries') or '').split('|')
            cc = ccs[0] if ccs else 'ZZ'
            ixp_country[ixp] = cc
            if asn in cn:
                ixp_cn_members[ixp] += 1
                cn_ixp_rows.append({'asn': asn, 'ixp': ixp, 'country': cc})

    # Total IXP sizes
    ixp_size = Counter()
    path = os.path.join(GLOBAL_DATA_DIR, 'ixp_stats.csv')
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            try:
                ixp_size[row['ixp_name']] = int(row['member_count'])
            except Exception:
                continue
            if row['ixp_name'] not in ixp_country:
                cc = (row.get('countries') or '').split('|')[0] or 'ZZ'
                ixp_country[row['ixp_name']] = cc

    write_csv('cn_ixp_memberships.csv', cn_ixp_rows,
              fieldnames=['asn', 'ixp', 'country'])

    # ── Top IXPs by CN presence ──
    top = ixp_cn_members.most_common(25)
    # Split domestic vs foreign
    domestic_top = [(i, c) for i, c in top if ixp_country.get(i) == 'CN']
    foreign_top = [(i, c) for i, c in top if ixp_country.get(i) != 'CN']

    import plotly.graph_objects as go

    # ── Bar: top IXPs globally by CN presence ──
    bar = go.Figure(go.Bar(
        x=[f'{i}<br>[{ixp_country.get(i, "?")}]' for i, _ in top],
        y=[c for _, c in top],
        marker_color=[country_color(ixp_country.get(i, 'ZZ')) for i, _ in top],
        text=[str(c) for _, c in top],
        textposition='outside',
    ))
    bar.update_layout(title='Top-25 IXPs by CN member count (colors = host country)',
                      yaxis=dict(title='# CN ASes member'),
                      xaxis=dict(tickangle=-60))

    # ── Geo-bubble map ──
    import math
    bubble_cc_agg = Counter()
    for ixp, cnt in ixp_cn_members.items():
        cc = ixp_country.get(ixp, 'ZZ')
        bubble_cc_agg[cc] += cnt
    ccs = [(cc, v) for cc, v in bubble_cc_agg.most_common() if iso2_to_iso3(cc)]
    map_fig = go.Figure(go.Choropleth(
        locations=[iso2_to_iso3(cc) for cc, _ in ccs],
        locationmode='ISO-3',
        z=[math.log10(v + 1) for _, v in ccs],
        colorscale='Reds',
        colorbar=dict(title='log10(CN members)'),
        text=[f'{cc}: {v:,} CN memberships' for cc, v in ccs],
        hovertemplate='%{text}<extra></extra>',
    ))
    map_fig.update_layout(
        title='CN ASes 在全球 IXP 的参与度 · CN membership heat map',
        geo=dict(bgcolor='#0D1117', showframe=False, showcoastlines=True,
                 coastlinecolor='#30363D', projection_type='natural earth',
                 landcolor='#161B22'),
        height=520,
    )

    # ── Domestic IXP bar ──
    dom = go.Figure(go.Bar(
        x=[i for i, _ in domestic_top],
        y=[c for _, c in domestic_top],
        marker_color=COLORS['red'],
        text=[str(c) for _, c in domestic_top],
        textposition='outside',
    ))
    dom.update_layout(
        title=f'中国境内 IXPs · Domestic CN-hosted IXPs ({len(domestic_top)} shown)',
        yaxis=dict(title='# CN members'),
        xaxis=dict(tickangle=-30))

    # ── Concentration ratio ──
    dom_cn_total = sum(c for _, c in domestic_top)
    frn_cn_total = sum(c for _, c in foreign_top)
    pie = go.Figure(go.Pie(
        labels=['境内 IXP CN 会员记录', '境外 IXP CN 会员记录'],
        values=[dom_cn_total, frn_cn_total],
        marker=dict(colors=[COLORS['red'], COLORS['cyan']]),
        hole=0.4, textinfo='label+percent',
    ))
    pie.update_layout(title='中国 AS 的 IXP 连接分布 · Domestic vs foreign share')

    metrics = {
        'cn_ixp_memberships_total': sum(ixp_cn_members.values()),
        'distinct_cn_ixps_participated': len(ixp_cn_members),
        'domestic_ixps_with_cn': len(domestic_top),
        'foreign_ixps_with_cn': len(foreign_top),
        'top5_foreign_ixps': [(i, c) for i, c in foreign_top[:5]],
        'top5_domestic_ixps': domestic_top[:5],
        'top5_countries_hosting_cn_presence': dict(bubble_cc_agg.most_common(5)),
    }
    write_step_metrics(STEP, metrics, TITLE_ZH, TITLE_EN)

    w = writeup(
        hypothesis=(
            '国家互联网独立性假设：自有 IXP 越多，跨境流量越少。现实中，大陆 IXP 市场被政策抑制，'
            '大量 CN AS 在香港/新加坡/法兰克福等海外 IXP 换路由。<br>'
            'A country with robust domestic IXPs should keep more local traffic onshore. In CN, domestic '
            'IXP market is policy-restricted; many CN ASes peer at offshore IXPs (HK, SG, AMS, FRA).'
        ),
        finding=(
            f'CN AS 参与 {len(ixp_cn_members)} 个 IXP（{sum(ixp_cn_members.values())} 条会员记录）。'
            f'境内 IXP 仅 {len(domestic_top)} 个有 CN 会员记录（合计 {dom_cn_total}），'
            f'境外 IXP 覆盖 {len(foreign_top)} 个（合计 {frn_cn_total}）。'
            f'最大海外 IXP：{", ".join(f"{i}({c})" for i, c in foreign_top[:3])}。<br>'
            f'CN ASes participate in {len(ixp_cn_members)} IXPs ({sum(ixp_cn_members.values())} memberships). '
            f'{len(domestic_top)} domestic vs {len(foreign_top)} foreign IXPs with CN presence. '
            f'Top foreign: {", ".join(f"{i}({c})" for i, c in foreign_top[:3])}.'
        ),
        reference='PeeringDB + CAIDA IXP data via IYP',
    )

    save_multi_plotly_html(
        [map_fig, bar, dom, pie], 'step11_ixp_landscape.html',
        step_num=STEP, title_zh=TITLE_ZH, title_en=TITLE_EN, source='cached CSV',
        writeup_html=w,
        subtitles=['1. CN 会员全球分布', '2. Top-25 IXP (CN 会员数)',
                   '3. 境内 IXP 榜', '4. 境内 vs 境外分布'],
    )


if __name__ == '__main__':
    main()
