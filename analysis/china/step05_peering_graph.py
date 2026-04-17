"""Step 05 · China AS Peering Graph.

Dimensions: AS -[:PEERS_WITH]- AS filtered where at least one endpoint is CN
Data: cached bgp_peering.csv + as_country.csv + as_metadata.csv
Output: cn_peering_subgraph.csv + Pyvis interactive network
"""
import csv
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.china.common import (  # noqa: E402
    COLORS, DATA_DIR, country_color, load_as_country_map, load_as_metadata,
    load_cn_ases, save_pyvis_html, write_csv, write_step_metrics, writeup,
)
from analysis.complex_network.utils import DATA_DIR as GLOBAL_DATA_DIR

STEP = 5
TITLE_ZH = '中国 AS 对等互联子图'
TITLE_EN = 'China AS Peering Subgraph'

MAX_NODES = 400  # visually tractable cap


def main():
    cn = load_cn_ases()
    md = load_as_metadata()
    cmap = load_as_country_map()

    # Load peering edges, keep rows where at least one endpoint is CN
    path = os.path.join(GLOBAL_DATA_DIR, 'bgp_peering.csv')
    deg = Counter()
    cn_neighbors = defaultdict(set)
    edges = []
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            try:
                s, d = int(row['src']), int(row['dst'])
            except Exception:
                continue
            if s == d:
                continue
            if s > d:
                s, d = d, s
            if s in cn or d in cn:
                deg[s] += 1
                deg[d] += 1
                if s in cn:
                    cn_neighbors[s].add(d)
                if d in cn:
                    cn_neighbors[d].add(s)
                edges.append((s, d))

    # Dedupe edges
    edges = list(set(edges))

    # Select top-X CN nodes by degree, then include their foreign neighbors up to MAX_NODES
    cn_in_edges = [a for a in deg if a in cn]
    cn_top = sorted(cn_in_edges, key=lambda a: deg[a], reverse=True)[:60]
    chosen = set(cn_top)
    # Add foreign neighbors of the top-60
    foreign_candidates = Counter()
    for asn in cn_top:
        for nb in cn_neighbors[asn]:
            if nb not in cn:
                foreign_candidates[nb] += 1
    for asn, _ in foreign_candidates.most_common(MAX_NODES - len(chosen)):
        chosen.add(asn)

    # Keep edges only within chosen set
    sub_edges = [(s, d) for s, d in edges if s in chosen and d in chosen]

    # Country counter among chosen foreign neighbors
    foreign_cc_count = Counter()
    for asn in chosen:
        if asn in cn:
            continue
        ccs = cmap.get(asn, set())
        for cc in ccs:
            foreign_cc_count[cc] += 1

    write_csv('cn_peering_subgraph.csv',
              [{'src': s, 'dst': d} for s, d in sub_edges],
              fieldnames=['src', 'dst'])

    # ── Pre-compute spring layout for better Pyvis output ──
    import networkx as nx
    G = nx.Graph()
    G.add_edges_from(sub_edges)
    try:
        pos = nx.spring_layout(G, k=0.8, iterations=120, seed=42)
    except Exception:
        pos = {n: (0, 0) for n in G.nodes()}

    # ── Pyvis network ──
    from pyvis.network import Network
    net = Network(height='720px', width='100%', bgcolor='#0D1117',
                  font_color='#E6EDF3', notebook=False, directed=False)
    net.toggle_physics(False)
    net.set_options('''
    var options = {
      "nodes": { "borderWidth": 1, "shadow": false },
      "edges": { "color": {"color": "#30363D", "opacity": 0.4},
                 "smooth": false, "width": 0.5 },
      "physics": { "enabled": false },
      "interaction": { "dragNodes": true, "hover": true, "zoomView": true }
    }
    ''')

    for asn in chosen:
        ccs = cmap.get(asn, {'ZZ'})
        primary_cc = 'CN' if asn in cn else (next(iter(ccs)) if ccs else 'ZZ')
        color = country_color(primary_cc)
        size = 10 + min(deg.get(asn, 1), 400) ** 0.5 * 1.2
        name = ''
        meta = md.get(asn)
        if meta and meta['tags']:
            name = ' · ' + (meta['tags'][0] if meta['tags'] else '')
        label = f'AS{asn}'
        title = f'AS{asn} [{primary_cc}] degree={deg.get(asn, 0)}{name}'
        x, y = pos.get(asn, (0, 0))
        net.add_node(asn, label=label, title=title, color=color, size=size,
                     x=float(x) * 1000, y=float(y) * 1000)

    for s, d in sub_edges:
        net.add_edge(s, d)

    w = writeup(
        hypothesis=(
            '小世界结构在互联网 AS 级别长期被观察到；但不同国家的对等互联模式差异显著：'
            '一些国家在本地形成稠密"半岛"（如 BR/DE），另一些则主要通过少量 Tier-1 上联（如 CN/RU）。<br>'
            'The Internet exhibits small-world structure at the AS level, but country-level peering patterns diverge: '
            'some countries form dense local peninsulas (BR, DE) while others rely on a few Tier-1 uplinks (CN, RU).'
        ),
        finding=(
            f'子图 {len(chosen)} 节点（其中 CN AS {len([a for a in chosen if a in cn])} 个）、'
            f'{len(sub_edges)} 条对等互联边。与 CN 相连的外国 ASN 覆盖 {len(foreign_cc_count)} 个国家；'
            f'最主要外部对端来自：{", ".join(f"{cc}({n})" for cc, n in foreign_cc_count.most_common(5))}。<br>'
            f'Subgraph: {len(chosen)} nodes ({len([a for a in chosen if a in cn])} CN), {len(sub_edges)} edges. '
            f'Top foreign peer countries: {", ".join(f"{cc}({n})" for cc, n in foreign_cc_count.most_common(5))}.'
        ),
        reference='BGPKIT AS relationship data, cached bgp_peering.csv',
    )

    metrics = {
        'nodes_total': len(chosen),
        'cn_nodes': len([a for a in chosen if a in cn]),
        'foreign_nodes': len([a for a in chosen if a not in cn]),
        'edges': len(sub_edges),
        'top_foreign_countries': dict(foreign_cc_count.most_common(10)),
    }
    write_step_metrics(STEP, metrics, TITLE_ZH, TITLE_EN)

    save_pyvis_html(net, 'step05_peering_graph.html',
                    step_num=STEP, title_zh=TITLE_ZH, title_en=TITLE_EN,
                    source='cached CSV', writeup_html=w)


if __name__ == '__main__':
    main()
