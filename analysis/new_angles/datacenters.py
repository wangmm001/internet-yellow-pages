"""International data-center layer panels (breadth-first, 4-axis).

Axes: Geography / Ownership / Temporal / Routing.
Reads facilities.csv, facility_members.csv, facility_ixps.csv,
peeringdb_nets.csv per snapshot from data_cache/new_angles/<YYYY-MM-DD>/.

Run AFTER run_dc_timeseries.sh completes (or produces only the static
panels when only the latest snapshot has DC data).

Outputs:
  analysis/new_angles/html/datacenters.html  (main, 8-12 panels)
  analysis/new_angles/html/dc_routing_pyvis.html  (P13 if built)
"""
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.china.common import (  # noqa: E402
    BANNER_CSS, COLORS, TEXT_PRIMARY, TEXT_SECONDARY,
    apply_plotly_theme, country_color, warning_block, ISO2_TO_ISO3,
)

REPO = Path(__file__).resolve().parent.parent.parent
CACHE = REPO / 'data_cache' / 'new_angles'
OUT = REPO / 'analysis' / 'new_angles' / 'html'


CITY_ALIASES = {
    # PeeringDB cleaned up city names mid-series (e.g. "Milano"→"Milan"
    # around 2025-10). Without normalization the top-city Δ list has
    # ghost growth that's pure alias consolidation. See DATACENTERS.md
    # methodology note.
    'milano': 'Milan', 'milan': 'Milan',
    'kiev': 'Kyiv', 'kyiv': 'Kyiv', 'Kiev': 'Kyiv', 'KYIV': 'Kyiv',
    'bogotá': 'Bogota', 'bogota': 'Bogota',
    'ciudad autónoma de buenos aires': 'Buenos Aires',
    'buenos aires': 'Buenos Aires',
    'sao paulo': 'São Paulo', 'são paulo': 'São Paulo',
    'hong kong': 'Hong Kong',
    'saint petersburg': 'St. Petersburg',
    'санкт-петербург': 'St. Petersburg',
}


