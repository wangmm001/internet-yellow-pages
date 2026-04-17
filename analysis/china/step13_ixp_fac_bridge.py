"""Step 13 · IXP + Facility Tripartite Bridge.

Dimensions: IXP-[:LOCATED_IN]-Facility combined with AS-[:LOCATED_IN]-Facility
            and AS-[:MEMBER_OF]-IXP
Data: live Neo4j join (small query)
Output: cn_ixp_fac_tripartite.csv + Pyvis tripartite network
"""
import csv
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.china.common import (  # noqa: E402
    COLORS, DATA_DIR, neo4j_available, save_pyvis_html, save_placeholder_html,
    write_csv, write_step_metrics, writeup,
)
from analysis.complex_network.utils import run_query

STEP = 13
TITLE_ZH = 'IXP + 机房 三部图：中国互联"物理桥梁"'
TITLE_EN = 'IXP + Facility Tripartite Bridge'

MAX_EDGES_DISPLAY = 400


def main():
    if not neo4j_available():
        save_placeholder_html('step13_ixp_fac_bridge.html', STEP, TITLE_ZH, TITLE_EN,
                              'Neo4j 不可用，跳过本步骤。', 'Neo4j unavailable.')
        return

    print('[step13] live Neo4j query…')
    # Fetch: (CN AS) -- MEMBER_OF -- (IXP) -- LOCATED_IN -- (Facility)
    # and  (CN AS) -- LOCATED_IN -- (Facility)
    recs = run_query("""
        MATCH (a:AS)-[:COUNTRY]->(:Country {country_code:'CN'})
        MATCH (a)-[:MEMBER_OF]->(ix:IXP)
        OPTIONAL MATCH (ix)-[:LOCATED_IN]->(f:Facility)
        OPTIONAL MATCH (f)-[:COUNTRY]->(fc:Country)
        OPTIONAL MATCH (ix)-[:COUNTRY]->(ic:Country)
        RETURN a.asn AS asn, ix.name AS ixp, ic.country_code AS ixp_cc,
               f.name AS fac, fc.country_code AS fac_cc LIMIT 20000
    """)
    if not recs:
        save_placeholder_html('step13_ixp_fac_bridge.html', STEP, TITLE_ZH, TITLE_EN,
                              '查询结果为空。', 'Query returned no data.')
        return

    rows = []
    ixp_cc = {}
    fac_cc = {}
    ixp_members = Counter()    # ixp -> # CN ASes
    fac_hosts = Counter()      # fac -> # records
    ixp_to_fac = Counter()     # (ixp, fac) -> pair count
    for r in recs:
        asn = r['asn']
        ixp = r['ixp']
        fac = r['fac']
        rows.append({'asn': asn, 'ixp': ixp, 'ixp_cc': r.get('ixp_cc') or '',
                     'fac': fac or '', 'fac_cc': r.get('fac_cc') or ''})
        if ixp:
            ixp_members[ixp] += 1
            if r.get('ixp_cc'):
                ixp_cc[ixp] = r['ixp_cc']
        if fac:
            fac_hosts[fac] += 1
            if r.get('fac_cc'):
                fac_cc[fac] = r['fac_cc']
            if ixp:
                ixp_to_fac[(ixp, fac)] += 1

    write_csv('cn_ixp_fac_tripartite.csv', rows,
              fieldnames=['asn', 'ixp', 'ixp_cc', 'fac', 'fac_cc'])

    # Top IXPs + their facilities + top CN ASes
    top_ixps = [i for i, _ in ixp_members.most_common(12)]
    chosen_facs = set()
    for ixp in top_ixps:
        # Top 3 facilities per IXP
        pairs = sorted(((f, c) for (i, f), c in ixp_to_fac.items() if i == ixp),
                       key=lambda x: -x[1])[:3]
        for f, _ in pairs:
            if f:
                chosen_facs.add(f)
    chosen_facs = list(chosen_facs)

    # Top CN ASes participating in these IXPs
    as_of_top_ixp = Counter()
    for r in rows:
        if r['ixp'] in top_ixps:
            as_of_top_ixp[r['asn']] += 1
    top_ases = [a for a, _ in as_of_top_ixp.most_common(30)]

    # ── Pyvis tripartite ──
    import networkx as nx
    G = nx.Graph()
    for a in top_ases:
        G.add_node(('as', a), type='as')
    for ixp in top_ixps:
        G.add_node(('ixp', ixp), type='ixp')
    for f in chosen_facs:
        G.add_node(('fac', f), type='fac')
    for r in rows:
        if r['ixp'] in top_ixps and r['asn'] in top_ases:
            G.add_edge(('as', r['asn']), ('ixp', r['ixp']))
        if r['fac'] in chosen_facs and r['ixp'] in top_ixps:
            G.add_edge(('ixp', r['ixp']), ('fac', r['fac']))

    # Layout: three columns
    pos = {}
    for i, a in enumerate(top_ases):
        pos[('as', a)] = (-1.0, (i - len(top_ases) / 2) / max(len(top_ases), 1) * 2.2)
    for i, ixp in enumerate(top_ixps):
        pos[('ixp', ixp)] = (0, (i - len(top_ixps) / 2) / max(len(top_ixps), 1) * 2.2)
    for i, fac in enumerate(chosen_facs):
        pos[('fac', fac)] = (1.0, (i - len(chosen_facs) / 2) / max(len(chosen_facs), 1) * 2.2)

    from pyvis.network import Network
    net = Network(height='720px', width='100%', bgcolor='#0D1117',
                  font_color='#E6EDF3', notebook=False, directed=False)
    net.toggle_physics(False)
    net.set_options('''
    var options = {
      "nodes": { "borderWidth": 2, "shadow": false },
      "edges": { "color": {"color": "#30363D", "opacity": 0.5},
                 "smooth": false, "width": 0.5 },
      "physics": { "enabled": false },
      "interaction": { "dragNodes": true, "hover": true }
    }
    ''')
    color_map = {'as': COLORS['red'], 'ixp': COLORS['cyan'], 'fac': COLORS['blue']}
    size_map = {'as': 20, 'ixp': 30, 'fac': 22}
    for nd in G.nodes():
        kind, key = nd
        x, y = pos[nd]
        net.add_node(
            f'{kind}:{key}',
            label=(f'AS{key}' if kind == 'as'
                   else key if len(str(key)) < 22 else str(key)[:22] + '…'),
            title=(f'AS{key} (CN)' if kind == 'as' else
                   f'IXP {key} [{ixp_cc.get(key, "?")}]' if kind == 'ixp' else
                   f'Facility {key} [{fac_cc.get(key, "?")}]'),
            color=color_map[kind], size=size_map[kind],
            x=float(x) * 1200, y=float(y) * 900,
        )
    for u, v in G.edges():
        net.add_edge(f'{u[0]}:{u[1]}', f'{v[0]}:{v[1]}')

    metrics = {
        'total_tripartite_rows': len(rows),
        'distinct_ixps_cn_used': len(ixp_members),
        'distinct_facilities_used_via_ixp': len({f for _, f in ixp_to_fac if f}),
        'top5_ixps_for_cn': [(i, ixp_members[i], ixp_cc.get(i, '?')) for i in top_ixps[:5]],
    }
    write_step_metrics(STEP, metrics, TITLE_ZH, TITLE_EN)

    w = writeup(
        hypothesis=(
            '物理层面："AS 在何处加入 IXP" 揭示国家出境流量的实际交换点。'
            '香港、新加坡、法兰克福、阿什本等"机房-IXP 合一"的枢纽承担着东亚出境流量的大部分互联。<br>'
            'Physically, where an AS joins an IXP reveals the actual cross-border exchange. Hubs like '
            'HK, SG, FRA, ASH co-locate IXPs with major carrier-neutral facilities.'
        ),
        finding=(
            f'提取 {len(rows)} 条 CN-AS / IXP / 机房 三部关系。'
            f'Top IXP 枢纽 (CN 视角): '
            + ', '.join(f'{i}[{ixp_cc.get(i, "?")}]({ixp_members[i]})' for i in top_ixps[:5])
            + f'。<br>'
            f'{len(rows)} tripartite rows extracted. Top IXP hubs for CN: '
            + ', '.join(f'{i}[{ixp_cc.get(i, "?")}]({ixp_members[i]})' for i in top_ixps[:5])
        ),
        reference='Live Neo4j join of MEMBER_OF × LOCATED_IN × COUNTRY',
    )

    save_pyvis_html(net, 'step13_ixp_fac_bridge.html',
                    step_num=STEP, title_zh=TITLE_ZH, title_en=TITLE_EN,
                    source='Neo4j live', writeup_html=w)


if __name__ == '__main__':
    main()
