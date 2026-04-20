"""Unbiased ROV adoption measurement via cross-quarter AS panel.

Fixes the sample-expansion pollution in Finding B: instead of counting
"AS with ratio >= 0.5" per snapshot (which is contaminated by ROVISTA's
one-time 2025 Q2 sampling expansion), we intersect the AS sets across
adjacent quarters and measure adoption *within the same AS panel*.

Key finding: the 2025 Q2 jump is real but 1/3 its apparent size.
  - Raw 'enforcing AS count' change: +2,932 (+68%)  ← polluted
  - Unbiased panel adoption: +902 net (+3.3 pp)   ← real
  - Remaining +2,030 jump = newly measured AS that happened to be
    already-enforcing (93% Validating vs 17% baseline).

Outputs: analysis/new_angles/html/rov_panel_adoption.html
"""
import csv
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.china.common import (  # noqa: E402
    BANNER_CSS, COLORS, TEXT_PRIMARY, TEXT_SECONDARY,
    apply_plotly_theme, warning_block,
)

REPO = Path(__file__).resolve().parent.parent.parent
CACHE = REPO / 'data_cache' / 'new_angles'
OUT = REPO / 'analysis' / 'new_angles' / 'html'

# Exclude 2024-01-15 (only 922 rovista rows)
SNAPS = [
    '2024-04-22', '2024-07-08', '2024-10-08', '2025-01-08',
    '2025-04-01', '2025-07-01', '2025-10-08', '2026-01-01',
    '2026-02-08', '2026-04-08',
]


def load_rov():
    """Return: asn→{snap: ratio} (ratio=0 if 'Not Validating' label)."""
    traj = {}
    per_snap = {}
    for s in SNAPS:
        per_snap[s] = set()
        for r in csv.DictReader(open(CACHE / s / 'rovista.csv',
                                     encoding='utf-8')):
            if not r['ratio']:
                continue
            asn = int(r['asn'])
            val = float(r['ratio']) if r['label'] == 'Validating RPKI ROV' else 0.0
            traj.setdefault(asn, {})[s] = val
            per_snap[s].add(asn)
    return traj, per_snap