OPERATOR_ALIASES = {
    # PeeringDB operator-field renames discovered via pdb_fac_id stable-key
    # audit (METHODOLOGY_AUDIT.md § 2.1). Covers M&A brand consolidation
    # lags (Digital Realty bought Interxion in 2020, only propagated 2024-
    # 2026), bankruptcy-reorg rebrands (Cyxtera → Centersquare 2024),
    # and cosmetic casing/suffix edits. Only "pure rename" cases are
    # canonicalized here; true divestments (e.g. Lumen selling EMEA
    # to Colt) are preserved as distinct operators because they reflect
    # real market structure changes, not brand consolidation.
    'Interxion - A Digital Realty Company': 'Digital Realty',
    'Cyxtera Technologies, Inc.': 'Centersquare',
    'Evoque Data Center Solutions': 'Centersquare',
    'CyrusOne': 'CyrusOne Inc.',
    'NTT Global Data Centers': "NTT DATA's Global Data Centers division",
    'NTT Communications (Data Centers)':
        'NTT  DOCOMO BUSINESS (Data Centers)',
    'Crown Castle': 'Crown Castle Inc.',
    'ST Telemedia Global Data Centres':
        'ST Telemedia Global Data Centres (STT GDC)',
    'SFR SA': 'UltraEdge',
    'AtlasEdge Data Centres': 'AtlasEdge',
    'KIO NETWORKS': 'KIO',
    'GleSYS AB': 'Glesys AB',
    'Pulsant (Scotland) Ltd': 'Pulsant',
    'Algar Telecom S/A': 'Algar',
    'IPHH - A Portus Data Centers Company': 'Portus Data Centers',
    'IPHH Internet Port Hamburg GmbH': 'Portus Data Centers',
    'Portus Data Centers Company': 'Portus Data Centers',
    'Datacenter One GmbH': 'AtlasEdge',
    'EUCLYDE DATACENTERS by nLighten': 'nLighten HQ BV',
    'Euclyde Data Centers': 'nLighten HQ BV',
    'RAXIO GROUP': 'RAXIO DATA CENTRES',
    'RAXIO DATA CENTRE SMC LIMITED': 'RAXIO DATA CENTRES',
    'Viettel Network Corporation': 'Viettel Group',
    'GELSEN-NET Kommunikationsgesellschaft mbH': 'GELSEN NET',
    'TimeWeb Co. Ltd.': 'JSC TimeWeb',
    'IXcellerate Ltd.': 'IXcellerate LLC',
    'SerinIX Inc.': 'SerinIX',
    'SerinIX Ukraine': 'SerinIX',
    'HL komm Telekommunikations GmbH': 'HLkomm Telekommunikations GmbH',
    'Hivelocity INC': 'Hivelocity LLC',
    'HostDime.com Inc': 'HostDime',
    '123.Net, Inc.': '123.Net, LLC.',
    'Scala Data Centers SA': 'Scala Data Centers',
    'brightsolid Ltd': 'Brightsolid Online Technology Ltd',
    'TeleMark Telekommunikationsgesellschaft Mark mbH':
        'Telemark Telekommunikationsgesellschaft Mark mbH',
    'ark data centers LLC': 'ark data centers',
    'ePLDT Inc.': 'Vitro Inc.',  # rebrand
    'Dataxion SAS': 'EASYTEAM (ex DATAXION)',
    'WIIT AG': 'WIIT Group (IT, DE, CH)',
    'WIIT AG (formerly myLoc managed IT AG)': 'WIIT Group (IT, DE, CH)',
    'myLoc managed IT AG': 'WIIT Group (IT, DE, CH)',
    'Orange Romania Communications S.A.': 'Orange Romania S.A. (AS9050)',
    'DataVita Ltd': 'DataVita',
    'Pacnet': 'Telstra (International)',
    'EVOLINK AD': 'EVOLINK EAD',
    'DATA4 Luxembourg s.a r.l': 'DATA4 s.a r.l',
    'Northc Schweiz AG': 'NorthC Schweiz AG',
    'iAdvantage Ltd.': 'iAdvantage Hong Kong',
    'dcBLOX, Inc.': 'DC BLOX Parent LLC',
    'Serverius Holding B.V.': 'KoloDC',
    'Tryideas Informatica Ltda': 'tryideas ltda',
    'Datacom Group Ltd': 'Datacom Data Centres Ltd',
    'Elea Digital Edge': 'Elea Data Centers',
    'POWERGRID TELESERVICES LIMITED': 'Powergrid Teleservices Limited',
    'Powergrid Corporation of India Limited':
        'Powergrid Teleservices Limited',
    'Ciklet Tasarim Iletisim ve Org. Tic. Ltd. Sti.': 'Ciklet Iletisim',
    'PT Mora Telematika Indonesia Tbk / Moratel International':
        'Moratelindo',
    'PT Mora Telematika Indonesia Tbk': 'Moratelindo',
    'Moratel International | PT Ekamas Mora Republik Tbk': 'Moratelindo',
    'Tanzania Telecommunications Corporation':
        'Tanzania Telecommunications Corporation (TTCL Corporation)',
    'Internexa Colombia': 'InterNexa',
    'HostPalace Web Solution Private Limited': 'HostPalace (INDIA)',
    'CPD TITAN': 'CPD Titan',
    'Host Color': 'HostColor',
    'NeoGrid Datacenter S.A.': 'Brasil TecPar',
    'Nova Rede de Telecomunicações Ltda': 'Brasil TecPar',
    'Brasil Tecnologia e Participacoes LTDA': 'Brasil TecPar',
    'LVT Telecom': 'Brasil TecPar',
    'Titania Telecom': 'Brasil TecPar',
    'BDx DC Services (HK) Limited': 'BDx DC Services Limited',
    'Luna.nl B.V.': 'Ekco B.V.',
    'Nessus GmbH': 'NESSUS',
    'Talex SA': 'Talex S.A.',
    'FiberState': 'FIBERSTATE',
    'Epcan GmbH': 'epcan GmbH',
    'Adyl Telecom': 'Adylnet Telecom',
    'AdylNET Telecom': 'Adylnet Telecom',
    'ark data centers LLC': 'ark data centers',
    'Involta, LLC': 'ark data centers',
    'R-KOM GmbH & Co. KG': 'R-KOM GmbH',
    'Anonymous': 'Anonymous SRL',
    'WhiteHat': 'Anonymous SRL',
    'Klixa AG': 'Klixa Group',
    'ReadyIDC CO.,LTD': 'ReadyIDC',
    'Oman Telecommunications Company (Omantel)':
        'Zain Omantel International (ZOI)',
}


def norm_op(op):
    """Canonicalize an operator name via OPERATOR_ALIASES."""
    if not op:
        return op
    return OPERATOR_ALIASES.get(op.strip(), op.strip())


def norm_city(c):
    if not c:
        return ''
    key = c.strip().lower().rstrip(',')
    return CITY_ALIASES.get(key, c.strip())


