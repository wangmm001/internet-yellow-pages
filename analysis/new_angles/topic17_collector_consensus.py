"""Topic 17: Multi-collector consensus — PCH route snapshots.

PCH publishes ORIGINATE edges with {count, seen_by_collectors}:
how many PCH collectors agree on each (AS, prefix) pair. Prefixes
visible to only 1-2 collectors may be regional-only, brand-new,
or mis-originated. Cross-references RouteViews/RIS via existing
bgpkit cached CSVs.
"""
import csv
import json
import os
import re
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
    banner = (
        '<div class="step-banner">'
        '<h1>多 collector 一致性 · Multi-Collector Consensus</h1>'
        '<h2>PCH daily snapshots: how many collectors agree on each '
        'prefix origin</h2></div>'
        '<div class="step-footer">topic 17 · placeholder</div>'
    )
    intro = (
        f'<p style="padding:0 16px;margin:16px 0;color:{COLORS["orange"]};'
        f'border-left:3px solid {COLORS["orange"]};padding-left:14px;'
        f'font-size:13px">⚠️ <b>数据缺口：</b>{reason}</p>'
    )
    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>多 collector 一致性 · Multi-Collector Consensus</title>'
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

    pch_path = CACHE / 'pch_prefix_collectors.csv'
    if not pch_path.exists() or pch_path.stat().st_size < 200:
        return _placeholder(
            '<code>pch_prefix_collectors.csv</code> 为空——'
            'pch.daily_routing_snapshots_* crawler 未运行或 reference_name '
            '模式不匹配。')

    as_cc = {int(r['asn']): r['cc'] for r in _read(CACHE / 'as_country.csv')
             if r.get('asn', '').isdigit()}

    # ⚠ pch CSV is ~1 GB; full list-load = ~9 GB Python heap → OOM risk.
    # Stream once, accumulate every needed aggregate in counters.
    bucket = Counter()
    low_cc = Counter()
    all_cc = Counter()
    solo_by_asn = Counter()
    v4_by_buck = Counter()
    v6_by_buck = Counter()
    total = 0
    distinct_asns = set()

    with open(pch_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            total += 1
            try:
                n = int(r.get('n_collectors') or 0)
            except (ValueError, KeyError):
                continue
            try:
                asn = int(r['asn'])
                distinct_asns.add(asn)
            except (ValueError, KeyError):
                asn = None
            try:
                af = int(r.get('af') or 4)
            except (ValueError, KeyError):
                af = 4
            # Bucket distribution
            if n == 1:
                bucket['1 collector'] += 1
            elif n <= 3:
                bucket['2-3'] += 1
            elif n <= 7:
                bucket['4-7'] += 1
            elif n <= 15:
                bucket['8-15'] += 1
            else:
                bucket['16+'] += 1
            # Per-country
            if asn is not None:
                cc = as_cc.get(asn)
                if cc:
                    all_cc[cc] += 1
                    if n <= 2:
                        low_cc[cc] += 1
                if n == 1:
                    solo_by_asn[asn] += 1
            # v4/v6 buckets
            bk = '1' if n == 1 else '2-3' if n <= 3 else '4+'
            if af == 6:
                v6_by_buck[bk] += 1
            else:
                v4_by_buck[bk] += 1

    distinct_asns_n = len(distinct_asns)
    distinct_asns = None  # release set memory

    order = ['1 collector', '2-3', '4-7', '8-15', '16+']
    p1 = go.Figure()
    p1.add_trace(go.Bar(
        x=order, y=[bucket.get(b, 0) for b in order],
        marker_color=[COLORS['red'], COLORS['orange'], COLORS['yellow'],
                      COLORS['cyan'], COLORS['green']],
        text=[f'{bucket.get(b, 0):,}' for b in order],
        textposition='outside',
    ))
    p1.update_layout(
        title='① PCH collector 覆盖分布 · # prefixes by # '
              'PCH collectors seeing them',
        xaxis=dict(title=''), yaxis=dict(title='# prefixes (log)',
                                         type='log'),
        height=440, showlegend=False,
    )

    # --- P2: Low-consensus prefixes per country ---
    rows2 = []
    for cc in set(TARGET) | {c for c, _ in all_cc.most_common(12)}:
        if all_cc[cc] < 100:
            continue
        rows2.append({
            'cc': cc, 'low': low_cc[cc], 'total': all_cc[cc],
            'pct': low_cc[cc] / all_cc[cc] * 100,
        })
    rows2.sort(key=lambda r: -r['pct'])
    rows2 = rows2[:15]
    p2 = go.Figure()
    p2.add_trace(go.Bar(
        x=[r['cc'] for r in rows2],
        y=[r['pct'] for r in rows2],
        marker_color=[country_color(r['cc']) if r['cc'] in TARGET
                      else COLORS['purple'] for r in rows2],
        text=[f'{r["pct"]:.1f}%<br>({r["low"]:,}/{r["total"]:,})'
              for r in rows2],
        textposition='outside',
    ))
    p2.update_layout(
        title='② 每国低共识前缀占比 · % prefixes seen by ≤2 PCH collectors '
              'per country',
        yaxis=dict(title='% low-consensus prefixes', rangemode='tozero'),
        xaxis=dict(title=''), height=460,
    )

    # --- P3: Top-20 ASes with most 1-collector prefixes (already aggregated) ---
    top_solo = solo_by_asn.most_common(20)
    p3 = go.Figure()
    if top_solo:
        p3.add_trace(go.Bar(
            orientation='h',
            y=[f'AS{a} ({as_cc.get(a, "?")})'
               for a, _ in top_solo][::-1],
            x=[c for _, c in top_solo][::-1],
            marker_color=[country_color(as_cc.get(a, '?'))
                          if as_cc.get(a) in TARGET else COLORS['purple']
                          for a, _ in top_solo][::-1],
            text=[f'{c:,}' for _, c in top_solo][::-1],
            textposition='outside',
        ))
    p3.update_layout(
        title='③ Top-20 AS · # prefixes seen by only 1 PCH collector',
        xaxis=dict(title='# single-collector prefixes'),
        height=560, margin=dict(l=180), showlegend=False,
    )

    # --- P4: v4 vs v6 coverage asymmetry (already aggregated) ---
    p4 = go.Figure()
    bkts = ['1', '2-3', '4+']
    p4.add_trace(go.Bar(
        name='IPv4', x=bkts, y=[v4_by_buck.get(b, 0) for b in bkts],
        marker_color=COLORS['cyan'],
        text=[f'{v4_by_buck.get(b, 0):,}' for b in bkts],
        textposition='outside',
    ))
    p4.add_trace(go.Bar(
        name='IPv6', x=bkts, y=[v6_by_buck.get(b, 0) for b in bkts],
        marker_color=COLORS['orange'],
        text=[f'{v6_by_buck.get(b, 0):,}' for b in bkts],
        textposition='outside',
    ))
    p4.update_layout(
        title='④ v4 vs v6 共识分布 · IPv4 vs IPv6 coverage buckets',
        barmode='group', height=440,
        yaxis=dict(title='# prefixes', type='log'),
        xaxis=dict(title='# PCH collectors'),
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

    # Top-level stats (total accumulated during stream pass)
    solo = bucket.get('1 collector', 0)

    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>数据：</b>PCH Packet Clearing House 每日路由快照——总计 '
        f'<b>{total:,}</b> 条 ORIGINATE 记录，分布在 '
        f'<b>{distinct_asns_n:,}</b> 个 AS。其中 <b>{solo:,}</b>'
        f'（{solo/max(total,1)*100:.1f}%）仅被 <b>1</b> 个 collector 看到——'
        f'这些可能是地域性 route leak、新出生前缀、或测试路由。'
        f'<br><b>对照：</b>RouteViews 全球 ~30 collector，RIS ~20，PCH 约 60+ '
        f'（按地区分布更分散）。PCH single-collector 信号因此更宝贵——'
        f'通常只在一地可见。此视图可辅助安全分析找"非正常"路由。'
        f'</p>'
    )

    banner = (
        '<div class="step-banner">'
        '<h1>多 collector 一致性 · Multi-Collector Consensus</h1>'
        '<h2>PCH daily routing snapshots · who sees what</h2>'
        '</div>'
        '<div class="step-footer">topic 17 · offline · '
        'pch.daily_routing_snapshots_v4/v6</div>'
    )

    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>多 collector 一致性 · Multi-Collector Consensus</title>'
        f'{BANNER_CSS}</head><body>{banner}'
        f'<div class="content">{intro}{"".join(parts)}</div></body></html>'
    )
    out_path = OUT / 'topic17_collector_consensus.html'
    out_path.write_text(html, encoding='utf-8')
    mirror = REPO / 'analysis' / 'countries' / 'html' / \
        'topic17_collector_consensus.html'
    mirror.write_text(html, encoding='utf-8')
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    print(f'total={total}  single-collector={solo}  '
          f'distinct_asns={distinct_asns_n}')


if __name__ == '__main__':
    build()
