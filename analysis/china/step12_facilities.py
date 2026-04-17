"""Step 12 · China AS Facility Co-location.

Dimensions: AS-[:LOCATED_IN]-Facility + Facility-[:COUNTRY]-Country
Data: cached as_facility.csv
Output: cn_facilities.csv + treemap + geo bubble
"""
import csv
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.china.common import (  # noqa: E402
    COLORS, DATA_DIR, country_color, iso2_to_iso3, load_as_metadata,
    load_cn_ases, save_multi_plotly_html, write_csv, write_step_metrics, writeup,
)
from analysis.complex_network.utils import DATA_DIR as GLOBAL_DATA_DIR

STEP = 12
TITLE_ZH = '中国 AS 机房与物理站点分布'
TITLE_EN = 'China AS Facility Co-location'


def main():
    cn = load_cn_ases()
    md = load_as_metadata()

    path = os.path.join(GLOBAL_DATA_DIR, 'as_facility.csv')
    rows = []
    fac_cc = {}            # facility -> country_code (primary)
    fac_cn_count = Counter()  # facility -> # CN ASes
    cc_count = Counter()      # country -> # CN AS-at-facility records
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            try:
                asn = int(row['asn'])
            except Exception:
                continue
            fac = row['facility_name']
            ccs = (row.get('fac_countries') or '').split('|')
            cc = ccs[0] if ccs else 'ZZ'
            fac_cc[fac] = cc
            if asn in cn:
                fac_cn_count[fac] += 1
                cc_count[cc] += 1
                rows.append({'asn': asn, 'facility': fac, 'country': cc})

    write_csv('cn_facilities.csv', rows,
              fieldnames=['asn', 'facility', 'country'])

    import plotly.graph_objects as go
    import math

    # ── Treemap: Country → Facility ──
    labels = ['Global']
    parents = ['']
    values = [sum(fac_cn_count.values())]
    colors_tree = [COLORS['red']]

    # Group facilities by country, take top 4 per country
    cc_to_facs = defaultdict(list)
    for fac, cnt in fac_cn_count.items():
        cc = fac_cc.get(fac, 'ZZ')
        cc_to_facs[cc].append((fac, cnt))

    for cc, facs in sorted(cc_to_facs.items(), key=lambda t: -sum(c for _, c in t[1])):
        facs.sort(key=lambda t: -t[1])
        total = sum(c for _, c in facs)
        labels.append(f'{cc} ({total})')
        parents.append('Global')
        values.append(total)
        colors_tree.append(country_color(cc))
        for fac, cnt in facs[:4]:
            lbl = f'{fac[:32]} · {cnt}'
            labels.append(lbl)
            parents.append(f'{cc} ({total})')
            values.append(cnt)
            colors_tree.append(country_color(cc))

    treemap = go.Figure(go.Treemap(
        labels=labels, parents=parents, values=values,
        marker=dict(colors=colors_tree),
        branchvalues='total',
        hovertemplate='<b>%{label}</b><br>%{value} CN AS-facility records<extra></extra>',
    ))
    treemap.update_layout(title='CN AS 机房分布 · Country → Facility treemap')

    # ── Geo bubble (choropleth) ──
    ccs = [(cc, v) for cc, v in cc_count.most_common() if iso2_to_iso3(cc)]
    map_fig = go.Figure(go.Choropleth(
        locations=[iso2_to_iso3(cc) for cc, _ in ccs],
        locationmode='ISO-3',
        z=[math.log10(v + 1) for _, v in ccs],
        colorscale='Reds',
        text=[f'{cc}: {v:,} CN AS-facility records' for cc, v in ccs],
        hovertemplate='%{text}<extra></extra>',
        colorbar=dict(title='log10(count)'),
    ))
    map_fig.update_layout(
        title='CN AS 机房部署国家热力图',
        geo=dict(bgcolor='#0D1117', showframe=False, landcolor='#161B22',
                 projection_type='natural earth'),
        height=520,
    )

    # ── Top facilities bar ──
    top_fac = fac_cn_count.most_common(20)
    bar = go.Figure(go.Bar(
        x=[f'{f[:28]}<br>[{fac_cc.get(f, "?")}]' for f, _ in top_fac],
        y=[c for _, c in top_fac],
        marker_color=[country_color(fac_cc.get(f, 'ZZ')) for f, _ in top_fac],
        text=[str(c) for _, c in top_fac],
        textposition='outside',
    ))
    bar.update_layout(title='Top-20 机房 · Facilities with most CN AS presence',
                      yaxis=dict(title='# CN ASes present'),
                      xaxis=dict(tickangle=-45))

    metrics = {
        'total_cn_as_facility_records': sum(fac_cn_count.values()),
        'distinct_facilities_with_cn': len(fac_cn_count),
        'top5_countries_by_cn_facility_presence': dict(cc_count.most_common(5)),
        'top5_facilities': [(f, c, fac_cc.get(f, '?')) for f, c in top_fac[:5]],
    }
    write_step_metrics(STEP, metrics, TITLE_ZH, TITLE_EN)

    w = writeup(
        hypothesis=(
            '机房 (Facility) 是物理 PoP 的代表；国家互联网的"物理边境外延"可由境外机房数量衡量。<br>'
            'Facility presence measures physical PoPs; a country\'s "physical network frontier" is partly the '
            'set of foreign data centers where its ASes operate equipment.'
        ),
        finding=(
            f'{len(fac_cn_count)} 个全球机房记录了 CN AS 存在（共 {sum(fac_cn_count.values())} 条记录）。'
            f'Top 国家：{", ".join(f"{cc}({v})" for cc, v in cc_count.most_common(5))}。'
            f'Top 机房：{", ".join(f"{f[:15]}({c})" for f, c in top_fac[:3])}。<br>'
            f'{len(fac_cn_count)} facilities worldwide host CN AS equipment ({sum(fac_cn_count.values())} records). '
            f'Top countries: {", ".join(f"{cc}({v})" for cc, v in cc_count.most_common(5))}.'
        ),
        reference='PeeringDB + CAIDA Facility data via IYP',
    )

    save_multi_plotly_html(
        [treemap, map_fig, bar], 'step12_facilities.html',
        step_num=STEP, title_zh=TITLE_ZH, title_en=TITLE_EN, source='cached CSV',
        writeup_html=w,
        subtitles=['1. 国家→机房 Treemap', '2. 热力图', '3. Top-20 机房'],
    )


if __name__ == '__main__':
    main()
