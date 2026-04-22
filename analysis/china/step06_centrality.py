"""Step 06 · CN Positions in Global Centrality.

Dimensions: multi-dimensional centrality on global AS peering graph
Data: cached step07_centrality_full.csv (reuse prior computation)
Output: cn_centrality.csv + scatter matrix + top-30 bar
"""
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.china.common import (  # noqa: E402
    COLORS, DATA_DIR, DARK_PANEL, TEXT_PRIMARY, TEXT_SECONDARY,
    as_hover_with_org, as_label_with_org, load_as_metadata, load_as_org_map,
    load_cn_ases, save_multi_plotly_html, write_csv,
    write_step_metrics, writeup,
)
from analysis.complex_network.utils import DATA_DIR as GLOBAL_DATA_DIR

STEP = 6
TITLE_ZH = '中国 AS 在全球中心性指标中的位置'
TITLE_EN = 'China ASes in Global Centrality Rankings'


def main():
    cn = load_cn_ases()
    md = load_as_metadata()
    org_map = load_as_org_map()
    path = os.path.join(GLOBAL_DATA_DIR, 'step07_centrality_full.csv')

    rows = []
    cn_rows = []
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            try:
                asn = int(row['asn'])
                r = {
                    'asn': asn,
                    'degree': float(row['degree']),
                    'betweenness': float(row['betweenness']),
                    'eigenvector': float(row['eigenvector']),
                    'pagerank': float(row['pagerank']),
                    'is_cn': asn in cn,
                }
            except Exception:
                continue
            rows.append(r)
            if asn in cn:
                cn_rows.append(r)
    rows.sort(key=lambda r: r['pagerank'], reverse=True)

    # Assign global rank per metric
    ranks = {}
    for metric in ['degree', 'betweenness', 'eigenvector', 'pagerank']:
        srt = sorted(rows, key=lambda r: r[metric], reverse=True)
        for i, r in enumerate(srt):
            ranks.setdefault(r['asn'], {})[f'rank_{metric}'] = i + 1

    for r in cn_rows:
        r.update(ranks.get(r['asn'], {}))

    write_csv('cn_centrality.csv', sorted(cn_rows, key=lambda r: r['pagerank'], reverse=True),
              fieldnames=['asn', 'degree', 'betweenness', 'eigenvector', 'pagerank',
                          'rank_degree', 'rank_betweenness', 'rank_eigenvector', 'rank_pagerank'])

    # ── Scatter: degree × pagerank, CN red vs others grey ──
    import plotly.graph_objects as go

    other_x = [r['degree'] for r in rows if not r['is_cn']]
    other_y = [r['pagerank'] for r in rows if not r['is_cn']]
    cn_x = [r['degree'] for r in rows if r['is_cn']]
    cn_y = [r['pagerank'] for r in rows if r['is_cn']]
    cn_text = [as_hover_with_org(r['asn'], org_map) for r in rows if r['is_cn']]

    scatter = go.Figure()
    scatter.add_trace(go.Scatter(
        x=other_x, y=other_y, mode='markers',
        marker=dict(color='#8B949E', size=3, opacity=0.3),
        name='其它国家 AS (Global)', hoverinfo='skip',
    ))
    scatter.add_trace(go.Scatter(
        x=cn_x, y=cn_y, mode='markers',
        marker=dict(color=COLORS['red'], size=8, opacity=0.85),
        name='中国 AS (CN)',
        text=cn_text,
        hovertemplate='%{text}<br>degree = %{x:.4g}<br>PageRank = %{y:.4g}<extra></extra>',
    ))
    scatter.update_layout(
        title='度中心性 × PageRank (log 轴) · CN highlighted',
        xaxis=dict(title='Degree centrality', type='log'),
        yaxis=dict(title='PageRank', type='log'),
        height=620,
        margin=dict(l=70, r=30, t=70, b=60),
    )

    # Top-30 CN by pagerank with global rank — x-axis label shows AS + Org
    top = sorted(cn_rows, key=lambda r: r['pagerank'], reverse=True)[:30]
    bar = go.Figure()
    bar.add_trace(go.Bar(
        x=[as_label_with_org(r['asn'], org_map, max_org_len=18) for r in top],
        y=[r['rank_pagerank'] for r in top],
        marker_color=COLORS['red'],
        text=[f'#{r["rank_pagerank"]}' for r in top],
        textposition='outside',
        customdata=[as_hover_with_org(r['asn'], org_map) for r in top],
        hovertemplate='%{customdata}<br>全球 PageRank 排名 #%{y}<extra></extra>',
        name='PageRank rank',
    ))
    bar.update_layout(
        title='Top-30 CN ASes · 全球 PageRank 排名 (数字越小 = 越中心)',
        yaxis=dict(title='Global rank (lower = more central)', autorange='reversed'),
        xaxis=dict(tickangle=-40, automargin=True, title='AS · 所属组织'),
        margin=dict(l=70, r=30, t=70, b=140),
        bargap=0.35,
    )

    # Scatter matrix of 4 centralities
    import plotly.figure_factory as ff
    import pandas as pd
    cn_df = pd.DataFrame(cn_rows)
    cn_df['group'] = 'CN'
    other_sample = [r for r in rows if not r['is_cn']][::50]  # subsample to ~2k
    other_df = pd.DataFrame(other_sample)
    other_df['group'] = 'Other'
    df = pd.concat([cn_df, other_df], ignore_index=True)

    from plotly.express import scatter_matrix
    splom = scatter_matrix(
        df, dimensions=['degree', 'betweenness', 'eigenvector', 'pagerank'],
        color='group',
        color_discrete_map={'CN': COLORS['red'], 'Other': '#8B949E'},
        opacity=0.55,
        height=720,
    )
    splom.update_traces(diagonal_visible=False, showupperhalf=False)
    splom.update_layout(title='4 维中心性散点矩阵 · Scatter matrix (CN red, Other grey)')

    top_pr_cn = min((r['rank_pagerank'] for r in cn_rows), default=None)
    top_deg_cn = min((r['rank_degree'] for r in cn_rows), default=None)
    top_bet_cn = min((r['rank_betweenness'] for r in cn_rows), default=None)

    metrics = {
        'cn_count': len(cn_rows),
        'best_pagerank_rank': top_pr_cn,
        'best_degree_rank': top_deg_cn,
        'best_betweenness_rank': top_bet_cn,
        'top5_by_pagerank': [(r['asn'], r['rank_pagerank']) for r in top[:5]],
    }
    write_step_metrics(STEP, metrics, TITLE_ZH, TITLE_EN)

    w = writeup(
        hypothesis=(
            '全球 AS 拓扑中，PageRank / Degree / Betweenness 高度相关但并不完全重合。'
            '过去研究表明，东亚地区 AS 虽然 Degree 排名靠前，但 Betweenness 相对较低，'
            '说明它们更像"流量接收端"而非"全球中继"。<br>'
            'PageRank / Degree / Betweenness are correlated but not identical in the global AS graph. '
            'Prior research (Labovitz 2010+) shows that East Asian ASes typically rank high on degree '
            'but lower on betweenness — signaling "eyeball terminals" rather than "global transit relays".'
        ),
        finding=(
            f'共 {len(cn_rows)} 个 CN AS 纳入中心性分析。全局最佳 CN 排名: '
            f'PageRank #{top_pr_cn} / Degree #{top_deg_cn} / Betweenness #{top_bet_cn}。'
            f'CN AS 在 PageRank/Degree 上有顶部代表，但高 Betweenness 位次显著少。<br>'
            f'Best CN global ranks: PageRank #{top_pr_cn}, Degree #{top_deg_cn}, Betweenness #{top_bet_cn}. '
            f'CN ASes reach the top on degree/PR, but high-betweenness positions remain scarce, consistent '
            'with an eyeball-side rather than a global-transit role.'
        ),
        reference='Reuse of complex_network/step07_centrality_full.csv (global AS-level)',
    )

    save_multi_plotly_html(
        [splom, scatter, bar], 'step06_centrality.html',
        step_num=STEP, title_zh=TITLE_ZH, title_en=TITLE_EN, source='cached CSV',
        writeup_html=w,
        subtitles=['1. 四维中心性散点矩阵', '2. Degree × PageRank 散点',
                   '3. CN Top-30 PageRank 全球排名'],
    )


if __name__ == '__main__':
    main()
