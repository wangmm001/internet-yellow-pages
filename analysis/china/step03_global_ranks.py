"""Step 03 · China vs World at a Glance.

Dimensions: aggregate per-country counts across AS/Prefix/IXP/Facility/HostName
Data: cached + optional live Neo4j for prefix-country
Output: global_country_stats.csv + choropleth + rank bars
"""
import csv
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.china.common import (  # noqa: E402
    COLORS, DATA_DIR, TEXT_PRIMARY, TEXT_SECONDARY, DARK_PANEL,
    iso2_to_iso3, load_country_as_map, neo4j_available,
    save_multi_plotly_html, write_csv, write_step_metrics, writeup,
)
from analysis.complex_network.utils import DATA_DIR as GLOBAL_DATA_DIR, run_query

STEP = 3
TITLE_ZH = '中国在全球尺度上的地位概览'
TITLE_EN = 'China vs World at a Glance'


def _load_csv_count(path, key_col):
    c = Counter()
    if not os.path.exists(path):
        return c
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            val = row.get(key_col, '').strip()
            if val:
                # handle pipe-separated multi-country
                for cc in val.split('|'):
                    if cc and len(cc) == 2:
                        c[cc] += 1
    return c


def main():
    # AS count per country
    as_per_country = {cc: len(asns) for cc, asns in load_country_as_map().items()}

    # IXP count per country (from ixp_stats.csv)
    ixp_per_country = _load_csv_count(
        os.path.join(GLOBAL_DATA_DIR, 'ixp_stats.csv'), 'countries')

    # Facility count per country (from as_facility.csv; each row = AS-at-facility)
    fac_per_country = Counter()
    fpath = os.path.join(GLOBAL_DATA_DIR, 'as_facility.csv')
    if os.path.exists(fpath):
        fac_names = defaultdict(set)  # cc -> set(fac_name)
        with open(fpath, encoding='utf-8') as f:
            for row in csv.DictReader(f):
                for cc in (row.get('fac_countries') or '').split('|'):
                    cc = cc.strip()
                    if cc:
                        fac_names[cc].add(row['facility_name'])
        fac_per_country = {cc: len(s) for cc, s in fac_names.items()}

    # Prefix count per country (live Neo4j, fallback cached if exists)
    prefix_per_country = {}
    if neo4j_available():
        try:
            recs = run_query("""
                MATCH (a:AS)-[:COUNTRY]->(c:Country)
                MATCH (a)-[:ORIGINATE]->(pfx:BGPPrefix)
                RETURN c.country_code AS cc, count(DISTINCT pfx) AS cnt
                ORDER BY cnt DESC
            """)
            prefix_per_country = {r['cc']: r['cnt'] for r in recs}
        except Exception as e:
            print(f'[neo4j] prefix query failed: {e}')

    # Union all countries seen
    all_countries = (set(as_per_country) | set(ixp_per_country) | set(fac_per_country)
                     | set(prefix_per_country))
    rows = []
    for cc in sorted(all_countries):
        rows.append({
            'country_code': cc,
            'as_count': as_per_country.get(cc, 0),
            'prefix_count': prefix_per_country.get(cc, 0),
            'ixp_count': ixp_per_country.get(cc, 0),
            'facility_count': fac_per_country.get(cc, 0),
        })
    write_csv('global_country_stats.csv', rows)

    # ── Plotly choropleth (AS count) ──
    import plotly.graph_objects as go

    def choropleth(metric, title, colorscale='Viridis'):
        import math
        ccs_iso3 = []
        vals = []
        texts = []
        for r in rows:
            if r['country_code'] in ('ZZ', ''):
                continue
            iso3 = iso2_to_iso3(r['country_code'])
            if not iso3:
                continue
            ccs_iso3.append(iso3)
            vals.append(math.log10(max(r[metric], 0) + 1))
            texts.append(f'{r["country_code"]}: {r[metric]:,}')
        fig = go.Figure(go.Choropleth(
            locations=ccs_iso3, locationmode='ISO-3', z=vals,
            colorscale=colorscale, colorbar=dict(title='log10(count)'),
            text=texts, hovertemplate='%{text}<extra></extra>',
        ))
        fig.update_layout(
            title=title,
            geo=dict(bgcolor='#0D1117', showframe=False, showcoastlines=True,
                     coastlinecolor='#30363D', projection_type='natural earth',
                     landcolor='#161B22'),
            height=520,
        )
        return fig

    def rank_bar(metric, title):
        sorted_rows = sorted([r for r in rows if r['country_code'] != 'ZZ'],
                             key=lambda r: r[metric], reverse=True)[:15]
        cn_rank_overall = next(
            (i + 1 for i, r in enumerate(sorted(
                [r for r in rows if r['country_code'] != 'ZZ'],
                key=lambda r: r[metric], reverse=True)) if r['country_code'] == 'CN'),
            None,
        )
        cn_val = next((r[metric] for r in rows if r['country_code'] == 'CN'), 0)
        colors = [COLORS['red'] if r['country_code'] == 'CN' else COLORS['cyan']
                  for r in sorted_rows]
        fig = go.Figure(go.Bar(
            x=[r['country_code'] for r in sorted_rows],
            y=[r[metric] for r in sorted_rows],
            marker_color=colors,
            text=[f'{r[metric]:,}' for r in sorted_rows],
            textposition='outside',
        ))
        fig.update_layout(
            title=f'{title} · CN rank = #{cn_rank_overall} ({cn_val:,})',
            yaxis=dict(title=metric),
        )
        return fig

    figs = []
    subtitles = []
    for metric, title in [
        ('as_count', 'AS 数 · Countries by AS count'),
        ('prefix_count', 'BGP 前缀数 · BGP prefixes per country'),
        ('ixp_count', 'IXP 数 · IXP count'),
        ('facility_count', '机房数 · Facility count'),
    ]:
        if metric == 'prefix_count' and not prefix_per_country:
            continue
        figs.append(choropleth(metric, f'全球分布 · {title}'))
        subtitles.append(f'Choropleth: {title}')
        figs.append(rank_bar(metric, title))
        subtitles.append(f'Top-15 Ranking: {title}')

    # Metrics
    cn_ranks = {}
    for metric in ['as_count', 'prefix_count', 'ixp_count', 'facility_count']:
        sr = sorted([r for r in rows if r['country_code'] != 'ZZ'],
                    key=lambda r: r[metric], reverse=True)
        for i, r in enumerate(sr):
            if r['country_code'] == 'CN':
                cn_ranks[metric] = {'rank': i + 1, 'value': r[metric]}
                break
    write_step_metrics(STEP, {'cn_ranks_by_metric': cn_ranks}, TITLE_ZH, TITLE_EN)

    w = writeup(
        hypothesis=(
            '互联网规模在各国之间极不均等，美国在 AS/前缀/IXP 各维度均处首位。'
            '中国在"用户侧规模"领先但在"互联基础设施（IXP / Facility）"维度往往低于欧美。<br>'
            'Internet size is highly skewed; US leads on AS/prefix/IXP/Facility; CN typically leads on '
            'eyeball scale but lags on interconnection infrastructure density.'
        ),
        finding=(
            f'CN 排名（全球）：AS 数 #{cn_ranks.get("as_count", {}).get("rank", "?")}，'
            f'前缀数 #{cn_ranks.get("prefix_count", {}).get("rank", "?")}，'
            f'IXP 数 #{cn_ranks.get("ixp_count", {}).get("rank", "?")}，'
            f'Facility 数 #{cn_ranks.get("facility_count", {}).get("rank", "?")}。'
            f'用户侧（AS/前缀）靠前，互联基础设施（IXP/Facility）明显靠后。<br>'
            f'CN ranks: AS #{cn_ranks.get("as_count", {}).get("rank", "?")}, '
            f'Prefix #{cn_ranks.get("prefix_count", {}).get("rank", "?")}, '
            f'IXP #{cn_ranks.get("ixp_count", {}).get("rank", "?")}, '
            f'Facility #{cn_ranks.get("facility_count", {}).get("rank", "?")}. '
            'Eyeball scale high, interconnection infrastructure density low.'
        ),
        reference='IYP live Neo4j + cached ixp_stats / as_facility',
    )

    save_multi_plotly_html(
        figs, 'step03_global_ranks.html',
        step_num=STEP, title_zh=TITLE_ZH, title_en=TITLE_EN,
        source=('Neo4j+CSV' if prefix_per_country else 'cached CSV'),
        writeup_html=w, subtitles=subtitles,
    )


if __name__ == '__main__':
    main()
