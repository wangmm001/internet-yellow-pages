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
        'id': 'G11', 'name': 'Cloudflare DNS + Google CRUX 层缺失',
        'path': '(:DomainName)-[:DNS_ACTIVITY]->(:Country|:AS); '
                '(:HostName)-[:RANK]->(:Ranking {name:"CrUX*"})',
        'finding': 'cloudflare.dns_top_locations / dns_top_ases / '
                   'google.crux_top1m_country 查询均返回 0 行——'
                   '2024-10 dump 里这些 crawler 未运行或 reference_name '
                   '过滤不匹配',
        'finding_en': 'Cloudflare DNS + Google CRUX crawlers returned '
                      '0 rows — not run in 2024-10 dump, or reference_name '
                      'filter mismatch',
        'topics': ['topic18 (placeholder)'],
        'snapshots': '2024-10 (tested)',
        'severity': 'Medium',
        'workaround': 'topic18 降级为 placeholder + banner；2026-04 dump '
                      '可能已补充（size 19.8GB 对 2024-10 的 4.5GB）',
        'upstream': '需要确认 config.json 里这些 crawler 在 2024-10 pipeline '
                    '实际运行了；或 reference_name 字段格式有变',
    },
    {
        'id': 'G12', 'name': 'UTwente LACES GeoPrefix 层缺失',
        'path': '(:GeoPrefix)-[:LOCATED_IN]->(:Point); '
                '(:GeoPrefix)-[:COUNTRY]->(:Country)',
        'finding': 'utwente.laces_v4/v6 crawler 未暴露 GeoPrefix-Point 关系',
        'finding_en': 'utwente LACES crawler did not expose GeoPrefix-Point '
                      'relations in 2024-10',
        'topics': ['topic20 (placeholder)'],
        'snapshots': '2024-10 (tested)',
        'severity': 'Medium',
        'workaround': 'topic20 降级；bgptools.anycast tag 仍可提供 '
                      '"是否 anycast" 但无 PoP 位置',
        'upstream': 'laces crawler 需要重跑或节点 label 对齐',
    },
    {
        'id': 'G13', 'name': 'DNS 权威三源全缺（forward / reverse / root）',
        'path': '(:DomainName)-[:MANAGED_BY]->(:HostName) '
                '× infra_ns / rirdata_rdns / iana.root_zone',
        'finding': 'openintel.infra_ns / simulamet.rirdata_rdns / '
                   'iana.root_zone 查询都返回 0 行；RDNSPrefix label 也不存在',
        'finding_en': 'infra_ns / rirdata_rdns / iana.root_zone all 0 rows; '
                      'RDNSPrefix label absent in dump',
        'topics': ['topic21 (placeholder)'],
        'snapshots': '2024-10 (tested)',
        'severity': 'Medium',
        'workaround': 'topic21 降级；topic14 的 dns_authority_top500 依旧'
                      '给出 operator 视角',
        'upstream': '多个 openintel/simulamet/iana crawler 需重跑',
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