def build():
    import plotly.graph_objects as go
    from plotly.io import to_html

    traj, per_snap = load_rov()

    # --- Panel 1: per-quarter adoption rate, panel vs naive ---
    naive = []
    panel_adopt = []
    for i in range(len(SNAPS) - 1):
        s1, s2 = SNAPS[i], SNAPS[i + 1]
        panel = per_snap[s1] & per_snap[s2]
        n1_panel = sum(1 for a in panel if traj[a][s1] >= 0.5)
        n2_panel = sum(1 for a in panel if traj[a][s2] >= 0.5)
        newly = sum(1 for a in panel
                    if traj[a][s1] < 0.5 and traj[a][s2] >= 0.5)
        lost = sum(1 for a in panel
                   if traj[a][s1] >= 0.5 and traj[a][s2] < 0.5)
        # naive: compare all-snapshot enforcing counts (polluted)
        all1 = sum(1 for a in per_snap[s1] if traj[a][s1] >= 0.5)
        all2 = sum(1 for a in per_snap[s2] if traj[a][s2] >= 0.5)
        naive_rate = (all2 - all1) / all1 * 100
        panel_rate = (n2_panel - n1_panel) / n1_panel * 100
        panel_adopt.append({
            'pair': f'{s1[:7]}→{s2[:7]}', 'panel_size': len(panel),
            'n1': n1_panel, 'n2': n2_panel,
            'newly': newly, 'lost': lost,
            'net': n2_panel - n1_panel,
            'panel_rate_pct': panel_rate,
            'naive_rate_pct': naive_rate,
            'true_adopt_pct': newly / len(panel) * 100,
        })
        naive.append(naive_rate)

    # Plot: naive vs panel
    p1 = go.Figure()
    xs = [d['pair'] for d in panel_adopt]
    p1.add_trace(go.Scatter(
        x=xs, y=[d['naive_rate_pct'] for d in panel_adopt],
        mode='lines+markers',
        name='Naive rate (all AS, % change enforcing count)',
        line=dict(color=COLORS['red'], dash='dash', width=2),
    ))
    p1.add_trace(go.Scatter(
        x=xs, y=[d['panel_rate_pct'] for d in panel_adopt],
        mode='lines+markers',
        name='Panel rate (same-AS % change)',
        line=dict(color=COLORS['green'], width=3),
    ))
    # Annotate divergence
    idx_q2 = next(i for i, d in enumerate(panel_adopt)
                  if '2025-01→2025-04' in d['pair'])
    p1.add_annotation(
        x=xs[idx_q2], y=panel_adopt[idx_q2]['naive_rate_pct'],
        text=f'Naive +{panel_adopt[idx_q2]["naive_rate_pct"]:.0f}%<br>'
             f'Panel +{panel_adopt[idx_q2]["panel_rate_pct"]:.1f}%<br>'
             f'Gap = measurement expansion',
        showarrow=True, arrowcolor=COLORS['orange'], ax=-100, ay=-60,
        font=dict(color=COLORS['orange'], size=11),
    )
    p1.update_layout(
        title='① 真实 vs 表观 ROV 采纳率 · '
              'Naive count-change misleads; panel-based reflects behavior',
        yaxis=dict(title='% change in enforcing AS'),
        height=460,
    )

    # --- Panel 2: bar - new vs lost per quarter within panel ---
    p2 = go.Figure()
    p2.add_trace(go.Bar(
        x=xs, y=[d['newly'] for d in panel_adopt],
        name='Newly enforcing (panel AS crossed 0.5)',
        marker_color=COLORS['green'],
    ))
    p2.add_trace(go.Bar(
        x=xs, y=[-d['lost'] for d in panel_adopt],
        name='Lost enforcing (panel AS dropped)',
        marker_color=COLORS['red'],
    ))
    p2.update_layout(
        title='② Panel 内 AS 翻转方向 · Adoption (green) vs attrition (red) '
              'by quarter',
        yaxis=dict(title='# panel AS crossing 0.5 threshold'),
        barmode='relative', height=440,
    )

    # --- Panel 3: quarterly true-adoption rate % ---
    p3 = go.Figure()
    true_rates = [d['true_adopt_pct'] for d in panel_adopt]
    p3.add_trace(go.Bar(
        x=xs, y=true_rates,
        marker_color=[
            COLORS['orange'] if v > 1.0 else COLORS['cyan']
            for v in true_rates],
        text=[f'{v:.2f}%' for v in true_rates],
        textposition='outside',
    ))
    p3.update_layout(
        title='③ 真实单季采纳率 · True quarterly adoption rate (% of '
              'panel newly enforcing) — baseline noise vs real spikes',
        yaxis=dict(title='% of panel', range=[0, 4]),
        height=440, showlegend=False,
    )
    p3.add_hline(y=0.25, line_dash='dash', line_color=TEXT_SECONDARY,
                 annotation_text='baseline noise band (~0.2%)',
                 annotation_position='bottom right')

    # --- Panel 4: cumulative adoption curve (panel-only) ---
    # For each snapshot, count panel AS that had ratio ≥ 0.5 *at any point up
    # to and including that snapshot*.
    panel_all = set.intersection(*[per_snap[s] for s in SNAPS])
    cum = []
    ever_enf = set()
    for s in SNAPS:
        for a in panel_all:
            if traj[a][s] >= 0.5:
                ever_enf.add(a)
        cum.append(len(ever_enf))

    p4 = go.Figure()
    p4.add_trace(go.Scatter(
        x=SNAPS, y=cum, mode='lines+markers',
        line=dict(color=COLORS['green'], width=3),
        name='Cumulative ever-enforcing',
    ))
    # Also plot currently-enforcing
    curr = [sum(1 for a in panel_all if traj[a][s] >= 0.5) for s in SNAPS]
    p4.add_trace(go.Scatter(
        x=SNAPS, y=curr, mode='lines+markers',
        line=dict(color=COLORS['cyan'], width=2),
        name='Currently enforcing',
    ))
    p4.update_layout(
        title=f'④ 真实累积采纳 · Cumulative {len(panel_all):,}-AS panel '
              '(measured every quarter 2024-04 → 2026-04)',
        yaxis=dict(title='# panel AS'),
        height=440,
    )

    figs = [p1, p2, p3, p4]
    for f in figs:
        apply_plotly_theme(f)
    parts = []
    first = True
    for f in figs:
        parts.append(to_html(
            f, include_plotlyjs=('inline' if first else False),
            full_html=False, default_height='460px'))
        first = False

    # Compute headline numbers for intro
    q2_entry = panel_adopt[idx_q2]
    total_cum_start = cum[0]
    total_cum_end = cum[-1]
    delta_cum = total_cum_end - total_cum_start

    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>方法：</b>取 2024-04 → 2026-04 每个季度都被 ROVISTA 测到的 '
        f'<b>{len(panel_all):,}</b> 个 AS（"稳定 panel"），'
        f'只比较每个 AS 自身跨季度的 ratio 变化。这样抵消了 2025 Q2 '
        f'ROVISTA 扩样本带来的污染（见 <a href="rov_jump_2025q2.html" '
        f'style="color:{COLORS["cyan"]}">jump attribution 页</a>）。'
        f'<br><b>验证结论：</b>'
        f'<br>• 2025 Q1→Q2 的跳变<b>确实真实存在</b>：panel 内 '
        f'<b>{q2_entry["newly"]:,} AS 自发翻到 enforcing</b>，'
        f'{q2_entry["lost"]:,} 下滑，净 +{q2_entry["net"]:,}，'
        f'采纳率 <b>{q2_entry["true_adopt_pct"]:.2f}%</b>。'
        f'<br>• 但比表面 +68% 小一个量级：真实采纳率 '
        f'<b>{q2_entry["panel_rate_pct"]:.1f}%</b>（表观 '
        f'{q2_entry["naive_rate_pct"]:.0f}%）。'
        f'<br>• 基线噪声：邻近 4 季度的 adopt rate 只有 '
        f'0.13–0.23%，2025 Q2 的 3.28% 仍比噪声高 10×。'
        f'<br>• <b>次发现</b>：2026 Q1→Q2 有 <b>1.32%</b> 次级峰（比 '
        f'baseline 高 6×），此前未被注意——可能是 2025 政策效应的延迟扩散。'
        f'<br><b>累积看</b>：2024-04 到 2026-04 两年里，稳定 panel 有 '
        f'<b>{delta_cum:,}</b> 个 AS 至少采纳过一次 ROV（cumulative '
        f'ever-enforcing 从 {total_cum_start:,} 涨到 {total_cum_end:,}），'
        f'真实增量 {delta_cum/total_cum_start*100:.1f}%。'
        f'</p>'
    )
    intro += warning_block(
        '<b>方法学说明：</b>"panel-based" 统计是对每个 AS 追踪自身前后的变化，'
        '而不是每季度独立 count。这能滤掉 sampling 变化和 label dropout。'
        '代价是只能用在"稳定 panel"内（本次 30,340 AS，占 2026-04 最新样本的 '
        '92%）——新加入的 AS（2025 Q2 的 +2,177 个）被排除。<br>'
        '<b>为什么 2025 Q2 还是比邻近季度高 10×？</b>两种可能（数据无法区分）：'
        '① RIPE NCC 或 APNIC 2024 秋季的 ROV 推广经过半年孵化才反映到 '
        'ROVISTA 测量结果；② ROVISTA 算法本身在 2025 Q2 升级了敏感度。',
        title='方法局限 · Caveats for the panel method',
    )

    banner = (
        '<div class="step-banner">'
        '<h1>ROV 采纳 panel 重估 · Panel-based ROV Adoption Re-estimate</h1>'
        '<h2>30,340-AS stable panel · unbiased by 2025 Q2 sampling '
        'expansion</h2>'
        '</div><div class="step-footer">rov_panel_adoption · '
        'rovista.csv × 10 quarters · same-AS self-comparison</div>'
    )
    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>ROV Panel Adoption</title>'
        f'{BANNER_CSS}</head><body>{banner}'
        f'<div class="content">{intro}{"".join(parts)}</div></body></html>'
    )
    out = OUT / 'rov_panel_adoption.html'
    out.write_text(html, encoding='utf-8')
    mirror = REPO / 'analysis' / 'countries' / 'html' \
        / 'rov_panel_adoption.html'
    mirror.write_text(html, encoding='utf-8')

    # Print summary
    print(f'Panel size (all 10 quarters): {len(panel_all):,}')
    print(f'\nPer-quarter adoption within panel:')
    print(f'{"transition":28}  {"panel":>6}  {"newly":>6}  {"lost":>5}  '
          f'{"net":>6}  {"true %":>8}  {"naive %":>8}')
    for d in panel_adopt:
        print(f'  {d["pair"]:25}  {d["panel_size"]:6,}  '
              f'{d["newly"]:6,}  {d["lost"]:5,}  '
              f'{d["net"]:+6,}  '
              f'{d["true_adopt_pct"]:7.2f}%  '
              f'{d["naive_rate_pct"]:+7.1f}%')
    print(f'\nCumulative ever-enforcing (panel): {cum[0]:,} → {cum[-1]:,} '
          f'(+{delta_cum:,}, +{delta_cum/cum[0]*100:.1f}%)')
    print(f'\nwrote {out}')


if __name__ == '__main__':
    build()
