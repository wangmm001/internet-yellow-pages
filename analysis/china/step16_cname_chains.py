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

    # ── Family / TLD aggregation ──
    FAMILY_COLOR = {
        'Aliyun': COLORS['orange'],
        'Aliyun CDN': COLORS['orange'],
        'Tencent': COLORS['blue'],
        'Tencent Cloud': COLORS['blue'],
        'Tencent DNSPod': COLORS['blue'],
        'Tencent DNS': COLORS['blue'],
        'Huawei': COLORS['red'],
        'Huawei Cloud': COLORS['red'],
        'Huawei CDN': COLORS['red'],
        'Baidu': COLORS['purple'],
        'NetEase': COLORS['pink'],
        'JD': COLORS['amber'],
        'JD Cloud': COLORS['amber'],
        'ChinaCache': COLORS['green'],
        'ChinaNetCenter': COLORS['green'],
        'Wangsu': COLORS['cyan'],
        'Wangsu CDN': COLORS['cyan'],
        'Other CN': COLORS['teal'],
    }

    def family_of(dst):
        return classify_target(dst) or 'Other CN'

    def tld_of(src):
        part = src.rsplit('.', 1)[-1].lower() if '.' in src else 'none'
        return part

    # Aggregate: TLD -> family edges
    from collections import Counter
    fam_target_count = Counter()     # family -> distinct target host count
    tld_edge_count = Counter()       # tld -> distinct src-domain count
    tld_to_fam = Counter()           # (tld, family) -> edge count
    for r in rows:
        fam = family_of(r['dst'])
        tld = tld_of(r['src'])
        fam_target_count[fam] += 1
        tld_edge_count[tld] += 1
        tld_to_fam[(tld, fam)] += 1

    # Top-K tlds: collapse tail into "other"
    TOP_TLDS = 12
    sorted_tlds = [t for t, _ in tld_edge_count.most_common()]
    main_tlds = set(sorted_tlds[:TOP_TLDS])

    def tld_bucket(t):
        return t if t in main_tlds else 'other'

    # Rebuild counters with bucketing
    tld_edges = Counter()
    tld_fam_edges = Counter()
    for r in rows:
        fam = family_of(r['dst'])
        tld = tld_bucket(tld_of(r['src']))
        tld_edges[tld] += 1
        tld_fam_edges[(tld, fam)] += 1

    # Node sizing (log-scale)
    import math
    def scaled(count, base=22, k=7.5, cap=70):
        return min(round(base + math.log(max(count, 1) + 1) * k), cap)

    # ── Pyvis two-column layout ──
    from pyvis.network import Network
    net = Network(height='780px', width='100%', bgcolor='#0D1117',
                  font_color='#E6EDF3', notebook=False, directed=True)
    net.toggle_physics(False)
    net.set_options('''
    var options = {
      "nodes": { "borderWidth": 2, "shadow": false, "font": {"color": "#E6EDF3", "size": 14} },
      "edges": { "arrows": {"to": {"enabled": true, "scaleFactor": 0.4}},
                 "color": {"color": "#484F58", "opacity": 0.55},
                 "smooth": {"enabled": true, "type": "continuous"} },
      "physics": { "enabled": false },
      "interaction": { "dragNodes": true, "hover": true, "navigationButtons": true }
    }
    ''')

    # Sort by volume within each side for aesthetically pleasing layout
    left_tlds = sorted(tld_edges.items(), key=lambda x: -x[1])
    right_fams = sorted(fam_target_count.items(), key=lambda x: -x[1])

    # Left column (TLDs)
    n_left = len(left_tlds)
    for i, (tld, count) in enumerate(left_tlds):
        label = f'.{tld}' if tld not in ('other', 'none') else tld
        # Try to color by country (TLD as cc)
        cc = tld.upper() if len(tld) == 2 else ''
        color = country_color(cc) if cc else COLORS['cyan']
        net.add_node(
            f'tld:{tld}',
            label=f'{label} ({count})',
            title=f'TLD {label} — {count} CNAME edges',
            color=color, size=scaled(count),
            x=-900, y=float(i - n_left / 2) * 90,
        )

    # Right column (families)
    n_right = len(right_fams)
    for i, (fam, count) in enumerate(right_fams):
        color = FAMILY_COLOR.get(fam, COLORS['teal'])
        net.add_node(
            f'fam:{fam}',
            label=f'{fam} ({count})',
            title=f'{fam} — {count} distinct target hosts',
            color=color, size=scaled(count),
            x=900, y=float(i - n_right / 2) * 90,
        )

    # Edges: TLD -> family
    for (tld, fam), count in tld_fam_edges.items():
        width = min(1 + math.log(count + 1), 8)
        net.add_edge(
            f'tld:{tld}', f'fam:{fam}',
            value=count, width=float(width),
            title=f'{count} edges',
        )

    metrics = {
        'alias_edges_sampled': len(rows),
        'distinct_cn_cloud_targets': len(target_count),
        'top_target_families': dict(family_count.most_common(8)),
        'top_individual_targets': target_count.most_common(5),
        'family_distribution': dict(fam_target_count.most_common(10)),
        'tld_distribution': dict(tld_edges.most_common(10)),
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
            f'已采样 {len(rows)} 条 CNAME 边指向中国大陆云/CDN 目标；涉及目标主机名 {len(target_count)} 个。'
            f'聚合为 {len(fam_target_count)} 个云家族 × {len(tld_edges)} 个源 TLD 的二分图。'
            f'最受欢迎的运营商家族：{", ".join(f"{k}({v})" for k, v in fam_target_count.most_common(5))}。<br>'
            f'{len(rows)} sampled alias edges. Aggregated into {len(fam_target_count)} cloud '
            f'families × {len(tld_edges)} source TLDs. Top families: '
            f'{", ".join(f"{k}({v})" for k, v in fam_target_count.most_common(5))}.'
        ),
        reference='OpenINTEL ALIAS_OF via IYP live query',
    )

    save_pyvis_html(net, 'step16_cname_chains.html',
                    step_num=STEP, title_zh=TITLE_ZH, title_en=TITLE_EN,
                    source='Neo4j live', writeup_html=w)


if __name__ == '__main__':
    main()
