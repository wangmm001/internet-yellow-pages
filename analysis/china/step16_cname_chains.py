"""Step 16 · CNAME Chains Crossing China.

Dimensions: HostName -[:ALIAS_OF]- HostName chains crossing CN cloud targets
Data: live Neo4j (targeted)
Output: cn_cname_chains.csv + Plotly Sankey cloud-provider flow diagram
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.china.common import (  # noqa: E402
    COLORS, DATA_DIR, country_color, neo4j_available,
    save_placeholder_html,
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

    # ── Plotly Sankey: cloud-provider flow ──
    # Delegate to the shared Sankey patcher (also usable as standalone post-processor)
    from analysis.web import patch_step16_html
    patch_step16_html.main()

    # Compute aggregates for metrics (mirrors patcher logic)
    fam_target_count = Counter()
    tld_edges = Counter()
    for r in rows:
        fam = classify_target(r['dst']) or 'Other CN'
        tld = r['src'].rsplit('.', 1)[-1].lower() if '.' in r['src'] else 'none'
        fam_target_count[fam] += 1
        tld_edges[tld] += 1

    metrics = {
        'alias_edges_sampled': len(rows),
        'distinct_cn_cloud_targets': len(target_count),
        'top_target_families': dict(family_count.most_common(8)),
        'family_distribution': dict(fam_target_count.most_common(10)),
        'top_individual_targets': target_count.most_common(5),
    }
    write_step_metrics(STEP, metrics, TITLE_ZH, TITLE_EN)

    writeup(
        hypothesis=(
            'CNAME 链揭示"运营依赖"而非 IP 层依赖。'
            '大量全球网站把 CDN/WAF 外包到 Cloudflare / Akamai；中国云服务的 CNAME 受众范围可反映"被中国 Cloud 承载"的海外流量。<br>'
            'CNAME chains reveal operational dependencies invisible at the IP layer. The population of hosts '
            'CNAMEd into Chinese clouds reflects foreign traffic operationally hosted by CN providers.'
        ),
        finding=(
            f'已采样 {len(rows)} 条 CNAME 边指向中国大陆云/CDN 目标；涉及目标主机名 {len(target_count)} 个。'
            f'聚合为 {len(fam_target_count)} 个云家族 × {len(tld_edges)} 个源 TLD 的 Sankey 流量图。'
            f'最受欢迎的运营商家族：{", ".join(f"{k}({v})" for k, v in fam_target_count.most_common(5))}。<br>'
            f'{len(rows)} sampled alias edges. Aggregated into {len(fam_target_count)} cloud '
            f'families × {len(tld_edges)} source TLDs (Sankey). Top families: '
            f'{", ".join(f"{k}({v})" for k, v in fam_target_count.most_common(5))}.'
        ),
        reference='OpenINTEL ALIAS_OF via IYP live query',
    )


if __name__ == '__main__':
    main()
