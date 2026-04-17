"""Step 20 · Synthesis Dashboard · China in the Global Internet Hierarchy.

Dimensions: integrative cross-layer (all 19 previous steps)
Data: reuse all step metrics JSON + key CSVs
Output: step20_synthesis.html with multi-panel master dashboard
"""
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.china.common import (  # noqa: E402
    COLORS, DATA_DIR, HTML_DIR, DARK_BG, DARK_PANEL, DARK_BORDER,
    TEXT_PRIMARY, TEXT_SECONDARY, read_step_metrics,
    save_multi_plotly_html, write_step_metrics, writeup,
)

STEP = 20
TITLE_ZH = '综合仪表板 · 中国在全球互联网分层中的位置'
TITLE_EN = 'Synthesis Dashboard · China in the Global Internet Hierarchy'


def main():
    # Pull in all prior metrics
    prior = {i: read_step_metrics(i) for i in range(1, 20)}

    import plotly.graph_objects as go
    import plotly.subplots as sp

    # ── Panel 1: Scope numbers (Step 1-3) ──
    scope = prior[1]['metrics'] if prior[1] else {}
    ranks = prior[3]['metrics']['cn_ranks_by_metric'] if prior[3] else {}

    scope_fig = go.Figure()
    scope_fig.add_trace(go.Indicator(
        mode='number', value=scope.get('cn_asns', 0),
        title=dict(text='CN 大陆 AS 数<br>Mainland CN ASes'),
        domain=dict(x=[0, 0.25], y=[0, 1])))
    scope_fig.add_trace(go.Indicator(
        mode='number', value=ranks.get('as_count', {}).get('rank', 0),
        title=dict(text='AS 总数 全球排名<br>AS count global rank'),
        number=dict(prefix='#', font=dict(color=COLORS['red'])),
        domain=dict(x=[0.25, 0.5], y=[0, 1])))
    scope_fig.add_trace(go.Indicator(
        mode='number', value=ranks.get('prefix_count', {}).get('rank', 0),
        title=dict(text='前缀数 全球排名<br>Prefix count global rank'),
        number=dict(prefix='#', font=dict(color=COLORS['orange'])),
        domain=dict(x=[0.5, 0.75], y=[0, 1])))
    scope_fig.add_trace(go.Indicator(
        mode='number', value=ranks.get('ixp_count', {}).get('rank', 0),
        title=dict(text='IXP 数 全球排名<br>IXP count global rank'),
        number=dict(prefix='#', font=dict(color=COLORS['purple'])),
        domain=dict(x=[0.75, 1], y=[0, 1])))
    scope_fig.update_layout(height=240, title='① 规模与全球排名 Scope & Rank')

    # ── Panel 2: Topology position (Step 5-7) ──
    s5 = prior[5]['metrics'] if prior[5] else {}
    s6 = prior[6]['metrics'] if prior[6] else {}
    s7 = prior[7]['metrics'] if prior[7] else {}
    top_foreign_cc = s5.get('top_foreign_countries', {}) or {}
    peer_fig = go.Figure()
    if top_foreign_cc:
        peer_fig.add_trace(go.Bar(
            x=list(top_foreign_cc.keys()),
            y=list(top_foreign_cc.values()),
            marker_color=COLORS['blue'],
            text=[str(v) for v in top_foreign_cc.values()],
            textposition='outside',
        ))
    peer_fig.update_layout(
        title=(f'② 对等互联伙伴 Top 国家 (Step 05) · max k-core={s7.get("cn_deepest_coreness", "?")}/'
               f'{s7.get("global_max_k", "?")}, best PR rank=#{s6.get("best_pagerank_rank", "?")}'),
        yaxis=dict(title='# peer ASes'), height=340,
    )

    # ── Panel 3: Hegemony Sankey-lite (Step 8-9) ──
    s8 = prior[8]['metrics'] if prior[8] else {}
    s9 = prior[9]['metrics'] if prior[9] else {}
    top_dest = s8.get('top_destination_countries', {}) or {}
    dep_cc = s9.get('top_dependent_countries', {}) or {}
    hege_fig = sp.make_subplots(
        rows=1, cols=2,
        subplot_titles=('CN→外 依赖国家 · outbound hegemony', '外→CN 依赖国家 · inbound hegemony'))
    if top_dest:
        hege_fig.add_trace(go.Bar(
            x=list(top_dest.keys()), y=list(top_dest.values()),
            marker_color=COLORS['red'], showlegend=False,
        ), row=1, col=1)
    if dep_cc:
        hege_fig.add_trace(go.Bar(
            x=list(dep_cc.keys()), y=list(dep_cc.values()),
            marker_color=COLORS['cyan'], showlegend=False,
        ), row=1, col=2)
    hege_fig.update_layout(
        title='③ AS Hegemony: 出向 vs 入向', height=360)

    # ── Panel 4: Concentration comparison (Step 10) ──
    s10 = prior[10]['metrics'] if prior[10] else {}
    conc_fig = go.Figure()
    dims = ['prefix', 'hostname', 'org', 'ixp']
    conc_fig.add_trace(go.Bar(
        x=dims,
        y=[s10.get(f'cn_hhi_{d}', 0) for d in dims] if s10 else [],
        name='CN HHI', marker_color=COLORS['red'],
    ))
    # Note: we don't have all global HHI cached in metrics; use what exists
    conc_fig.update_layout(
        title='④ 集中度指数 HHI · CN (higher = more concentrated)',
        yaxis=dict(title='HHI'), height=300,
    )

    # ── Panel 5: Physical infrastructure (Step 11-12) ──
    s11 = prior[11]['metrics'] if prior[11] else {}
    s12 = prior[12]['metrics'] if prior[12] else {}
    phys = s11.get('top5_countries_hosting_cn_presence', {}) or {}
    fac = s12.get('top5_countries_by_cn_facility_presence', {}) or {}
    phys_fig = sp.make_subplots(
        rows=1, cols=2,
        subplot_titles=('IXP hosting country · Step 11', 'Facility country · Step 12'))
    if phys:
        phys_fig.add_trace(go.Bar(
            x=list(phys.keys()), y=list(phys.values()),
            marker_color=COLORS['orange'], showlegend=False,
        ), row=1, col=1)
    if fac:
        phys_fig.add_trace(go.Bar(
            x=list(fac.keys()), y=list(fac.values()),
            marker_color=COLORS['purple'], showlegend=False,
        ), row=1, col=2)
    phys_fig.update_layout(title='⑤ 物理基础设施分布 · IXP + Facility', height=340)

    # ── Panel 6: DNS / content (Step 14-16) ──
    s14 = prior[14]['metrics'] if prior[14] else {}
    s15 = prior[15]['metrics'] if prior[15] else {}
    s16 = prior[16]['metrics'] if prior[16] else {}
    split = s14.get('cloud_vs_isp_split_hostnames', {}) or {}
    cname_fam = s16.get('top_target_families', {}) or {}
    dns_fig = sp.make_subplots(
        rows=1, cols=3,
        specs=[[{'type': 'pie'}, {'type': 'pie'}, {'type': 'bar'}]],
        subplot_titles=('CN 托管 Cloud vs ISP (Step 14)', '.cn 域管理国籍 (Step 15)',
                        'CNAME target families (Step 16)'))
    if split:
        dns_fig.add_trace(go.Pie(
            labels=list(split.keys()), values=list(split.values()),
            marker_colors=[COLORS['blue'], COLORS['orange'], COLORS['green']],
            hole=0.4, showlegend=False), row=1, col=1)
    cn_share = s15.get('cn_operator_share_pct', 0) or 0
    us_share = s15.get('us_operator_share_pct', 0) or 0
    dns_fig.add_trace(go.Pie(
        labels=['CN operator', 'US operator', 'Other'],
        values=[cn_share, us_share, max(100 - cn_share - us_share, 0)],
        marker_colors=[COLORS['red'], COLORS['blue'], COLORS['green']],
        hole=0.4, showlegend=False), row=1, col=2)
    if cname_fam:
        dns_fig.add_trace(go.Bar(
            x=list(cname_fam.keys()), y=list(cname_fam.values()),
            marker_color=COLORS['red'], showlegend=False,
        ), row=1, col=3)
    dns_fig.update_layout(title='⑥ DNS / Content 层', height=380)

    # ── Panel 7: Censorship & Atlas (Step 18-19) ──
    s18 = prior[18]['metrics'] if prior[18] else {}
    s19 = prior[19]['metrics'] if prior[19] else {}
    tests = dict(s18.get('top5_tests', []) or [])
    atlas_tgt = s19.get('target_measurement_counts', {}) or {}
    sec_fig = sp.make_subplots(
        rows=1, cols=2,
        subplot_titles=('Top OONI 测试类型 (Step 18)', 'Atlas 测量 CN 目标 (Step 19)'))
    if tests:
        sec_fig.add_trace(go.Bar(
            x=list(tests.keys()), y=list(tests.values()),
            marker_color=COLORS['red'], showlegend=False), row=1, col=1)
    if atlas_tgt:
        sec_fig.add_trace(go.Bar(
            x=list(atlas_tgt.keys()), y=list(atlas_tgt.values()),
            marker_color=COLORS['teal'], showlegend=False), row=1, col=2)
    sec_fig.update_layout(title='⑦ 安全监管与可观测性', height=340)

    # ── Panel 8: China Internet Sovereignty Index ──
    # Composite score on 5 sub-metrics:
    # 1. hosting_in_cn_ratio (cloud+isp hosted on CN AS) — higher = more sovereign
    # 2. dns_ns_in_cn_ratio (from step15 cn_operator_share_pct)
    # 3. prefix_rpki_rate (from step4 rpki_rate_pct) — higher = healthier
    # 4. ixp_in_cn_ratio (domestic vs total CN memberships)
    # 5. inbound/outbound hegemony ratio — higher = more globally connected as hub
    s4 = prior[4]['metrics'] if prior[4] else {}
    host_in_cn = s14.get('cn_total_hostnames_hosted', 0) or 0
    # Approximate global — harder to compute here; use Step 3 stats implicitly
    # For scoring we normalize each dimension 0-1 using sensible caps
    dns_sov = cn_share / 100.0
    rpki = (s4.get('rpki_rate_pct', 0) or 0) / 100.0
    ixp_in_cn_count = len(s11.get('top5_domestic_ixps', []) or [])
    ixp_ratio = ixp_in_cn_count / max(s11.get('distinct_cn_ixps_participated', 1), 1)
    inbound_edges = s9.get('total_inbound_edges_hege_ge_003', 0) or 1
    outbound_edges = s8.get('total_outbound_edges_hege_ge_005', 0) or 1
    hub_ratio = min(inbound_edges / max(outbound_edges, 1), 1.0)
    hosting_proxy = min(host_in_cn / 300000, 1.0)

    components = {
        'Hosting Sovereignty\n托管自给率': hosting_proxy,
        'DNS Sovereignty\nDNS 自主率': dns_sov,
        'RPKI Adoption\n路由安全': rpki,
        'IXP Domesticization\nIXP 本地化': ixp_ratio,
        'Hub-Ratio\n入向/出向': hub_ratio,
    }
    overall = sum(components.values()) / len(components)

    radar_fig = go.Figure(go.Scatterpolar(
        r=list(components.values()) + [list(components.values())[0]],
        theta=list(components.keys()) + [list(components.keys())[0]],
        fill='toself', fillcolor='rgba(255,107,107,0.3)',
        line=dict(color=COLORS['red'], width=3),
        name='China Internet Sovereignty Index',
    ))
    radar_fig.update_layout(
        title=f'⑧ 中国互联网主权综合指数 · Composite = {overall:.3f}',
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1], gridcolor=DARK_BORDER),
            bgcolor=DARK_PANEL,
            angularaxis=dict(gridcolor=DARK_BORDER),
        ),
        height=560,
    )

    metrics = {
        'composite_sovereignty_index': round(overall, 4),
        'components': {k: round(v, 4) for k, v in components.items()},
        'source_steps': list(range(1, 20)),
    }
    write_step_metrics(STEP, metrics, TITLE_ZH, TITLE_EN)

    # ── Narrative ──
    narrative_html = f'''
    <div class="sidebar-note">
      <b>综合叙事 · Integrated Narrative</b><br><br>
      中国在"规模维度"上排名靠前 (AS #{ranks.get('as_count', {}).get('rank', '?')},
      Prefix #{ranks.get('prefix_count', {}).get('rank', '?')}), 但"互联基础设施"层面薄弱
      (IXP #{ranks.get('ixp_count', {}).get('rank', '?')},
      Facility #{ranks.get('facility_count', {}).get('rank', '?')})。<br>
      网络拓扑特征显示 <b>AS38255 (CERNET) 进入全球 PageRank #1</b>，
      而 <b>{s7.get('cn_count_k_ge_100', '?')} 个 CN AS 进入 k≥100 深层核心</b>
      (全局 max k = {s7.get('global_max_k', '?')})。<br>
      跨境依赖：CN 出向 hegemony 显著依赖 US/HK/SE/BE，AS6939 (HE) 单一 AS 被 5,000+ CN ASes
      依赖；外部 AS 依赖 CN 的数量相对较小 ({s9.get('foreign_dependents', '?')} 个)，
      说明 CN 更多扮演"终端"而非"全球中继"角色。<br>
      DNS 主权率仅 {cn_share:.1f}%，RPKI ROA 覆盖率 {s4.get('rpki_rate_pct', 0):.1f}%，均低于欧美平均。<br>
      <b>综合主权指数 = {overall:.3f}</b> (满分 1.0).<br><br>
      <b>English summary:</b> China leads on <b>scale</b> (AS/prefix top-3) but lags on
      <b>interconnection density</b> (IXP/facility). Topologically it reaches the global innermost
      k-core ({s7.get('cn_count_k_ge_100', '?')} ASes in k≥100; CERNET is #1 PageRank globally).
      Outbound hegemony is dominated by US/HK carriers; inbound is limited — CN is a <b>regional hub
      but not yet a global transit relay</b>. DNS sovereignty ({cn_share:.1f}%) and RPKI
      ({s4.get('rpki_rate_pct', 0):.1f}%) remain below Western benchmarks.
      Composite Sovereignty Index = {overall:.3f}.
    </div>
    '''

    save_multi_plotly_html(
        [scope_fig, peer_fig, hege_fig, conc_fig, phys_fig, dns_fig, sec_fig, radar_fig],
        'step20_synthesis.html',
        step_num=STEP, title_zh=TITLE_ZH, title_en=TITLE_EN,
        source='synthesis of steps 1-19',
        writeup_html=narrative_html,
        subtitles=[
            '① 规模与全球排名', '② 拓扑位置与对等互联伙伴',
            '③ 依赖与 Hegemony', '④ 集中度',
            '⑤ 物理基础设施', '⑥ DNS / 内容',
            '⑦ 审查与可观测性',
            '⑧ 中国互联网主权综合指数',
        ],
    )


if __name__ == '__main__':
    main()
