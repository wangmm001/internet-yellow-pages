"""Topic 16: IXP session reality check — Alice-LG live vs PeeringDB declared.

Alice-LG crawlers (13 IXPs: AMS-IX, DE-CIX, LINX, Netnod, SIX, BCIX, DD-IX,
IX.br, IXAustralia, Megaport, NZIX, PIX, SFMIX, TopIX) expose live
route-server data — each MEMBER_OF edge carries {state, uptime,
routes_received}. PeeringDB (cached as as_ixp_membership.csv via the
complex-network extract) is the declared membership list. This topic
asks: how many "declared" members are never in Established state?
"""
import csv
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.china.common import (  # noqa: E402
    BANNER_CSS, COLORS, TEXT_PRIMARY, TEXT_SECONDARY,
    apply_plotly_theme, country_color,
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


def _read(p):
    return list(csv.DictReader(open(p, encoding='utf-8'))) \
        if p.exists() else []


def _placeholder(reason):
    """Emit a placeholder HTML when data is missing."""
    banner = (
        '<div class="step-banner">'
        '<h1>IXP 会话真伪对照 · IXP Session Reality Check</h1>'
        '<h2>Alice-LG live route-server data vs PeeringDB declared '
        'membership</h2>'
        '</div>'
        '<div class="step-footer">topic 16 · placeholder</div>'
    )
    intro = (
        f'<p style="padding:0 16px;margin:16px 0;color:{COLORS["orange"]};'
        f'border-left:3px solid {COLORS["orange"]};padding-left:14px;'
        f'font-size:13px">⚠️ <b>数据缺口：</b>{reason}</p>'
    )
    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>IXP 会话真伪对照 · IXP Reality Check</title>'
        f'{BANNER_CSS}</head><body>{banner}'
        f'<div class="content">{intro}</div></body></html>'
    )
    for dest in (OUT / 'topic16_ixp_reality.html',
                 REPO / 'analysis' / 'countries' / 'html' /
                 'topic16_ixp_reality.html'):
        dest.write_text(html, encoding='utf-8')
    print(f'topic 16: placeholder ({reason})')


