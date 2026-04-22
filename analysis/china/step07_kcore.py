"""Step 07 · CN Positions in Global k-Core.

Dimensions: k-core decomposition of global AS peering graph
Data: cached step08_coreness.csv
Output: cn_coreness.csv + coreness histogram + rich-core CN scatter
"""
import csv
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.china.common import (  # noqa: E402
    COLORS, DATA_DIR, as_hover_with_org, as_label_with_org,
    load_as_country_map, load_as_metadata, load_as_org_map, load_cn_ases,
    save_multi_plotly_html, write_csv, write_step_metrics, writeup,
)
from analysis.complex_network.utils import DATA_DIR as GLOBAL_DATA_DIR

STEP = 7
TITLE_ZH = '中国 AS 在全球 k-core 层级中的位置'
TITLE_EN = 'China ASes in Global k-Core Hierarchy'


def main():
    cn = load_cn_ases()
    cmap = load_as_country_map()
    path = os.path.join(GLOBAL_DATA_DIR, 'step08_coreness.csv')

    rows = []
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            try:
                rows.append({
                    'asn': int(row['asn']),
                    'coreness': int(row['coreness']),
                    'degree': int(row['degree']),
                    'ixp_count': int(row['ixp_count']),
                })
            except Exception:
                continue

    max_core = max(r['coreness'] for r in rows)
    cn_rows = [r for r in rows if r['asn'] in cn]
    cn_rows.sort(key=lambda r: r['coreness'], reverse=True)
    write_csv('cn_coreness.csv', cn_rows,
              fieldnames=['asn', 'coreness', 'degree', 'ixp_count'])

    # ── Histogram: coreness distribution per region-group ──
    import plotly.graph_objects as go
    groups = {'CN': cn, 'US': cmap.get('US', set()), 'DE': cmap.get('DE', set()),
              'BR': cmap.get('BR', set()), 'Other': None}
    colors = {'CN': COLORS['red'], 'US': COLORS['blue'],
              'DE': COLORS['purple'], 'BR': COLORS['green'], 'Other': '#8B949E'}
    histo = go.Figure()
    all_core_counts = Counter()
    for r in rows:
        all_core_counts[r['coreness']] += 1
    for name, asns in groups.items():
        buckets = defaultdict(int)
        for r in rows:
            if name == 'Other':
                if r['asn'] in cn:
                    continue
                if r['asn'] in cmap.get('US', set()):
                    continue
                if r['asn'] in cmap.get('DE', set()):
                    continue
                if r['asn'] in cmap.get('BR', set()):
                    continue
                buckets[r['coreness']] += 1
            elif r['asn'] in asns:
                buckets[r['coreness']] += 1
        ks = sorted(buckets)
        histo.add_trace(go.Bar(
            name=name, x=ks, y=[buckets[k] for k in ks],
            marker_color=colors[name], opacity=0.85,
        ))
    histo.update_layout(
        barmode='stack',
        title=f'按 coreness 层级的 AS 数量 (max k={max_core}) · Distribution by region',
        xaxis=dict(title='Coreness (k-core layer)'),
        yaxis=dict(title='AS count', type='log'),
    )

    # ── CN in inner-core (k >= 50) ── use Org on the x-axis so operator identity
    # is readable at a glance; fallback to first IYP tag if Org is missing.
    md = load_as_metadata()
    org_map = load_as_org_map()
    deep = [r for r in cn_rows if r['coreness'] >= 30]
    deep.sort(key=lambda r: r['coreness'], reverse=True)
    labels = []
    for r in deep[:20]:
        lbl = as_label_with_org(r['asn'], org_map, max_org_len=22)
        if ' · ' not in lbl:  # no org — use first IYP tag
            tags = md.get(r['asn'], {}).get('tags', [])
            if tags:
                lbl += f' · {tags[0][:22]}'
        labels.append(lbl)
    bar = go.Figure(go.Bar(
        x=labels,
        y=[r['coreness'] for r in deep[:20]],
        marker_color=COLORS['red'],
        text=[str(r['coreness']) for r in deep[:20]],
        textposition='outside',
        customdata=[as_hover_with_org(r['asn'], org_map) for r in deep[:20]],
        hovertemplate='%{customdata}<br>coreness = %{y}<extra></extra>',
    ))
    bar.update_layout(
        title=f'深入核心的中国 AS · CN ASes reaching deep k-core (k≥30) · max={max_core}',
        yaxis=dict(title='Coreness'),
        xaxis=dict(tickangle=-40, automargin=True, title='AS · 所属组织'),
        margin=dict(l=70, r=30, t=70, b=150),
        bargap=0.3,
    )

    # ── Coreness vs degree (CN vs Other) ──
    scatter = go.Figure()
    other_ks = [r['coreness'] for r in rows if r['asn'] not in cn]
    other_deg = [r['degree'] for r in rows if r['asn'] not in cn]
    scatter.add_trace(go.Scatter(
        x=other_ks, y=other_deg, mode='markers',
        marker=dict(color='#8B949E', size=3, opacity=0.25), name='Other',
        hoverinfo='skip',
    ))
    scatter.add_trace(go.Scatter(
        x=[r['coreness'] for r in cn_rows],
        y=[r['degree'] for r in cn_rows],
        mode='markers', marker=dict(color=COLORS['red'], size=7),
        name='CN',
        text=[as_hover_with_org(r['asn'], org_map) for r in cn_rows],
        hovertemplate='%{text}<br>coreness = %{x}<br>degree = %{y}<extra></extra>',
    ))
    scatter.update_layout(
        title='Coreness × Degree (CN red)',
        xaxis=dict(title='Coreness'),
        yaxis=dict(title='Degree', type='log'),
        margin=dict(l=70, r=30, t=70, b=60),
    )

    metrics = {
        'global_max_k': max_core,
        'cn_deepest_coreness': max(r['coreness'] for r in cn_rows) if cn_rows else None,
        'cn_count_k_ge_30': len([r for r in cn_rows if r['coreness'] >= 30]),
        'cn_count_k_ge_100': len([r for r in cn_rows if r['coreness'] >= 100]),
        'cn_top5_coreness': [(r['asn'], r['coreness']) for r in cn_rows[:5]],
    }
    write_step_metrics(STEP, metrics, TITLE_ZH, TITLE_EN)

    w = writeup(
        hypothesis=(
            'k-core 分解揭示层级化核心结构；'
            '先前全局分析显示 k=197 的最内核仅含 340 个 AS (<0.4%)，主要由欧美 Tier-1 构成。<br>'
            'k-core decomposition reveals a hierarchical core; prior global analysis showed the k=197 innermost '
            'core contains just 340 ASes (<0.4%), predominantly EU/US Tier-1.'
        ),
        finding=(
            f'全球最大 coreness k={max_core}。中国 AS 最深达 coreness {metrics["cn_deepest_coreness"]}；'
            f'进入 k≥30 层的 CN AS 共 {metrics["cn_count_k_ge_30"]} 个，'
            f'进入 k≥100 层的 CN AS 共 {metrics["cn_count_k_ge_100"]} 个。<br>'
            f'Global max k={max_core}; CN deepest coreness = {metrics["cn_deepest_coreness"]}. '
            f'CN ASes reaching k≥30: {metrics["cn_count_k_ge_30"]}; reaching k≥100: '
            f'{metrics["cn_count_k_ge_100"]}. CN presence in the global core is limited.'
        ),
        reference='Reuse of complex_network/step08_coreness.csv',
    )

    save_multi_plotly_html(
        [histo, bar, scatter], 'step07_kcore.html',
        step_num=STEP, title_zh=TITLE_ZH, title_en=TITLE_EN, source='cached CSV',
        writeup_html=w,
        subtitles=['1. 各区域 coreness 分布', '2. CN 进入深层核心 AS',
                   '3. Coreness × Degree'],
    )


if __name__ == '__main__':
    main()
