"""Step 09 · Who depends on China? (inbound hegemony).

Dimensions: AS -[:DEPENDS_ON {hege}]- AS where destination (upstream) is CN
Data: cached as_dependency.csv
Output: cn_dependency_inbound.csv + Pyvis radial graph
"""
import csv
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.china.common import (  # noqa: E402
    COLORS, DATA_DIR, country_color, load_as_country_map,
    load_as_metadata, load_cn_ases, save_pyvis_html, write_csv,
    write_step_metrics, writeup,
)
from analysis.complex_network.utils import DATA_DIR as GLOBAL_DATA_DIR

STEP = 9
TITLE_ZH = '谁依赖中国? · 入向 AS Hegemony'
TITLE_EN = 'Who Depends on China? (Inbound Hegemony)'

HEGE_MIN = 0.03


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
            # Upstream (d) is CN, source (s) can be anywhere
            if d in cn and s not in cn:
                rows.append({'src': s, 'dst': d, 'hege': h})

    write_csv('cn_dependency_inbound.csv', rows,
              fieldnames=['src', 'dst', 'hege'])

    # Top CN upstreams by dependent count
    upstream_count = Counter()
    for r in rows:
        upstream_count[r['dst']] += 1
    top_cn_upstreams = [a for a, _ in upstream_count.most_common(5)]

    # For each top CN upstream, list top 25 foreign dependents
    import networkx as nx
    G = nx.Graph()
    for anchor in top_cn_upstreams:
        dependents = [(r['src'], r['hege']) for r in rows if r['dst'] == anchor]
        dependents.sort(key=lambda t: t[1], reverse=True)
        G.add_node(anchor, role='anchor')
        for dep, hege in dependents[:40]:
            G.add_node(dep, role='dependent')
            G.add_edge(anchor, dep, hege=hege)

    # Collect foreign countries most dependent
    dep_cc = Counter()
    for a in G.nodes():
        if G.nodes[a].get('role') == 'dependent':
            cc = next(iter(cmap.get(a, {'ZZ'})), 'ZZ')
            dep_cc[cc] += 1

    # Pre-compute layout
    try:
        pos = nx.spring_layout(G, k=1.8, iterations=120, seed=42)
    except Exception:
        pos = {n: (0, 0) for n in G.nodes()}

    # ── Pyvis ──
    from pyvis.network import Network
    net = Network(height='720px', width='100%', bgcolor='#0D1117',
                  font_color='#E6EDF3', notebook=False, directed=True)
    net.toggle_physics(False)
    net.set_options('''
    var options = {
      "nodes": { "borderWidth": 2, "shadow": true },
      "edges": { "arrows": {"to": {"enabled": true, "scaleFactor": 0.5}},
                 "color": {"color": "#30363D", "opacity": 0.6},
                 "smooth": false },
      "physics": { "enabled": false },
      "interaction": { "dragNodes": true, "hover": true }
    }
    ''')

    for asn in G.nodes():
        role = G.nodes[asn]['role']
        ccs = cmap.get(asn, {'ZZ'})
        primary_cc = 'CN' if asn in cn else (next(iter(ccs)) if ccs else 'ZZ')
        tags = md.get(asn, {}).get('tags', [])
        label = f'AS{asn}' + (f'\n{tags[0][:18]}' if tags and role == 'anchor' else '')
        color = country_color(primary_cc)
        if role == 'anchor':
            size = 45
            title = f'中国骨干 AS{asn} · degree={G.degree(asn)} · {(tags[0] if tags else "")}'
        else:
            size = 14
            title = f'AS{asn} [{primary_cc}] depends on CN anchor'
        x, y = pos.get(asn, (0, 0))
        net.add_node(asn, label=label, title=title, color=color,
                     size=size, x=float(x) * 1400, y=float(y) * 1400)

    for u, v, data in G.edges(data=True):
        anchor = u if G.nodes[u]['role'] == 'anchor' else v
        dep = v if anchor == u else u
        net.add_edge(dep, anchor, value=float(data['hege']))

    metrics = {
        'total_inbound_edges_hege_ge_003': len(rows),
        'foreign_dependents': len({r['src'] for r in rows}),
        'top5_cn_upstream': [(a, upstream_count[a]) for a in top_cn_upstreams],
        'top_dependent_countries': dict(dep_cc.most_common(10)),
    }
    write_step_metrics(STEP, metrics, TITLE_ZH, TITLE_EN)

    w = writeup(
        hypothesis=(
            '多数"Tier-1 级"AS 的出现假设是全球性的 (Labovitz 2010)；'
            '如果中国 AS 出现作为其他国家的上游，说明中国已从"纯末端"转向"区域 hub"。<br>'
            'Prior work suggests Tier-1-like roles are global. Any CN AS acting as upstream for foreign ASes '
            'indicates a transition from pure eyeball to regional hub status.'
        ),
        finding=(
            f'{len(rows)} 条外部 AS → CN 依赖边 (hege≥{HEGE_MIN})。'
            f'{len({r["src"] for r in rows})} 个外部 AS 依赖中国上游。'
            f'Top-5 CN 上游: {", ".join(f"AS{a}({upstream_count[a]})" for a in top_cn_upstreams)}。'
            f'依赖方国家分布: {", ".join(f"{cc}({c})" for cc, c in dep_cc.most_common(5))}。<br>'
            f'{len(rows)} foreign→CN dependency edges. {len({r["src"] for r in rows})} foreign ASes depend '
            f'on CN upstreams. Top-5 CN hubs: {", ".join(f"AS{a}({upstream_count[a]})" for a in top_cn_upstreams)}.'
        ),
        reference='IHR hegemony (as_dependency.csv)',
    )

    save_pyvis_html(net, 'step09_dependents.html',
                    step_num=STEP, title_zh=TITLE_ZH, title_en=TITLE_EN,
                    source='cached CSV', writeup_html=w)


if __name__ == '__main__':
    main()
