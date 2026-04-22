"""Step 18 · Censorship Topology in China.

Dimensions: AS -[:CENSORED]- (IP | URL | Tag) filtered to CN ASes
Data: cached censorship.csv + step08_coreness.csv + step07_centrality_full.csv
Output: cn_censorship.csv + heatmap + topology feature comparison
"""
import csv
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.china.common import (  # noqa: E402
    COLORS, DATA_DIR, as_hover_with_org, as_label_with_org,
    load_as_org_map, load_cn_ases, save_multi_plotly_html,
    write_csv, write_step_metrics, writeup,
)
from analysis.complex_network.utils import DATA_DIR as GLOBAL_DATA_DIR

STEP = 18
TITLE_ZH = '中国 AS 审查与阻断拓扑'
TITLE_EN = 'Censorship Topology in China'


def main():
    cn = load_cn_ases()
    org_map = load_as_org_map()
    # Load censorship
    cens_path = os.path.join(GLOBAL_DATA_DIR, 'censorship.csv')
    rows = []
    all_rows = []
    per_as_total = Counter()
    per_test = Counter()
    with open(cens_path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            try:
                asn = int(row['asn'])
                cnt = int(row['detection_count'])
            except Exception:
                continue
            all_rows.append({'asn': asn, 'target_type': row['target_type'],
                             'test_name': row['test_name'], 'detection_count': cnt})
            if asn in cn:
                rows.append({'asn': asn, 'target_type': row['target_type'],
                             'test_name': row['test_name'], 'detection_count': cnt})
                per_as_total[asn] += cnt
                per_test[row['test_name']] += cnt
    write_csv('cn_censorship.csv', rows)

    # Load coreness + centrality
    def load_dict(path, keycol, valcol, vtype=float):
        d = {}
        if not os.path.exists(path):
            return d
        with open(path, encoding='utf-8') as f:
            for row in csv.DictReader(f):
                try:
                    d[int(row[keycol])] = vtype(row[valcol])
                except Exception:
                    continue
        return d
    coreness = load_dict(os.path.join(GLOBAL_DATA_DIR, 'step08_coreness.csv'),
                         'asn', 'coreness', int)
    pagerank = load_dict(os.path.join(GLOBAL_DATA_DIR, 'step07_centrality_full.csv'),
                         'asn', 'pagerank', float)
    degree = load_dict(os.path.join(GLOBAL_DATA_DIR, 'step07_centrality_full.csv'),
                       'asn', 'degree', float)

    # CN ASes with censorship signal vs without
    cn_censoring_ases = set(per_as_total)
    cn_other_ases = cn - cn_censoring_ases

    import plotly.graph_objects as go
    import plotly.subplots as sp

    # ── Heatmap: AS × test-type (top-25 CN ASes with most detections) ──
    top_as = [a for a, _ in per_as_total.most_common(25)]
    tests = [t for t, _ in per_test.most_common(12)]
    matrix = []
    for asn in top_as:
        row = []
        for t in tests:
            v = 0
            for r in rows:
                if r['asn'] == asn and r['test_name'] == t:
                    v = r['detection_count']
                    break
            row.append(v)
        matrix.append(row)
    # y labels carry Org so the reader sees operator identity directly;
    # customdata supplies a richer tooltip.
    y_labels = [as_label_with_org(a, org_map, max_org_len=18) for a in top_as]
    hover_text = [[as_hover_with_org(a, org_map) for _ in tests] for a in top_as]
    heatmap = go.Figure(go.Heatmap(
        z=matrix, x=tests, y=y_labels,
        colorscale='Reds',
        customdata=hover_text,
        hovertemplate='%{customdata}<br>测试 %{x}<br>检出 %{z}<extra></extra>',
    ))
    heatmap.update_layout(
        title='中国 AS × 测试类型 审查热图 · Top-25 AS × Top-12 tests',
        height=680,
        xaxis=dict(tickangle=-30, automargin=True),
        yaxis=dict(automargin=True, title='AS · 所属组织'),
        margin=dict(l=180, r=30, t=70, b=100),
    )

    # ── Topology features: censoring vs non-censoring vs global ──
    import statistics
    def stats(lst):
        lst = [x for x in lst if x is not None]
        return (statistics.median(lst) if lst else 0,
                statistics.mean(lst) if lst else 0,
                len(lst))

    c_core = [coreness.get(a) for a in cn_censoring_ases if coreness.get(a) is not None]
    c_pr = [pagerank.get(a) for a in cn_censoring_ases if pagerank.get(a) is not None]
    c_deg = [degree.get(a) for a in cn_censoring_ases if degree.get(a) is not None]
    o_core = [coreness.get(a) for a in cn_other_ases if coreness.get(a) is not None]
    o_pr = [pagerank.get(a) for a in cn_other_ases if pagerank.get(a) is not None]
    o_deg = [degree.get(a) for a in cn_other_ases if degree.get(a) is not None]
    g_core = list(coreness.values())
    g_pr = list(pagerank.values())
    g_deg = list(degree.values())

    cat_fig = sp.make_subplots(
        rows=1, cols=3, subplot_titles=('Coreness', 'PageRank', 'Degree'))
    for col, (cens, other, glob, label) in enumerate([
        (c_core, o_core, g_core, 'Coreness'),
        (c_pr, o_pr, g_pr, 'PageRank'),
        (c_deg, o_deg, g_deg, 'Degree'),
    ]):
        cat_fig.add_trace(go.Box(
            y=cens, name='CN-Censoring', marker_color=COLORS['red'],
            boxpoints=False, showlegend=(col == 0),
        ), row=1, col=col + 1)
        cat_fig.add_trace(go.Box(
            y=other, name='CN-Other', marker_color=COLORS['cyan'],
            boxpoints=False, showlegend=(col == 0),
        ), row=1, col=col + 1)
        cat_fig.add_trace(go.Box(
            y=glob, name='Global', marker_color='#8B949E',
            boxpoints=False, showlegend=(col == 0),
        ), row=1, col=col + 1)
    cat_fig.update_layout(
        title='审查 vs 非审查 vs 全球 AS 拓扑特征对比 (log-y)',
        height=560,
    )
    cat_fig.update_yaxes(type='log')

    # ── Bar: top tests detected ──
    top_tests = per_test.most_common(15)
    bar = go.Figure(go.Bar(
        x=[t for t, _ in top_tests],
        y=[c for _, c in top_tests],
        marker_color=COLORS['red'],
        text=[f'{c:,}' for _, c in top_tests],
        textposition='outside',
    ))
    bar.update_layout(
        title='CN AS 上检出最多的 OONI 测试类型',
        yaxis=dict(title='Detection count'),
        xaxis=dict(tickangle=-35, automargin=True),
        margin=dict(l=70, r=30, t=70, b=130))

    metrics = {
        'cn_ases_with_censorship_signal': len(cn_censoring_ases),
        'cn_total_detections': sum(per_as_total.values()),
        'top5_censoring_ases': per_as_total.most_common(5),
        'top5_tests': per_test.most_common(5),
        'coreness_median_censoring': c_core and statistics.median(c_core),
        'coreness_median_non_censoring': o_core and statistics.median(o_core),
    }
    write_step_metrics(STEP, metrics, TITLE_ZH, TITLE_EN)

    w = writeup(
        hypothesis=(
            '审查是否发生在"核心 AS"还是"边缘 AS"？'
            '若审查主要在核心 AS 上检出，则对路径影响大；在边缘则影响局部。<br>'
            'Does censorship manifest at core or peripheral ASes? If at the core, path impact is large; '
            'if at peripheral ASes, impact is local.'
        ),
        finding=(
            f'{len(cn_censoring_ases)} 个 CN AS 检出审查信号，总计 {sum(per_as_total.values()):,} 次检出。'
            f'Top 测试：{", ".join(f"{t}({c:,})" for t, c in per_test.most_common(3))}。'
            f'审查 AS 的 coreness 中位数={metrics["coreness_median_censoring"]}，'
            f'非审查 CN AS={metrics["coreness_median_non_censoring"]}。<br>'
            f'{len(cn_censoring_ases)} CN ASes show censorship signals ({sum(per_as_total.values()):,} '
            f'detections). Censoring-AS median coreness = {metrics["coreness_median_censoring"]} vs '
            f'non-censoring CN AS = {metrics["coreness_median_non_censoring"]}.'
        ),
        reference='OONI censorship measurements + reuse of step07/step08 topology',
    )

    save_multi_plotly_html(
        [heatmap, cat_fig, bar], 'step18_censorship.html',
        step_num=STEP, title_zh=TITLE_ZH, title_en=TITLE_EN, source='cached CSV',
        writeup_html=w,
        subtitles=['1. AS × 测试 热图',
                   '2. 审查 vs 非审查 vs 全球 拓扑特征',
                   '3. 测试类型分布'],
    )


if __name__ == '__main__':
    main()
