"""Step 01 · China AS Inventory & Scope Definition.

Dimensions: AS-[:COUNTRY]->Country, Tag
Data: cached as_country.csv + as_metadata.csv
Output: cn_ases.csv + sunburst/table HTML
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.china.common import (  # noqa: E402
    COLORS, DATA_DIR, DARK_BG, DARK_PANEL, TEXT_PRIMARY,
    load_as_metadata, load_greater_china_groups,
    save_multi_plotly_html, write_csv, write_step_metrics, writeup,
)

STEP = 1
TITLE_ZH = '中国自治系统清册与范围界定'
TITLE_EN = 'China AS Inventory & Scope Definition'


def main():
    groups = load_greater_china_groups()
    md = load_as_metadata()

    # Build flat records: asn, region (CN/HK/TW/MO), primary_tag
    records = []
    tag_category_keywords = [
        ('ISP', ['Internet Service Provider', 'Home ISP', 'ISP', 'Carrier']),
        ('Eyeball', ['Eyeball', 'Business Broadband', 'Mobile Data']),
        ('Content/CDN', ['Content Delivery Network', 'Cloud', 'Hosting', 'CDN']),
        ('Academic/Edu', ['Academic', 'Education', 'Universities']),
        ('Government', ['Government', 'Defense', 'Military']),
        ('Enterprise', ['Enterprise', 'Business']),
        ('Other', []),
    ]

    def primary_tag(tags):
        if not tags:
            return 'Unknown'
        blob = '|'.join(tags)
        for cat, kws in tag_category_keywords:
            for kw in kws:
                if kw in blob:
                    return cat
        return 'Other'

    tag_counters = {k: Counter() for k in groups}
    total_asns = 0
    for region, asns in groups.items():
        for asn in asns:
            meta = md.get(asn, {'tags': []})
            cat = primary_tag(meta['tags'])
            tag_counters[region][cat] += 1
            records.append({'asn': asn, 'region': region, 'category': cat,
                            'tags': '|'.join(meta['tags'][:5])})
            total_asns += 1

    write_csv('cn_ases.csv', records, fieldnames=['asn', 'region', 'category', 'tags'])

    # ── Build Plotly sunburst: region → category ──
    import plotly.graph_objects as go
    ROOT_LABEL = '中国区 · China Region'
    labels = [ROOT_LABEL]
    parents = ['']
    values = [total_asns]
    colors = [COLORS['red']]
    for region in ['CN', 'HK', 'TW', 'MO']:
        labels.append(region)
        parents.append(ROOT_LABEL)
        values.append(len(groups[region]))
        colors.append(COLORS['red'] if region == 'CN' else COLORS['pink'])
        for cat, cnt in tag_counters[region].most_common():
            if cnt == 0:
                continue
            labels.append(f'{region}/{cat}')
            parents.append(region)
            values.append(cnt)
            colors.append(COLORS['cyan'] if cat in ('ISP', 'Eyeball') else
                          COLORS['blue'] if cat in ('Content/CDN',) else
                          COLORS['purple'] if cat == 'Academic/Edu' else
                          COLORS['orange'])

    sunburst = go.Figure(go.Sunburst(
        labels=labels, parents=parents, values=values,
        marker=dict(colors=colors, line=dict(color=DARK_BG, width=1)),
        branchvalues='total', hovertemplate='<b>%{label}</b><br>%{value} ASNs<extra></extra>',
    ))
    sunburst.update_layout(
        title=f'中国区 AS 分层 · China Region AS breakdown · {total_asns:,} ASNs total',
        margin=dict(l=40, r=40, t=80, b=40),
    )

    # ── Category table per region ──
    all_cats = sorted({c for r in groups for c in tag_counters[r]})
    header = ['Category'] + list(groups.keys())
    table_cells = [all_cats]
    for region in groups.keys():
        table_cells.append([tag_counters[region].get(c, 0) for c in all_cats])

    table_fig = go.Figure(go.Table(
        header=dict(values=header, fill_color=DARK_PANEL,
                    font=dict(color=TEXT_PRIMARY, size=13), align='left'),
        cells=dict(values=table_cells,
                   fill_color=[['#0D1117', '#161B22'] * len(all_cats)],
                   font=dict(color=TEXT_PRIMARY), align='left'),
    ))
    table_fig.update_layout(title='Region × Tag-Category distribution')

    # ── Bar: region sizes ──
    bar = go.Figure(go.Bar(
        x=list(groups.keys()),
        y=[len(groups[r]) for r in groups],
        marker_color=[COLORS['red'], COLORS['pink'], COLORS['amber'], COLORS['yellow']],
        text=[f'{len(groups[r]):,}' for r in groups],
        textposition='outside',
    ))
    bar.update_layout(title='中国区各注册地 AS 规模对比 · AS count by region',
                      yaxis=dict(title='unique ASNs'),
                      xaxis=dict(title='Region'),
                      margin=dict(l=60, r=30, t=70, b=60))

    metrics = {
        'total_greater_china_asns': total_asns,
        'cn_asns': len(groups['CN']),
        'hk_asns': len(groups['HK']),
        'tw_asns': len(groups['TW']),
        'mo_asns': len(groups['MO']),
        'cn_tag_categories': dict(tag_counters['CN'].most_common()),
    }
    write_step_metrics(STEP, metrics, TITLE_ZH, TITLE_EN)

    w = writeup(
        hypothesis=(
            '国家互联网范围通常以注册国为界，但在AS层面常见"一个实体、多国注册"现象（diaspora）。'
            '大陆/港/澳/台在统计与监管意义上需要区分讨论。<br>'
            'Country scope is usually defined by registration; AS diaspora (multi-country siblings) is common. '
            'Mainland CN vs HK/TW/MO must be tracked separately.'
        ),
        finding=(
            f'中国大陆注册 AS {len(groups["CN"]):,} 个，香港 {len(groups["HK"]):,}，'
            f'台湾 {len(groups["TW"]):,}，澳门 {len(groups["MO"]):,}。大陆 AS 以 ISP / Eyeball 类为主，'
            f'占比 {(tag_counters["CN"].get("ISP", 0) + tag_counters["CN"].get("Eyeball", 0)) / max(len(groups["CN"]), 1) * 100:.1f}%。<br>'
            f'Mainland CN: {len(groups["CN"]):,} ASNs; HK: {len(groups["HK"]):,}; '
            f'TW: {len(groups["TW"]):,}; MO: {len(groups["MO"]):,}. ISP+Eyeball dominate mainland.'
        ),
        reference='IYP as_country.csv + as_metadata.csv (cached snapshot 2026-04)',
    )

    save_multi_plotly_html(
        [sunburst, bar, table_fig], 'step01_scope.html',
        step_num=STEP, title_zh=TITLE_ZH, title_en=TITLE_EN, source='cached CSV',
        writeup_html=w,
        subtitles=['1. 中国区 AS 分层旭日图 · Sunburst', '2. 区域 AS 规模对比',
                   '3. 区域 × 标签类别 分布表'],
    )


if __name__ == '__main__':
    main()
