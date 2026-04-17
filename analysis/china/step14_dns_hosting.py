"""Step 14 · China DNS Hosting Footprint.

Dimensions: HostName-[:RESOLVES_TO]-IP-[:PART_OF]-Prefix-[:ORIGINATE]-AS
Data: cached dns_as_hosting.csv + as_metadata.csv + as_country.csv
Output: cn_dns_hosting.csv + sunburst + Top-20 bar
"""
import csv
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.china.common import (  # noqa: E402
    COLORS, DATA_DIR, country_color, load_as_metadata, load_as_country_map,
    load_cn_ases, save_multi_plotly_html, write_csv,
    write_step_metrics, writeup,
)
from analysis.complex_network.utils import DATA_DIR as GLOBAL_DATA_DIR

STEP = 14
TITLE_ZH = '中国 DNS 主机托管版图'
TITLE_EN = 'China DNS Hosting Footprint'


def main():
    cn = load_cn_ases()
    cmap = load_as_country_map()
    md = load_as_metadata()

    path = os.path.join(GLOBAL_DATA_DIR, 'dns_as_hosting.csv')
    rows = []
    cn_hosting_rows = []
    global_by_country = Counter()
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            try:
                asn = int(row['asn'])
                hc = int(row['hostname_count'])
            except Exception:
                continue
            ccs = cmap.get(asn, set())
            primary_cc = next(iter(ccs)) if ccs else 'ZZ'
            global_by_country[primary_cc] += hc
            rows.append((asn, hc, primary_cc))
            if asn in cn:
                cn_hosting_rows.append({
                    'asn': asn, 'hostname_count': hc, 'ip_count': int(row.get('ip_count') or 0),
                    'country': primary_cc,
                    'org_tags': '|'.join(md.get(asn, {}).get('tags', [])[:3]),
                })
    cn_hosting_rows.sort(key=lambda r: r['hostname_count'], reverse=True)
    write_csv('cn_dns_hosting.csv', cn_hosting_rows)

    import plotly.graph_objects as go

    # ── Sunburst: Country (top 10) → top-5 ASes ──
    top_countries = [cc for cc, _ in global_by_country.most_common(10)]
    labels = ['Global']
    parents = ['']
    values = [sum(global_by_country.values())]
    colors = [COLORS['cyan']]
    as_by_country = defaultdict(list)
    for asn, hc, cc in rows:
        as_by_country[cc].append((asn, hc))
    for cc in top_countries:
        total = global_by_country[cc]
        labels.append(cc)
        parents.append('Global')
        values.append(total)
        colors.append(country_color(cc))
        lst = sorted(as_by_country[cc], key=lambda t: -t[1])[:5]
        for asn, hc in lst:
            labels.append(f'AS{asn} · {hc:,}')
            parents.append(cc)
            values.append(hc)
            colors.append(country_color(cc))

    sun = go.Figure(go.Sunburst(
        labels=labels, parents=parents, values=values,
        marker=dict(colors=colors),
        branchvalues='total',
        hovertemplate='<b>%{label}</b><br>%{value:,} hostnames<extra></extra>',
    ))
    sun.update_layout(
        title='全球托管规模 · HostName hosting by country→AS (top 10 countries × top 5 AS)')

    # ── Top-20 CN ASes ──
    top_cn = cn_hosting_rows[:20]
    bar = go.Figure(go.Bar(
        x=[f'AS{r["asn"]}' for r in top_cn],
        y=[r['hostname_count'] for r in top_cn],
        marker_color=COLORS['red'],
        text=[f'{r["hostname_count"]:,}' for r in top_cn],
        textposition='outside',
        hovertext=[r['org_tags'] for r in top_cn],
    ))
    bar.update_layout(
        title='中国托管最多 HostName 的 AS · Top-20 CN hosting ASes',
        yaxis=dict(title='HostName count (log)', type='log'),
        xaxis=dict(tickangle=-30))

    # ── Pie: CN hosting by commercial cloud vs ISP ──
    cloud_keywords = ['Hosting', 'Cloud', 'Content Delivery Network']
    cn_cloud_total = 0
    cn_isp_total = 0
    cn_other_total = 0
    for r in cn_hosting_rows:
        tags = md.get(r['asn'], {}).get('tags', [])
        blob = '|'.join(tags)
        if any(k in blob for k in cloud_keywords):
            cn_cloud_total += r['hostname_count']
        elif any(k in blob for k in ['ISP', 'Carrier', 'Home ISP']):
            cn_isp_total += r['hostname_count']
        else:
            cn_other_total += r['hostname_count']
    pie = go.Figure(go.Pie(
        labels=['Cloud / CDN / Hosting', 'ISP / Carrier', 'Other'],
        values=[cn_cloud_total, cn_isp_total, cn_other_total],
        marker=dict(colors=[COLORS['blue'], COLORS['orange'], COLORS['green']]),
        hole=0.4, textinfo='label+percent',
    ))
    pie.update_layout(title='中国承载主机名按 AS 性质分布 · Cloud vs ISP split')

    metrics = {
        'cn_hosting_ases': len(cn_hosting_rows),
        'cn_total_hostnames_hosted': sum(r['hostname_count'] for r in cn_hosting_rows),
        'top5_cn_hosters': [(r['asn'], r['hostname_count']) for r in top_cn[:5]],
        'global_rank_of_cn_by_hosting': (
            next((i + 1 for i, (cc, _) in enumerate(global_by_country.most_common())
                  if cc == 'CN'), None)),
        'cloud_vs_isp_split_hostnames': {
            'cloud_cdn': cn_cloud_total, 'isp': cn_isp_total, 'other': cn_other_total,
        },
    }
    write_step_metrics(STEP, metrics, TITLE_ZH, TITLE_EN)

    w = writeup(
        hypothesis=(
            '过去十年"Web 集中化"使得 AS16509 (AWS)、AS15169 (Google)、AS13335 (Cloudflare) 承载巨量域名。'
            '中国类似角色由 AS37963 (Aliyun) / AS45090 (Tencent) / AS55960 (Huawei Cloud) 等承担。<br>'
            'Web consolidation concentrates hostnames on a few mega-ASes globally (AWS/Google/Cloudflare). '
            'In China, Aliyun/Tencent/Huawei Cloud play analogous roles.'
        ),
        finding=(
            f'{len(cn_hosting_rows)} 个 CN AS 托管 {sum(r["hostname_count"] for r in cn_hosting_rows):,} '
            f'个 HostName。按国家总托管量 CN 排名全球 #{metrics["global_rank_of_cn_by_hosting"]}。'
            f'Top5 CN 托管 AS: {", ".join(f"AS{r[0]}" for r in metrics["top5_cn_hosters"])}。'
            f'Cloud/CDN 占 CN 总托管的 {cn_cloud_total / max(1, cn_cloud_total + cn_isp_total + cn_other_total) * 100:.1f}%。<br>'
            f'{len(cn_hosting_rows)} CN ASes host {sum(r["hostname_count"] for r in cn_hosting_rows):,} hostnames. '
            f'CN ranks #{metrics["global_rank_of_cn_by_hosting"]} globally by hosting. Cloud/CDN captures '
            f'{cn_cloud_total / max(1, cn_cloud_total + cn_isp_total + cn_other_total) * 100:.1f}% of CN hosting.'
        ),
        reference='OpenINTEL + BGPKIT origin via IYP; cached dns_as_hosting.csv',
    )

    save_multi_plotly_html(
        [sun, bar, pie], 'step14_dns_hosting.html',
        step_num=STEP, title_zh=TITLE_ZH, title_en=TITLE_EN, source='cached CSV',
        writeup_html=w,
        subtitles=['1. 全球托管分布 Sunburst', '2. Top-20 CN 托管 AS',
                   '3. Cloud vs ISP 分布'],
    )


if __name__ == '__main__':
    main()
