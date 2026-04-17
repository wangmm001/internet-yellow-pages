"""Step 16 · CNAME Chains Crossing China.

Dimensions: HostName -[:ALIAS_OF]- HostName chains crossing CN cloud targets
Data: live Neo4j (targeted)
Output: cn_cname_chains.csv + Pyvis directed alias graph
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.china.common import (  # noqa: E402
    COLORS, DATA_DIR, country_color, neo4j_available,
    save_pyvis_html, save_placeholder_html,
    write_csv, write_step_metrics, writeup,
)
from analysis.complex_network.utils import run_query

STEP = 16
TITLE_ZH = '跨境 CNAME 别名链'
TITLE_EN = 'CNAME Chains Crossing China'


def classify_target(name):
    """Classify a host name into a CN cloud / CDN family."""
    if not name:
        return 'Unknown'
    n = name.lower()
    mapping = [
        ('aliyun', 'Aliyun'), ('alicdn', 'Aliyun CDN'), ('alibabadns', 'Aliyun'),
        ('tencent', 'Tencent'), ('qcloud', 'Tencent Cloud'),
        ('myqcloud', 'Tencent Cloud'), ('dnspod', 'Tencent DNSPod'),
        ('huawei', 'Huawei'), ('hwclouds', 'Huawei Cloud'), ('myhwclouds', 'Huawei Cloud'),
        ('baidu', 'Baidu'), ('bdstatic', 'Baidu'),
        ('chinacache', 'ChinaCache'), ('chinanetcenter', 'ChinaNetCenter'),
        ('wangsu', 'Wangsu'), ('wscloudcdn', 'Wangsu CDN'),
        ('cdnhwc', 'Huawei CDN'), ('dnsv1', 'Tencent DNS'),
        ('netease', 'NetEase'), ('163', 'NetEase'),
        ('jd', 'JD'), ('jdcdn', 'JD Cloud'),
    ]
    for k, v in mapping:
        if k in n:
            return v
    return None


def main():
    if not neo4j_available():
        save_placeholder_html('step16_cname_chains.html', STEP, TITLE_ZH, TITLE_EN,
                              'Neo4j 不可用。', 'Neo4j unavailable.')
        return

    print('[step16] querying CNAME chains to CN cloud targets…')
    # Find alias chains where target is Chinese cloud / CDN
    recs = run_query("""
        MATCH (h1:HostName)-[:ALIAS_OF]->(h2:HostName)
        WHERE h2.name CONTAINS 'aliyuncs'
           OR h2.name CONTAINS 'alicdn'
           OR h2.name CONTAINS 'myqcloud'
           OR h2.name CONTAINS 'cloudflare.net.aliyun'
           OR h2.name CONTAINS 'hwclouds'
           OR h2.name CONTAINS 'cdnhwc'
           OR h2.name CONTAINS 'wscloudcdn'
           OR h2.name CONTAINS 'bdstatic'
           OR h2.name CONTAINS 'chinacache'
           OR h2.name CONTAINS 'chinanetcenter'
        RETURN h1.name AS src, h2.name AS dst LIMIT 2500
    """)

    if not recs:
        save_placeholder_html('step16_cname_chains.html', STEP, TITLE_ZH, TITLE_EN,
                              '查询结果为空。', 'Query returned no chains.')
        return

    rows = []
    target_count = Counter()
    family_count = Counter()
    src_domains = set()
    for r in recs:
        rows.append({'src': r['src'], 'dst': r['dst']})
        target_count[r['dst']] += 1
        fam = classify_target(r['dst']) or 'Other CN'
        family_count[fam] += 1
        # infer source TLD
        src_domains.add(r['src'].rsplit('.', 1)[-1] if '.' in r['src'] else 'none')

    write_csv('cn_cname_chains.csv', rows, fieldnames=['src', 'dst'])

    # ── Pyvis: bipartite-ish network, sources aggregated by TLD ──
    import networkx as nx
    G = nx.DiGraph()
    # Build with sources truncated
    MAX_ROWS_VIS = 300
    sample = rows[:MAX_ROWS_VIS]
    for r in sample:
        src = r['src']
        dst = r['dst']
        if len(src) > 40:
            src = src[:37] + '…'
        if len(dst) > 40:
            dst = dst[:37] + '…'
        G.add_edge(src, dst)

    try:
        pos = nx.spring_layout(G, k=0.5, iterations=100, seed=42)
    except Exception:
        pos = {n: (0, 0) for n in G.nodes()}

    from pyvis.network import Network
    net = Network(height='720px', width='100%', bgcolor='#0D1117',
                  font_color='#E6EDF3', notebook=False, directed=True)
    net.toggle_physics(False)
    net.set_options('''
    var options = {
      "nodes": { "borderWidth": 1, "shadow": false },
      "edges": { "arrows": {"to": {"enabled": true, "scaleFactor": 0.4}},
                 "color": {"color": "#30363D", "opacity": 0.4},
                 "smooth": false, "width": 0.5 },
      "physics": { "enabled": false },
      "interaction": { "dragNodes": true, "hover": true }
    }
    ''')

    for node in G.nodes():
        fam = classify_target(node)
        if fam:
            color = COLORS['red']
            size = 18
            title = f'CN cloud target · {node} ({fam})'
        else:
            color = COLORS['cyan']
            size = 7
            title = f'Source domain · {node}'
        x, y = pos.get(node, (0, 0))
        net.add_node(node, label=node[:20], title=title, color=color, size=size,
                     x=float(x) * 1200, y=float(y) * 900)

    for u, v in G.edges():
        net.add_edge(u, v)

    metrics = {
        'alias_edges_sampled': len(rows),
        'distinct_cn_cloud_targets': len(target_count),
        'top_target_families': dict(family_count.most_common(8)),
        'top_individual_targets': target_count.most_common(5),
    }
    write_step_metrics(STEP, metrics, TITLE_ZH, TITLE_EN)

    w = writeup(
        hypothesis=(
            'CNAME 链揭示"运营依赖"而非 IP 层依赖。'
            '大量全球网站把 CDN/WAF 外包到 Cloudflare / Akamai；中国云服务的 CNAME 受众范围可反映"被中国 Cloud 承载"的海外流量。<br>'
            'CNAME chains reveal operational dependencies invisible at the IP layer. The population of hosts '
            'CNAMEd into Chinese clouds reflects foreign traffic operationally hosted by CN providers.'
        ),
        finding=(
            f'已采样 {len(rows)} 条 CNAME 边指向中国云/CDN 目标；涉及目标主机名 {len(target_count)} 个。'
            f'最受欢迎的运营商家族：{", ".join(f"{k}({v})" for k, v in family_count.most_common(5))}。<br>'
            f'{len(rows)} sampled alias edges pointing to CN cloud/CDN targets covering {len(target_count)} '
            f'distinct CN target hostnames. Top families: '
            f'{", ".join(f"{k}({v})" for k, v in family_count.most_common(5))}.'
        ),
        reference='OpenINTEL ALIAS_OF via IYP live query',
    )

    save_pyvis_html(net, 'step16_cname_chains.html',
                    step_num=STEP, title_zh=TITLE_ZH, title_en=TITLE_EN,
                    source='Neo4j live', writeup_html=w)


if __name__ == '__main__':
    main()
