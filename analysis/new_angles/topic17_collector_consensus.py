"""Topic 17: BGP peering visibility across sources.

Originally intended for PCH daily routing snapshots (ORIGINATE edges with
per-prefix collector counts). That crawler did not run in the 2026-04 dump
(G14 in schema_gaps). This version uses the bgpkit peerstats crawler
instead — it gives the same "observation redundancy" signal at the
peer-edge level: for each AS, how many peer-ASes are visible via
bgpkit.as2rel_v4 vs as2rel_v6.

Analytical angle:
 · v4 vs v6 observation asymmetry — ASes visible in one family only
 · top by total peer visibility — who sits most-connected in the graph
 · distribution shapes per source
 · country aggregation: where are the v6-invisible ASes
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
OUT = REPO / 'analysis' / 'new_angles' / 'html'
OUT.mkdir(parents=True, exist_ok=True)

TARGET = ['US', 'CN', 'JP', 'IN', 'DE', 'GB', 'FR', 'NL', 'RU']
COUNTRY_NAME = {
    'US': '美国', 'CN': '中国', 'JP': '日本', 'IN': '印度', 'DE': '德国',
    'GB': '英国', 'FR': '法国', 'NL': '荷兰', 'RU': '俄罗斯',
}


def _read_stream(p):
    if not p.exists():
        return iter([])
    return csv.DictReader(open(p, encoding='utf-8'))


def _placeholder(reason):
    banner = (
        '<div class="step-banner">'
        '<h1>BGP 观测冗余度 · Multi-Source Peering Visibility</h1>'
        '<h2>bgpkit peerstats: who is visible in v4 vs v6 sources · '
        'per-AS peer-edge count</h2>'
        '</div><div class="step-footer">topic 17 · placeholder</div>'
    )
    intro = (
        f'<p style="padding:0 16px;margin:16px 0;color:{COLORS["orange"]};'
        f'border-left:3px solid {COLORS["orange"]};padding-left:14px;'
        f'font-size:13px">⚠️ <b>数据缺口：</b>{reason}</p>'
    )
    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>BGP 观测冗余度 · Peering Visibility</title>'
        f'{BANNER_CSS}</head><body>{banner}'
        f'<div class="content">{intro}</div></body></html>'
    )
    for dest in (OUT / 'topic17_collector_consensus.html',
                 REPO / 'analysis' / 'countries' / 'html' /
                 'topic17_collector_consensus.html'):
        dest.write_text(html, encoding='utf-8')
    print(f'topic 17: placeholder ({reason})')


def build():
    import plotly.graph_objects as go
    from plotly.io import to_html

    cs = CACHE / 'collector_observations.csv'
    if not cs.exists() or cs.stat().st_size < 200:
        return _placeholder(
            '<code>collector_observations.csv</code> 为空——'
            'bgpkit.peerstats crawler 未产生 PEERS_WITH 边。')

    # Stream once, build per-AS v4/v6/other peer counts
    as_v4 = {}; as_v6 = {}; as_other = {}
    src_count = Counter()
    for r in _read_stream(cs):
        try:
            asn = int(r['asn']); pc = int(r['peer_count'])
        except (ValueError, KeyError):
            continue
        src = r.get('src', '')
        src_count[src] += 1
        if 'as2rel_v4' in src:
            as_v4[asn] = pc
        elif 'as2rel_v6' in src:
            as_v6[asn] = pc
        else:
            as_other[asn] = pc

    as_cc = {}
    for r in _read_stream(CACHE / 'as_country.csv'):
        try:
            as_cc[int(r['asn'])] = r['cc']
        except (ValueError, KeyError):
            continue

    # --- P1: source breakdown + v4/v6/dual counts
    v4_set = set(as_v4)
    v6_set = set(as_v6)
    dual = v4_set & v6_set
    v4_only = v4_set - v6_set
    v6_only = v6_set - v4_set
    p1 = go.Figure()
    p1.add_trace(go.Bar(
        x=['v4 only', 'v4+v6 双栈', 'v6 only'],
        y=[len(v4_only), len(dual), len(v6_only)],
        marker_color=[COLORS['cyan'], COLORS['green'], COLORS['orange']],
        text=[f'{len(v4_only):,}', f'{len(dual):,}', f'{len(v6_only):,}'],
        textposition='outside',
    ))
    p1.update_layout(
        title='① v4 / v6 观测分组 · # ASes visible in each BGP source',
        xaxis=dict(title=''), yaxis=dict(title='# ASes'),
        height=460, showlegend=False,
    )

    # --- P2: peer-count distribution per source (log-log)
    p2 = go.Figure()
    for name, d, color in [
        ('as2rel_v4', as_v4, COLORS['cyan']),
        ('as2rel_v6', as_v6, COLORS['orange']),
    ]:
        counts = Counter(d.values())
        if not counts:
            continue
        xs = sorted(counts.keys())
        ys = [counts[x] for x in xs]
        p2.add_trace(go.Scatter(
            x=xs, y=ys, mode='markers', name=name,
            marker=dict(size=6, color=color, opacity=0.6),
        ))
    p2.update_layout(
        title='② 每 AS 可见 peer 数量分布 · Per-AS peer-count distribution',
        xaxis=dict(title='# peers observed', type='log'),
        yaxis=dict(title='# ASes', type='log'),
        height=440,
    )

    # --- P3: Top-20 by total visibility (v4 + v6 + other)
    total = {}
    for s in (as_v4, as_v6, as_other):
        for a, c in s.items():
            total[a] = total.get(a, 0) + c
    top20 = sorted(total.items(), key=lambda t: -t[1])[:20]
    p3 = go.Figure()
    p3.add_trace(go.Bar(
        orientation='h',
        y=[f'AS{a} ({as_cc.get(a, "?")})' for a, _ in top20][::-1],
        x=[c for _, c in top20][::-1],
        marker_color=[country_color(as_cc.get(a, '?'))
                      if as_cc.get(a) in TARGET else COLORS['purple']
                      for a, _ in top20][::-1],
        text=[f'{c:,}' for _, c in top20][::-1],
        textposition='outside',
    ))
    p3.update_layout(
        title='③ Top-20 观测最广 AS · sum of peer counts across v4+v6',
        xaxis=dict(title='# peer edges'),
        height=560, margin=dict(l=180), showlegend=False,
    )

    # --- P4: country aggregation — v4/v6 dual-stack rate per country
    cc_v4 = defaultdict(set); cc_v6 = defaultdict(set)
    for asn in v4_set:
        cc = as_cc.get(asn)
        if cc:
            cc_v4[cc].add(asn)
    for asn in v6_set:
        cc = as_cc.get(asn)
        if cc:
            cc_v6[cc].add(asn)
    rows4 = []
    for cc in set(cc_v4) | set(cc_v6):
        v4n = len(cc_v4.get(cc, set()))
        v6n = len(cc_v6.get(cc, set()))
        union = len(cc_v4.get(cc, set()) | cc_v6.get(cc, set()))
        dual_n = len(cc_v4.get(cc, set()) & cc_v6.get(cc, set()))
        if union < 10:
            continue
        rows4.append({
            'cc': cc, 'dual': dual_n, 'union': union,
            'rate': dual_n / union * 100,
        })
    rows4.sort(key=lambda r: -r['rate'])
    top_cc = rows4[:20]
    p4 = go.Figure()
    p4.add_trace(go.Bar(
        x=[r['cc'] for r in top_cc],
        y=[r['rate'] for r in top_cc],
        marker_color=[country_color(r['cc']) if r['cc'] in TARGET
                      else COLORS['purple'] for r in top_cc],
        text=[f'{r["rate"]:.0f}%<br>({r["dual"]}/{r["union"]})'
              for r in top_cc],
        textposition='outside',
    ))
    p4.update_layout(
        title='④ 国家双栈率 · % of observed ASes visible in BOTH v4 and v6 '
              '(top 20 by rate, min 10 ASes)',
        yaxis=dict(title='% dual-stack'),
        xaxis=dict(title=''),
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

    n_total = len(v4_set | v6_set)
    dual_pct = len(dual) / max(n_total, 1) * 100
    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>数据：</b>bgpkit peerstats crawler 产生的 '
        f'PEERS_WITH 边——按源分类后每 AS 在 as2rel_v4 / as2rel_v6 '
        f'里分别有多少可见 peer。共观察到 <b>{n_total:,}</b> 个 AS；'
        f'其中 <b>{len(dual):,}</b>（{dual_pct:.1f}%）同时在 v4 和 v6 '
        f'数据集里被看到（"双栈可见"）。'
        f'<br><b>原计划：</b>本 topic 原设计读 PCH daily_routing_snapshots_* '
        f'的 ORIGINATE 边（每前缀被多少 collector 看到）。但 2026-04 IYP '
        f'dump 未跑 PCH crawler（G14 gap）——现用 bgpkit peerstats '
        f'作功能等价：同样测"观测冗余度"，但粒度是 peer-edge 而非 prefix。'
        f'</p>'
    )

    banner = (
        '<div class="step-banner">'
        '<h1>BGP 观测冗余度 · Multi-Source Peering Visibility</h1>'
        '<h2>bgpkit peerstats · who is visible in v4 vs v6 · '
        'per-AS peer-edge count</h2>'
        '</div><div class="step-footer">topic 17 · offline · '
        'bgpkit.as2rel_v4 + as2rel_v6</div>'
    )

    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>BGP 观测冗余度 · Peering Visibility</title>'
        f'{BANNER_CSS}</head><body>{banner}'
        f'<div class="content">{intro}{"".join(parts)}</div></body></html>'
    )
    out_path = OUT / 'topic17_collector_consensus.html'
    out_path.write_text(html, encoding='utf-8')
    mirror = REPO / 'analysis' / 'countries' / 'html' / \
        'topic17_collector_consensus.html'
    mirror.write_text(html, encoding='utf-8')
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    print(f'v4: {len(v4_set)}  v6: {len(v6_set)}  dual: {len(dual)} '
          f'({dual_pct:.1f}%)')
    print(f'top-5 by visibility: {top20[:5]}')


if __name__ == '__main__':
    build()
