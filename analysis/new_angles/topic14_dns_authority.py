"""Topic 14: Global DNS authoritative NS concentration.

Reads dns_authority_top500.csv (top 500 NS by domain count) and
ns_to_as.csv (which AS hosts each NS). Aggregates to "who runs the
world's DNS" at both NS and AS level.
"""
import csv
import os
import re
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


def _read(p):
    return list(csv.DictReader(open(p, encoding='utf-8'))) \
        if p.exists() else []


def _operator(ns_name):
    """Extract likely operator from NS hostname (2nd-level domain)."""
    parts = ns_name.strip('.').split('.')
    if len(parts) >= 2:
        return '.'.join(parts[-2:])
    return ns_name


def load():
    as_cc = {int(r['asn']): r['cc'] for r in _read(CACHE / 'as_country.csv')
             if r.get('asn', '').isdigit()}
    asn_org = {int(r['asn']): r.get('org_name', '') or ''
               for r in _read(COMPLEX / 'as_organization.csv')
               if r.get('asn', '').isdigit()}

    top_ns = []
    for r in _read(COMPLEX / 'dns_authority_top500.csv'):
        try:
            top_ns.append({
                'ns': r.get('ns_name', ''),
                'domains': int(r.get('domain_count', 0) or 0),
                'operator': _operator(r.get('ns_name', '')),
            })
        except (ValueError, KeyError):
            pass
    top_ns.sort(key=lambda x: -x['domains'])

    # NS → hosting ASes
    ns_asns = defaultdict(list)
    for r in _read(COMPLEX / 'ns_to_as.csv'):
        ns = r.get('ns_name', '')
        asns_raw = r.get('hosting_asns', '')
        if not ns or not asns_raw:
            continue
        for a in re.split(r'[;|,\s]+', asns_raw):
            a = a.strip()
            if a.isdigit():
                ns_asns[ns].append(int(a))
    return top_ns, ns_asns, as_cc, asn_org


