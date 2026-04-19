"""Schema-gap consolidation report.

Built during 15-topic + evolution work, every dashboard flagged some
upstream IYP schema mismatch that forced a workaround. This page
collects them into one filing-ready list so an upstream issue can be
opened with all the context in one place.

Output: analysis/new_angles/html/schema_gaps.html
Site mirror: analysis/countries/html/schema_gaps.html
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.china.common import (  # noqa: E402
    BANNER_CSS, COLORS, TEXT_PRIMARY, TEXT_SECONDARY,
    apply_plotly_theme,
)

REPO = Path(__file__).resolve().parent.parent.parent
OUT = REPO / 'analysis' / 'new_angles' / 'html'
OUT.mkdir(parents=True, exist_ok=True)


GAPS = [
    {
        'id': 'G1', 'name': 'Worldbank Population 属性名',
        'path': '(:Country)-[:POPULATION]->(:Population)',
        'finding': 'crawler 把人口写在 `p.value`，分析代码长期读 `p.population`',
        'finding_en': 'crawler writes to p.value; analysis read p.population',
        'topics': ['topic1', 'synthesis', 'evolution'],
        'snapshots': 'all 10',
        'severity': 'Low',
        'workaround': '静态 2024 fallback dict 覆盖 9 国',
        'upstream': 'crawler 文档未声明属性名，建议标准化',
    },
    {
        'id': 'G2', 'name': 'MANRS IMPLEMENT 关系缺失',
        'path': '(:AS)-[:IMPLEMENT]->(:Tag {label:"MANRS"})',
        'finding': '2024-10 dump 上 MANRS 维度空；安全叙事只能用 RPKI+ROV',
        'finding_en': 'MANRS dimension empty; security narrative falls back '
                      'to RPKI+ROV only',
        'topics': ['topic2'],
        'snapshots': '2024-10',
        'severity': 'Medium',
        'workaround': 'banner 声明；降级为二维视图',
        'upstream': 'MANRS crawler 可能失败或节点缺失',
    },
    {
        'id': 'G3', 'name': 'AWS GeoPrefix 地理分桶',
        'path': '(:AS {asn:16509})-[:ORIGINATE]->(:GeoPrefix)',
        'finding': '无 AWS 地域细分前缀数据',
        'finding_en': 'no geo-bucketed prefix data for hyperscalers',
        'topics': ['topic5', 'topic6'],
        'snapshots': 'all',
        'severity': 'Medium',
        'workaround': 'bgptools.as_names 角色标签替代 (content/CDN 分类)',
        'upstream': '需要 hyperscaler-geo crawler',
    },
    {
        'id': 'G4', 'name': 'OONI country_code 边属性空',
        'path': '(:AS)-[:CENSORED {country_code:?}]->(:DomainName)',
        'finding': '所有 11,804 条 CENSORED 边的 country_code 属性为空字符串',
        'finding_en': 'country_code edge property empty in all 11,804 rows',
        'topics': ['topic7'],
        'snapshots': 'all',
        'severity': 'High',
        'workaround': '用 as_country.csv 从 AS 反查国家',
        'upstream': 'OONI crawler 没写入 country_code；问题详见 '
                    'topic 7 note',
    },
    {
        'id': 'G5', 'name': 'PeeringDB 组织记录 schema',
        'path': '(:Organization)-[:EXTERNAL_ID]->(:PeeringDBID)',
        'finding': 'EXTERNAL_ID 边的属性 key 对不上，查询返回 0 行',
        'finding_en': 'EXTERNAL_ID edge property keys mismatch, 0 rows',
        'topics': ['topic8'],
        'snapshots': 'all',
        'severity': 'High',
        'workaround': '替换为 ROVISTA-by-country 视角',
        'upstream': 'peeringdb crawler 的边属性命名需对齐',
    },
    {
        'id': 'G6', 'name': 'Atlas Probe 标签',
        'path': '(:AtlasProbe)-[:HAS_TAG]->(:Tag)',
        'finding': 'atlas_probes crawler schema 不暴露 tags；只剩地理位置',
        'finding_en': 'atlas_probes schema does not expose tags, '
                      'geography only',
        'topics': ['topic9'],
        'snapshots': '2024-10',
        'severity': 'Medium',
        'workaround': '降级为纯地理覆盖分析',
        'upstream': 'atlas crawler 需要补 tag relationship 抽取',
    },
    {
        'id': 'G7', 'name': 'IANA / NRO 分配节点',
        'path': '(:NROStatistic)-[:ALLOCATED]->(:Prefix)',
        'finding': 'IANA/NRO 分配图缺失，无法做"分配 vs 实际使用"对照',
        'finding_en': 'no IANA/NRO allocation map; cannot compare '
                      'allocated vs observed',
        'topics': ['topic11'],
        'snapshots': 'all',
        'severity': 'Medium',
        'workaround': '替换为 as_organization 所有权集中度分析',
        'upstream': 'NRO crawler 未运行或未建模',
    },
    {
        'id': 'G8', 'name': 'Per-Prefix RPKI Valid Tag',
        'path': '(:Prefix)-[:CATEGORIZED]->(:Tag {label:"RPKI Valid"})',
        'finding': '2024-07 / 2025-01 dumps 在 Prefix 节点上只挂 Anycast tag；'
                   'AS 级 Validating RPKI ROV 仍在但不同粒度。probe 确认',
        'finding_en': '2024-07/2025-01 dumps have only Anycast tag on '
                      'Prefix nodes; AS-level Validating RPKI ROV still '
                      'present. Probe-confirmed',
        'topics': ['evolution', 'step04_prefix'],
        'snapshots': '2024-07, 2025-01',
        'severity': 'Medium',
        'workaround': 'evolution 页自动检测整列为 0 → 留白不插值',
        'upstream': 'RPKI 前缀标签 crawler 在那两个 cycle 没跑完整',
    },
    {
        'id': 'G9', 'name': 'BGPPrefix vs Prefix 标签命名',
        'path': '(pfx:BGPPrefix|Prefix)',
        'finding': '老 dump 用 `Prefix`，新 dump 用 `BGPPrefix`；同一查询在两个'
                   'schema 下行为不同',
        'finding_en': 'older dumps use :Prefix, newer use :BGPPrefix; '
                      'same query differs in behavior',
        'topics': ['step_lib step04'],
        'snapshots': '2024-*',
        'severity': 'Low',
        'workaround': 'step04 里 try BGPPrefix fallback to Prefix',
        'upstream': 'IYP 应声明 label rename 为破坏性变更',
    },
    {
        'id': 'G10', 'name': '多层非时间递增（sticky layers）',
        'path': 'AS / Peering / IXP_MEMBER / IHR_DEPENDS_ON',
        'finding': '2024-01 到 2025-01 五个快照里 AS 清册 / peering / IXP 成员'
                   ' / hegemony 依赖图的数字完全相同；2025-07/10/2026-01 同样'
                   '一致。本质是 IYP 老 dump 对这些 crawler 层没按季度重建',
        'finding_en': 'AS inventory / peering / IXP / hegemony edges are '
                      'identical across 5-6 consecutive quarterly dumps. '
                      'These crawler layers are not re-run per quarter in '
                      'the archival dumps',
        'topics': ['evolution'],
        'snapshots': 'all 10 (5 early + 3 mid clustered)',
        'severity': 'High',
        'workaround': 'evolution 页只画真正逐快照变化的 BGP 层；'
                      '提示 reader 不要把其他指标当时间序列',
        'upstream': 'IYP archive 需要对所有层按季度重 crawl，或明确声明'
                    '哪些层是"latest-only"',
    },
    {
        'id': 'G11', 'name': 'Cloudflare DNS 层缺失（确认）',
        'path': '(:DomainName)-[:QUERIED_FROM]->(:Country|:AS) — 关系不存在',
        'finding': 'cloudflare.dns_top_locations / dns_top_ases 在 '
                   '2024-10 和 2026-04 两次 dump 里均完全缺失。Probe 确认 '
                   'QUERIED_FROM / DNS_ACTIVITY 关系类型都不存在。'
                   'crawler 在 config.json 里被列出但未运行',
        'finding_en': 'Cloudflare DNS crawlers totally absent in both '
                      '2024-10 and 2026-04 dumps. Probe confirmed neither '
                      'QUERIED_FROM nor DNS_ACTIVITY relationship types '
                      'exist. Listed in config.json but not actually run',
        'topics': ['topic18 (CRUX-only fallback)'],
        'snapshots': '2024-10 + 2026-04 confirmed',
        'severity': 'Medium',
        'workaround': 'topic18 改用 google.crux_top1m_country 作为'
                      '需求侧信号（200K rows 可用）',
        'upstream': '需要 IYP 真正运行 cloudflare.dns_top_* crawlers；'
                    '可能是 API key 或限速问题',
    },
    {
        'id': 'G12', 'name': 'UTwente LACES GeoPrefix（已解决 in 2026-04）',
        'path': '(:GeoPrefix)-[:LOCATED_IN]->(:Point); '
                '(:GeoPrefix)-[:COUNTRY]->(:Country)',
        'finding': '2026-04 dump 里 LACES 提供 500K GeoPrefix-Country 边'
                   '（7,814 distinct prefix）。其中 7,807 在多国分布，'
                   '即 anycast。但 lat/lng 在 Point 节点为 NULL，'
                   '只能国家级粒度',
        'finding_en': '2026-04 dump exposes 500K GeoPrefix-Country '
                      'edges (7,814 distinct, 7,807 multi-country = '
                      'anycast). But Point nodes have NULL lat/lng — '
                      'only country-level granularity',
        'topics': ['topic20'],
        'snapshots': 'fixed in 2026-04; absent in 2024-10',
        'severity': 'Low',
        'workaround': 'topic20 推断 anycast 通过 multi-country 而非 '
                      'CATEGORIZED→Tag (Anycast tag 不挂在 GeoPrefix)',
        'upstream': '可选：补充 Point.lat/lng 属性以实现 PoP 地图',
    },
    {
        'id': 'G13', 'name': 'DNS 权威三源（已大部分解决 in 2026-04）',
        'path': '(:DomainName)-[:MANAGED_BY]->(:HostName) '
                '× openintel.dnsgraph / simulamet.rirdata_rdns / iana.root_zone',
        'finding': '2026-04 dump 里 MANAGED_BY 关系正常工作：forward via '
                   'openintel.dnsgraph (28M edges) + openintel.toplist (21M); '
                   'reverse via simulamet.rirdata_rdns (3.5M); root via '
                   'iana.root_zone (5K)。'
                   '注意：openintel.infra_ns 文档说只产生 RESOLVES_TO/'
                   'ALIAS_OF，不产生 MANAGED_BY——之前的 query 用错关系',
        'finding_en': 'In 2026-04: MANAGED_BY works via dnsgraph (28M) + '
                      'toplist (21M) + rirdata_rdns (3.5M) + iana.root_zone '
                      '(5K). Note: openintel.infra_ns produces RESOLVES_TO/'
                      'ALIAS_OF only, NOT MANAGED_BY (per parent class doc)',
        'topics': ['topic21'],
        'snapshots': 'fixed in 2026-04 (with corrected query)',
        'severity': 'Low',
        'workaround': 'topic21 改用 dnsgraph 作 forward source；'
                      '原 infra_ns query 是文档错误',
        'upstream': '已解决；如需 infra_ns MANAGED_BY 须改 crawler',
    },
    {
        'id': 'G14', 'name': 'PCH 路由快照在 2026-04 缺失（regression）',
        'path': '(:AS)-[:ORIGINATE]->(:Prefix) WHERE source=pch.*',
        'finding': '2024-10 dump 里 pch.daily_routing_snapshots_v4/v6 '
                   '提供 500K ORIGINATE 边（含 collector count + '
                   'seen_by_collectors）。2026-04 dump probe 显示 '
                   'ORIGINATE 关系只有 bgpkit.pfx2asn (1.6M) 和 ihr.rov '
                   '(1.3M)——pch crawler 整个未运行',
        'finding_en': 'PCH crawler ran in 2024-10 (500K records) but did '
                      'NOT run in 2026-04 (probe shows ORIGINATE only has '
                      'bgpkit + ihr.rov). Regression',
        'topics': ['topic17 (rewired to bgpkit.peerstats)'],
        'snapshots': '2024-10 had data, 2026-04 missing',
        'severity': 'Medium',
        'workaround': 'topic17 重写用 bgpkit peerstats 作功能等价——'
                      '改测"per-AS peer-edge count 在 v4/v6 里分别多少"，'
                      '同样反映观测冗余度但粒度从 prefix 变为 edge',
        'upstream': 'pch.daily_routing_snapshots_v4/v6 crawler 需在 '
                    '2026-04 重新启用；修好后可补充 per-prefix 视角',
    },
]


SEVERITY_COLOR = {
    'Low': COLORS['cyan'], 'Medium': COLORS['orange'], 'High': COLORS['red'],
}


def build():
    import plotly.graph_objects as go
    from plotly.io import to_html

    # --- Panel 1: severity bar ---
    from collections import Counter
    sev = Counter(g['severity'] for g in GAPS)
    p1 = go.Figure()
    order = ['High', 'Medium', 'Low']
    p1.add_trace(go.Bar(
        x=order, y=[sev[s] for s in order],
        marker_color=[SEVERITY_COLOR[s] for s in order],
        text=[sev[s] for s in order], textposition='outside',
    ))
    p1.update_layout(
        title='按严重度分类 · Gap severity distribution',
        yaxis=dict(title='# gaps'), xaxis=dict(title=''),
        height=340, showlegend=False,
    )
    apply_plotly_theme(p1)

    parts = [to_html(p1, include_plotlyjs='inline',
                     full_html=False, default_height='340px')]

    # --- Table ---
    def sev_badge(s):
        return (f'<span style="background:{SEVERITY_COLOR[s]}22;'
                f'color:{SEVERITY_COLOR[s]};padding:2px 8px;'
                f'border-radius:6px;border:1px solid {SEVERITY_COLOR[s]}66;'
                f'font-size:11px">{s}</span>')

    rows_html = []
    for g in GAPS:
        topics = ', '.join(g['topics'])
        rows_html.append(
            f'<tr>'
            f'<td style="color:{TEXT_SECONDARY};white-space:nowrap">{g["id"]}</td>'
            f'<td><b>{g["name"]}</b>'
            f'<br><code style="color:{COLORS["cyan"]};font-size:11px">'
            f'{g["path"]}</code></td>'
            f'<td style="font-size:12px">{g["finding"]}'
            f'<br><i style="color:{TEXT_SECONDARY}">{g["finding_en"]}</i></td>'
            f'<td style="white-space:nowrap;color:{TEXT_SECONDARY};'
            f'font-size:12px">{topics}</td>'
            f'<td style="white-space:nowrap;font-size:12px;'
            f'color:{TEXT_SECONDARY}">{g["snapshots"]}</td>'
            f'<td>{sev_badge(g["severity"])}</td>'
            f'<td style="font-size:12px">{g["workaround"]}</td>'
            f'<td style="font-size:12px;color:{TEXT_SECONDARY}">'
            f'{g["upstream"]}</td>'
            f'</tr>'
        )
    table_html = (
        f'<table style="width:100%;border-collapse:collapse;'
        f'margin:24px 0;font-size:13px;color:{TEXT_PRIMARY}">'
        f'<thead><tr style="border-bottom:2px solid {COLORS["cyan"]};'
        f'color:{COLORS["cyan"]}">'
        f'<th style="text-align:left;padding:10px 8px">ID</th>'
        f'<th style="text-align:left;padding:10px 8px">Gap · Cypher path</th>'
        f'<th style="text-align:left;padding:10px 8px">Finding</th>'
        f'<th style="text-align:left;padding:10px 8px">Topics</th>'
        f'<th style="text-align:left;padding:10px 8px">Snapshots</th>'
        f'<th style="text-align:left;padding:10px 8px">Sev</th>'
        f'<th style="text-align:left;padding:10px 8px">Workaround</th>'
        f'<th style="text-align:left;padding:10px 8px">Upstream action</th>'
        f'</tr></thead><tbody>'
        + ''.join(f'<tr style="border-bottom:1px solid rgba(255,255,255,0.05)'
                  f';vertical-align:top">{r[4:]}'
                  for r in rows_html)
        + '</tbody></table>'
    )

    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>意图：</b>记录 IYP 2024-01 → 2026-04 期间在 15-topic + '
        f'evolution 分析里发现的所有 upstream schema 不一致 / 缺失，供'
        f'向 IYP 项目提 issue 或 PR 参考。每条都列出具体 Cypher 路径、'
        f'受影响的 topic 与 snapshot、本页采用的 workaround。'
        f'<br><b>当前状态：</b>共 <b>{len(GAPS)}</b> 个 gap'
        f'（High {sev["High"]} · Medium {sev["Medium"]} · Low {sev["Low"]}），'
        f'已全部 workaround；upstream 修复后相应 topic 的 banner 会自动消失。'
        f'</p>'
    )

    banner = (
        '<div class="step-banner">'
        '<h1>上游 Schema 缺口清单 · IYP Upstream Schema Gap Report</h1>'
        '<h2>10 gaps discovered across 15 topics + evolution work · '
        'filing-ready reference for upstream IYP issue</h2>'
        '</div>'
        '<div class="step-footer">schema_gaps · reference · '
        'update on upstream fix</div>'
    )

    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>上游 Schema 缺口清单 · Upstream Schema Gap Report</title>'
        f'{BANNER_CSS}</head><body>'
        f'{banner}<div class="content">{intro}{"".join(parts)}{table_html}'
        '</div></body></html>'
    )
    out_path = OUT / 'schema_gaps.html'
    out_path.write_text(html, encoding='utf-8')
    mirror = REPO / 'analysis' / 'countries' / 'html' / 'schema_gaps.html'
    mirror.write_text(html, encoding='utf-8')
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    print(f'mirrored to {mirror}')
    print(f'severity: High={sev["High"]} Medium={sev["Medium"]} '
          f'Low={sev["Low"]}')


if __name__ == '__main__':
    build()