def build():
    import plotly.graph_objects as go
    from plotly.io import to_html

    live = _read(CACHE / 'ixp_live_members.csv')
    declared = _read(COMPLEX / 'as_ixp_membership.csv')
    as_cc = {int(r['asn']): r['cc'] for r in _read(CACHE / 'as_country.csv')
             if r.get('asn', '').isdigit()}

    if not live:
        return _placeholder(
            '<code>ixp_live_members.csv</code> 为空——Alice-LG 13 个 IXP '
            'crawler 未运行或 MEMBER_OF 边的 reference_name 模式不匹配。')

    # --- prepare indices
    # live: (asn, ixp_name, source, state, uptime, routes_received, ...)
    # declared: from complex_network (asn, ixp_id, ixp_name, country, ...)
    live_by_asn_ixp = {}  # (asn, ixp) -> row
    for r in live:
        try:
            asn = int(r['asn'])
        except (ValueError, KeyError):
            continue
        ixp = r.get('ixp_name') or r.get('source', '').split('.')[-1]
        live_by_asn_ixp[(asn, ixp)] = r

    # Alice-LG IXP list
    alice_ixps = sorted({k[1] for k in live_by_asn_ixp.keys()})

    # For each alice_lg IXP, compute:
    #   active_count = # live members with state='Established'
    #   declared_count = # members from peeringdb for the same IXP (by name)
    # We need to fuzzy-match declared IXP names to alice_lg names.
    decl_by_ixp = defaultdict(set)
    for r in declared:
        ixp = r.get('ixp_name', '') or r.get('ixp', '')
        try:
            asn = int(r.get('asn', 0))
        except (ValueError, KeyError):
            continue
        decl_by_ixp[ixp].add(asn)

    def _norm(s):
        return ''.join(c.lower() for c in (s or '') if c.isalnum())

    # Build per-IXP reality ratio
    per_ixp = []
    for ixp in alice_ixps:
        members = [r for (a, i), r in live_by_asn_ixp.items() if i == ixp]
        active = sum(1 for r in members
                     if r.get('state', '').lower() in
                     ('up', 'established', 'active'))
        live_asns = {int(r['asn']) for r in members
                     if r.get('asn', '').isdigit()}
        # Try to find declared peers by fuzzy match on IXP name
        best_match = None; best_overlap = 0
        ixp_n = _norm(ixp)
        for dixp, dasns in decl_by_ixp.items():
            dn = _norm(dixp)
            if ixp_n and (ixp_n in dn or dn in ixp_n):
                overlap = len(live_asns & dasns)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_match = (dixp, dasns)
        dec_asns = best_match[1] if best_match else set()
        per_ixp.append({
            'ixp': ixp,
            'live_total': len(members),
            'active': active,
            'declared': len(dec_asns),
            'declared_match': best_match[0] if best_match else '—',
            'dark': len(dec_asns - live_asns),  # declared but not seen live
            'ghost': len(live_asns - dec_asns),  # live but not declared
        })

    # --- P1: declared vs active bar chart (13 IXPs) ---
    per_ixp.sort(key=lambda r: -r['declared'])
    p1 = go.Figure()
    xs = [r['ixp'] for r in per_ixp]
    p1.add_trace(go.Bar(
        name='PeeringDB declared', x=xs,
        y=[r['declared'] for r in per_ixp],
        marker_color=COLORS['cyan'],
        text=[r['declared'] for r in per_ixp],
        textposition='outside',
    ))
    p1.add_trace(go.Bar(
        name='Alice-LG active (Established)', x=xs,
        y=[r['active'] for r in per_ixp],
        marker_color=COLORS['green'],
        text=[r['active'] for r in per_ixp],
        textposition='outside',
    ))
    p1.update_layout(
        title='① Declared vs Active · PeeringDB 声称 vs Alice-LG 实测会话',
        barmode='group', height=520,
        xaxis=dict(title='', tickangle=-25),
        yaxis=dict(title='# member ASes'),
        legend=dict(orientation='h', y=-0.3),
    )

    # --- P2: Uptime CDF per IXP ---
    uptimes_by_ixp = defaultdict(list)
    for (asn, ixp), r in live_by_asn_ixp.items():
        try:
            u = float(r.get('uptime') or 0)
            if u > 0:
                uptimes_by_ixp[ixp].append(u / 86400)  # seconds → days
        except ValueError:
            continue
    p2 = go.Figure()
    for ixp, vals in uptimes_by_ixp.items():
        if len(vals) < 10:
            continue
        vals = sorted(vals)
        cdf = [i / len(vals) for i in range(1, len(vals) + 1)]
        p2.add_trace(go.Scatter(
            x=vals, y=cdf, mode='lines', name=ixp,
            line=dict(width=1.5),
        ))
    p2.update_layout(
        title='② 会话正常运行时间 CDF · Session uptime (days) per IXP',
        xaxis=dict(title='uptime (days)', type='log'),
        yaxis=dict(title='CDF'),
        height=480,
    )

    # --- P3: Top-20 "dark peers" — declared in peeringdb but never seen ---
    # Find declared ASNs that never appear in live for an IXP, weighted by
    # how many IXPs they're declared in
    dark_count = Counter()
    for r in per_ixp:
        dixp_name = r['declared_match']
        if dixp_name == '—':
            continue
        live_asns = {int(x['asn']) for x in live if x.get('asn', '').isdigit()
                     and x.get('ixp_name') == r['ixp']}
        declared_here = decl_by_ixp.get(dixp_name, set())
        dark = declared_here - live_asns
        for asn in dark:
            dark_count[asn] += 1
    top_dark = dark_count.most_common(20)
    p3 = go.Figure()
    if top_dark:
        p3.add_trace(go.Bar(
            orientation='h',
            y=[f'AS{a} ({as_cc.get(a, "?")})'
               for a, _ in top_dark][::-1],
            x=[c for _, c in top_dark][::-1],
            marker_color=[country_color(as_cc.get(a, '?'))
                          if as_cc.get(a) in TARGET else COLORS['purple']
                          for a, _ in top_dark][::-1],
            text=[c for _, c in top_dark][::-1],
            textposition='outside',
        ))
    p3.update_layout(
        title='③ Top-20 "声称但不活跃" AS · Dark peers '
              '(declared in N IXPs but not live at any)',
        xaxis=dict(title='# IXPs declared-but-dark'),
        height=560, margin=dict(l=180),
    )

    # --- P4: country reality ratio: live active / declared per country ---
    live_by_cc = Counter()
    decl_by_cc = Counter()
    for (asn, ixp), r in live_by_asn_ixp.items():
        cc = as_cc.get(asn)
        if cc and r.get('state', '').lower() in (
                'up', 'established', 'active'):
            live_by_cc[cc] += 1
    for ixp, asns in decl_by_ixp.items():
        for asn in asns:
            cc = as_cc.get(asn)
            if cc:
                decl_by_cc[cc] += 1
    rows4 = []
    for cc in TARGET:
        live_n = live_by_cc.get(cc, 0)
        decl_n = decl_by_cc.get(cc, 0)
        if decl_n:
            rows4.append({'cc': cc, 'live': live_n, 'declared': decl_n,
                          'ratio': live_n / decl_n * 100})
    rows4.sort(key=lambda r: -r['ratio'])
    p4 = go.Figure()
    p4.add_trace(go.Bar(
        x=[f'{COUNTRY_NAME[r["cc"]]} {r["cc"]}' for r in rows4],
        y=[r['ratio'] for r in rows4],
        marker_color=[country_color(r['cc']) for r in rows4],
        text=[f'{r["ratio"]:.0f}%<br>({r["live"]}/{r["declared"]})'
              for r in rows4],
        textposition='outside',
    ))
    p4.update_layout(
        title='④ 国家级"真实率" · Live active / declared per country '
              '(sample limited to Alice-LG IXPs)',
        yaxis=dict(title='% live / declared', rangemode='tozero'),
        xaxis=dict(title='', tickangle=-15),
        height=460, showlegend=False,
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

    # Top-level statistics
    total_live = len(live_by_asn_ixp)
    total_active = sum(1 for r in live_by_asn_ixp.values()
                       if r.get('state', '').lower() in
                       ('up', 'established', 'active'))
    total_dark = sum(r['dark'] for r in per_ixp)
    total_declared = sum(r['declared'] for r in per_ixp)

    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>数据：</b>Alice-LG 13 个 IXP 实时 route-server 拉到 '
        f'<b>{total_live:,}</b> 条 MEMBER_OF 边，其中 '
        f'<b>{total_active:,}</b>（{total_active/max(total_live,1)*100:.0f}%）'
        f'当前 state=Established。PeeringDB 在相同 IXP 子集里声称 '
        f'<b>{total_declared:,}</b> 个成员，差集约 <b>{total_dark:,}</b> '
        f'个"声称但不活跃"。'
        f'<br><b>含义：</b>PeeringDB 是自报数据，成员加入后很少主动退出；'
        f'real-time 会话状态才能反映真实连通性。本页用 13 个 Alice-LG '
        f'IXP 作样本；剩余全球 ~1000 IXP 无 Alice-LG 数据。'
        f'</p>'
    )

    banner = (
        '<div class="step-banner">'
        '<h1>IXP 会话真伪对照 · IXP Session Reality Check</h1>'
        '<h2>Alice-LG 13 × live route-server vs PeeringDB declared · '
        'who declares but never shows up?</h2>'
        '</div>'
        '<div class="step-footer">topic 16 · offline · '
        'alice_lg × peeringdb</div>'
    )

    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>IXP 会话真伪对照 · IXP Reality Check</title>'
        f'{BANNER_CSS}</head><body>{banner}'
        f'<div class="content">{intro}{"".join(parts)}</div></body></html>'
    )
    out_path = OUT / 'topic16_ixp_reality.html'
    out_path.write_text(html, encoding='utf-8')
    mirror = REPO / 'analysis' / 'countries' / 'html' / \
        'topic16_ixp_reality.html'
    mirror.write_text(html, encoding='utf-8')
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    print(f'live={total_live}  active={total_active}  dark={total_dark}')
    for r in per_ixp[:5]:
        print(f'  {r["ixp"]:20}  live={r["live_total"]:4}  '
              f'active={r["active"]:4}  declared={r["declared"]:4}  '
              f'dark={r["dark"]:4}')


if __name__ == '__main__':
    build()
