"""Step 19 · RIPE Atlas Measurement Presence in China.

Dimensions: AtlasProbe -[:LOCATED_IN]- (Country | AS)
            + AtlasMeasurement -[:TARGET]- (IP | AS | HostName)
Data: live Neo4j
Output: cn_atlas.csv + geo bubble + target distribution
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.china.common import (  # noqa: E402
    COLORS, DATA_DIR, iso2_to_iso3, neo4j_available, save_multi_plotly_html,
    save_placeholder_html, write_csv, write_step_metrics, writeup,
)
from analysis.complex_network.utils import run_query

STEP = 19
TITLE_ZH = '中国境内 RIPE Atlas 测量观测点'
TITLE_EN = 'RIPE Atlas Measurement Presence in China'


def main():
    if not neo4j_available():
        save_placeholder_html('step19_atlas.html', STEP, TITLE_ZH, TITLE_EN,
                              'Neo4j 不可用。', 'Neo4j unavailable.')
        return

    print('[step19] querying Atlas probes in CN…')
    # Probes whose hosting AS is in CN or located in CN country
    probes = run_query("""
        MATCH (p:AtlasProbe)
        OPTIONAL MATCH (p)-[:LOCATED_IN]->(c:Country)
        OPTIONAL MATCH (p)-[:LOCATED_IN]->(a:AS)
        OPTIONAL MATCH (p)-[:LOCATED_IN]->(pt:Point)
        WITH p, c, a, pt
        WHERE (c IS NOT NULL AND c.country_code = 'CN')
           OR (a IS NOT NULL AND (a)-[:COUNTRY]->(:Country {country_code:'CN'}))
        RETURN p.id AS probe_id, c.country_code AS cc,
               a.asn AS asn,
               pt.longitude AS lon, pt.latitude AS lat LIMIT 3000
    """)
    print(f'[step19] CN probes found: {len(probes)}')

    # Global probe counts per country for comparison
    print('[step19] global probe counts by country…')
    country_probes = run_query("""
        MATCH (p:AtlasProbe)-[:LOCATED_IN]->(c:Country)
        RETURN c.country_code AS cc, count(DISTINCT p) AS cnt
        ORDER BY cnt DESC LIMIT 50
    """)

    print('[step19] measurements targeting CN…')
    targets = run_query("""
        MATCH (m:AtlasMeasurement)-[:TARGET]->(a:AS)-[:COUNTRY]->(:Country {country_code:'CN'})
        RETURN 'AS' AS kind, count(DISTINCT m) AS cnt
        UNION ALL
        MATCH (m:AtlasMeasurement)-[:TARGET]->(h:HostName)
        WHERE h.name ENDS WITH '.cn'
        RETURN 'HostName' AS kind, count(DISTINCT m) AS cnt
    """)

    rows = []
    for p in probes:
        rows.append({
            'probe_id': p['probe_id'],
            'cc': p.get('cc') or '',
            'asn': p.get('asn') or '',
            'lon': p.get('lon') or '',
            'lat': p.get('lat') or '',
        })
    write_csv('cn_atlas.csv', rows)

    import plotly.graph_objects as go
    # ── Geo-scatter: CN probes ──
    valid_probes = [(p.get('lon'), p.get('lat'), p.get('asn'), p.get('probe_id'))
                    for p in probes if p.get('lon') and p.get('lat')]
    geo = go.Figure(go.Scattergeo(
        lon=[lon for lon, lat, _, _ in valid_probes],
        lat=[lat for lon, lat, _, _ in valid_probes],
        mode='markers',
        marker=dict(size=8, color=COLORS['red'], line=dict(width=1, color='#E6EDF3')),
        text=[f'Probe {pid}<br>AS{asn}' for _, _, asn, pid in valid_probes],
        hovertemplate='%{text}<extra></extra>',
    ))
    geo.update_geos(
        scope='asia', bgcolor='#0D1117', showframe=False,
        showcoastlines=True, coastlinecolor='#30363D',
        landcolor='#161B22', center=dict(lon=104, lat=36), projection_scale=3,
    )
    geo.update_layout(
        title=f'中国境内 RIPE Atlas 探针地理分布 (N={len(valid_probes)})', height=520,
    )

    # ── Bar: global top-20 vs CN position ──
    top_cc = country_probes[:20]
    cn_rank = next((i + 1 for i, r in enumerate(country_probes) if r['cc'] == 'CN'), None)
    cn_count = next((r['cnt'] for r in country_probes if r['cc'] == 'CN'), 0)
    bar = go.Figure(go.Bar(
        x=[r['cc'] for r in top_cc],
        y=[r['cnt'] for r in top_cc],
        marker_color=[COLORS['red'] if r['cc'] == 'CN' else COLORS['cyan'] for r in top_cc],
        text=[str(r['cnt']) for r in top_cc],
        textposition='outside',
    ))
    bar.update_layout(
        title=f'全球 Atlas 探针 Top-20 国家 · CN rank = #{cn_rank} ({cn_count})',
        yaxis=dict(title='# probes'),
    )

    # ── Target count bar ──
    tgt_fig = go.Figure(go.Bar(
        x=[t['kind'] for t in targets],
        y=[t['cnt'] for t in targets],
        marker_color=[COLORS['red'], COLORS['orange']],
        text=[f'{t["cnt"]:,}' for t in targets],
        textposition='outside',
    ))
    tgt_fig.update_layout(
        title='Atlas measurements targeting CN resources',
        yaxis=dict(title='# measurements'))

    metrics = {
        'cn_probes_count': len(probes),
        'cn_probes_with_coords': len(valid_probes),
        'cn_rank_global_probe_count': cn_rank,
        'target_measurement_counts': {t['kind']: t['cnt'] for t in targets},
    }
    write_step_metrics(STEP, metrics, TITLE_ZH, TITLE_EN)

    w = writeup(
        hypothesis=(
            'RIPE Atlas 是全球测量网络；一国的探针密度直接影响学术社区的观测能力。'
            '在中国大陆探针一直稀少，形成"测量盲点"。<br>'
            'RIPE Atlas probe density reflects observational capacity. Mainland China has historically had '
            'few probes, creating measurement blind spots.'
        ),
        finding=(
            f'中国境内约 {len(probes)} 个 Atlas 探针记录（全球排名 #{cn_rank}，共 {cn_count}）；'
            f'{len(valid_probes)} 个有经纬度。'
            f'针对 CN 资源的 Atlas 测量统计：'
            + ', '.join(f'{t["kind"]}={t["cnt"]:,}' for t in targets)
            + f'。<br>~{len(probes)} Atlas probes in CN (global rank #{cn_rank}). '
            + f'Measurements targeting CN: '
            + ', '.join(f'{t["kind"]}={t["cnt"]:,}' for t in targets)
            + '.'
        ),
        reference='RIPE Atlas via IYP AtlasProbe & AtlasMeasurement nodes',
    )

    save_multi_plotly_html(
        [geo, bar, tgt_fig], 'step19_atlas.html',
        step_num=STEP, title_zh=TITLE_ZH, title_en=TITLE_EN, source='Neo4j live',
        writeup_html=w,
        subtitles=['1. CN 探针地理分布',
                   '2. 全球 Top-20 国家 (CN 突出)',
                   '3. Atlas 测量的 CN 目标'],
    )


if __name__ == '__main__':
    main()
