"""Topic 10: BGP observation source diversity (v4 vs v6).

Reveals which ASes are differently visible across IPv4 / IPv6 BGP
collectors. The 2024-10 extract only yielded bgpkit.as2rel_v4 and
v6 as data sources (PCH daily routing snapshots are not connected
via PEERS_WITH), so this is the v4/v6 asymmetry view, not the
full "collector diversity" view originally planned.
"""
import csv
import os
import sys
from collections import defaultdict, Counter
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.china.common import (  # noqa: E402
    BANNER_CSS, COLORS, DARK_BG, DARK_BORDER, DARK_PANEL,
    TEXT_PRIMARY, TEXT_SECONDARY, apply_plotly_theme, country_color,
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


def _read(name):
    p = CACHE / name
    return list(csv.DictReader(open(p, encoding='utf-8'))) if p.exists() else []


def load():
    as_cc = {int(r['asn']): r['cc'] for r in _read('as_country.csv')
             if r.get('asn', '').isdigit()}
    v4, v6 = {}, {}
    for r in _read('collector_observations.csv'):
        try:
            asn = int(r['asn']); n = int(r['peer_count']); src = r['src']
        except (ValueError, KeyError):
            continue
        if 'v4' in src:
            v4[asn] = v4.get(asn, 0) + n
        elif 'v6' in src:
            v6[asn] = v6.get(asn, 0) + n
    return as_cc, v4, v6


def build():
    import plotly.graph_objects as go
    as_cc, v4, v6 = load()
    all_asn = set(v4) | set(v6)
    both = {a for a in all_asn if a in v4 and a in v6}
    only_v4 = {a for a in all_asn if a in v4 and a not in v6}
    only_v6 = {a for a in all_asn if a in v6 and a not in v4}

    # ---- Panel 1: v4 × v6 scatter ----
    xs = [v4[a] for a in both]; ys = [v6[a] for a in both]
    ccs = [as_cc.get(a, '??') for a in both]
    p1 = go.Figure()
    # Highlight target countries
    for cc in TARGET:
        xx = [v4[a] for a in both if as_cc.get(a) == cc]
        yy = [v6[a] for a in both if as_cc.get(a) == cc]
        aa = [a for a in both if as_cc.get(a) == cc]
        if xx:
            p1.add_trace(go.Scatter(
                x=xx, y=yy, mode='markers', name=f'{cc} ({len(xx)})',
                marker=dict(size=6, color=country_color(cc),
                            line=dict(color='#fff', width=0.4)),
                customdata=aa,
                hovertemplate=(f'{cc} AS%{{customdata}}<br>v4 peers=%{{x}}<br>'
                               f'v6 peers=%{{y}}<extra></extra>'),
            ))
    # Others in gray
    other_x = [v4[a] for a in both if as_cc.get(a) not in TARGET]
    other_y = [v6[a] for a in both if as_cc.get(a) not in TARGET]
    p1.add_trace(go.Scatter(
        x=other_x, y=other_y, mode='markers', name='other',
        marker=dict(size=3, color='rgba(142,142,147,0.3)'),
        hoverinfo='skip',
    ))
    p1.update_layout(
        title=f'① v4 × v6 peering 观测对比 · {len(both):,} AS 同时出现于两源',
        xaxis=dict(title='v4 peers observed', type='log'),
        yaxis=dict(title='v6 peers observed', type='log'),
        height=560, legend=dict(orientation='h', y=-0.12),
    )

    # ---- Panel 2: presence breakdown per country ----
    per_cc = defaultdict(lambda: [0, 0, 0])  # both, v4only, v6only
    for a in both:
        cc = as_cc.get(a)
        if cc: per_cc[cc][0] += 1
    for a in only_v4:
        cc = as_cc.get(a)
        if cc: per_cc[cc][1] += 1
    for a in only_v6:
        cc = as_cc.get(a)
        if cc: per_cc[cc][2] += 1
    order = sorted(TARGET, key=lambda c: -sum(per_cc[c]))
    p2 = go.Figure()
    labels = ['both v4+v6', 'v4 only', 'v6 only']
    colors = [COLORS['green'], COLORS['cyan'], COLORS['orange']]
    for i, lbl in enumerate(labels):
        p2.add_trace(go.Bar(
            x=[f'{COUNTRY_NAME[c]} {c}' for c in order],
            y=[per_cc[c][i] for c in order],
            name=lbl, marker_color=colors[i],
            text=[str(per_cc[c][i]) for c in order],
            textposition='inside',
        ))
    p2.update_layout(
        title='② 各国 AS 在 v4/v6 peering 可见度 · Per-country visibility mix',
        barmode='stack', yaxis=dict(title='# of AS'),
        xaxis=dict(title='', tickangle=-20),
        height=480, legend=dict(orientation='h', y=-0.15),
    )

    # ---- Panel 3: v6 adoption ratio per country ----
    rows = []
    for cc in TARGET:
        b, o4, o6 = per_cc[cc]
        total = b + o4 + o6
        if total == 0:
            continue
        v6_present = b + o6
        rows.append({'cc': cc, 'total': total, 'v6_present': v6_present,
                     'v6_ratio': v6_present / total * 100})
    rows.sort(key=lambda r: -r['v6_ratio'])
    p3 = go.Figure()
    p3.add_trace(go.Bar(
        x=[f'{COUNTRY_NAME[r["cc"]]} {r["cc"]}' for r in rows],
        y=[r['v6_ratio'] for r in rows],
        marker_color=[country_color(r['cc']) for r in rows],
        text=[f'{r["v6_ratio"]:.1f}%<br>({r["v6_present"]}/{r["total"]})'
              for r in rows], textposition='outside',
    ))
    p3.update_layout(
        title='③ v6 peering 观测覆盖率 · % of country ASes visible on v6',
        yaxis=dict(title='% of observed AS with v6 peers', range=[0, 100]),
        xaxis=dict(title='', tickangle=-20),
        height=480, showlegend=False,
    )

    # ---- Panel 4: top-20 v6-heavy AS (v6_peers > v4_peers) ----
    v6_heavy = [(a, v4.get(a, 0), v6.get(a, 0),
                 v6.get(a, 0) - v4.get(a, 0)) for a in both]
    v6_heavy.sort(key=lambda t: -t[3])
    top20 = v6_heavy[:20]
    p4 = go.Figure()
    p4.add_trace(go.Bar(
        orientation='h',
        y=[f'AS{a} ({as_cc.get(a, "??")})' for a, _, _, _ in top20][::-1],
        x=[d for _, _, _, d in top20][::-1],
        marker_color=[country_color(as_cc.get(a, '??')) for a, _, _, _ in top20][::-1],
        text=[f'v4={v4_c} v6={v6_c}' for _, v4_c, v6_c, _ in top20][::-1],
        textposition='outside',
    ))
    p4.update_layout(
        title='④ Top-20 v6 偏向 AS · ASes with v6-peers > v4-peers (Δ)',
        xaxis=dict(title='v6-peers − v4-peers'),
        height=560, margin=dict(l=200), showlegend=False,
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

    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>数据：</b>bgpkit.as2rel 的 v4 与 v6 两个 peering 观测源。'
        f'<b>{len(all_asn):,}</b> AS 在至少一源可见 · '
        f'<b>{len(both):,}</b> 在两源可见 · '
        f'<b>{len(only_v4):,}</b> 仅 v4 · <b>{len(only_v6):,}</b> 仅 v6。'
        f'<br>v4/v6 可见度差代表 IPv6 部署真实度（登记 ≠ 被观测到）。</p>'
        f'<p style="margin:4px 16px 12px;padding:10px 14px;'
        f'border-left:3px solid #ff9f0a;background:rgba(255,159,10,0.08);'
        f'color:{TEXT_PRIMARY};font-size:13px;border-radius:4px">'
        f'⚠️ <b>PCH collector 缺位：</b>原计划 PCH.daily_routing_snapshots + '
        f'BGPKit.peerstats 4 源对比，但在 2024-10 dump 里 PCH 数据没以 '
        f'PEERS_WITH 关系连出。本页只用 bgpkit v4/v6 双源。</p>'
    )

    banner = (
        '<div class="step-banner">'
        '<h1>BGP 观测源多样性 · BGP Observation Diversity</h1>'
        '<h2>v4 vs v6 peering visibility · bgpkit.as2rel dual-source</h2>'
        '</div>'
        '<div class="step-footer">topic 10 · 2024-10 snapshot · bgpkit v4+v6</div>'
    )
    out_path = OUT / 'topic10_bgp_observation.html'
    out_path.write_text(
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>BGP 观测源多样性 · BGP Observation Diversity</title>'
        f'{BANNER_CSS}</head><body>'
        f'{banner}<div class="content">{intro}'
        f'{"".join(parts)}</div></body></html>',
        encoding='utf-8',
    )
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    print(f'v4={len(v4):,} v6={len(v6):,} both={len(both):,}')


if __name__ == '__main__':
    build()
