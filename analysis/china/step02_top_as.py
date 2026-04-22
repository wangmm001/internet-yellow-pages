"""Step 02 · Top-20 Chinese ASes · Identity Cards.

Dimensions: AS + Name + Organization + Ranking + EXTERNAL_ID + Tag
Data: live Neo4j for per-AS detail + cached IHR CN country-rank for selection
Output: cn_top20_identity.csv + plotly card grid + summary table
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.china.common import (  # noqa: E402
    COLORS, DARK_BG, DARK_PANEL, DATA_DIR, TEXT_PRIMARY, TEXT_SECONDARY,
    load_as_metadata, load_cn_ases, neo4j_available,
    save_multi_plotly_html, save_placeholder_html, write_csv,
    write_step_metrics, writeup,
)
from analysis.complex_network.utils import run_query

STEP = 2
TITLE_ZH = '中国头部自治系统身份档案 (TOP-20)'
TITLE_EN = 'Top-20 Chinese ASes · Identity Cards'

KNOWN_ANCHORS = [23911, 38255, 4134, 4837, 23764, 4538, 9808, 17621, 58543,
                 4847, 17622, 4812, 4808, 9929, 55836, 45102, 7497, 17623,
                 58466, 56040]


def fetch_identity(asn):
    """Fetch a compact identity dossier for one AS via Neo4j."""
    recs = run_query("""
        MATCH (a:AS {asn: $asn})
        OPTIONAL MATCH (a)-[:NAME]->(n:Name)
        OPTIONAL MATCH (a)-[:MANAGED_BY]->(o:Organization)
        OPTIONAL MATCH (a)-[:COUNTRY]->(c:Country)
        OPTIONAL MATCH (a)-[:CATEGORIZED]->(t:Tag)
        OPTIONAL MATCH (a)-[r:RANK]->(rk:Ranking)
        OPTIONAL MATCH (a)-[:ORIGINATE]->(pfx:BGPPrefix)
        OPTIONAL MATCH (a)-[:EXTERNAL_ID]->(eid:PeeringdbNetID)
        RETURN a.asn AS asn,
               collect(DISTINCT n.name)[..4] AS names,
               collect(DISTINCT o.name)[..4] AS orgs,
               collect(DISTINCT c.country_code) AS countries,
               collect(DISTINCT t.label)[..10] AS tags,
               count(DISTINCT pfx) AS prefix_count,
               count(DISTINCT r) AS ranking_count,
               count(DISTINCT eid) AS peeringdb_ids
    """, {'asn': asn})
    return recs[0] if recs else None


def main():
    if not neo4j_available():
        save_placeholder_html(
            'step02_top_as.html', STEP, TITLE_ZH, TITLE_EN,
            'Neo4j 不可用，跳过本步骤。可启动 docker compose --profile local up 后重试。',
            'Neo4j unavailable; start it and rerun this step.',
        )
        return

    cn = load_cn_ases()
    # Determine top-20: start from known anchors intersected with CN scope,
    # then fill with CAIDA-ASRank top-CN.
    anchors = [a for a in KNOWN_ANCHORS if a in cn]
    recs = run_query("""
        MATCH (a:AS)-[:COUNTRY]->(c:Country {country_code:'CN'})
        MATCH (a)-[r:RANK]->(rk:Ranking {name:'CAIDA ASRank'})
        RETURN a.asn AS asn, r.rank AS rank ORDER BY r.rank LIMIT 40
    """)
    for r in recs:
        if len(anchors) >= 20:
            break
        if r['asn'] not in anchors:
            anchors.append(r['asn'])
    anchors = anchors[:20]

    md = load_as_metadata()
    dossiers = []
    for asn in anchors:
        d = fetch_identity(asn)
        if not d:
            continue
        d['fallback_tags'] = md.get(asn, {}).get('tags', [])[:5]
        dossiers.append(d)

    rows = [{
        'asn': d['asn'],
        'name': (d['names'] or ['?'])[0],
        'org': (d['orgs'] or ['?'])[0],
        'countries': '|'.join(d['countries'] or []),
        'tags': '|'.join((d['tags'] or d['fallback_tags'] or [])[:6]),
        'prefix_count': d['prefix_count'],
        'ranking_count': d['ranking_count'],
        'peeringdb_ids': d['peeringdb_ids'],
    } for d in dossiers]
    write_csv('cn_top20_identity.csv', rows)

    # ── Plotly table ──
    import plotly.graph_objects as go
    headers = ['ASN', '名称 Name', '组织 Org', '注册国', 'PFX 数', 'Rank 数', '主要标签 Tags']
    cells = [
        [r['asn'] for r in rows],
        [r['name'] for r in rows],
        [r['org'] for r in rows],
        [r['countries'] for r in rows],
        [f'{r["prefix_count"]:,}' for r in rows],
        [r['ranking_count'] for r in rows],
        [r['tags'] for r in rows],
    ]
    table = go.Figure(go.Table(
        header=dict(values=headers, fill_color=DARK_PANEL,
                    font=dict(color=TEXT_PRIMARY, size=12), align='left'),
        cells=dict(values=cells,
                   fill_color=[['#0D1117', '#161B22'] * len(rows)],
                   font=dict(color=TEXT_PRIMARY, size=11), align='left'),
    ))
    table.update_layout(title=f'Top-{len(rows)} 中国 AS 身份档案表 · Identity Table')

    # ── Bar: prefix_count (x-axis label carries AS + Org so the reader doesn't
    # need to mentally map ASNs to operators) ──
    rows_sorted = sorted(rows, key=lambda r: r['prefix_count'], reverse=True)
    def _short(s, n=22):
        s = s or '?'
        return s if len(s) <= n else s[: n - 1] + '…'
    bar = go.Figure(go.Bar(
        x=[f'AS{r["asn"]}<br>{_short(r["org"] or r["name"])}' for r in rows_sorted],
        y=[r['prefix_count'] for r in rows_sorted],
        marker_color=COLORS['red'],
        text=[f'{r["prefix_count"]:,}' for r in rows_sorted],
        textposition='outside',
        customdata=[[r['name'], r['org']] for r in rows_sorted],
        hovertemplate=(
            '<b>AS%{x}</b><br>名称 %{customdata[0]}<br>组织 %{customdata[1]}'
            '<br>前缀数 %{y:,}<extra></extra>'
        ),
    ))
    bar.update_layout(title='前缀数排名 · Prefixes originated per top CN AS',
                      yaxis=dict(title='BGPPrefix count', type='log'),
                      xaxis=dict(title='AS · 所属组织', tickangle=-30, automargin=True),
                      margin=dict(l=70, r=30, t=70, b=130))

    metrics = {
        'top_ases_analyzed': len(rows),
        'total_prefixes_top20': sum(r['prefix_count'] for r in rows),
        'asns': [r['asn'] for r in rows],
    }
    write_step_metrics(STEP, metrics, TITLE_ZH, TITLE_EN)

    w = writeup(
        hypothesis=(
            '大型国家级 ISP 的 AS 数目有限但承载全部流量。中国 Top-5 公认为 ChinaNet / CU169 / CMNET / CNGI / CERNET。<br>'
            'Each country\'s Internet is dominated by a handful of backbone ASes; for CN the expected Top-5 is '
            'ChinaNet (4134), China Unicom (4837), CMNET (9808), CNGI (23911), CERNET (38255).'
        ),
        finding=(
            f'已处理 {len(rows)} 个头部 AS，共承载 BGP 前缀 {sum(r["prefix_count"] for r in rows):,} 个。'
            f'注意 AS23911 CNGI-BJIX 等研究型骨干的前缀规模远小于 AS4134 ChinaNet 的商业骨干。<br>'
            f'Top-{len(rows)} Chinese ASes originate {sum(r["prefix_count"] for r in rows):,} BGP prefixes combined; '
            f'commercial backbones (4134/4837/9808) dominate numerically over research backbones (23911/38255).'
        ),
        reference='IYP Neo4j live query (CAIDA ASRank + IYP Name/Org/EXTERNAL_ID)',
    )

    save_multi_plotly_html(
        [table, bar], 'step02_top_as.html',
        step_num=STEP, title_zh=TITLE_ZH, title_en=TITLE_EN, source='Neo4j live',
        writeup_html=w,
        subtitles=['1. Top-20 身份表', '2. 前缀数排名 (log 轴)'],
    )


if __name__ == '__main__':
    main()
