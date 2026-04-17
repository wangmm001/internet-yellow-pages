"""Step 15 · DNS Authority & .cn Zone Sovereignty.

Dimensions: DomainName -[:MANAGED_BY]- AuthoritativeNameServer
Data: live Neo4j for .cn zone nameservers
Output: cn_dns_authority.csv + horizontal bar + Sankey
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.china.common import (  # noqa: E402
    COLORS, DATA_DIR, TEXT_PRIMARY, DARK_PANEL, country_color,
    neo4j_available, save_multi_plotly_html, save_placeholder_html,
    write_csv, write_step_metrics, writeup,
)
from analysis.complex_network.utils import run_query

STEP = 15
TITLE_ZH = '.cn 域名权威 DNS 主权分析'
TITLE_EN = 'DNS Authority & .cn Zone Sovereignty'


def infer_provider(ns_name):
    """Group NS hostnames into logical providers."""
    if not ns_name:
        return 'Unknown'
    n = ns_name.lower()
    mapping = [
        ('aliyun', 'Aliyun'), ('alidns', 'Aliyun'),
        ('dnspod', 'Tencent DNSPod'), ('qcloud', 'Tencent Cloud'),
        ('huawei', 'Huawei'),
        ('cloudflare', 'Cloudflare'),
        ('awsdns', 'AWS Route53'), ('amazonaws', 'AWS'),
        ('google', 'Google'), ('googledomains', 'Google'),
        ('nstld', 'VeriSign'), ('verisign', 'VeriSign'),
        ('cnnic', 'CNNIC'), ('cn.com', 'CNNIC'),
        ('baidu', 'Baidu'),
        ('netease', 'NetEase'),
        ('bjtu', 'CERNET'), ('cernet', 'CERNET'),
        ('xinnet', 'Xinnet'),
        ('paycenter', 'CTDNS'),
        ('godaddy', 'GoDaddy'), ('domaincontrol', 'GoDaddy'),
    ]
    for k, v in mapping:
        if k in n:
            return v
    # TLD-based heuristic
    tld = n.rsplit('.', 1)[-1]
    return f'Other ({tld})'


def provider_country(provider):
    cn_providers = {'Aliyun', 'Tencent DNSPod', 'Tencent Cloud', 'Huawei',
                    'CNNIC', 'Baidu', 'NetEase', 'CERNET', 'Xinnet', 'CTDNS'}
    us_providers = {'Cloudflare', 'AWS Route53', 'AWS', 'Google', 'VeriSign', 'GoDaddy'}
    if provider in cn_providers:
        return 'CN'
    if provider in us_providers:
        return 'US'
    return 'Other'


def main():
    if not neo4j_available():
        save_placeholder_html('step15_dns_authority.html', STEP, TITLE_ZH, TITLE_EN,
                              'Neo4j 不可用。', 'Neo4j unavailable.')
        return

    print('[step15] querying .cn zone authority…')
    recs = run_query("""
        MATCH (d:DomainName)-[:MANAGED_BY]->(ns:AuthoritativeNameServer)
        WHERE d.name ENDS WITH '.cn'
        RETURN ns.name AS ns_name, count(DISTINCT d) AS cnt
        ORDER BY cnt DESC LIMIT 500
    """)

    if not recs:
        save_placeholder_html('step15_dns_authority.html', STEP, TITLE_ZH, TITLE_EN,
                              '查询 .cn 域无结果。', 'No .cn zone data.')
        return

    # Reverse direction: CN-operated NS managing foreign domains
    print('[step15] querying CN-operated NS serving foreign zones…')
    recs_cn_ns = run_query("""
        MATCH (d:DomainName)-[:MANAGED_BY]->(ns:AuthoritativeNameServer)
        WHERE ns.name CONTAINS '.aliyun' OR ns.name CONTAINS 'alidns'
           OR ns.name CONTAINS 'dnspod' OR ns.name CONTAINS 'huaweicloud'
           OR ns.name CONTAINS 'cnnic'
        RETURN ns.name AS ns_name, count(DISTINCT d) AS cnt
        ORDER BY cnt DESC LIMIT 50
    """)

    rows_cn = []
    provider_count = Counter()
    country_count = Counter()
    for r in recs:
        rows_cn.append({'ns_name': r['ns_name'], 'zone_count': r['cnt']})
        p = infer_provider(r['ns_name'])
        provider_count[p] += r['cnt']
        country_count[provider_country(p)] += r['cnt']

    write_csv('cn_dns_authority.csv', rows_cn)

    import plotly.graph_objects as go

    # ── Horizontal bar: top-20 providers ──
    top_providers = provider_count.most_common(20)
    bar = go.Figure(go.Bar(
        y=[p for p, _ in top_providers][::-1],
        x=[c for _, c in top_providers][::-1],
        orientation='h',
        marker_color=[country_color(provider_country(p)) for p, _ in top_providers][::-1],
        text=[f'{c:,}' for _, c in top_providers][::-1],
        textposition='outside',
    ))
    bar.update_layout(
        title='.cn 域名管理 NS 提供商 Top-20 (colors=provider country)',
        xaxis=dict(title='# .cn domains managed'),
        height=640,
    )

    # ── Sankey: provider → country ──
    nodes = []
    node_idx = {}

    def nidx(label, color):
        if label not in node_idx:
            node_idx[label] = len(nodes)
            nodes.append((label, color))
        return node_idx[label]

    for provider, cnt in top_providers:
        cc = provider_country(provider)
        s = nidx(provider, country_color(cc))
        d = nidx(f'Country={cc}', country_color(cc))

    link_src, link_dst, link_val = [], [], []
    for provider, cnt in top_providers:
        cc = provider_country(provider)
        link_src.append(node_idx[provider])
        link_dst.append(node_idx[f'Country={cc}'])
        link_val.append(cnt)

    sankey = go.Figure(go.Sankey(
        node=dict(label=[n[0] for n in nodes],
                  color=[n[1] for n in nodes], pad=14, thickness=18),
        link=dict(source=link_src, target=link_dst, value=link_val,
                  color='rgba(69,183,209,0.3)'),
    ))
    sankey.update_layout(
        title='.cn 管理链流向国家 · Provider → country Sankey', height=620)

    # ── Pie: CN vs US vs Other share ──
    pie = go.Figure(go.Pie(
        labels=list(country_count.keys()),
        values=list(country_count.values()),
        marker=dict(colors=[country_color(k) for k in country_count.keys()]),
        textinfo='label+percent', hole=0.4,
    ))
    pie.update_layout(title='.cn 域名管理运营商国籍分布 · Operator-country share')

    # ── Reverse: CN-operated NS managing foreign ──
    reverse_txt = ''
    for r in (recs_cn_ns or [])[:10]:
        reverse_txt += f'<tr><td>{r["ns_name"]}</td><td>{r["cnt"]:,}</td></tr>'
    reverse_html = (
        '<h3 style="color:#E6EDF3;margin-top:30px">中国运营商 NS 管理全球域的数量</h3>'
        '<table><tr><th>NS</th><th>Domains managed</th></tr>' + reverse_txt + '</table>')

    cn_share = country_count.get('CN', 0) / sum(country_count.values()) * 100
    us_share = country_count.get('US', 0) / sum(country_count.values()) * 100

    metrics = {
        'ns_sampled_for_cn_tld': len(rows_cn),
        'total_cn_domains_covered': sum(provider_count.values()),
        'cn_operator_share_pct': round(cn_share, 2),
        'us_operator_share_pct': round(us_share, 2),
        'top5_providers': top_providers[:5],
        'cn_operated_ns_serving_foreign_top': [(r['ns_name'], r['cnt'])
                                               for r in (recs_cn_ns or [])[:5]],
    }
    write_step_metrics(STEP, metrics, TITLE_ZH, TITLE_EN)

    w = writeup(
        hypothesis=(
            'DNS 权威主权：一个国家的域名由本地运营商管理的比例越高，在 DNS 断网与被劫持等风险下越"可守"。<br>'
            'DNS sovereignty: the higher the share of a country\'s zone managed by domestic operators, the more '
            'resilient it is to cross-border DNS disruption.'
        ),
        finding=(
            f'采样 .cn 域名由 {len(provider_count)} 类 NS 提供商管理；'
            f'其中中国本土运营商覆盖 {cn_share:.1f}%，美国运营商 {us_share:.1f}%，其它 {100 - cn_share - us_share:.1f}%。'
            f'Top 提供商：{", ".join(f"{p}({c:,})" for p, c in top_providers[:5])}。<br>'
            f'CN operators cover {cn_share:.1f}% of sampled .cn domain management; US {us_share:.1f}%. '
            f'Top providers: {", ".join(f"{p}({c:,})" for p, c in top_providers[:5])}.'
        ),
        reference='OpenINTEL MANAGED_BY via IYP live Neo4j query',
    )

    save_multi_plotly_html(
        [bar, sankey, pie], 'step15_dns_authority.html',
        step_num=STEP, title_zh=TITLE_ZH, title_en=TITLE_EN, source='Neo4j live',
        writeup_html=w + reverse_html,
        subtitles=['1. Top-20 .cn 权威 NS 提供商',
                   '2. 提供商 → 国家 Sankey',
                   '3. 国籍占比'],
    )


if __name__ == '__main__':
    main()
