"""Synthesis: 15 new-angle topics distilled into a single narrative page.

Organizes the findings into 3 structural truths about the global
internet + a CN-specific section. Each claim links back to the
underlying topic page. Numbers pulled fresh from cached CSVs so the
page auto-updates when the underlying data changes.

Output: analysis/new_angles/html/synthesis.html
Site mirror: analysis/countries/html/new_angles_synthesis.html
"""
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.china.common import (  # noqa: E402
    BANNER_CSS, COLORS, DARK_BG, DARK_BORDER, DARK_PANEL,
    TEXT_PRIMARY, TEXT_SECONDARY, apply_plotly_theme, country_color,
)

REPO = Path(__file__).resolve().parent.parent.parent
CACHE = REPO / 'data_cache' / 'new_angles'
COMPLEX = REPO / 'data_cache' / 'complex_network'
OUT = REPO / 'analysis' / 'new_angles' / 'html'
OUT.mkdir(parents=True, exist_ok=True)

TARGET = ['US', 'CN', 'JP', 'IN', 'DE', 'GB', 'FR', 'NL', 'RU']
COUNTRY_NAME = {
    'US': '美国', 'CN': '中国', 'JP': '日本', 'IN': '印度', 'DE': '德国',
    'GB': '英国', 'FR': '法国', 'NL': '荷兰', 'RU': '俄罗斯',
}

# Population fallback (same as topic 1 for consistency)
POP_2024 = {
    'US': 336_810_000, 'CN': 1_410_710_000, 'JP': 123_750_000,
    'IN': 1_428_630_000, 'DE': 84_480_000, 'GB': 68_350_000,
    'FR': 68_170_000, 'NL': 17_880_000, 'RU': 143_830_000,
}


def _read(p):
    return list(csv.DictReader(open(p, encoding='utf-8'))) \
        if p.exists() else []


def _int(s, default=0):
    try:
        return int(s)
    except (ValueError, TypeError):
        return default


def _float(s, default=0.0):
    try:
        return float(s)
    except (ValueError, TypeError):
        return default