def build():
    import plotly.graph_objects as go
    top_ns, ns_asns, as_cc, asn_org = load()

    # ---- Panel 1: Top-20 operators by domain count (aggregate NS by 2LD) ----
    by_op = Counter()
    for ns in top_ns:
        by_op[ns['operator']] += ns['domains']
    top_ops = by_op.most_common(20)
    p1 = go.Figure()
    p1.add_trace(go.Bar(
        orientation='h',
        y=[op for op, _ in top_ops][::-1],
        x=[c for _, c in top_ops][::-1],
        marker_color=COLORS['cyan'],
        text=[f'{c:,}' for _, c in top_ops][::-1],
        textposition='outside',
    ))
    p1.update_layout(
        title='① Top-20 DNS 权威运营商 · Top-20 NS operators (by domain count)',
        xaxis=dict(title='# domains hosted'),
        height=620, margin=dict(l=200), showlegend=False,
    )

    # ---- Panel 2: Top-20 operators → primary country of hosting AS ----
    op_cc = Counter()
    for ns in top_ns:
        asns = ns_asns.get(ns['ns'], [])
        if not asns:
            continue
        cc_counts = Counter(as_cc.get(a) for a in asns if as_cc.get(a))
        if cc_counts:
            primary = cc_counts.most_common(1)[0][0]
            op_cc[primary] += ns['domains']
    ordered = op_cc.most_common(12)
    p2 = go.Figure()
    p2.add_trace(go.Bar(
        x=[c for c, _ in ordered], y=[n for _, n in ordered],
        marker_color=[country_color(c) if c in TARGET else COLORS['purple']
                      for c, _ in ordered],
        text=[f'{n:,}' for _, n in ordered], textposition='outside',
    ))
    p2.update_layout(
        title='② Top-500 NS 所在国分布 · Where are the top-500 NS hosted?',
        yaxis=dict(title='# domains served'),
        xaxis=dict(title='country'),
        height=480, showlegend=False,
    )

    # ---- Panel 3: HHI on operators ----
    p3 = go.Figure()
    total_d = sum(c for _, c in by_op.most_common())
    shares = [c / total_d for _, c in by_op.most_common()]
    hhi = sum(s * s for s in shares) * 10000
    p3.add_trace(go.Scatter(
        x=list(range(1, 21)),
        y=[c / total_d * 100 for _, c in top_ops],
        mode='lines+markers', line=dict(color=COLORS['orange'], width=2.5),
        marker=dict(size=9),
    ))
    p3.add_annotation(
        x=10, y=max([c / total_d * 100 for _, c in top_ops]) * 0.8,
        text=f'Top-5 占 {sum(c/total_d*100 for _, c in top_ops[:5]):.1f}%<br>'
             f'HHI (on top-500) = <b>{hhi:.0f}</b>',
        showarrow=False, bgcolor='rgba(10,20,35,0.8)',
        font=dict(color=TEXT_PRIMARY, size=13),
    )
    p3.update_layout(
        title='③ DNS 运营商市场份额曲线 · Top-20 operator share',
        xaxis=dict(title='rank'), yaxis=dict(title='% of top-500 domains'),
        height=440, showlegend=False,
    )

    # ---- Panel 4: Top-15 NS detail ----
    top15 = top_ns[:15]
    p4 = go.Figure()
    ns_ccs = []
    for ns in top15:
        asns = ns_asns.get(ns['ns'], [])
        ccs = Counter(as_cc.get(a) for a in asns if as_cc.get(a))
        primary = ccs.most_common(1)[0][0] if ccs else '?'
        ns_ccs.append(primary)
    p4.add_trace(go.Bar(
        orientation='h',
        y=[f'{n["ns"]} ({cc})'
           for n, cc in zip(top15, ns_ccs)][::-1],
        x=[n['domains'] for n in top15][::-1],
        marker_color=[country_color(cc) if cc in TARGET else COLORS['purple']
                      for cc in ns_ccs][::-1],
        text=[f'{n["domains"]:,}' for n in top15][::-1],
        textposition='outside',
    ))
    p4.update_layout(
        title='④ Top-15 单个 NS · Biggest single-NS server by domain count',
        xaxis=dict(title='# domains'),
        height=560, margin=dict(l=260), showlegend=False,
    )

    from plotly.io import to_html
    for fig in (p1, p2, p3, p4):
        apply_plotly_theme(fig)
    parts = []; first = True
    for fig in (p1, p2, p3, p4):
        parts.append(to_html(
            fig, include_plotlyjs=('inline' if first else False),
            full_html=False, default_height='520px'))
        first = False

    top_op_name, top_op_count = top_ops[0]
    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>数据：</b>OpenINTEL 的 Top-500 权威 NS 服务器，按所托管域名数排序。'
        f'交叉 ns_to_as 得到每个 NS 所在的托管 AS，再映射到国家。'
        f'<br><b>Scope:</b> 500 NS · {len(by_op)} 独立运营商 · '
        f'最大运营商 <b>{top_op_name}</b> 托管 {top_op_count:,} 域名。'
        f'HHI (on 500) ≈ {sum((c/sum(by_op.values()))**2 for _,c in by_op.most_common())*10000:.0f}'
        f'</p>'
    )

    banner = (
        '<div class="step-banner">'
        '<h1>全球 DNS 权威集中度 · Global DNS Authority Concentration</h1>'
        '<h2>Top-500 authoritative NS · operator concentration + hosting country</h2>'
        '</div>'
        '<div class="step-footer">topic 14 · offline · '
        'OpenINTEL dns_authority_top500</div>'
    )
    out_path = OUT / 'topic14_dns_authority.html'
    out_path.write_text(
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>全球 DNS 权威集中度 · DNS Authority Concentration</title>'
        f'{BANNER_CSS}</head><body>'
        f'{banner}<div class="content">{intro}'
        f'{"".join(parts)}</div></body></html>',
        encoding='utf-8',
    )
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    print(f'top-5 operators: {top_ops[:5]}')


if __name__ == '__main__':
    build()
