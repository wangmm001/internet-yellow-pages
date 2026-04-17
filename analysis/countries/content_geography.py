"""Content geography: where is each country's hosting physically located?

Uses cached dns_as_hosting.csv + as_country.csv (no heavy Neo4j joins).
Produces content_geography.html with:
 - Per-country hosting treemap (which ASes host the most, colored by AS country)
 - Choropleth of countries by total hostnames hosted
 - 3×3 donut: for each target country, where its own ASes' hostnames resolve
"""
import argparse
import csv
import math
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.countries.common import (  # noqa: E402
    COLORS, DARK_BG, DARK_PANEL, HTML_DIR, TARGET_COUNTRIES,
    apply_plotly_theme, bilingual, country_color, iso2_to_iso3,
    load_country_as_map, plotly_inline_once, save_consolidated_html, zh,
)
from analysis.complex_network.utils import DATA_DIR as CACHE_DIR


def load_hosting_by_country():
    """Return dict[cc] -> total hostname count (across ASes registered in cc)."""
    # Build asn -> primary cc
    as_cc = {}
    for cc, asns in load_country_as_map().items():
        for a in asns:
            as_cc.setdefault(a, cc)
    host_by_cc = Counter()
    host_per_as = []
    path = os.path.join(CACHE_DIR, 'dns_as_hosting.csv')
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            try:
                asn = int(row['asn'])
                hc = int(row['hostname_count'])
            except Exception:
                continue
            cc = as_cc.get(asn)
            if cc:
                host_by_cc[cc] += hc
                host_per_as.append((asn, hc, cc))
    return host_by_cc, host_per_as


