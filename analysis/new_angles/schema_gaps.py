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
        'id': 'G3', 'name': 'AWS GeoPrefix 所有者（部分解决 in 2026-04）',
        'path': '(:AS)-[:ORIGINATE]->(:BGPPrefix) ⋈ '
                '(:GeoPrefix)-[:CATEGORIZED]->(:Tag {AMAZON/EC2/S3/...})',
        'finding': 'GeoPrefix 和 BGPPrefix 是不同节点（前者是 amazon.aws_ip_'
                   'ranges 注册的地理前缀，后者是真实观测的 BGP 前缀）。'
                   'AS 不直接 ORIGINATE GeoPrefix——要按 prefix 字符串 join '
                   '两边。2026-04-08 dump：AWS GeoPrefix 15,384 条，'
                   'prefix-string join 后得 55 条 AS-service 映射',
        'finding_en': 'GeoPrefix and BGPPrefix are distinct nodes '
                      '(the former is registered by amazon.aws_ip_ranges, '
                      'the latter is observed BGP). AS does not ORIGINATE '
                      'GeoPrefix directly — must join by prefix string. '
                      'After fix: 55 AS-service mappings from 2026-04-08',
        'topics': ['topic5', 'topic6'],
        'snapshots': 'partial fix in 2026-04-08 (small yield)',
        'severity': 'Low',
        'workaround': 'hyperscaler_originators.csv 现有 55 行可用；'
                      '如需更全面覆盖，需 IYP 补 IPv6 AWS 前缀 crawler',
        'upstream': 'amazon.aws_ip_ranges 本身只管 v4；IPv6 AWS 覆盖待补',
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
        'id': 'G5', 'name': 'PeeringDB 组织记录 schema（已解决）',
        'path': '(:Organization)-[:EXTERNAL_ID]->(:PeeringdbOrgID)',
        'finding': '原查询用 <code>(o:OpaqueID)</code> 作为目标节点标签返回 0 行。'
                   '2026-04-08 dump probe 确认目标标签是 '
                   '<code>PeeringdbOrgID</code>；修正后得 33,366 行组织记录'
                   '（含 policy_general / info_type / info_traffic）',
        'finding_en': 'Query used (o:OpaqueID) which returned 0. '
                      'Probe against 2026-04-08 confirmed the destination '
                      'label is :PeeringdbOrgID — fixed query yields 33,366 '
                      'org records with policy / info attributes',
        'topics': ['topic8'],
        'snapshots': 'resolved in 2026-04-08 (extract_data.py v3)',
        'severity': 'Low (resolved)',
        'workaround': '分析查询已修正；peeringdb_orgs.csv 可用',
        'upstream': '无需改 crawler；是分析端查询的 label 名错',
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
        'id': 'G7', 'name': 'IANA / NRO 分配节点（已解决）',
        'path': '(:RIRPrefix)-[:COUNTRY]->(:Country) via nro.delegated_stats',
        'finding': '原查询用 <code>[:ASSIGNED]->(:Country)</code> 返回 0 行——'
                   'ASSIGNED 边实际指向 <code>:OpaqueID</code>（AS 注册号），'
                   '国家归属走 <code>[:COUNTRY]</code> 边。2026-04-08 dump 有 '
                   '649,631 条 RIRPrefix→Country 关系，352 个 IANAPrefix 节点',
        'finding_en': 'Query used [:ASSIGNED]->(:Country) returning 0. '
                      '[:ASSIGNED] actually goes to :OpaqueID (AS IDs); '
                      'country mapping is on [:COUNTRY] edge. 2026-04-08 '
                      'dump has 649,631 RIRPrefix→Country edges + 352 '
                      'IANAPrefix nodes',
        'topics': ['topic11'],
        'snapshots': 'resolved in 2026-04-08 (extract_data.py v3)',
        'severity': 'Low (resolved)',
        'workaround': '分析查询已修正；nro_country_prefixes.csv 可用',
        'upstream': '无需改 crawler；是分析端走错了关系类型',
    },
    {
        'id': 'G8', 'name': 'Per-Prefix RPKI Valid Tag',
        'path': '(:Prefix)-[:CATEGORIZED]->(:Tag {label:"RPKI Valid"})',
        'finding': '3/11 dumps 的 Prefix 节点上 RPKI Valid tag 不存在——'
                   '全量时序扫描确认：2024-07 / 2025-01 / 2025-07 三个快照，'
                   '<code>rpki_per_as.csv</code> 有 85K 行但 <code>rpki</code> '
                   '列全 0。其余 8 个快照有真 RPKI 数据',
        'finding_en': '3/11 dumps missing RPKI Valid tag on Prefix nodes. '
                      'Full time-series scan confirms 2024-07, 2025-01, '
                      '2025-07. rpki_per_as.csv has 85K rows but rpki '
                      'column is all 0 in those 3 snapshots',
        'topics': ['evolution', 'evolution_timeseries', 'step04_prefix'],
        'snapshots': '2024-07, 2025-01, 2025-07 (3 of 11)',
        'severity': 'Medium',
        'workaround': 'evolution 页自动检测整列为 0 → 留白不插值',
        'upstream': 'RPKI 前缀标签 crawler 在那 3 个 cycle 没跑完整',
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
        'id': 'G11', 'name': 'Cloudflare DNS 层 — 间歇性缺失（已纠正）',
        'path': '(:DomainName)-[:QUERIED_FROM]->(:Country|:AS)',
        'finding': '原先误判为"整个管道从未运行 CF DNS"，全时序扫描后纠正：'
                   'QUERIED_FROM 关系在 9/11 个季度 dump 里正常存在（'
                   '每次 50K country + 100K AS 行）。仅 2025-01 和 2026-04 '
                   '两次 snapshot 完全空——后者恰好是我最初测试的 dump，'
                   '所以被误以为永久缺失。实为 2 次点状 regression',
        'finding_en': 'Earlier classified as "pipeline never populates CF "'
                      'DNS". Full time-series scan corrected: QUERIED_FROM '
                      'works in 9/11 quarterly dumps (50K country + 100K '
                      'AS rows each). Only 2025-01 and 2026-04 are empty '
                      '— the latter happened to be my first test dump, '
                      'producing the incorrect "always missing" story. '
                      'Actually 2 isolated regressions',
        'topics': ['topic18 (CRUX-only fallback no longer needed for most '
                   'snapshots)'],
        'snapshots': '2/11 missing: 2025-01 + 2026-04',
        'severity': 'Low (mostly populated)',
        'workaround': 'topic18 可改用 QUERIED_FROM，仅对 2025-01/2026-04 '
                      '回退到 CRUX',
        'upstream': '2 次 crawler 执行失败；原因未查（可能 API 限速或 '
                    '那两次 cycle 配置问题）',
    },
    {
        'id': 'G12', 'name': 'UTwente LACES GeoPrefix（完全解决 in 2026-04）',
        'path': '(:GeoPrefix)-[:LOCATED_IN]->(:Point); '
                '(:GeoPrefix)-[:COUNTRY]->(:Country)',
        'finding': '2026-04 dump 里 LACES 提供 500K GeoPrefix-Country 边'
                   '（7,814 distinct prefix，7,807 多国 = anycast）。'
                   'Point 节点的坐标以 <code>position</code> WGS84Point 属性'
                   '存储（不是 <code>lat</code>/<code>lng</code> 分列）——'
                   '查询改用 <code>p.position.y</code> / <code>p.position.x</code>'
                   '后拿到真实经纬度，可以做 PoP 地图',
        'finding_en': '2026-04 dump: 500K GeoPrefix-Country edges (7,814 '
                      'prefixes, 7,807 multi-country anycast). Point '
                      'coordinates stored as a single `position` WGS84Point '
                      'property (not lat/lng columns); query now uses '
                      'p.position.y / p.position.x and gets real coords',
        'topics': ['topic20'],
        'snapshots': 'fully resolved in 2026-04-08 (extract_data.py v3)',
        'severity': 'Low (resolved)',
        'workaround': '分析查询已修正；laces_geoprefix_countries.csv 有真 lat/lng',
        'upstream': '无；Point schema 本身正确，仅分析端属性名错',
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
        'id': 'G14', 'name': 'PCH 路由快照 regression 起点（已定位）',
        'path': '(:AS)-[:ORIGINATE]->(:Prefix) WHERE source=pch.*',
        'finding': '全时序扫描定位 regression 精确起点：'
                   'pch.daily_routing_snapshots 在 2024-01 → 2025-10 '
                   '(8 个季度) 里每次提供 500K ORIGINATE 边，'
                   '<b>从 2026-01 snapshot 开始连续 3 次 (2026-01/02/04) '
                   '全部为 0</b>。不是 2026-04 单点失败，是 2026 Q1 '
                   '起的持续 regression',
        'finding_en': 'Full time-series scan identifies the exact '
                      'regression boundary: PCH crawler populated 500K '
                      'edges consistently from 2024-01 through 2025-10 '
                      '(8 quarters), then went to 0 in 2026-01 and has '
                      'stayed missing through 2026-04 (3 consecutive '
                      'missing snapshots). Not a one-off failure',
        'topics': ['topic17 (rewired to bgpkit.peerstats)'],
        'snapshots': '8/11 have data (2024-01..2025-10); '
                     '3/11 missing (2026-01/02/04)',
        'severity': 'Medium (persistent)',
        'workaround': 'topic17 重写用 bgpkit peerstats 作功能等价——'
                      '改测"per-AS peer-edge count 在 v4/v6 里分别多少"，'
                      '同样反映观测冗余度但粒度从 prefix 变为 edge',
        'upstream': 'pch.daily_routing_snapshots_v4/v6 crawler 需定位为何 '
                    '2026 Q1 起不再运行；修好后可补充 per-prefix 视角',
    },
    {
        'id': 'G15', 'name': '2024-07 dump 的 AS-COUNTRY 断层（新发现）',
        'path': '(:AS)-[:COUNTRY]->(:Country)',
        'finding': '全时序扫描发现：2024-07-08 dump 仅 242K AS 有 '
                   'COUNTRY 边（其它 snapshot 360K-380K 稳定）。其余'
                   'crawler 输出（peeringdb/rpki/atlas/ixp）量级正常，'
                   '只有 COUNTRY 关系掉了 33%。前 5 大国（US/BR/RU/IN/CN）'
                   '的 AS 数都按同样比例缩小——是该国 COUNTRY 边 crawler '
                   '部分失败',
        'finding_en': '2024-07-08 dump has only 242K AS with COUNTRY '
                      'edges (vs 360-380K stable elsewhere). Other '
                      'crawlers (peeringdb/rpki/atlas/ixp) normal; only '
                      'COUNTRY relation dropped 33% uniformly across top '
                      '5 countries. COUNTRY-edge crawler partially failed',
        'topics': ['any topic that joins on AS→Country'],
        'snapshots': '1/11 affected: 2024-07-08',
        'severity': 'Medium',
        'workaround': 'evolution_timeseries Panel ① 显示为小凹点；'
                      '下游 topic 用 as_country 映射时 2024-07 会丢 1/3 数据',
        'upstream': 'COUNTRY crawler 在 2024-07 cycle 为何只跑了 2/3 '
                    '需回溯',
    },
    {
        'id': 'G16', 'name': '新 crawler 上线时间线（情报）',
        'path': '多个 crawler 首次出现',
        'finding': '全时序扫描确定每个 crawler 进入 IYP 的季度：'
                   'ixp_live_members (alice_lg) 首现 2024-04；'
                   'ooni.* 2024-10；crux_top1m_country 2025-04；'
                   'nro.delegated_stats COUNTRY 关系 2025-04；'
                   'utwente.laces_v4/v6 2026-01；amazon.aws_ip_ranges '
                   '2026-02。manrs 从未出现',
        'finding_en': 'Full scan pinned down first-appearance quarter: '
                      'alice_lg 2024-04; OONI 2024-10; CRUX 2025-04; '
                      'NRO COUNTRY 2025-04; LACES 2026-01; AWS IP ranges '
                      '2026-02. MANRS never',
        'topics': ['evolution_timeseries Panel ⑧'],
        'snapshots': 'all 11 (as timeline)',
        'severity': 'Low (informational)',
        'workaround': 'Panel ⑧ 直接可视化；topic 脚本须容忍某些 snapshot '
                      '没有该源',
        'upstream': '此为 IYP 项目能力增长记录，不是 gap',
    },
]


SEVERITY_COLOR = {
    'Low': COLORS['cyan'], 'Medium': COLORS['orange'], 'High': COLORS['red'],
    'Low (resolved)': COLORS['green'],
    'Low (mostly populated)': COLORS['green'],
    'Low (informational)': COLORS['cyan'],
    'Medium (persistent)': COLORS['orange'],
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
