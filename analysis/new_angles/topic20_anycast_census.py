"""Topic 20: Anycast geographic census — UTwente LACES.

LACES v4/v6 GeoPrefixes with LOCATED_IN→Point give per-PoP geographic
location for anycast prefixes. This gives a true PoP-count view of
anycast deployment (vs bgptools which only tags prefixes Anycast=true).
"""
import csv
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.china.common import (  # noqa: E402
    BANNER_CSS, COLORS, TEXT_PRIMARY, TEXT_SECONDARY,
    apply_plotly_theme, country_color, warning_block,
)

REPO = Path(__file__).resolve().parent.parent.parent
CACHE = REPO / 'data_cache' / 'new_angles'
OUT = REPO / 'analysis' / 'new_angles' / 'html'
OUT.mkdir(parents=True, exist_ok=True)

TARGET = ['US', 'CN', 'JP', 'IN', 'DE', 'GB', 'FR', 'NL', 'RU']
COUNTRY_NAME = {
    'US': '美国', 'CN': '中国', 'JP': '日本', 'IN': '印度', 'DE': '德国',
    'GB': '英国', 'FR': '法国', 'NL': '荷兰', 'RU': '俄罗斯',
}


def _read(p):
    return list(csv.DictReader(open(p, encoding='utf-8'))) \
        if p.exists() else []


def _placeholder(reason):
    banner = (
        '<div class="step-banner">'
        '<h1>Anycast 地理普查 · Anycast Geographic Census</h1>'
        '<h2>UTwente LACES per-PoP location data</h2>'
        '</div><div class="step-footer">topic 20 · placeholder</div>'
    )
    intro = warning_block(reason, title='数据缺口 · Data gap')
    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>Anycast 地理普查 · Anycast Census</title>'
        f'{BANNER_CSS}</head><body>{banner}'
        f'<div class="content">{intro}</div></body></html>'
    )
    for dest in (OUT / 'topic20_anycast_census.html',
                 REPO / 'analysis' / 'countries' / 'html' /
                 'topic20_anycast_census.html'):
        dest.write_text(html, encoding='utf-8')
    print(f'topic 20: placeholder ({reason})')


