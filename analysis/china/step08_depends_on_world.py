"""Step 08 · Who does China depend on? (outbound hegemony).

Dimensions: AS-[:DEPENDS_ON {hege}]-AS where src is CN AS
Data: cached as_dependency.csv + as_country.csv
Output: cn_dependency_outbound.csv + Sankey + top-foreign bars
"""
import csv
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.china.common import (  # noqa: E402
    COLORS, DATA_DIR, country_color, load_as_country_map,
    load_as_metadata, load_cn_ases, save_multi_plotly_html, write_csv,
    write_step_metrics, writeup,
)
from analysis.complex_network.utils import DATA_DIR as GLOBAL_DATA_DIR

STEP = 8
TITLE_ZH = '中国对外依赖 · 出向 AS Hegemony'
TITLE_EN = 'Who Does China Depend On? (Outbound Hegemony)'

HEGE_MIN = 0.05  # filter weak edges


def main():
    cn = load_cn_ases()
    cmap = load_as_country_map()
    md = load_as_metadata()

    path = os.path.join(GLOBAL_DATA_DIR, 'as_dependency.csv')
    rows = []
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            try:
                s = int(row['src'])
                d = int(row['dst'])
                h = float(row['hege'])
            except Exception:
                continue
            if s == d:
                continue
            if h < HEGE_MIN:
                continue
            if s in cn and d not in cn:
                rows.append({'src': s, 'dst': d, 'hege': h})

    write_csv('cn_dependency_outbound.csv', rows,
              fieldnames=['src', 'dst', 'hege'])

    # Aggregate: which foreign AS is most depended on by CN ASes
    dep_count = Counter()
    dep_total = defaultdict(float)
    for r in rows:
        dep_count[r['dst']] += 1
        dep_total[r['dst']] += r['hege']

    # Top foreign ASes by number of CN dependents
    top_by_count = dep_count.most_common(30)

    # Country of top foreign ASes
    cc_for = {}
    for asn, _ in top_by_count:
        cc = next(iter(cmap.get(asn, {'ZZ'})), 'ZZ')
        cc_for[asn] = cc

    # ── Plotly Sankey: top-20 CN sources → top-15 foreign destinations ──
    import plotly.graph_objects as go
    src_count = Counter(r['src'] for r in rows)
    top_src = [a for a, _ in src_count.most_common(20)]
    top_dst = [a for a, _ in dep_count.most_common(15)]
    src_set = set(top_src)
    dst_set = set(top_dst)

    node_labels = [f'AS{a} (CN)' for a in top_src] + [
        f'AS{a} ({cc_for.get(a, "?")})' for a in top_dst]
    node_colors = ([COLORS['red']] * len(top_src)
                   + [country_color(cc_for.get(a, 'ZZ')) for a in top_dst])
    src_idx = {a: i for i, a in enumerate(top_src)}
    dst_idx = {a: len(top_src) + i for i, a in enumerate(top_dst)}

    links_src, links_dst, links_val, links_lbl = [], [], [], []
    for r in rows:
        if r['src'] in src_set and r['dst'] in dst_set:
            links_src.append(src_idx[r['src']])
            links_dst.append(dst_idx[r['dst']])
            links_val.append(r['hege'])
            links_lbl.append(f'hege={r["hege"]:.3f}')

    sankey = go.Figure(go.Sankey(
        node=dict(label=node_labels, color=node_colors, pad=14, thickness=18),
        link=dict(source=links_src, target=links_dst, value=links_val,
                  label=links_lbl, color='rgba(69,183,209,0.3)'),
    ))
    sankey.update_layout(
        title='Top-20 CN → Top-15 Foreign Transit (edge width = hegemony)', height=700)

    # ── Bar: top-15 foreign ASes by # CN dependents ──
    top15 = dep_count.most_common(15)
    bar = go.Figure(go.Bar(
        x=[f'AS{a}<br>{cc_for.get(a, "?")}' for a, _ in top15],
        y=[c for _, c in top15],
        marker_color=[country_color(cc_for.get(a, 'ZZ')) for a, _ in top15],
        text=[str(c) for _, c in top15],
        textposition='outside',
    ))
    bar.update_layout(title='中国 AS 依赖最多的海外 AS · Foreign ASes most-depended-on by CN',
                      yaxis=dict(title='# CN ASes depending on'),
                      xaxis=dict(tickangle=-30))

    # ── Country aggregation ──
    country_dep_count = Counter()
    for a, c in dep_count.items():
        cc = cc_for.get(a) or next(iter(cmap.get(a, {'ZZ'})), 'ZZ')
        country_dep_count[cc] += c

    top_cc = country_dep_count.most_common(10)
    pie = go.Figure(go.Pie(
        labels=[cc for cc, _ in top_cc],
        values=[c for _, c in top_cc],
        marker=dict(colors=[country_color(cc) for cc, _ in top_cc]),
        textinfo='label+percent',
    ))
    pie.update_layout(
        title='CN 对外依赖按国家聚合 · Outbound dependency by destination country')

    metrics = {
        'total_outbound_edges_hege_ge_005': len(rows),
        'foreign_ases_depended_on': len(dep_count),
        'top5_foreign_upstream': [(a, dep_count[a], cc_for.get(a, '?')) for a, _ in top15[:5]],
        'top_destination_countries': dict(country_dep_count.most_common(8)),
    }
    write_step_metrics(STEP, metrics, TITLE_ZH, TITLE_EN)

    w = writeup(
        hypothesis=(
            'AS Hegemony (IHR) 度量一个 AS 作为"必经转发点"的比例；'
            '国家出向依赖反映了跨境流量的结构性控制点。'
            '假设：中国主要依赖的上游 AS 集中在美国 Tier-1 与东亚枢纽 (JP/SG/HK)。<br>'
            'AS Hegemony quantifies how often an AS sits on shortest paths. '
            'Hypothesis: CN outbound dependency concentrates on US Tier-1s and East-Asian hubs (JP/SG/HK).'
        ),
        finding=(
            f'CN→外 有效依赖边 {len(rows):,} 条（hege≥{HEGE_MIN}）。最核心外部上游：'
            + ', '.join(f'AS{a}({cc_for.get(a, "?")})' for a, _ in top15[:5])
            + f'。目的地国家分布：' + ', '.join(f'{cc}({c})' for cc, c in country_dep_count.most_common(5))
            + f'。<br>'
            + f'{len(rows):,} outbound dependency edges (hege≥{HEGE_MIN}). '
            + f'Top foreign upstreams: '
            + ', '.join(f'AS{a}({cc_for.get(a, "?")})' for a, _ in top15[:5])
            + '.'
        ),
        reference='IHR AS Hegemony + IYP as_dependency.csv cache',
    )

    save_multi_plotly_html(
        [sankey, bar, pie], 'step08_depends_on_world.html',
        step_num=STEP, title_zh=TITLE_ZH, title_en=TITLE_EN, source='cached CSV',
        writeup_html=w,
        subtitles=['1. CN→Foreign Sankey (top-20 × top-15)',
                   '2. 外部上游依赖度排名', '3. 目的国家聚合分布'],
    )


if __name__ == '__main__':
    main()