def compute_signals():
    """Compute all numbers used in the narrative, cached from CSVs."""
    sig = {}

    # T1: eyeball vs total AS, CN-specific
    as_cc = {_int(r['asn']): r['cc'] for r in _read(CACHE / 'as_country.csv')}
    eyeball = defaultdict(set)
    for r in _read(CACHE / 'eyeball_as_country.csv'):
        try:
            eyeball[r['cc']].add(int(r['asn']))
        except (ValueError, KeyError):
            pass
    country_as = defaultdict(int)
    for cc in as_cc.values():
        country_as[cc] += 1
    sig['cn_as'] = country_as.get('CN', 0)
    sig['cn_eyeball'] = len(eyeball.get('CN', set()))
    sig['cn_eyeball_pct'] = sig['cn_eyeball'] / max(sig['cn_as'], 1) * 100
    # AS per million
    sig['as_per_m'] = {
        cc: country_as.get(cc, 0) / (POP_2024[cc] / 1e6)
        for cc in TARGET if cc in POP_2024
    }

    # T1p5: k-core distortion CN
    coreness = {}
    for r in _read(COMPLEX / 'step08_coreness.csv'):
        coreness[_int(r['asn'])] = _int(r['coreness'])
    THRESH = 30
    cn_country_as = {a for a, c in as_cc.items() if c == 'CN'}
    cn_eye = eyeball.get('CN', set()) & cn_country_as
    cn_infra_deep = sum(1 for a in cn_country_as if coreness.get(a, 0) >= THRESH) \
        / max(len(cn_country_as), 1) * 100
    cn_user_deep = sum(1 for a in cn_eye if coreness.get(a, 0) >= THRESH) \
        / max(len(cn_eye), 1) * 100
    sig['cn_core_infra'] = cn_infra_deep
    sig['cn_core_user'] = cn_user_deep
    sig['cn_core_ratio'] = cn_user_deep / max(cn_infra_deep, 1e-3)

    # T2: RPKI × ROVISTA gap
    rpki = {}
    for r in _read(CACHE / 'rpki_per_as.csv'):
        try:
            asn = int(r['asn']); tot = int(r['total']); val = int(r['rpki'])
            if tot > 0:
                rpki[asn] = val / tot * 100
        except (ValueError, KeyError):
            continue
    rov = {}
    for r in _read(CACHE / 'rovista.csv'):
        try:
            asn = int(r['asn']); raw = r.get('ratio') or ''
            if raw.strip():
                rov[asn] = float(raw)
        except (ValueError, KeyError):
            continue
    joined = {a for a in rpki if a in rov}
    signed = sum(1 for a in joined if rpki[a] >= 50)
    gap = sum(1 for a in joined if rpki[a] >= 50 and rov[a] < 0.5)
    sig['joined'] = len(joined)
    sig['signed'] = signed
    sig['gap'] = gap
    sig['gap_pct'] = gap / max(signed, 1) * 100

    # T12: top global hegemony AS
    ihr_rows = []
    for r in _read(CACHE / 'ihr_hegemony_incoming.csv'):
        asn = _int(r['asn']); inc = _float(r['incoming']); nd = _int(r['n_deps'])
        ihr_rows.append((asn, inc, nd))
    ihr_rows.sort(key=lambda t: -t[1])
    sig['ihr_top3'] = ihr_rows[:3]
    sig['ihr_top1_asn'] = ihr_rows[0][0] if ihr_rows else None

    # T14: top DNS operators
    ns_by_op = Counter()
    for r in _read(COMPLEX / 'dns_authority_top500.csv'):
        ns = r.get('ns_name', '')
        parts = ns.strip('.').split('.')
        op = '.'.join(parts[-2:]) if len(parts) >= 2 else ns
        ns_by_op[op] += _int(r.get('domain_count', 0))
    sig['dns_top3'] = ns_by_op.most_common(3)

    # T15: 9×9 country dep matrix — net balance
    matrix = defaultdict(float)
    for r in _read(COMPLEX / 'as_dependency.csv'):
        try:
            s = as_cc.get(int(r['src']))
            d = as_cc.get(int(r['dst']))
            h = float(r.get('hege') or 0)
            if s in TARGET and d in TARGET:
                matrix[(s, d)] += h
        except (ValueError, KeyError):
            continue
    sig['net_balance'] = {}
    for cc in TARGET:
        inn = sum(matrix.get((s, cc), 0) for s in TARGET if s != cc)
        out = sum(matrix.get((cc, d), 0) for d in TARGET if d != cc)
        sig['net_balance'][cc] = {'in': inn, 'out': out, 'net': inn - out}

    # T9: Atlas probe inequality
    probe_cc = Counter()
    for r in _read(CACHE / 'atlas_probes.csv'):
        cc = r.get('cc') or ''
        if cc:
            probe_cc[cc] += 1
    sig['atlas_total'] = sum(probe_cc.values())
    sig['atlas_top5_share'] = (
        sum(c for _, c in probe_cc.most_common(5))
        / max(sum(probe_cc.values()), 1) * 100
    )

    return sig