def _read(path):
    if not path.exists() or path.stat().st_size < 5:
        return []
    rows = list(csv.DictReader(open(path, encoding='utf-8')))
    # Apply normalization to facility rows
    for r in rows:
        if 'city' in r:
            r['city'] = norm_city(r['city'])
        if 'operator' in r:
            r['operator'] = norm_op(r['operator'])
    return rows


def discover_snaps():
    return sorted(
        d.name for d in CACHE.iterdir()
        if d.is_dir() and d.name[0].isdigit()
        and (d / 'facilities.csv').exists()
        and (d / 'facilities.csv').stat().st_size > 1000
    )


def build():
    import plotly.graph_objects as go
    from plotly.io import to_html

    snaps = discover_snaps()
    latest = snaps[-1] if snaps else '2026-04-08'
    print(f'Snapshots with DC data: {snaps}', flush=True)
    print(f'Using latest = {latest} for static panels', flush=True)

    facs = _read(CACHE / latest / 'facilities.csv')
    members = _read(CACHE / latest / 'facility_members.csv')
    fac_ixps = _read(CACHE / latest / 'facility_ixps.csv')
    pdb_nets = _read(CACHE / latest / 'peeringdb_nets.csv')
    laces = _read(CACHE / latest / 'laces_geoprefix_countries.csv')
    aws = _read(CACHE / latest / 'aws_prefixes.csv')
    hyperscale = _read(CACHE / latest / 'hyperscaler_originators.csv')

    # ─── Geography Axis ───────────────────────────────────────────

    # P1: per-country DC count choropleth
    cc_count = Counter(r['cc'] for r in facs if r['cc'])
    p1 = go.Figure()
    locs = [ISO2_TO_ISO3.get(c, c) for c, _ in cc_count.most_common()]
    zs = [n for _, n in cc_count.most_common()]
    p1.add_trace(go.Choropleth(
        locations=locs, z=zs, locationmode='ISO-3',
        colorscale='Viridis',
        text=[f'{c}: {n:,} DCs' for c, n in cc_count.most_common()],
        colorbar=dict(title='# DCs'),
    ))
    p1.update_layout(
        title=f'① 全球 DC 分布（{latest}）· {len(facs):,} facilities × '
              f'{len(cc_count)} countries',
        geo=dict(showframe=False, showcoastlines=True,
                 projection_type='natural earth', bgcolor='rgba(0,0,0,0)'),
        height=520,
    )

    # P2: top-20 metros (city, cc)
    city = Counter(
        f"{r['city']}, {r['cc']}" for r in facs
        if r['city'] and r['cc']
    )
    top_city = city.most_common(20)
    p2 = go.Figure()
    p2.add_trace(go.Bar(
        x=[n for _, n in top_city][::-1],
        y=[c for c, _ in top_city][::-1],
        orientation='h',
        marker_color=[
            country_color(c.split(', ')[-1])
            for c, _ in top_city][::-1],
        text=[str(n) for _, n in top_city][::-1],
        textposition='outside',
    ))
    p2.update_layout(
        title='② Top-20 DC hub 城市 · ranking by facility count',
        xaxis=dict(title='# DCs'), yaxis=dict(title=''),
        height=600, showlegend=False, margin=dict(l=240),
    )

    # P3: anycast PoP geography vs DC geography
    # Count PoPs per country from laces
    laces_cc = Counter(r['cc'] for r in laces if r['cc'])
    common = set(cc_count) | set(laces_cc)
    # Order by DC count desc
    ordered = sorted(common, key=lambda c: -cc_count.get(c, 0))[:20]
    p3 = go.Figure()
    p3.add_trace(go.Bar(
        x=ordered,
        y=[cc_count.get(c, 0) for c in ordered],
        name='# DCs (PeeringDB Facility)',
        marker_color=COLORS['cyan'],
    ))
    p3.add_trace(go.Bar(
        x=ordered,
        y=[laces_cc.get(c, 0) / 10 for c in ordered],
        name='# Anycast PoP rows / 10 (LACES)',
        marker_color=COLORS['orange'],
    ))
    p3.update_layout(
        title='③ DC 实体 vs Anycast PoP 投射 · physical DCs vs '
              'measurement-level anycast PoPs (scaled)',
        yaxis=dict(title='count'),
        barmode='group', height=460,
    )

    # ─── Ownership Axis ───────────────────────────────────────────

    # P4: top-25 operators
    op = Counter(r['operator'] for r in facs if r['operator'])
    top_op = op.most_common(25)
    p4 = go.Figure()
    p4.add_trace(go.Bar(
        x=[n for _, n in top_op][::-1],
        y=[o[:60] for o, _ in top_op][::-1],
        orientation='h',
        marker_color=COLORS['purple'],
        text=[str(n) for _, n in top_op][::-1],
        textposition='outside',
    ))
    p4.update_layout(
        title='④ Top-25 DC 运营商 · by facility count',
        xaxis=dict(title='# DCs operated'),
        height=720, showlegend=False, margin=dict(l=300),
    )

    # P5: operator-country bilateral — how many countries each operator spans
    op_cc = defaultdict(set)
    for r in facs:
        if r['operator'] and r['cc']:
            op_cc[r['operator']].add(r['cc'])
    span = sorted(op_cc.items(), key=lambda kv: -len(kv[1]))[:20]
    p5 = go.Figure()
    p5.add_trace(go.Bar(
        x=[len(v) for _, v in span][::-1],
        y=[k[:50] for k, _ in span][::-1],
        orientation='h',
        marker_color=[
            COLORS['red'] if len(v) > 15 else COLORS['orange'] if len(v) > 5
            else COLORS['cyan']
            for _, v in span][::-1],
        text=[f'{len(v)} countries · {op[k]:,} DCs'
              for k, v in span][::-1],
        textposition='outside',
    ))
    p5.update_layout(
        title='⑤ 跨国运营商 · how many countries each top-20 operator spans',
        xaxis=dict(title='# countries'), height=600,
        margin=dict(l=280), showlegend=False,
    )

    # P6: AWS region distribution (from aws_prefixes.csv)
    if aws:
        aws_cc = Counter(r['cc'] for r in aws if r['cc'])
        top_aws = aws_cc.most_common(15)
        p6 = go.Figure()
        p6.add_trace(go.Bar(
            x=[c for c, _ in top_aws],
            y=[n for _, n in top_aws],
            marker_color=[country_color(c) for c, _ in top_aws],
            text=[str(n) for _, n in top_aws],
            textposition='outside',
        ))
        p6.update_layout(
            title=f'⑥ AWS 区域分布 · {len(aws):,} AWS GeoPrefix × '
                  f'{len(aws_cc)} countries',
            xaxis=dict(title='country'),
            yaxis=dict(title='# AWS prefixes'),
            height=440, showlegend=False,
        )
    else:
        p6 = None

    # ─── Temporal Axis (time-series) ───────────────────────────────

    # Gather per-snapshot metrics
    ts_metrics = []
    for s in snaps:
        facs_s = _read(CACHE / s / 'facilities.csv')
        memb_s = _read(CACHE / s / 'facility_members.csv')
        ixps_s = _read(CACHE / s / 'facility_ixps.csv')
        ts_metrics.append({
            'snap': s,
            'n_fac': len(facs_s),
            'n_ops': len({r['operator'] for r in facs_s if r['operator']}),
            'n_cc': len({r['cc'] for r in facs_s if r['cc']}),
            'n_as_fac_edges': len(memb_s),
            'n_ixp_colo': len(ixps_s),
            'ops': Counter(r['operator'] for r in facs_s if r['operator']),
            'cc_count': Counter(r['cc'] for r in facs_s if r['cc']),
        })

    # P7: DC count over time (global + top-5 countries)
    p7 = go.Figure()
    xs = [m['snap'] for m in ts_metrics]
    p7.add_trace(go.Scatter(
        x=xs, y=[m['n_fac'] for m in ts_metrics], mode='lines+markers',
        name='Global DCs', line=dict(color=COLORS['cyan'], width=3),
    ))
    # Plot top-5 countries separately
    top5_cc = [c for c, _ in cc_count.most_common(5)]
    for c in top5_cc:
        p7.add_trace(go.Scatter(
            x=xs,
            y=[m['cc_count'].get(c, 0) for m in ts_metrics],
            mode='lines+markers', name=c,
            line=dict(color=country_color(c), width=2),
            yaxis='y2',
        ))
    p7.update_layout(
        title='⑦ DC 数时序 · global total + top-5 countries',
        yaxis=dict(title='Global # DCs'),
        yaxis2=dict(title='Per-country # DCs', overlaying='y',
                    side='right'),
        height=500,
    )

    # P8: operator churn — top-15 operators over time
    top15_ops = [o for o, _ in op.most_common(15)]
    p8 = go.Figure()
    for o_idx, o in enumerate(top15_ops):
        p8.add_trace(go.Scatter(
            x=xs,
            y=[m['ops'].get(o, 0) for m in ts_metrics],
            mode='lines+markers', name=o[:40],
            line=dict(width=2),
        ))
    p8.update_layout(
        title='⑧ Top-15 运营商 DC 数时序 · ownership changes',
        yaxis=dict(title='# DCs operated'),
        height=560,
    )

    # P9: AWS region growth (only 2026-02, 2026-04 have data)
    aws_ts = []
    for s in snaps:
        aws_s = _read(CACHE / s / 'aws_prefixes.csv')
        aws_ts.append({'snap': s,
                       'n_aws_pfx': len(aws_s),
                       'n_cc': len({r['cc'] for r in aws_s if r['cc']})})
    p9 = go.Figure()
    p9.add_trace(go.Bar(
        x=[m['snap'] for m in aws_ts],
        y=[m['n_aws_pfx'] for m in aws_ts],
        marker_color=[COLORS['red'] if m['n_aws_pfx'] else COLORS['cyan']
                      for m in aws_ts],
        text=[f'{m["n_aws_pfx"]:,}' if m['n_aws_pfx'] else 'n/a'
              for m in aws_ts],
        textposition='outside',
    ))
    p9.update_layout(
        title='⑨ AWS GeoPrefix 覆盖时序 · amazon.aws_ip_ranges crawler '
              'introduced 2026-02',
        yaxis=dict(title='# AWS prefixes'),
        height=380, showlegend=False,
    )

    # ─── Routing Axis ──────────────────────────────────────────────

    # P10: Facility AS-density distribution (facility size histogram)
    fac_as = Counter()
    for r in members:
        fac_as[r['facility']] += 1
    sizes = sorted(fac_as.values(), reverse=True)
    # Histogram on log scale
    p10 = go.Figure()
    bins = [1, 2, 5, 10, 25, 50, 100, 250, 500, 1000, 10000]
    bin_counts = [0] * (len(bins) - 1)
    for n in sizes:
        for i in range(len(bins) - 1):
            if bins[i] <= n < bins[i + 1]:
                bin_counts[i] += 1
                break
    bin_labels = [f'{bins[i]}–{bins[i+1]-1}' for i in range(len(bins) - 1)]
    p10.add_trace(go.Bar(
        x=bin_labels, y=bin_counts,
        marker_color=COLORS['purple'],
        text=[str(c) for c in bin_counts], textposition='outside',
    ))
    p10.update_layout(
        title=f'⑩ 每 DC 的 AS 数分布 · {len(fac_as):,} DCs with AS '
              f'presence (median={sizes[len(sizes)//2]}, max={sizes[0]})',
        xaxis=dict(title='# AS in facility'),
        yaxis=dict(title='# DCs'),
        height=440, showlegend=False,
    )

    # P11: DC × IXP bipartite top-facilities
    fac_ixp_count = Counter()
    for r in fac_ixps:
        fac_ixp_count[r['facility']] += 1
    top_fac_ixp = fac_ixp_count.most_common(20)
    p11 = go.Figure()
    p11.add_trace(go.Bar(
        x=[n for _, n in top_fac_ixp][::-1],
        y=[c[:60] for c, _ in top_fac_ixp][::-1],
        orientation='h',
        marker_color=COLORS['teal'],
        text=[str(n) for _, n in top_fac_ixp][::-1],
        textposition='outside',
    ))
    p11.update_layout(
        title='⑪ Top-20 IXP 密集 DC · which facility hosts most IXPs',
        xaxis=dict(title='# IXPs colocated'),
        height=640, showlegend=False, margin=dict(l=280),
    )

    # P12: hyperscaler originator AS timeline
    hyper_ts = []
    for s in snaps:
        hs = _read(CACHE / s / 'hyperscaler_originators.csv')
        distinct_as = len({r['asn'] for r in hs})
        hyper_ts.append({'snap': s, 'n_as': distinct_as,
                         'n_rows': len(hs)})
    p12 = go.Figure()
    p12.add_trace(go.Bar(
        x=[m['snap'] for m in hyper_ts],
        y=[m['n_as'] for m in hyper_ts],
        marker_color=COLORS['red'],
        text=[f'{m["n_as"]}' if m['n_as'] else '0' for m in hyper_ts],
        textposition='outside',
    ))
    p12.update_layout(
        title='⑫ Hyperscaler 源 AS 数时序 · only 2026-02+ (crawler new)',
        yaxis=dict(title='# AS originating AWS prefixes'),
        height=380, showlegend=False,
    )

    # Gather headline stats for intro
    top5_op_str = ' · '.join(f'{o} ({n})' for o, n in op.most_common(5))
    global_dc = len(facs)
    n_countries = len(cc_count)
    as_total = sum(fac_as.values())

    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>范围：</b>{latest} 快照 · <b>{global_dc:,}</b> DCs 跨 '
        f'<b>{n_countries}</b> 国 · <b>{as_total:,}</b> 条 AS→DC 出现关系 · '
        f'<b>{len(fac_ixps):,}</b> 条 IXP→DC 共置关系 · '
        f'<b>{len(pdb_nets):,}</b> AS 有 PeeringDB 网络记录'
        f'<br><b>地理集中</b>：US 占 {cc_count.get("US",0)/global_dc*100:.0f}%；'
        f'Top-15 城市占 {sum(n for _, n in city.most_common(15))/sum(city.values())*100:.0f}%。'
        f'<br><b>所有权集中</b>：Top-5 运营商 — {top5_op_str}；'
        f'前 5 家共运营 {sum(n for _, n in op.most_common(5)):,} DCs = '
        f'{sum(n for _, n in op.most_common(5))/global_dc*100:.0f}%。'
        f'<br><b>时序</b>：{len(snaps)} 个快照 '
        f'（{snaps[0]} → {latest}）。'
        f'</p>'
    )
    if len(snaps) == 1:
        intro += warning_block(
            '当前只有 1 个快照的 DC 数据，时序面板 ⑦⑧⑨⑫ 是占位，'
            '等 <code>run_dc_timeseries.sh</code> 把全部 11 dump 跑完再重生成页面。',
            title='时序面板待补 · time-series panels pending',
        )
    else:
        intro += warning_block(
            f'物理层限制：IYP schema 不含海缆（submarine cable）/ '
            f'光纤路径节点；本页的"routing"轴是 AS×DC 共置 + IXP×DC 共置，'
            f'不是物理传输路径。完整物理拓扑需接入 TeleGeography / '
            f'PacketClearingHouse 外部数据。',
            title='Scope 说明 · physical-layer out of scope',
        )

    # Collate
    figs = [p1, p2, p3, p4, p5]
    if p6 is not None:
        figs.append(p6)
    figs += [p7, p8, p9, p10, p11, p12]
    for f in figs:
        apply_plotly_theme(f)

    parts = []
    first = True
    for f in figs:
        parts.append(to_html(
            f, include_plotlyjs=('inline' if first else False),
            full_html=False, default_height='480px'))
        first = False

    banner = (
        '<div class="step-banner">'
        '<h1>国际数据中心层 · International Data Centers in IYP</h1>'
        '<h2>Geography · Ownership · Temporal · Routing · '
        f'{global_dc:,} facilities / {len(cc_count)} countries / '
        f'{as_total:,} AS presence</h2>'
        '</div><div class="step-footer">datacenters · '
        'facilities.csv + facility_members.csv + facility_ixps.csv × '
        f'{len(snaps)} snapshots</div>'
    )
    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>DC · Data Centers</title>'
        f'{BANNER_CSS}</head><body>{banner}'
        f'<div class="content">{intro}{"".join(parts)}</div></body></html>'
    )
    out_path = OUT / 'datacenters.html'
    out_path.write_text(html, encoding='utf-8')
    mirror = REPO / 'analysis' / 'countries' / 'html' / 'datacenters.html'
    mirror.write_text(html, encoding='utf-8')
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    print(f'wrote {mirror}')

    # Also dump metrics JSON
    metrics_path = REPO / 'analysis' / 'new_angles' / 'data' \
        / 'datacenters_metrics.json'
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(
        json.dumps({
            'latest_snap': latest,
            'n_snaps': len(snaps),
            'global_dc': global_dc,
            'n_countries': n_countries,
            'top_metros': top_city[:20],
            'top_operators': top_op[:25],
            'top_fac_by_as': [(r['name'], r['cc'], r['net_count'],
                               r['ix_count'])
                              for r in sorted(
                                  facs,
                                  key=lambda r: int(r['net_count'])
                                  if r['net_count'] else 0,
                                  reverse=True)[:25]],
        }, indent=2, default=str),
        encoding='utf-8',
    )
    print(f'wrote {metrics_path}')


if __name__ == '__main__':
    build()