def build(snapshot='2026-04'):
    host_by_cc, host_per_as = load_hosting_by_country()
    if not host_by_cc:
        print('[content_geo] no hosting data available; run extract_dns_layer.py first')

    import plotly.graph_objects as go
    import plotly.subplots as sp

    # Panel 1: Choropleth of all countries by hosted hostnames (log10)
    valid = [(cc, v) for cc, v in host_by_cc.items() if iso2_to_iso3(cc)]
    choro = go.Figure(go.Choropleth(
        locations=[iso2_to_iso3(cc) for cc, _ in valid],
        locationmode='ISO-3',
        z=[math.log10(v + 1) for _, v in valid],
        colorscale='Viridis',
        colorbar=dict(title='log10(hosted hostnames)'),
        text=[f'{cc}: {v:,}' for cc, v in valid],
        hovertemplate='%{text}<extra></extra>',
    ))
    choro.update_layout(
        title='① 全球 HostName 物理托管分布 · Global hosted hostname footprint by country',
        geo=dict(bgcolor=DARK_BG, showframe=False, landcolor=DARK_PANEL,
                 projection_type='natural earth'),
        height=520,
    )

    # Panel 2: Top-15 countries by hosting
    top15 = host_by_cc.most_common(15)
    bar = go.Figure(go.Bar(
        x=[cc for cc, _ in top15],
        y=[v for _, v in top15],
        marker_color=[country_color(cc) for cc, _ in top15],
        text=[f'{v:,}' for _, v in top15],
        textposition='outside',
    ))
    bar.update_layout(
        title='② Top-15 托管国家 · Top hosting countries (log y)',
        yaxis=dict(type='log', title='HostName count'),
        height=440,
    )

    # Panel 3: Treemap showing top-50 hosting ASes aggregated by country
    top_ases = sorted(host_per_as, key=lambda t: -t[1])[:50]
    labels = ['All top-50 ASes']
    parents = ['']
    values = [sum(h for _, h, _ in top_ases)]
    colors_tm = [COLORS['cyan']]
    # Group by country
    by_cc = defaultdict(list)
    for asn, hc, cc in top_ases:
        by_cc[cc].append((asn, hc))
    for cc, lst in sorted(by_cc.items(), key=lambda t: -sum(h for _, h in t[1])):
        total = sum(h for _, h in lst)
        labels.append(f'{cc}: {total:,}')
        parents.append('All top-50 ASes')
        values.append(total)
        colors_tm.append(country_color(cc))
        for asn, hc in lst[:4]:
            labels.append(f'AS{asn} · {hc:,}')
            parents.append(f'{cc}: {total:,}')
            values.append(hc)
            colors_tm.append(country_color(cc))
    tm = go.Figure(go.Treemap(
        labels=labels, parents=parents, values=values,
        marker=dict(colors=colors_tm), branchvalues='total',
        hovertemplate='%{label}<br>%{value:,} hostnames<extra></extra>',
    ))
    tm.update_layout(
        title='③ Top-50 托管 AS · Hosting AS treemap (colored by AS country)',
        height=560,
    )

    # Panel 4: 3×3 donut — for each target country, the country breakdown
    # of top-10 foreign "hosting partner" countries (where its residents'
    # cross-border dependencies go). We use host_per_as filtered to the
    # target country's ASes only — shows intra vs inter-country concentration.
    donut = sp.make_subplots(
        rows=3, cols=3, specs=[[{'type': 'pie'}] * 3] * 3,
        subplot_titles=[f'{cc} · {zh(cc)} hosting partners'
                        for cc in TARGET_COUNTRIES])
    cmap = load_country_as_map()
    for idx, target_cc in enumerate(TARGET_COUNTRIES):
        row = idx // 3 + 1
        col = idx % 3 + 1
        target_ases = cmap.get(target_cc, set())
        # For each of target's ASes, see where its hosting is registered
        # Here approximation: hostname count vs target's OWN ASes
        distribution = Counter()
        for asn, hc, cc in host_per_as:
            if asn in target_ases:
                distribution[cc] += hc
        top = distribution.most_common(8)
        if not top:
            continue
        donut.add_trace(go.Pie(
            labels=[t[0] for t in top], values=[t[1] for t in top],
            marker_colors=[country_color(t[0]) for t in top],
            textinfo='label+percent', hole=0.4, showlegend=False,
        ), row=row, col=col)
    donut.update_layout(
        title='④ 各国 AS 托管主机的国别构成 · Hosting-AS origins per target country',
        height=720,
    )

    # Panel 5: Top-5 target-country AS hosters
    target_hosters = []
    for target_cc in TARGET_COUNTRIES:
        target_ases = cmap.get(target_cc, set())
        top5 = sorted([(asn, hc) for asn, hc, _ in host_per_as
                      if asn in target_ases], key=lambda t: -t[1])[:5]
        target_hosters.append((target_cc, top5))
    thl = [f'<b>{bilingual(cc)}</b>: '
           + ', '.join(f'AS{a}({hc:,})' for a, hc in top)
           for cc, top in target_hosters]

    narr = f'''
    <div class="sidebar-note">
    <b>内容地理 · Content Geography</b><br><br>
    本视图使用 dns_as_hosting.csv 缓存（HostName → IP → Prefix → AS 已聚合），
    将每个 AS 托管的主机名数量按其注册国汇总。<br>
    Uses cached dns_as_hosting.csv aggregated by AS's registration country. Shows
    where the "visible Web" is physically hosted at per-country granularity.<br>
    <br><b>各国头部托管 AS:</b><br>
    {"<br>".join(thl)}
    </div>
    '''

    figs = [choro, bar, tm, donut]
    for f in figs:
        apply_plotly_theme(f)
    body = narr + plotly_inline_once(figs)
    save_consolidated_html(
        body, 'content_geography.html',
        title_zh='内容地理 · 可见 Web 的物理托管分布',
        title_en=f'Content Geography · Physical Hosting of the Visible Web · {snapshot}',
        subtitle=f'cached dns_as_hosting × as_country · {snapshot}',
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--snapshot', default='2026-04')
    args = ap.parse_args()
    build(args.snapshot)


if __name__ == '__main__':
    main()
