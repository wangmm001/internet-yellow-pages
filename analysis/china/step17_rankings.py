"""Step 17 · China ASes in Global Rankings.

Dimensions: AS -[:RANK]- Ranking (CAIDA ASRank, APNIC, IHR, Tranco top-hosting, etc.)
Data: live Neo4j (small query)
Output: cn_rankings.csv + parallel coordinates + density
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.china.common import (  # noqa: E402
    COLORS, DATA_DIR, neo4j_available, save_multi_plotly_html,
    save_placeholder_html, write_csv, write_step_metrics, writeup,
)
from analysis.complex_network.utils import run_query

STEP = 17
TITLE_ZH = '中国 AS 在全球多套排名体系中的位置'
TITLE_EN = 'China ASes in Global Rankings'


def main():
    if not neo4j_available():
        save_placeholder_html('step17_rankings.html', STEP, TITLE_ZH, TITLE_EN,
                              'Neo4j 不可用。', 'Neo4j unavailable.')
        return

    print('[step17] querying rankings…')
    # First, pull all ranking names to understand what's available
    rk_names = run_query("""
        MATCH (:AS)-[:RANK]->(rk:Ranking)
        RETURN rk.name AS name, count(*) AS c
        ORDER BY c DESC LIMIT 30
    """)
    print('[step17] available rankings:', [r['name'] for r in rk_names][:10])

    # Pull CN AS rankings in top-5 most-populated rankings (limit to those w/ CN coverage)
    preferred = ['CAIDA ASRank', 'IHR country ranking: Total AS (CN)',
                 'APNIC eyeball estimates (CN)', 'IHR country ranking: Total eyeball (CN)',
                 'IHR country ranking: Total domains (CN)']
    # Verify which exist
    existing_names = [r['name'] for r in rk_names]
    rankings_to_use = [n for n in preferred if n in existing_names]
    if len(rankings_to_use) < 3:
        # Fallback: just take CAIDA ASRank + top CN-linked rankings
        cn_rkgs = run_query("""
            MATCH (rk:Ranking)-[:COUNTRY]->(:Country {country_code:'CN'})
            RETURN rk.name AS name LIMIT 10
        """)
        rankings_to_use = (['CAIDA ASRank'] +
                           [r['name'] for r in cn_rkgs])[:5]

    print(f'[step17] using rankings: {rankings_to_use}')

    rows = defaultdict(dict)  # asn -> {ranking_name: rank}
    per_ranking_totals = {}
    for name in rankings_to_use:
        recs = run_query("""
            MATCH (a:AS)-[:COUNTRY]->(:Country {country_code:'CN'})
            MATCH (a)-[r:RANK]->(rk:Ranking {name: $n})
            RETURN a.asn AS asn, r.rank AS rank
            ORDER BY r.rank LIMIT 2000
        """, {'n': name})
        per_ranking_totals[name] = len(recs)
        for r in recs:
            rows[r['asn']][name] = r['rank']

    # Write CSV
    fieldnames = ['asn'] + rankings_to_use
    out_rows = [
        {'asn': asn, **{n: d.get(n, '') for n in rankings_to_use}}
        for asn, d in rows.items()
    ]
    write_csv('cn_rankings.csv', out_rows, fieldnames=fieldnames)

    import plotly.graph_objects as go
    import plotly.express as px

    # ── Parallel coordinates: each CN AS = one line across rankings ──
    # Use ASes that have values in >=2 rankings
    complete = [d for d in rows.values() if sum(1 for n in rankings_to_use if n in d) >= 2]
    complete = complete[:200]  # visually tractable
    if complete:
        dims = []
        for name in rankings_to_use:
            vals = [d.get(name) for d in complete]
            vals_clean = [v if v is not None else max(
                (x for x in vals if x is not None), default=10000) + 1 for v in vals]
            dims.append(dict(label=name[:25], values=vals_clean))
        parcoords = go.Figure(go.Parcoords(
            line=dict(color=COLORS['red']),
            dimensions=dims,
        ))
        parcoords.update_layout(title='中国 AS 多排名平行坐标图 (低=更靠前)',
                                height=560)
    else:
        parcoords = go.Figure()
        parcoords.update_layout(title='(数据不足)')

    # ── Histogram: CN AS rank distribution per ranking ──
    hist = go.Figure()
    for name in rankings_to_use:
        vals = [d[name] for d in rows.values() if name in d]
        if not vals:
            continue
        hist.add_trace(go.Histogram(
            x=vals, name=name[:30], opacity=0.6, nbinsx=40,
        ))
    hist.update_layout(
        barmode='overlay',
        title=f'CN AS 在各排名中的位次分布 ({len(rankings_to_use)} rankings)',
        xaxis=dict(title='Rank (lower = more prominent)', type='log'),
        yaxis=dict(title='CN AS count'),
    )

    # ── Top-10 CN by top-ranking-available ──
    primary_name = rankings_to_use[0]
    top10 = sorted(
        [(asn, d[primary_name]) for asn, d in rows.items() if primary_name in d],
        key=lambda t: t[1],
    )[:20]
    bar = go.Figure(go.Bar(
        x=[f'AS{a}' for a, _ in top10],
        y=[r for _, r in top10],
        marker_color=COLORS['red'],
        text=[f'#{r}' for _, r in top10],
        textposition='outside',
    ))
    bar.update_layout(
        title=f'Top-20 CN ASes in "{primary_name}" (lower = better)',
        yaxis=dict(title='Rank', autorange='reversed'),
        xaxis=dict(tickangle=-45))

    metrics = {
        'rankings_used': rankings_to_use,
        'per_ranking_cn_count': per_ranking_totals,
        'cn_ases_with_any_rank': len(rows),
        'top5_in_primary': [(a, r) for a, r in top10[:5]],
    }
    write_step_metrics(STEP, metrics, TITLE_ZH, TITLE_EN)

    w = writeup(
        hypothesis=(
            '多套排名（CAIDA / APNIC / IHR）度量不同维度（客户锥、Eyeball 覆盖、IHR 依赖）；'
            '头部玩家通常在多套排名同时靠前（coherent leadership）。<br>'
            'Rankings measure different dimensions (customer-cone vs eyeball vs hegemony). Coherent leadership '
            'means top-N ASes appear near the top of many rankings simultaneously.'
        ),
        finding=(
            f'采用 {len(rankings_to_use)} 套排名，共 {len(rows)} 个 CN AS 至少进入一套。'
            f'在 "{primary_name}" 排名中 Top-5：'
            + ', '.join(f'AS{a}(#{r})' for a, r in top10[:5])
            + f'。<br>'
            + f'{len(rankings_to_use)} rankings used; {len(rows)} CN ASes appear in at least one. '
            + f'Top-5 in "{primary_name}": '
            + ', '.join(f'AS{a}(#{r})' for a, r in top10[:5])
        ),
        reference='IYP RANK relationships (CAIDA / IHR / APNIC)',
    )

    save_multi_plotly_html(
        [parcoords, hist, bar], 'step17_rankings.html',
        step_num=STEP, title_zh=TITLE_ZH, title_en=TITLE_EN, source='Neo4j live',
        writeup_html=w,
        subtitles=['1. 多排名平行坐标图',
                   '2. CN AS 排名分布（log 轴）',
                   '3. Top-20 CN ASes in primary ranking'],
    )


if __name__ == '__main__':
    main()
