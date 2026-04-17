"""Step 04 · China BGP Prefix Footprint.

Dimensions: BGPPrefix -[:ORIGINATE]- AS, ROUTE_ORIGIN_AUTHORIZATION (RPKI), CATEGORIZED (Tag)
Data: live Neo4j (RPKI + anycast tags) + fallback cached as_prefix_count.csv
Output: cn_prefixes.csv + treemap + RPKI/anycast bars
"""
import csv
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.china.common import (  # noqa: E402
    COLORS, DATA_DIR, DARK_PANEL, TEXT_PRIMARY,
    load_cn_ases, neo4j_available, save_multi_plotly_html,
    save_placeholder_html, write_csv, write_step_metrics, writeup,
)
from analysis.complex_network.utils import DATA_DIR as GLOBAL_DATA_DIR, run_query

STEP = 4
TITLE_ZH = '中国 BGP 前缀空间与 RPKI 覆盖度'
TITLE_EN = 'China BGP Prefix Footprint & RPKI Coverage'


def main():
    cn = load_cn_ases()
    source = 'cached CSV'
    per_as = defaultdict(lambda: {'v4': 0, 'v6': 0, 'roa': 0, 'anycast': 0, 'total': 0})
    total_v4 = total_v6 = total_roa = total_any = 0

    if neo4j_available():
        print('[step04] running live Neo4j query...')
        try:
            recs = run_query("""
                MATCH (a:AS)-[:COUNTRY]->(:Country {country_code:'CN'})
                MATCH (a)-[:ORIGINATE]->(pfx:BGPPrefix)
                OPTIONAL MATCH (pfx)-[:CATEGORIZED]->(t:Tag)
                WITH a.asn AS asn, pfx, collect(DISTINCT t.label) AS tags
                RETURN asn, pfx.prefix AS prefix, pfx.af AS af, tags
            """)
            for r in recs:
                d = per_as[r['asn']]
                if r.get('af') == 6:
                    d['v6'] += 1
                    total_v6 += 1
                else:
                    d['v4'] += 1
                    total_v4 += 1
                tags = r.get('tags') or []
                if any(t == 'RPKI Valid' for t in tags):
                    d['roa'] += 1
                    total_roa += 1
                if any('Anycast' in (t or '') for t in tags):
                    d['anycast'] += 1
                    total_any += 1
                d['total'] += 1
            source = 'Neo4j live'
        except Exception as e:
            print(f'[step04] Neo4j query failed: {e}')

    if not per_as:
        # Fallback to cached per-AS count (no RPKI info)
        pfx_path = os.path.join(GLOBAL_DATA_DIR, 'as_prefix_count.csv')
        if os.path.exists(pfx_path):
            with open(pfx_path, encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    asn = int(row['asn'])
                    if asn in cn:
                        per_as[asn] = {'v4': int(row['prefix_count']),
                                       'v6': 0, 'roa': 0, 'anycast': 0,
                                       'total': int(row['prefix_count'])}
                        total_v4 += int(row['prefix_count'])

    if not per_as:
        save_placeholder_html(
            'step04_prefixes.html', STEP, TITLE_ZH, TITLE_EN,
            '无缓存且 Neo4j 不可用。请启动 Neo4j 或先运行全局分析。',
            'No cache and Neo4j unavailable.',
        )
        return

    # Rows sorted by total
    rows = sorted(
        [{'asn': asn, **d} for asn, d in per_as.items()],
        key=lambda r: r['total'], reverse=True,
    )
    write_csv('cn_prefixes.csv', rows,
              fieldnames=['asn', 'v4', 'v6', 'roa', 'anycast', 'total'])

    # ── Treemap of top-30 originators ──
    import plotly.graph_objects as go
    top = rows[:30]
    treemap = go.Figure(go.Treemap(
        labels=[f'AS{r["asn"]}<br>{r["total"]:,}' for r in top],
        parents=['' for _ in top],
        values=[r['total'] for r in top],
        textinfo='label', marker=dict(
            colors=[r['v6'] / max(r['total'], 1) for r in top],
            colorscale='Viridis', colorbar=dict(title='v6 fraction'),
        ),
    ))
    treemap.update_layout(title='前 30 起源 AS 前缀总数 · Prefix count (color = IPv6 fraction)')

    # ── v4/v6 split ──
    v4v6 = go.Figure()
    v4v6.add_trace(go.Bar(name='IPv4', x=[f'AS{r["asn"]}' for r in top],
                          y=[r['v4'] for r in top], marker_color=COLORS['red']))
    v4v6.add_trace(go.Bar(name='IPv6', x=[f'AS{r["asn"]}' for r in top],
                          y=[r['v6'] for r in top], marker_color=COLORS['cyan']))
    v4v6.update_layout(barmode='stack',
                       title='v4/v6 分解 · IPv4 vs IPv6 prefix split',
                       yaxis=dict(type='log'))

    # ── RPKI pie + anycast pie ──
    rpki_fig = go.Figure(go.Pie(
        labels=['有 ROA (ROV 可验证) · With ROA', '无 ROA · Without ROA'],
        values=[total_roa, max(total_v4 + total_v6 - total_roa, 0)],
        marker=dict(colors=[COLORS['green'], COLORS['red']]),
        hole=0.5,
    ))
    pct = total_roa / max(total_v4 + total_v6, 1) * 100
    rpki_fig.update_layout(
        title=f'RPKI ROA 覆盖率 · {pct:.1f}% ({total_roa:,}/{total_v4 + total_v6:,})')

    any_fig = go.Figure(go.Pie(
        labels=['Anycast 标记前缀', '常规前缀'],
        values=[total_any, max(total_v4 + total_v6 - total_any, 0)],
        marker=dict(colors=[COLORS['blue'], COLORS['orange']]),
        hole=0.5,
    ))
    any_fig.update_layout(title=f'Anycast 前缀比例 · {total_any:,} tagged anycast')

    metrics = {
        'cn_originators': len(per_as),
        'v4_prefixes': total_v4,
        'v6_prefixes': total_v6,
        'rpki_rate_pct': round(pct, 2),
        'anycast_prefixes': total_any,
        'top5_originators': [(r['asn'], r['total']) for r in rows[:5]],
    }
    write_step_metrics(STEP, metrics, TITLE_ZH, TITLE_EN)

    w = writeup(
        hypothesis=(
            'RPKI ROV 在 2020 年后全球部署率快速上升，但不同地区差异显著；东亚地区历史上 ROA 签发率低于北欧/北美。<br>'
            'Global RPKI ROV deployment has accelerated since 2020 but varies by region; East Asia historically trails Northern Europe / North America.'
        ),
        finding=(
            f'中国起源的 BGP 前缀共 {total_v4 + total_v6:,} 条（IPv4 {total_v4:,} / IPv6 {total_v6:,}），'
            f'其中 RPKI ROA 覆盖率 {pct:.1f}%。Anycast 标签前缀 {total_any:,} 条。<br>'
            f'CN originated {total_v4 + total_v6:,} BGP prefixes (v4 {total_v4:,} / v6 {total_v6:,}); '
            f'RPKI ROA coverage {pct:.1f}%; {total_any:,} anycast-tagged prefixes.'
        ),
        reference='IYP BGPKIT originate + RIPE/IHR ROV + IYP anycast tag',
    )

    save_multi_plotly_html(
        [treemap, v4v6, rpki_fig, any_fig], 'step04_prefixes.html',
        step_num=STEP, title_zh=TITLE_ZH, title_en=TITLE_EN, source=source,
        writeup_html=w,
        subtitles=['1. 起源前缀数 Treemap', '2. v4/v6 split (log)',
                   '3. RPKI ROA 覆盖率', '4. Anycast 前缀比例'],
    )


if __name__ == '__main__':
    main()