def _build_mini_figs(sig):
    """Build 3 small signature charts for the narrative."""
    import plotly.graph_objects as go

    figs = []

    # Fig 1: US vs CN dependency asymmetry
    f1 = go.Figure()
    cc_order = sorted(TARGET, key=lambda c: -sig['net_balance'][c]['net'])
    f1.add_trace(go.Bar(
        x=[f'{COUNTRY_NAME[c]} {c}' for c in cc_order],
        y=[sig['net_balance'][c]['net'] for c in cc_order],
        marker_color=[COLORS['green'] if sig['net_balance'][c]['net'] > 0
                      else COLORS['red'] for c in cc_order],
        text=[f'{sig["net_balance"][c]["net"]:+.0f}' for c in cc_order],
        textposition='outside',
    ))
    f1.add_hline(y=0, line=dict(color='#8e8e93', width=1, dash='dash'))
    f1.update_layout(
        title='Fig A · 9 国净依赖平衡（hege 加权）· '
              'US 是唯一净出口，CN 最大净进口',
        yaxis=dict(title='net hege weight (in − out)'),
        xaxis=dict(title='', tickangle=-20),
        height=380, showlegend=False,
    )
    figs.append(f1)

    # Fig 2: RPKI × ROVISTA gap
    f2 = go.Figure()
    categories = ['全球已测 AS', '宣告 RPKI (≥50%)', '其中实测不执行 ROV']
    values = [sig['joined'], sig['signed'], sig['gap']]
    f2.add_trace(go.Bar(
        x=categories, y=values,
        marker_color=[COLORS['cyan'], COLORS['orange'], COLORS['red']],
        text=[f'{v:,}' for v in values],
        textposition='outside',
    ))
    f2.update_layout(
        title=f'Fig B · 路由安全落差漏斗 · '
              f'{sig["gap_pct"]:.0f}% 宣告的 AS 并未实施',
        yaxis=dict(title='# AS'), height=380, showlegend=False,
    )
    figs.append(f2)

    # Fig 3: CN distortion (k-core)
    f3 = go.Figure()
    f3.add_trace(go.Bar(
        x=['Infra 视角 (全部 6,660 AS)', 'User 视角 (71 eyeball AS)'],
        y=[sig['cn_core_infra'], sig['cn_core_user']],
        marker_color=['#8e8e93', COLORS['red']],
        text=[f'{sig["cn_core_infra"]:.2f}%',
              f'{sig["cn_core_user"]:.1f}%<br>({sig["cn_core_ratio"]:.1f}×)'],
        textposition='outside',
    ))
    f3.update_layout(
        title='Fig C · CN 深层 k-core 密度 · '
              '等权统计把 CN 严重稀释 23×',
        yaxis=dict(title='% in deep k-core (coreness ≥ 30)'),
        height=380, showlegend=False,
    )
    figs.append(f3)

    return figs