def build():
    import plotly.graph_objects as go
    from plotly.io import to_html

    data = _read(CACHE / 'laces_geoprefix_countries.csv')
    if not data:
        return _placeholder(
            '<code>laces_geoprefix_countries.csv</code> 为空——'
            'utwente.laces_v4/v6 crawler 未运行，或 GeoPrefix-Point 关系缺失。')

    # Group PoPs per prefix
    pops_per_prefix = defaultdict(list)  # prefix -> [(af, cc)]
    explicit_anycast = set()
    for r in data:
        pfx = r.get('prefix')
        if not pfx:
            continue
        try:
            af = int(r.get('af') or 4)
        except (ValueError, KeyError):
            af = 4
        cc = r.get('cc', '')
        pops_per_prefix[pfx].append((af, cc))
        if r.get('is_anycast') in ('1', 1, True, 'True'):
            explicit_anycast.add(pfx)
    # The Anycast tag isn't always propagated to GeoPrefix nodes in some
    # dumps. LACES's purpose is anycast census — treat any prefix with
    # PoPs in 2+ distinct countries as anycast.
    anycast_pfx = set(explicit_anycast)
    for pfx, pops in pops_per_prefix.items():
        ccs = {cc for (af, cc) in pops if cc}
        if len(ccs) >= 2:
            anycast_pfx.add(pfx)

    # --- P1: # anycast prefixes per country (where PoPs land) ---
    cc_pops = Counter()
    for pfx in anycast_pfx:
        ccs = {cc for (af, cc) in pops_per_prefix[pfx] if cc}
        for cc in ccs:
            cc_pops[cc] += 1
    top_cc = cc_pops.most_common(20)
    p1 = go.Figure()
    if top_cc:
        p1.add_trace(go.Bar(
            x=[cc for cc, _ in top_cc],
            y=[cc_pops[cc] for cc, _ in top_cc],
            marker_color=[country_color(cc) if cc in TARGET
                          else COLORS['purple']
                          for cc, _ in top_cc],
            text=[f'{cc_pops[cc]:,}' for cc, _ in top_cc],
            textposition='outside',
        ))
    p1.update_layout(
        title='① 每国承载的 Anycast 前缀数 · '
              '# distinct anycast prefixes with a PoP in country',
        xaxis=dict(title='country'),
        yaxis=dict(title='# anycast prefixes'),
        height=460, showlegend=False,
    )

    # --- P2: PoPs-per-prefix distribution ---
    pop_counts = Counter()
    for pfx in anycast_pfx:
        ccs = {cc for (af, cc) in pops_per_prefix[pfx] if cc}
        pop_counts[len(ccs)] += 1
    p2 = go.Figure()
    if pop_counts:
        xs = sorted(pop_counts.keys())
        p2.add_trace(go.Bar(
            x=xs, y=[pop_counts[x] for x in xs],
            marker_color=COLORS['cyan'],
            text=[pop_counts[x] for x in xs],
            textposition='outside',
        ))
    p2.update_layout(
        title='② PoP/前缀分布 · # anycast prefixes by # countries with PoP',
        xaxis=dict(title='# distinct countries a PoP lands in'),
        yaxis=dict(title='# prefixes (log)', type='log'),
        height=440, showlegend=False,
    )

    # --- P3: v4 vs v6 deployment per country (scatter) ---
    v4_per_cc = Counter(); v6_per_cc = Counter()
    for pfx, pops in pops_per_prefix.items():
        if pfx not in anycast_pfx:
            continue
        ccs_v4 = {cc for (af, cc) in pops if af == 4 and cc}
        ccs_v6 = {cc for (af, cc) in pops if af == 6 and cc}
        for cc in ccs_v4:
            v4_per_cc[cc] += 1
        for cc in ccs_v6:
            v6_per_cc[cc] += 1

    ccs_all = sorted(set(v4_per_cc) | set(v6_per_cc),
                     key=lambda c: -(v4_per_cc[c] + v6_per_cc[c]))[:25]
    p3 = go.Figure()
    p3.add_trace(go.Scatter(
        x=[v4_per_cc[c] for c in ccs_all],
        y=[v6_per_cc[c] for c in ccs_all],
        mode='markers+text',
        text=ccs_all, textposition='top center',
        marker=dict(size=14,
                    color=[country_color(c) if c in TARGET
                           else COLORS['purple'] for c in ccs_all],
                    line=dict(color=TEXT_PRIMARY, width=1)),
        showlegend=False,
    ))
    # Diagonal
    m = max(max([v4_per_cc[c] for c in ccs_all] + [1]),
            max([v6_per_cc[c] for c in ccs_all] + [1]))
    p3.add_shape(type='line', x0=1, y0=1, x1=m, y1=m,
                 line=dict(color=TEXT_SECONDARY, dash='dash', width=1))
    p3.update_layout(
        title='③ v4 vs v6 Anycast 部署 · IPv4 × IPv6 parity per country',
        xaxis=dict(title='# anycast v4 prefixes with PoP', type='log'),
        yaxis=dict(title='# anycast v6 prefixes with PoP', type='log'),
        height=500,
    )

    # --- P4: Most-spread prefixes (highest PoP count) ---
    spread = sorted(
        [(pfx, len({cc for (af, cc) in pops if cc}))
         for pfx, pops in pops_per_prefix.items()
         if pfx in anycast_pfx],
        key=lambda t: -t[1],
    )[:20]
    p4 = go.Figure()
    if spread:
        p4.add_trace(go.Bar(
            orientation='h',
            y=[f'{pfx} ({n}c)' for pfx, n in spread][::-1],
            x=[n for _, n in spread][::-1],
            marker_color=COLORS['orange'],
            text=[n for _, n in spread][::-1],
            textposition='outside',
        ))
    p4.update_layout(
        title='④ Top-20 最广分布 Anycast 前缀 · '
              'Most-geographically-spread anycast prefixes',
        xaxis=dict(title='# distinct countries with PoP'),
        height=560, margin=dict(l=180), showlegend=False,
    )

    figs = [p1, p2, p3, p4]
    for f in figs:
        apply_plotly_theme(f)
    parts = []; first = True
    for f in figs:
        parts.append(to_html(
            f, include_plotlyjs=('inline' if first else False),
            full_html=False, default_height='500px'))
        first = False

    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>数据：</b>UTwente LACES v4/v6——<b>{len(pops_per_prefix):,}</b> '
        f'独立前缀，其中 <b>{len(anycast_pfx):,}</b> 被标记 Anycast。'
        f'共 <b>{len(data):,}</b> 条 PoP 定位记录。'
        f'<br><b>对照：</b>bgptools.anycast_prefixes 只标"是不是 anycast"，'
        f'不给位置。LACES 把每个前缀的多点测量合起来告诉我们 PoP 实际落在'
        f'哪些国家——用来看 CDN 布点、DNS 根服务器地理多样性、'
        f'anycast v4 vs v6 对齐度。'
        f'</p>'
    )

    banner = (
        '<div class="step-banner">'
        '<h1>Anycast 地理普查 · Anycast Geographic Census</h1>'
        '<h2>UTwente LACES · who runs anycast where · v4/v6 parity</h2>'
        '</div><div class="step-footer">topic 20 · offline · '
        'utwente.laces_v4/v6</div>'
    )

    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>Anycast 地理普查 · Anycast Census</title>'
        f'{BANNER_CSS}</head><body>{banner}'
        f'<div class="content">{intro}{"".join(parts)}</div></body></html>'
    )
    out_path = OUT / 'topic20_anycast_census.html'
    out_path.write_text(html, encoding='utf-8')
    mirror = REPO / 'analysis' / 'countries' / 'html' / \
        'topic20_anycast_census.html'
    mirror.write_text(html, encoding='utf-8')
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    print(f'prefixes={len(pops_per_prefix)}  anycast={len(anycast_pfx)}  '
          f'rows={len(data)}')


if __name__ == '__main__':
    build()
