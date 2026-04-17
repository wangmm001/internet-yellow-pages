"""Per-country profile: runs 20 extractors + emits profile_<CC>.html.

Usage:
  python3 -m analysis.countries.country_pipeline --country US --snapshot 2026-04
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.countries.common import (  # noqa: E402
    COLORS, DARK_BG, DARK_BORDER, DARK_PANEL, HTML_DIR, TEXT_PRIMARY, TEXT_SECONDARY,
    apply_plotly_theme, bilingual, en, plotly_inline_once, save_consolidated_html,
    zh,
)
from analysis.countries.step_lib import STEP_TITLES, run_all_for_country


def build_profile(country, snapshot, results):
    """Build multi-panel profile HTML from step metrics."""
    import plotly.graph_objects as go
    import plotly.subplots as sp

    s1 = results.get(1, {})
    s3 = results.get(3, {})
    s4 = results.get(4, {})
    s5 = results.get(5, {})
    s6 = results.get(6, {})
    s7 = results.get(7, {})
    s8 = results.get(8, {})
    s9 = results.get(9, {})
    s10 = results.get(10, {})
    s11 = results.get(11, {})
    s12 = results.get(12, {})
    s14 = results.get(14, {})
    s15 = results.get(15, {})
    s18 = results.get(18, {})
    s20 = results.get(20, {})

    # Panel 1: KPI indicators — scale metrics (from Step 3)
    kpi = go.Figure()
    kpi.add_trace(go.Indicator(
        mode='number', value=s3.get('as_count', {}).get('rank', 0) or 0,
        title=dict(text=f'AS 数 全球排名<br>AS count rank'),
        number=dict(prefix='#', font=dict(color=COLORS['red'])),
        domain=dict(x=[0, 0.25], y=[0, 1])))
    kpi.add_trace(go.Indicator(
        mode='number', value=s3.get('prefix_count', {}).get('rank', 0) or 0,
        title=dict(text='前缀数 排名<br>Prefix rank'),
        number=dict(prefix='#', font=dict(color=COLORS['orange'])),
        domain=dict(x=[0.25, 0.5], y=[0, 1])))
    kpi.add_trace(go.Indicator(
        mode='number', value=s3.get('ixp_count', {}).get('rank', 0) or 0,
        title=dict(text='IXP 数 排名<br>IXP rank'),
        number=dict(prefix='#', font=dict(color=COLORS['purple'])),
        domain=dict(x=[0.5, 0.75], y=[0, 1])))
    kpi.add_trace(go.Indicator(
        mode='number', value=s3.get('facility_count', {}).get('rank', 0) or 0,
        title=dict(text='机房数 排名<br>Facility rank'),
        number=dict(prefix='#', font=dict(color=COLORS['cyan'])),
        domain=dict(x=[0.75, 1], y=[0, 1])))
    kpi.update_layout(height=240, title='① 规模与全球排名 · Scale & Rank')

    # Panel 2: Tag distribution pie
    tag_dist = s1.get('tag_distribution', {}) or {}
    if tag_dist:
        tag_fig = go.Figure(go.Pie(
            labels=list(tag_dist.keys()),
            values=list(tag_dist.values()),
            hole=0.4, marker=dict(colors=[COLORS['red'], COLORS['cyan'],
                                          COLORS['blue'], COLORS['orange'],
                                          COLORS['purple'], COLORS['green'],
                                          COLORS['yellow'], COLORS['pink']]),
            textinfo='label+percent',
        ))
    else:
        tag_fig = go.Figure()
    tag_fig.update_layout(title='② AS 标签分布 · Tag distribution', height=360)

    # Panel 3: Peering partners
    peer_cc = s5.get('top_peer_countries', {}) or {}
    peer_fig = go.Figure()
    if peer_cc:
        peer_fig.add_trace(go.Bar(
            x=list(peer_cc.keys()), y=list(peer_cc.values()),
            marker_color=COLORS['blue'],
            text=[str(v) for v in peer_cc.values()],
            textposition='outside',
        ))
    peer_fig.update_layout(
        title=(f'③ 主要对等互联伙伴国 · Top peering partner countries · '
               f'best PR rank #{(s6.get("best_ranks") or {}).get("pagerank", "?")} · '
               f'k-core max={s7.get("deepest_k_in_country", "?")}'),
        yaxis=dict(title='# peer ASes'), height=340,
    )

    # Panel 4: Hegemony comparison
    hege = sp.make_subplots(
        rows=1, cols=2,
        subplot_titles=('出向依赖 → 目的国 · Outbound hegemony destinations',
                        '入向依赖 ← 来源国 · Inbound hegemony sources'))
    out_dest = s8.get('top_destination_countries', {}) or {}
    if out_dest:
        hege.add_trace(go.Bar(
            x=list(out_dest.keys()), y=list(out_dest.values()),
            marker_color=COLORS['red'], showlegend=False,
        ), row=1, col=1)
    in_src = s9.get('top_source_countries', {}) or {}
    if in_src:
        hege.add_trace(go.Bar(
            x=list(in_src.keys()), y=list(in_src.values()),
            marker_color=COLORS['cyan'], showlegend=False,
        ), row=1, col=2)
    hege.update_layout(title='④ AS Hegemony · 出向 vs 入向', height=360)

    # Panel 5: Concentration
    conc_fig = go.Figure()
    dims = ['prefix', 'hostname', 'org']
    conc_fig.add_trace(go.Bar(
        x=dims, y=[s10.get(f'hhi_{d}', 0) or 0 for d in dims],
        name='HHI', marker_color=COLORS['red'],
    ))
    conc_fig.add_trace(go.Bar(
        x=dims, y=[s10.get(f'gini_{d}', 0) or 0 for d in dims],
        name='Gini', marker_color=COLORS['cyan'],
    ))
    conc_fig.update_layout(
        title='⑤ 集中度 · HHI & Gini', barmode='group', height=300)

    # Panel 6: Physical
    phys_fig = sp.make_subplots(
        rows=1, cols=2,
        subplot_titles=('IXP 参与国家分布 · IXP host countries',
                        '机房部署国家 · Facility host countries'))
    ixp_cc = s11.get('top_ixp_host_countries', {}) or {}
    if ixp_cc:
        phys_fig.add_trace(go.Bar(
            x=list(ixp_cc.keys()), y=list(ixp_cc.values()),
            marker_color=COLORS['orange'], showlegend=False,
        ), row=1, col=1)
    fac_cc = s12.get('top_countries_by_facility_presence', {}) or {}
    if fac_cc:
        phys_fig.add_trace(go.Bar(
            x=list(fac_cc.keys()), y=list(fac_cc.values()),
            marker_color=COLORS['purple'], showlegend=False,
        ), row=1, col=2)
    phys_fig.update_layout(title='⑥ 物理基础设施分布', height=340)

    # Panel 7: DNS / Content
    cloud = s14.get('cloud_hostnames', 0) or 0
    isp = s14.get('isp_hostnames', 0) or 0
    other = s14.get('other_hostnames', 0) or 0
    dns_sov_pct = s15.get('domestic_pct', 0) or 0
    rpki = s4.get('rpki_rate_pct', 0) or 0
    dns_fig = sp.make_subplots(
        rows=1, cols=3, specs=[[{'type': 'pie'}, {'type': 'pie'}, {'type': 'bar'}]],
        subplot_titles=('托管 Cloud vs ISP · Hosting split',
                        f'ccTLD 运营商国籍 · NS country',
                        '路由安全 · RPKI + Anycast'))
    if cloud + isp + other > 0:
        dns_fig.add_trace(go.Pie(
            labels=['Cloud/CDN', 'ISP', 'Other'], values=[cloud, isp, other],
            marker_colors=[COLORS['blue'], COLORS['orange'], COLORS['green']],
            hole=0.4, showlegend=False), row=1, col=1)
    dns_fig.add_trace(go.Pie(
        labels=['Domestic', 'Foreign'],
        values=[dns_sov_pct, max(100 - dns_sov_pct, 0)],
        marker_colors=[COLORS['red'], COLORS['cyan']],
        hole=0.4, showlegend=False), row=1, col=2)
    dns_fig.add_trace(go.Bar(
        x=['RPKI Valid %', 'Anycast %'],
        y=[rpki, (s4.get('anycast_prefixes', 0) or 0) /
           max(s4.get('total_prefixes', 1), 1) * 100],
        marker_color=COLORS['green'], showlegend=False,
    ), row=1, col=3)
    dns_fig.update_layout(title='⑦ DNS / 内容 / 路由安全', height=380)

    # Panel 8: Censorship & security
    tests = dict(s18.get('top5_tests', []) or [])
    sec_fig = go.Figure()
    if tests:
        sec_fig.add_trace(go.Bar(
            x=list(tests.keys()), y=list(tests.values()),
            marker_color=COLORS['red'],
        ))
    sec_fig.update_layout(
        title=(f'⑧ 审查信号 OONI · {s18.get("censoring_ases", 0)} ASes, '
               f'{s18.get("total_detections", 0)} detections'),
        yaxis=dict(title='Detection count'), height=320)

    # Panel 9: Sovereignty radar
    comps = s20.get('components', {}) or {}
    comp_labels_map = {
        'hosting_sovereignty': '托管自给率\nHosting',
        'dns_sovereignty': 'DNS 主权\nDNS Sov',
        'rpki_adoption': '路由安全\nRPKI',
        'ixp_domesticization': 'IXP 本地化\nIXP Dom',
        'hub_ratio': '入向/出向\nHub Ratio',
    }
    labels = [comp_labels_map.get(k, k) for k in comps.keys()]
    values = list(comps.values())
    if labels:
        radar = go.Figure(go.Scatterpolar(
            r=values + [values[0]] if values else [],
            theta=labels + [labels[0]] if labels else [],
            fill='toself', fillcolor='rgba(255,107,107,0.3)',
            line=dict(color=COLORS['red'], width=3),
            name='Sovereignty Index',
        ))
        radar.update_layout(
            title=(f'⑨ 主权综合指数 · Composite = '
                   f'{s20.get("composite_sovereignty_index", 0):.3f}'),
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 1], gridcolor=DARK_BORDER),
                bgcolor=DARK_PANEL,
                angularaxis=dict(gridcolor=DARK_BORDER),
            ), height=520)
    else:
        radar = go.Figure()

    # Narrative — use safe formatters so missing / non-numeric values don't crash
    def _n(v):
        try:
            return f'{int(v):,}'
        except (TypeError, ValueError):
            return '?'

    def _f(v, spec='.1f'):
        try:
            return format(float(v), spec)
        except (TypeError, ValueError):
            return '?'

    narr = f'''
    <div class="sidebar-note">
    <b>摘要 · Summary</b><br><br>
    {bilingual(country)} 拥有 AS {_n(s1.get("total_ases"))} 个，全球排名
    #{s3.get("as_count", {}).get("rank", "?")}；BGP 前缀 {_n(s4.get("total_prefixes"))}
    (IPv4 {_n(s4.get("v4_prefixes"))} / IPv6 {_n(s4.get("v6_prefixes"))})，
    RPKI 覆盖 {_f(s4.get("rpki_rate_pct"))}%。<br>
    全球最佳 PageRank 排名 #{(s6.get("best_ranks") or {}).get("pagerank", "?")}，
    深入 k-core 达 {s7.get("deepest_k_in_country", "?")} 层。<br>
    出向依赖边 {_n(s8.get("outbound_edges"))}，入向依赖边 {_n(s9.get("inbound_edges"))}；
    DNS 本土运营商占比 {_f(dns_sov_pct)}%。<br>
    <b>综合主权指数 · Sovereignty Index = {_f(s20.get("composite_sovereignty_index"), ".3f")}</b>
    </div>
    '''

    figs = [kpi, tag_fig, peer_fig, hege, conc_fig, phys_fig, dns_fig, sec_fig, radar]
    for f in figs:
        apply_plotly_theme(f)
    body = narr + plotly_inline_once(figs)
    title_zh = f'{zh(country)}互联网分层档案 · 20 Step Analysis'
    title_en = f'{en(country)} Internet Hierarchy Profile · {snapshot} snapshot'
    save_consolidated_html(body, f'profile_{country}.html', title_zh, title_en,
                           subtitle=f'snapshot={snapshot} · generated by country_pipeline.py')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--country', required=True)
    ap.add_argument('--snapshot', default='2026-04')
    args = ap.parse_args()
    results = run_all_for_country(args.country, args.snapshot)
    build_profile(args.country, args.snapshot, results)


if __name__ == '__main__':
    main()
