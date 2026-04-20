"""Industry capacity-growth panel — a novel unbiased signal.

Finding: in `peeringdb_nets.csv` the `info_traffic` field is an ordered
ladder of 18 buckets (0-20Mbps ... 100+Tbps). Methodology audit
(METHODOLOGY_AUDIT.md § 3.1) found 3,109 AS (13.5%) had their bucket
move monotonically upward over 27 months — this is a real industry
capacity-upgrade signal, independent of vendor self-reports or Cisco
Annual Internet Report projections.

This script:
  1. Builds per-AS bucket trajectories across 11 snapshots.
  2. Panel-method: for AS observed in ≥2 snapshots, compute Δ bucket.
  3. Aggregates by info_type and country.
  4. Emits 6-panel HTML + metrics JSON.

Outputs: analysis/new_angles/html/capacity_growth.html
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

SNAPS = [
    '2024-01-15', '2024-04-22', '2024-07-08', '2024-10-08',
    '2025-01-08', '2025-04-01', '2025-07-01', '2025-10-08',
    '2026-01-01', '2026-02-08', '2026-04-08',
]

# Ordered ladder (idx 0 = lowest); empty/Not Disclosed is excluded
LADDER = [
    '0-20Mbps', '20-100Mbps', '100-1000Mbps',
    '1-5Gbps', '5-10Gbps', '10-20Gbps', '20-50Gbps', '50-100Gbps',
    '100-200Gbps', '200-300Gbps', '300-500Gbps', '500-1000Gbps',
    '1-5Tbps', '5-10Tbps', '10-20Tbps', '20-50Tbps',
    '50-100Tbps', '100+Tbps',
]
BUCKET_IDX = {b: i for i, b in enumerate(LADDER)}


def load_all():
    """traj[asn] = {snap: (bucket, info_type, cc)}."""
    traj = defaultdict(dict)
    as_cc = {}
    for s in SNAPS:
        for r in csv.DictReader(open(CACHE / s / 'as_country.csv',
                                     encoding='utf-8')):
            as_cc[int(r['asn'])] = r['cc']
        for r in csv.DictReader(open(CACHE / s / 'peeringdb_nets.csv',
                                     encoding='utf-8')):
            asn = int(r['asn'])
            tb = (r.get('info_traffic') or '').strip()
            if tb not in BUCKET_IDX:
                continue
            it = (r.get('info_type') or '').strip() or 'Not Disclosed'
            traj[asn][s] = (tb, it)
    return traj, as_cc


def build():
    import plotly.graph_objects as go
    from plotly.io import to_html

    traj, as_cc = load_all()
    print(f'Loaded {len(traj):,} AS with ≥1 declared traffic bucket',
          flush=True)

    # Panel: AS observed in earliest and latest snapshot
    earliest_snap = next(
        s for s in SNAPS if any(s in t for t in traj.values()))
    latest_snap = SNAPS[-1]
    # Use first/last snapshot the AS is observed
    panel = {}
    for asn, t in traj.items():
        snaps_present = sorted(t.keys())
        if len(snaps_present) < 2:
            continue
        first = snaps_present[0]
        last = snaps_present[-1]
        if first == last:
            continue
        b_first = BUCKET_IDX[t[first][0]]
        b_last = BUCKET_IDX[t[last][0]]
        delta = b_last - b_first
        it_last = t[last][1]
        panel[asn] = {
            'first_snap': first, 'last_snap': last,
            'first_bucket': t[first][0], 'last_bucket': t[last][0],
            'b_first': b_first, 'b_last': b_last,
            'delta': delta,
            'info_type': it_last,
            'cc': as_cc.get(asn, ''),
        }

    print(f'Panel (≥2 snapshots): {len(panel):,}', flush=True)
    n_up = sum(1 for p in panel.values() if p['delta'] > 0)
    n_same = sum(1 for p in panel.values() if p['delta'] == 0)
    n_down = sum(1 for p in panel.values() if p['delta'] < 0)
    print(f'  upgrade: {n_up:,} ({n_up/len(panel)*100:.1f}%)',
          flush=True)
    print(f'  stable:  {n_same:,} ({n_same/len(panel)*100:.1f}%)',
          flush=True)
    print(f'  downgrade: {n_down:,} ({n_down/len(panel)*100:.1f}%)',
          flush=True)

    # ─── P1: delta histogram ───
    delta_counts = Counter(p['delta'] for p in panel.values())
    xs = list(range(-5, 11))
    ys = [delta_counts.get(d, 0) for d in xs]
    colors = [
        COLORS['red'] if d < 0 else COLORS['cyan'] if d == 0
        else COLORS['green']
        for d in xs
    ]
    p1 = go.Figure()
    p1.add_trace(go.Bar(
        x=[f'{"+" if d>0 else ""}{d}' for d in xs],
        y=ys,
        marker_color=colors,
        text=[str(y) if y else '' for y in ys],
        textposition='outside',
    ))
    p1.update_layout(
        title=f'① Bucket Δ 分布 · {len(panel):,} AS panel (first vs last '
              f'observation) — {n_up/len(panel)*100:.0f}% upgraded, '
              f'{n_down/len(panel)*100:.0f}% downgraded',
        xaxis=dict(title='bucket positions moved'),
        yaxis=dict(title='# AS'),
        height=440, showlegend=False,
    )

    # ─── P2: bucket distribution evolution per snapshot ───
    snap_buckets = {}
    for s in SNAPS:
        c = Counter()
        for asn, t in traj.items():
            if s in t:
                c[t[s][0]] += 1
        snap_buckets[s] = c

    # Group buckets into tiers for readable stacked chart
    TIERS = [
        ('<1Gbps', ['0-20Mbps', '20-100Mbps', '100-1000Mbps']),
        ('1-10Gbps', ['1-5Gbps', '5-10Gbps']),
        ('10-100Gbps', ['10-20Gbps', '20-50Gbps', '50-100Gbps']),
        ('100Gbps-1Tbps', ['100-200Gbps', '200-300Gbps', '300-500Gbps',
                           '500-1000Gbps']),
        ('1-50Tbps', ['1-5Tbps', '5-10Tbps', '10-20Tbps', '20-50Tbps']),
        ('50+Tbps', ['50-100Tbps', '100+Tbps']),
    ]
    TIER_COLOR = [COLORS['red'], COLORS['orange'], COLORS['yellow'],
                  COLORS['cyan'], COLORS['green'], COLORS['purple']]
    p2 = go.Figure()
    for (tier_name, tier_buckets), tc in zip(TIERS, TIER_COLOR):
        ys = []
        for s in SNAPS:
            ys.append(sum(snap_buckets[s].get(b, 0)
                          for b in tier_buckets))
        p2.add_trace(go.Bar(
            x=SNAPS, y=ys, name=tier_name,
            marker_color=tc,
        ))
    p2.update_layout(
        barmode='stack',
        title='② 容量桶分布时序 · AS 按 traffic tier 分组 '
              '(整个 PeeringDB-net 样本 per snapshot)',
        yaxis=dict(title='# AS declaring this tier'),
        height=500,
    )

    # ─── P3: upgrade rate by info_type ───
    by_type = defaultdict(lambda: {'n': 0, 'up': 0, 'down': 0,
                                    'delta_sum': 0})
    for p in panel.values():
        b = by_type[p['info_type']]
        b['n'] += 1
        b['delta_sum'] += p['delta']
        if p['delta'] > 0:
            b['up'] += 1
        elif p['delta'] < 0:
            b['down'] += 1
    types_sorted = sorted(
        [(t, v) for t, v in by_type.items() if v['n'] >= 50],
        key=lambda kv: -kv[1]['up'] / max(kv[1]['n'], 1))

    p3 = go.Figure()
    p3.add_trace(go.Bar(
        x=[t for t, _ in types_sorted],
        y=[v['up'] / v['n'] * 100 for _, v in types_sorted],
        name='Upgrade %',
        marker_color=COLORS['green'],
        text=[f'{v["up"]}/{v["n"]}<br>({v["up"]/v["n"]*100:.0f}%)'
              for _, v in types_sorted],
        textposition='outside',
    ))
    p3.add_trace(go.Bar(
        x=[t for t, _ in types_sorted],
        y=[v['down'] / v['n'] * 100 for _, v in types_sorted],
        name='Downgrade %',
        marker_color=COLORS['red'],
    ))
    p3.update_layout(
        barmode='group',
        title='③ 按 info_type 的升级率 · which AS types upgrade fastest',
        yaxis=dict(title='% of panel in category'),
        height=460,
    )

    # ─── P4: by country (top 15 by absolute # upgraders) ───
    by_cc = defaultdict(lambda: {'n': 0, 'up': 0, 'delta_sum': 0})
    for p in panel.values():
        if p['cc']:
            by_cc[p['cc']]['n'] += 1
            if p['delta'] > 0:
                by_cc[p['cc']]['up'] += 1
            by_cc[p['cc']]['delta_sum'] += p['delta']
    cc_sorted = sorted(
        [(c, v) for c, v in by_cc.items() if v['n'] >= 50],
        key=lambda kv: -kv[1]['up'])[:15]
    p4 = go.Figure()
    p4.add_trace(go.Bar(
        x=[c for c, _ in cc_sorted],
        y=[v['up'] for _, v in cc_sorted],
        name='# upgrades',
        marker_color=[country_color(c) for c, _ in cc_sorted],
        text=[f'{v["up"]}/{v["n"]}' for _, v in cc_sorted],
        textposition='outside',
    ))
    p4.update_layout(
        title='④ 按国家的升级绝对数 · top 15 by count of upgrading AS',
        yaxis=dict(title='# AS with bucket↑'),
        height=440, showlegend=False,
    )

    # ─── P5: top-25 AS by Δ bucket ───
    top_up = sorted(panel.items(), key=lambda kv: -kv[1]['delta'])[:25]
    p5 = go.Figure()
    p5.add_trace(go.Bar(
        x=[p['delta'] for _, p in top_up][::-1],
        y=[f'AS{asn} ({p["info_type"][:15]}/{p["cc"]})'
           for asn, p in top_up][::-1],
        orientation='h',
        marker_color=COLORS['green'],
        text=[f'{p["first_bucket"]}→{p["last_bucket"]}'
              for _, p in top_up][::-1],
        textposition='outside',
    ))
    p5.update_layout(
        title=f'⑤ Top-25 AS by bucket Δ · biggest single-AS growth jumps',
        xaxis=dict(title='bucket positions moved'),
        height=720, showlegend=False, margin=dict(l=260),
    )

    # ─── P6: median bucket over time by info_type ───
    p6 = go.Figure()
    focus_types = ['Content', 'Cable/DSL/ISP', 'NSP', 'Enterprise',
                   'Educational/Research']
    TYPE_COLOR = {'Content': COLORS['green'],
                  'Cable/DSL/ISP': COLORS['orange'],
                  'NSP': COLORS['blue'],
                  'Enterprise': COLORS['purple'],
                  'Educational/Research': COLORS['pink']}
    for ft in focus_types:
        medians = []
        for s in SNAPS:
            buckets = []
            for asn, t in traj.items():
                if s in t and t[s][1] == ft:
                    buckets.append(BUCKET_IDX[t[s][0]])
            if buckets:
                buckets.sort()
                medians.append(buckets[len(buckets) // 2])
            else:
                medians.append(None)
        p6.add_trace(go.Scatter(
            x=SNAPS, y=medians, mode='lines+markers',
            name=ft, line=dict(color=TYPE_COLOR.get(ft), width=3),
        ))
    # Y-axis labels as bucket names
    p6.update_layout(
        title='⑥ 各 info_type 的中位数 traffic bucket 时序 · '
              'industry-median capacity evolution',
        yaxis=dict(
            title='bucket index (median)',
            tickmode='array',
            tickvals=list(range(len(LADDER))),
            ticktext=LADDER,
        ),
        height=520,
    )

    # Figures + HTML
    figs = [p1, p2, p3, p4, p5, p6]
    for f in figs:
        apply_plotly_theme(f)
    parts = []
    first = True
    for f in figs:
        parts.append(to_html(
            f, include_plotlyjs=('inline' if first else False),
            full_html=False, default_height='480px'))
        first = False

    # Headline deltas
    # Median delta across panel
    deltas = sorted(p['delta'] for p in panel.values())
    median_d = deltas[len(deltas) // 2]
    mean_d = sum(deltas) / len(deltas)
    # Content AS Δ
    content = [p for p in panel.values() if p['info_type'] == 'Content']
    cable = [p for p in panel.values() if p['info_type'] == 'Cable/DSL/ISP']
    nsp = [p for p in panel.values() if p['info_type'] == 'NSP']

    def pct_up(xs):
        return sum(1 for p in xs if p['delta'] > 0) / max(len(xs), 1) * 100
    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>方法</b>：PeeringDB 的 <code>info_traffic</code> 字段是'
        f'一个 <b>18 级有序阶梯</b>（0-20Mbps → 100+Tbps）。'
        f'任一 AS 在两个快照里 bucket 如果从低阶迁向高阶，就是'
        f'<b>自报容量升级</b>。用 panel 法（同 AS 自比）抵消测量扩张。'
        f'<br><b>规模</b>：{len(panel):,} AS 在两个或更多快照里有 '
        f'traffic bucket 申报，是未污染 panel。'
        f'<br><b>Headline</b>：'
        f'<b>{n_up:,}</b> AS ({n_up/len(panel)*100:.0f}%) 两年里升级，'
        f'<b>{n_down:,}</b> ({n_down/len(panel)*100:.0f}%) 降级，'
        f'中位 Δ = <b>{median_d:+d}</b>、均值 Δ = <b>{mean_d:+.2f}</b> bucket。'
        f'<br><b>细分</b>：Content AS 升级率 <b>{pct_up(content):.0f}%</b>；'
        f'Cable/DSL/ISP <b>{pct_up(cable):.0f}%</b>；'
        f'NSP <b>{pct_up(nsp):.0f}%</b>。'
        f'</p>'
    )
    intro += warning_block(
        '这是 <b>自报</b> 数据——AS 自己更新 PeeringDB 时选新桶。'
        '它不等于真实流量变化，但能反映 operator 的"战略申报"（他们'
        '认为自己的网络规模属于哪一级）。优点：<b>独立于 vendor 报告'
        '和 Cisco Annual Internet Report 的预测</b>，直接测量'
        'operator-side 的 self-identification。<br>'
        '局限：升级和申报有延迟（operator 可能建好 1 年才改 PeeringDB）；'
        'PeeringDB 用户偏向 Peering-heavy AS，不能代表完整 Internet。',
        title='方法说明 · What this measures (and doesn\'t)',
    )

    banner = (
        '<div class="step-banner">'
        '<h1>容量升级 panel · Industry Capacity Growth</h1>'
        '<h2>PeeringDB info_traffic 阶梯 · AS-panel method · '
        '2024-01 → 2026-04</h2>'
        '</div><div class="step-footer">capacity_growth · '
        'unbiased by sample expansion — same-AS bucket self-comparison'
        '</div>'
    )
    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>Capacity Growth Panel</title>'
        f'{BANNER_CSS}</head><body>{banner}'
        f'<div class="content">{intro}{"".join(parts)}</div></body></html>'
    )
    out_path = OUT / 'capacity_growth.html'
    out_path.write_text(html, encoding='utf-8')
    mirror = REPO / 'analysis' / 'countries' / 'html' / 'capacity_growth.html'
    mirror.write_text(html, encoding='utf-8')
    print(f'wrote {out_path}', flush=True)

    # JSON export
    metrics = {
        'panel_size': len(panel),
        'upgrade_pct': n_up / len(panel) * 100,
        'downgrade_pct': n_down / len(panel) * 100,
        'median_delta': median_d,
        'mean_delta': mean_d,
        'by_info_type': {
            t: {'n': v['n'], 'up_pct': v['up'] / v['n'] * 100,
                'delta_mean': v['delta_sum'] / v['n']}
            for t, v in by_type.items() if v['n'] >= 50
        },
        'by_country_top20': [
            {'cc': c, 'up': v['up'], 'n': v['n'],
             'up_pct': v['up'] / v['n'] * 100,
             'mean_delta': v['delta_sum'] / v['n']}
            for c, v in sorted(
                [(c, v) for c, v in by_cc.items() if v['n'] >= 50],
                key=lambda kv: -kv[1]['up'])[:20]
        ],
        'top25_by_delta': [
            {'asn': asn, 'delta': p['delta'],
             'first': p['first_bucket'], 'last': p['last_bucket'],
             'info_type': p['info_type'], 'cc': p['cc']}
            for asn, p in top_up
        ],
    }
    metrics_path = REPO / 'analysis' / 'new_angles' / 'data' \
        / 'capacity_growth_metrics.json'
    metrics_path.write_text(json.dumps(metrics, indent=2, default=str),
                            encoding='utf-8')
    print(f'wrote {metrics_path}')


if __name__ == '__main__':
    build()