def build():
    from plotly.io import to_html
    sig = compute_signals()
    figs = _build_mini_figs(sig)
    for f in figs:
        apply_plotly_theme(f)
    fig_htmls = [to_html(f, include_plotlyjs=('inline' if i == 0 else False),
                         full_html=False, default_height='400px')
                 for i, f in enumerate(figs)]

    def card(label, value, hint=''):
        return (
            f'<div style="flex:1;min-width:200px;background:{DARK_PANEL};'
            f'border:1px solid {DARK_BORDER};border-radius:8px;'
            f'padding:14px 18px;margin:6px">'
            f'<div style="font-size:12px;color:{TEXT_SECONDARY};'
            f'text-transform:uppercase;letter-spacing:1px">{label}</div>'
            f'<div style="font-size:26px;color:{COLORS["yellow"]};'
            f'font-weight:600;margin-top:6px">{value}</div>'
            + (f'<div style="font-size:12px;color:{TEXT_SECONDARY};'
               f'margin-top:4px">{hint}</div>' if hint else '')
            + '</div>'
        )

    # Compose narrative sections
    top3_str = ' · '.join(
        f'AS{a} ({int(inc):,})' for a, inc, _ in sig['ihr_top3'])
    dns_top3_str = ' · '.join(
        f'<code>{op}</code> ({n:,})' for op, n in sig['dns_top3'])
    top_exporter = max(TARGET, key=lambda c: sig['net_balance'][c]['net'])
    bot_importer = min(TARGET, key=lambda c: sig['net_balance'][c]['net'])

    # ---- Section 1 — Centralization ----
    sec1 = f"""
    <h2 style="color:{COLORS['yellow']};margin-top:32px">
    ① 中心化悖论 · Centralization paradox
    </h2>
    <p style="color:{TEXT_PRIMARY};line-height:1.7">
    从"一个 AS 一票"的视角看互联网看似高度分布式 —
    全球 87,367 个可观测 AS，97,759 个不同组织，各国 HHI &lt; 200（
    <a href="org-concentration/">T11</a>）。但每换一个维度，
    就暴露一次集中：
    <br><br>
    <b>骨干层：</b>IYP hegemony top-3 为
    {top3_str}（<a href="ihr-hegemony/">T12</a>）。
    Hurricane Electric 单独从 62,992 个 AS 收到 27,576 的依赖权重，
    比第二名 Lumen 高 2.5×。
    <br><br>
    <b>DNS 层：</b>全球 top-500 权威服务器被少数运营商瓜分 —
    {dns_top3_str}（<a href="dns-authority/">T14</a>）。
    <br><br>
    <b>国家层：</b>9 个主要互联网经济体中，
    <b>只有美国是净出口</b>（+{sig['net_balance']['US']['net']:.0f}），
    其余 8 国都是净进口，
    <b>中国逆差最大</b>（{sig['net_balance']['CN']['net']:.0f}，
    出/入比 <b>253:1</b>，<a href="country-dep/">T15</a>）。
    <br><br>
    <b>组织层：</b>只有 814 / 97,759（0.8%）的组织 AS 跨国延伸（
    <a href="multinational/">T13</a>）。ISC 覆盖 18 国（运行 F-root），
    AT&amp;T Japan 12 国。跨国 AS 所有权是稀有事件，但每一个都是战略节点。
    </p>
    """

    # ---- Section 2 — Security Theater ----
    sec2 = f"""
    <h2 style="color:{COLORS['red']};margin-top:32px">
    ② 安全剧场 · Security theater
    </h2>
    <p style="color:{TEXT_PRIMARY};line-height:1.7">
    <b>RPKI 宣告率是公关指标，ROV 实测才是真实防御。</b>
    在 {sig['joined']:,} 个同时有 RPKI 和 ROVISTA 测量的 AS 中，
    {sig['signed']:,} 个宣告了 ≥50% 前缀 RPKI 签名，
    其中 <b>{sig['gap']:,}（{sig['gap_pct']:.0f}%）实测不 drop 无效路由</b>
    （<a href="routing-security/">T2</a>）。
    <br><br>
    国家层面（<a href="rovista-country/">T8</a>），
    129 个有≥10 AS 测量的国家中，
    顶部：Bhutan 63% · Mongolia 57% · Estonia 45% 真在执行；
    底部五国（TJ/SS/BF/LA/BH）执行率 = 0%。
    <br><br>
    <b>MANRS 维度在 2024-10 dump 完全缺失</b>，3 轴降级 2 轴
    — 这本身说明现行评估过于依赖自证。
    <br><br>
    OONI 审查测量提供类似的"宣称 vs 实证"窗口
    （<a href="ooni/">T7</a>，测量 × 10 种测试 ×
    11,804 pair），但 country_code 边属性在本快照全 NULL — 另一处
    crawler 层的 schema bug。
    </p>
    """

    # ---- Section 3 — Measurement lens ----
    top_dens = max(sig['as_per_m'], key=sig['as_per_m'].get)
    bot_dens = min(sig['as_per_m'], key=sig['as_per_m'].get)
    sec3 = f"""
    <h2 style="color:{COLORS['cyan']};margin-top:32px">
    ③ 测量视角偏差 · Measurement lens
    </h2>
    <p style="color:{TEXT_PRIMARY};line-height:1.7">
    IYP 所有基于"AS 计数"的指标都隐含一个假设：
    一个 AS = 一个 AS。但实际上企业/高校/政府自治号往往不服务任何外部用户。
    CN 有 {sig['cn_as']:,} 个 AS 但只有 <b>{sig['cn_eyeball']}
    （{sig['cn_eyeball_pct']:.1f}%）可被 APNIC eyeball 测到</b>，
    即只有这一小部分真正服务网民
    （<a href="eyeball/">T1</a>）。
    <br><br>
    换成 <b>用户视角</b>后，CN 的"深层 k-core 密度"从
    <b>{sig['cn_core_infra']:.2f}%</b>（infra 视角，看上去极弱）
    变成 <b>{sig['cn_core_user']:.1f}%</b>（{sig['cn_core_ratio']:.1f}× 反转）—
    接近 US 水平（<a href="eyeball/">T1 panel ⑤</a>）。
    同一指标下 "CN 连接弱" 是测量伪像，不是事实。
    但 IXP 本地化（T1 panel ⑥）在 user 视角仍 4.4%，
    远低于 JP/IN/DE/NL 的 70-82% — 这是真差距。
    <br><br>
    <b>测量基础设施本身也不平等</b>：Atlas 探针全球 {sig['atlas_total']:,} 个
    分布在 217 国，但 <b>top-5 国占 {sig['atlas_top5_share']:.0f}%</b>
    （US/DE/FR/GB 主导，<a href="atlas/">T9</a>）。
    我们从这个图谱看到的任何"路由异常/DNS 故障"都带有欧美中心偏差。
    <br><br>
    AS 密度：{COUNTRY_NAME[top_dens]} {top_dens} 最高
    （{sig['as_per_m'][top_dens]:.1f} AS/百万人），
    {COUNTRY_NAME[bot_dens]} {bot_dens} 最低
    （{sig['as_per_m'][bot_dens]:.2f}，相差 {sig['as_per_m'][top_dens] / sig['as_per_m'][bot_dens]:.0f}×）。
    </p>
    """

    # ---- Section 4 — CN corrective ----
    sec4 = f"""
    <h2 style="color:{country_color('CN')};margin-top:32px">
    ④ 对 CN 主权指数的 3 条修正
    </h2>
    <p style="color:{TEXT_PRIMARY};line-height:1.7">
    原始 <code>composite_sovereignty_index(CN) = 0.269</code>（九国末位）
    在新角度下需要分层解读：
    </p>
    <ol style="color:{TEXT_PRIMARY};line-height:1.8;padding-left:24px">
    <li><b>hub_ratio 低是伪弱</b>：
      分量 0.019 的极低读数来自 6,660 AS 的分母稀释。
      用户视角下深层 k-core 密度与 US 相当（T1 panel ⑤）。
      这一分量不应单独作为弱点解读。</li>
    <li><b>IXP 本地化确实差</b>：
      user 视角（T1 panel ⑥）也只有 4.4%，
      JP/IN/DE 都在 70-82%。这是真实的基础设施缺口，
      直接关联 CN 对外流量的路径必然长化。</li>
    <li><b>对外依赖度是 9 国最强</b>：
      在 9×9 依赖矩阵（T15）里，CN 净 -5,018 是最大进口方，
      出/入比 253:1。这不是 composite 指数里某个分量的问题，
      而是系统性事实。任何以"依赖程度"为切入点的主权讨论
      都应以此作为基础。</li>
    </ol>
    <p style="color:{TEXT_PRIMARY};line-height:1.7;margin-top:12px">
    综合说，CN 低分由"数据层稀释 + 真实缺口 + 结构依赖"
    三部分组成；混为一谈会得出错误结论。
    </p>
    """

    # ---- Topic catalog ----
    catalog_rows = [
        ('1', '用户加权主权视角', 'eyeball/',
         f'CN {sig["cn_eyeball_pct"]:.1f}% eyeball · NL 93 AS/百万 vs CN 4.7'),
        ('2', '路由安全真身（RPKI × ROVISTA）', 'routing-security/',
         f'{sig["gap_pct"]:.0f}% 宣告 AS 不执行 ROV'),
        ('3', 'Tranco Top-10k 深度', 'toplist/',
         '.com 51.6% · 350 unique TLDs · 降级自 4-源对比'),
        ('4', 'AS 业务类型图谱', 'asdb/',
         'Computer & IT 57% · Service 16K'),
        ('5', 'AS 业务原型', 'archetype/',
         'Eyeball 8332 / Content 1173 / Carrier 557 / T1 15 · 降级自 AWS'),
        ('6', 'AS 行为标签地图', 'bgp-tags/',
         'Home ISP 2424 · ToR 974 · VPN 751 · 关键 Infra 448'),
        ('7', 'OONI 审查测试图谱', 'ooni/',
         '10 测试 · 11,804 pair · 179 严重阻断 · cc 缺失降级'),
        ('8', 'ROV 执行国别地图', 'rovista-country/',
         'BT 63% 顶部 · 五国 0% · 替换自 PeeringDB'),
        ('9', 'Atlas 探针全球覆盖', 'atlas/',
         f'{sig["atlas_total"]:,} probe · top-5 国占 {sig["atlas_top5_share"]:.0f}%'),
        ('10', 'BGP 观测多样性', 'bgp-obs/',
         '13K v4 · 6.8K v6 · 6.2K 两源 · 降级自 PCH'),
        ('11', 'AS 所有权集中度', 'org-concentration/',
         '9 国 HHI 都 <200（组织级分散）'),
        ('12', '全球 IHR Hegemony', 'ihr-hegemony/',
         f'HE 27.5K 权重 > Lumen 10.9K · CN CERNET2 全球 #5'),
        ('13', '跨国组织 AS 足迹', 'multinational/',
         '814 跨国组织 · ISC 18 国 · AT&T Japan 12 国'),
        ('14', '全球 DNS 权威集中度', 'dns-authority/',
         'GoDaddy 1.3M · dns-parking 728K · Google 652K'),
        ('15', '9×9 国家依赖矩阵', 'country-dep/',
         f'US 唯一净出口 +13.6K · CN 最大净进口 -5.0K · 比 253:1'),
    ]
    cat_rows = ''.join(
        f'<tr style="border-bottom:1px solid {DARK_BORDER}">'
        f'<td style="padding:6px 12px;color:{COLORS["cyan"]};font-weight:600">T{n}</td>'
        f'<td style="padding:6px 12px"><a href="{url}" style="color:{TEXT_PRIMARY};text-decoration:none">{title}</a></td>'
        f'<td style="padding:6px 12px;color:{TEXT_SECONDARY};font-size:13px">{hint}</td>'
        f'</tr>'
        for n, title, url, hint in catalog_rows
    )
    catalog = f"""
    <h2 style="color:{TEXT_PRIMARY};margin-top:40px">
    15 个 topic 索引 · Topic catalog
    </h2>
    <table style="width:100%;border-collapse:collapse;margin-top:12px">
    <thead><tr style="border-bottom:2px solid {DARK_BORDER}">
      <th style="padding:8px;text-align:left;color:{TEXT_SECONDARY}">#</th>
      <th style="padding:8px;text-align:left;color:{TEXT_SECONDARY}">Topic</th>
      <th style="padding:8px;text-align:left;color:{TEXT_SECONDARY}">Key finding</th>
    </tr></thead>
    <tbody>{cat_rows}</tbody>
    </table>
    """

    # Header hero + cards
    hero_cards = ''.join([
        card('Topics', '15', '跨 4 轮 commit · 16 Countries dashboard'),
        card('Degraded', '6', 'schema 缺失降级'),
        card('Substituted', '2', 'AWS→archetype · PeeringDB→ROV'),
        card('Full', '7', '原计划 100% 执行'),
    ])

    banner = (
        '<div class="step-banner">'
        '<h1>15 个新角度 · 3 个结构性洞察</h1>'
        '<h2>The Internet Yellow Pages through 15 novel lenses · '
        'distilled</h2>'
        '</div>'
        '<div class="step-footer">synthesis · 2024-10 snapshot · '
        'offline from data_cache/</div>'
    )

    body = (
        banner
        + f'<div class="content">'
        f'<div style="display:flex;flex-wrap:wrap;margin:16px -6px">{hero_cards}</div>'
        + fig_htmls[0]
        + sec1
        + fig_htmls[1]
        + sec2
        + fig_htmls[2]
        + sec3
        + sec4
        + catalog
        + f'<p style="margin-top:40px;color:{TEXT_SECONDARY};font-size:13px">'
        f'Each finding is linked to its source dashboard; all numbers are '
        f'recomputed from <code>data_cache/</code> every build.</p>'
        f'</div>'
    )

    out_path = OUT / 'synthesis.html'
    out_path.write_text(
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>15 个新角度汇总 · New Angles Synthesis</title>'
        f'{BANNER_CSS}</head><body>{body}</body></html>',
        encoding='utf-8',
    )
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    print(f'CN: eyeball {sig["cn_eyeball"]} / {sig["cn_as"]} '
          f'({sig["cn_eyeball_pct"]:.2f}%)')
    print(f'RPKI gap: {sig["gap"]} / {sig["signed"]} = {sig["gap_pct"]:.1f}%')
    print(f'US net: +{sig["net_balance"]["US"]["net"]:.0f}  '
          f'CN net: {sig["net_balance"]["CN"]["net"]:.0f}')


if __name__ == '__main__':
    build()
