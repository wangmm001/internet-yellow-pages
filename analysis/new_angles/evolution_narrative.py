"""Evolution narrative: a story built on 11 real-dump-extracted snapshots.

This page is the prose companion to evolution.html. Where evolution.html
shows every trajectory, this page picks 6 scenes that, taken together,
describe what happened to China's Internet footprint between 2024-01 and
2026-04 — and honestly flags what DIDN'T change (the sticky layers that
IYP's archival cadence does not re-crawl per quarter).

Scenes:
 ① CN prefix 轨迹 — slow 2024, accelerated 2025, leapt in 2026
 ② CN vs US growth-rate race (normalized to 2024-01 = 100)
 ③ RPKI adoption — the every-6-month schema gap + CN 2026-Q2 doubling
 ④ Anycast deployment trajectory per country
 ⑤ 27-month summary table — who moved most on each axis
 ⑥ "What doesn't change" callout — sticky layers that IYP archives don't refresh

Output: analysis/new_angles/html/evolution_narrative.html
Site mirror: analysis/countries/html/evolution_narrative.html
"""
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.china.common import (  # noqa: E402
    BANNER_CSS, COLORS, DARK_BG, DARK_BORDER, DARK_PANEL,
    TEXT_PRIMARY, TEXT_SECONDARY, apply_plotly_theme, country_color,
)
from analysis.new_angles.evolution import (  # noqa: E402
    SNAPS, COUNTRIES, COUNTRY_NAME, collect,
)

REPO = Path(__file__).resolve().parent.parent.parent
SNAP_ROOT = REPO / 'analysis' / 'countries' / 'data'
OUT = REPO / 'analysis' / 'new_angles' / 'html'
OUT.mkdir(parents=True, exist_ok=True)


def _load_step(snap, cc, step):
    f = SNAP_ROOT / snap / cc / f'step{step:02d}_metrics.json'
    if not f.exists():
        return {}
    return json.loads(f.read_text(encoding='utf-8')).get('metrics', {}) or {}


def _sticky_series(step, key):
    """Fetch a series across SNAPS for CN; used to show what doesn't move."""
    return [_load_step(s, 'CN', step).get(key) for s in SNAPS]


def _snap_month_index(snap):
    """Months since 2024-01 for x-axis positioning."""
    y, m = snap.split('-')
    return (int(y) - 2024) * 12 + (int(m) - 1)


def build():
    import plotly.graph_objects as go
    from plotly.io import to_html
    import plotly.subplots as sp

    series = collect()
    months = [_snap_month_index(s) for s in SNAPS]

    # ---- Scene 1: CN prefix trajectory with annotations ----
    cn_pfx = series['total_prefixes']['CN']
    p1 = go.Figure()
    p1.add_trace(go.Scatter(
        x=SNAPS, y=cn_pfx, mode='lines+markers+text',
        text=[f'{v:,}' for v in cn_pfx], textposition='top center',
        line=dict(color=COLORS['red'], width=3),
        marker=dict(size=10, color=COLORS['red']),
        name='CN total prefix',
    ))
    # Annotations: inflection + 2026 jump
    if len(cn_pfx) >= 7:
        p1.add_annotation(
            x='2025-07', y=cn_pfx[6],
            text='加速起点<br>~2025 Q3',
            showarrow=True, arrowhead=2, ax=-40, ay=-40,
            bgcolor='rgba(255,159,10,0.15)',
            bordercolor=COLORS['orange'], borderwidth=1,
            font=dict(color=COLORS['orange']),
        )
    p1.update_layout(
        title='① CN 前缀轨迹 · 2024 慢爬升 → 2025 加速 → 2026 新高',
        xaxis=dict(title=''),
        yaxis=dict(title='# total BGP prefixes (CN)'),
        height=480, showlegend=False,
    )

    # ---- Scene 2: CN vs US growth-rate race (2024-01 = 100) ----
    p2 = go.Figure()
    for cc in ['CN', 'US', 'JP', 'IN']:
        vals = series['total_prefixes'][cc]
        if not vals or not vals[0]:
            continue
        base = vals[0]
        norm = [v / base * 100 if v else None for v in vals]
        p2.add_trace(go.Scatter(
            x=SNAPS, y=norm, mode='lines+markers',
            name=f'{COUNTRY_NAME[cc]} {cc}',
            line=dict(color=country_color(cc), width=2.5),
            marker=dict(size=8),
        ))
    p2.add_hline(y=100, line=dict(color=TEXT_SECONDARY, width=1, dash='dash'))
    p2.update_layout(
        title='② 累积增长率竞赛 · Cumulative prefix growth (2024-01 = 100)',
        xaxis=dict(title=''),
        yaxis=dict(title='prefixes, normalized'),
        height=460,
        legend=dict(orientation='h', y=-0.22),
    )

    # ---- Scene 3: RPKI adoption trajectory — all 9 countries ----
    p3 = go.Figure()
    for cc in COUNTRIES:
        vals = series['rpki_rate_pct'][cc]
        p3.add_trace(go.Scatter(
            x=SNAPS, y=vals, mode='lines+markers',
            name=f'{COUNTRY_NAME[cc]} {cc}',
            line=dict(color=country_color(cc), width=2.2),
            marker=dict(size=8, color=country_color(cc)),
            connectgaps=False,
        ))
    # CN 2026-Q2 jump annotation
    cn_rpki = series['rpki_rate_pct']['CN']
    if cn_rpki[-1] and cn_rpki[-2]:
        p3.add_annotation(
            x='2026-04', y=cn_rpki[-1],
            text=f'CN: {cn_rpki[-2]}% → {cn_rpki[-1]}%<br>（3 个月翻倍）',
            showarrow=True, arrowhead=2, ax=-60, ay=-30,
            bgcolor='rgba(255,69,58,0.15)',
            bordercolor=COLORS['red'], borderwidth=1,
            font=dict(color=COLORS['red']),
        )
    gap_snaps = [SNAPS[i] for i, v in enumerate(cn_rpki) if v is None]
    if gap_snaps:
        p3.add_annotation(
            xref='paper', yref='paper', x=0.02, y=1.08,
            text=f'⚠ {", ".join(gap_snaps)}: 每半年一个 IYP 上游 '
                 f'prefix-tag crawler 跳跃（留白，不插值）',
            showarrow=False, bgcolor='rgba(255,159,10,0.12)',
            bordercolor=COLORS['orange'], borderwidth=1,
            font=dict(color=COLORS['orange'], size=11),
        )
    p3.update_layout(
        title='③ RPKI 覆盖轨迹 · 每半年 schema gap + CN 2026-Q2 翻倍',
        xaxis=dict(title=''),
        yaxis=dict(title='RPKI-valid share of prefixes %'),
        height=520,
        legend=dict(orientation='h', y=-0.22),
    )

    # ---- Scene 4: Anycast deployment trajectory ----
    p4 = go.Figure()
    for cc in COUNTRIES:
        vals = series['anycast_prefixes'][cc]
        p4.add_trace(go.Scatter(
            x=SNAPS, y=vals, mode='lines+markers',
            name=f'{COUNTRY_NAME[cc]} {cc}',
            line=dict(color=country_color(cc), width=2.2),
            marker=dict(size=7),
        ))
    p4.update_layout(
        title='④ Anycast 前缀部署 · 10 季度累积',
        xaxis=dict(title=''),
        yaxis=dict(title='# anycast-tagged prefixes'),
        height=460,
        legend=dict(orientation='h', y=-0.22),
    )

    # ---- Scene 5: 27-month summary table ----
    def _cagr_pct(start, end, m):
        if start and end and start > 0 and end > 0 and m > 0:
            return round(((end / start) ** (12 / m) - 1) * 100, 1)
        return None

    def _delta_pp(xs):
        clean = [v for v in xs if v is not None]
        if len(clean) < 2:
            return None
        return round(clean[-1] - clean[0], 1)

    span_months = months[-1] - months[0]
    rows = []
    for cc in COUNTRIES:
        pfx = series['total_prefixes'][cc]
        rpki_series = series['rpki_rate_pct'][cc]
        any_ = series['anycast_prefixes'][cc]
        rows.append({
            'cc': cc,
            'pfx_start': pfx[0], 'pfx_end': pfx[-1],
            'pfx_cagr': _cagr_pct(pfx[0], pfx[-1], span_months),
            'rpki_delta': _delta_pp(rpki_series),
            'any_cagr': _cagr_pct(any_[0], any_[-1], span_months)
            if any_[0] else None,
        })
    rows.sort(key=lambda r: -(r['pfx_cagr'] or -999))

    def _fmt_pct(v, sign=True):
        if v is None:
            return '—'
        fmt = f'{v:+.1f}%' if sign else f'{v:.1f}%'
        return fmt

    header_cells = ['国家', '2024-01', '2026-04', '前缀 CAGR',
                    'RPKI Δpp', 'Anycast CAGR']
    rows_cells = [
        [f'{COUNTRY_NAME[r["cc"]]} {r["cc"]}' for r in rows],
        [f'{r["pfx_start"]:,}' for r in rows],
        [f'{r["pfx_end"]:,}' for r in rows],
        [_fmt_pct(r['pfx_cagr']) for r in rows],
        [_fmt_pct(r['rpki_delta']) if r['rpki_delta'] is not None else '—'
         for r in rows],
        [_fmt_pct(r['any_cagr']) for r in rows],
    ]
    p5 = go.Figure(data=[go.Table(
        header=dict(
            values=[f'<b>{h}</b>' for h in header_cells],
            fill_color=DARK_PANEL,
            align='left',
            font=dict(color=TEXT_PRIMARY, size=13),
            height=34,
        ),
        cells=dict(
            values=rows_cells,
            fill_color=DARK_BG,
            align='left',
            font=dict(color=TEXT_PRIMARY, size=12),
            height=30,
        ),
    )])
    p5.update_layout(
        title=f'⑤ 27 月累计变化 · 2024-01 → 2026-04 '
              f'({len(SNAPS)} 季度，真 dump × 全部)',
        height=430,
    )

    # ---- Scene 6: "What doesn't change" — sticky layers ----
    sticky_probes = [
        ('AS 总数', 1, 'total_ases'),
        ('Peering internal edges', 5, 'internal_edges'),
        ('IXP 本地会员', 11, 'ixp_memberships_domestic'),
        ('Outbound hegemony 边', 8, 'outbound_edges'),
    ]
    p6 = sp.make_subplots(
        rows=2, cols=2,
        subplot_titles=[label for label, _, _ in sticky_probes],
        vertical_spacing=0.13, horizontal_spacing=0.10,
    )
    for i, (_, step, key) in enumerate(sticky_probes):
        r, c = i // 2 + 1, i % 2 + 1
        for cc in COUNTRIES:
            vals = [_load_step(s, cc, step).get(key) for s in SNAPS]
            p6.add_trace(go.Scatter(
                x=SNAPS, y=vals, mode='lines+markers',
                line=dict(color=country_color(cc), width=1.4),
                marker=dict(size=5),
                name=cc, legendgroup=cc,
                showlegend=(i == 0),
            ), row=r, col=c)
    p6.update_layout(
        title='⑥ 不变的层 · Sticky layers — what IYP archive doesn\'t '
              're-crawl per quarter',
        height=560,
        legend=dict(orientation='h', y=-0.15),
    )

    figs = [p1, p2, p3, p4, p5, p6]
    for f in figs:
        apply_plotly_theme(f)
    parts = []; first = True
    for f in figs:
        parts.append(to_html(
            f, include_plotlyjs=('inline' if first else False),
            full_html=False, default_height='500px'))
        first = False

    # Build narrative prose inserts between scenes
    cn_pfx_delta = cn_pfx[-1] - cn_pfx[0]
    cn_pfx_pct = cn_pfx_delta / cn_pfx[0] * 100
    us_pfx_pct = ((series['total_prefixes']['US'][-1] -
                   series['total_prefixes']['US'][0]) /
                  series['total_prefixes']['US'][0] * 100)
    cn_any_growth = (series['anycast_prefixes']['CN'][-1] /
                     max(series['anycast_prefixes']['CN'][0], 1))
    nl_rpki = [v for v in series['rpki_rate_pct']['NL'] if v is not None]
    nl_delta = round(nl_rpki[-1] - nl_rpki[0], 1) if len(nl_rpki) >= 2 else 0

    intro = f"""
<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px;
          line-height:1.6">
<b>一段 27 个月的故事：</b>从 2024-01 到 2026-04，十一个独立的 IYP 季度
dump 揭示了中国互联网数据足迹的真实形状。每个数据点都从独立 Neo4j
dump 抽出——没有合成点、没有插值。本页是对 <a
href="evolution.html" style="color:{COLORS['cyan']}">evolution 仪表板</a>
的散文注释——6 个场景讲一条连贯的线。
</p>
"""

    prose1 = f"""
<div style="padding:0 16px;margin:24px 0;color:{TEXT_PRIMARY};font-size:14px;
            line-height:1.7">
<h3 style="color:{COLORS['cyan']};margin-bottom:6px">
场景 ① · 三段式加速</h3>
CN 前缀数从 <b>{cn_pfx[0]:,}</b> 升到 <b>{cn_pfx[-1]:,}</b>
(<b>+{cn_pfx_delta:,}, +{cn_pfx_pct:.1f}%</b>)，但并非匀速——2024
几乎横盘，2025 Q3 开始加速，2026 进入新台阶。27 月年化 CAGR 约
<b>{((cn_pfx[-1]/cn_pfx[0])**(12/span_months)-1)*100:.1f}%</b>。
</div>
"""

    prose2 = f"""
<div style="padding:0 16px;margin:24px 0;color:{TEXT_PRIMARY};font-size:14px;
            line-height:1.7">
<h3 style="color:{COLORS['cyan']};margin-bottom:6px">
场景 ② · 相对速度</h3>
把起点都拉到 100 再比：CN 累积长到 <b>{cn_pfx[-1]/cn_pfx[0]*100:.0f}</b>，
US <b>{series['total_prefixes']['US'][-1]/series['total_prefixes']['US'][0]*100:.0f}</b>。
CN 增速约为 US 的
<b>{cn_pfx_pct/max(us_pfx_pct, 0.1):.1f}x</b>，但起始规模比 US 小一个
量级（85K vs 341K），所以绝对量仍被拉开。
</div>
"""

    prose3 = f"""
<div style="padding:0 16px;margin:24px 0;color:{TEXT_PRIMARY};font-size:14px;
            line-height:1.7">
<h3 style="color:{COLORS['cyan']};margin-bottom:6px">
场景 ③ · RPKI 的异常跃升</h3>
<b>2024-07 / 2025-01 / 2025-07</b> 三个季度全球 RPKI 显示 0%——
probe 确认是 IYP 上游 prefix-level <code>RPKI Valid</code> tag 未被挂到
Prefix 节点（AS 级 ROV tag 仍在）。这 3 个点在图上留白，不插值。
<br><br>
更有意思的是：<b>CN 的 RPKI 从 2026-01 的 {cn_rpki[-2] if cn_rpki[-2] else '—'}% 跃升到
2026-04 的 {cn_rpki[-1]}%——3 个月翻倍</b>。对比：NL 27 月累计只涨
{nl_delta}pp，而 CN 在最后一季就涨 {cn_rpki[-1] - (cn_rpki[-2] or 0):.1f}pp。
这不像自然渗透，更像政策或合规推动的阶跃。
</div>
"""

    prose4 = f"""
<div style="padding:0 16px;margin:24px 0;color:{TEXT_PRIMARY};font-size:14px;
            line-height:1.7">
<h3 style="color:{COLORS['cyan']};margin-bottom:6px">
场景 ④ · Anycast 的慢积累</h3>
CN anycast 前缀从 <b>{series['anycast_prefixes']['CN'][0]}</b> 涨到
<b>{series['anycast_prefixes']['CN'][-1]}</b>
(<b>×{cn_any_growth:.1f}</b>)——不是爆发式，是渐进式的基础设施投入。
RU 和 IN 从更低起点翻了更多倍（100%+ CAGR），但绝对量仍小。
</div>
"""

    prose5 = f"""
<div style="padding:0 16px;margin:24px 0;color:{TEXT_PRIMARY};font-size:14px;
            line-height:1.7">
<h3 style="color:{COLORS['cyan']};margin-bottom:6px">
场景 ⑤ · 27 月排名</h3>
按前缀 CAGR 排序，各国 27 个月累积变化一览。
</div>
"""

    prose6 = f"""
<div style="padding:0 16px;margin:24px 0;color:{TEXT_PRIMARY};font-size:14px;
            line-height:1.7">
<h3 style="color:{COLORS['cyan']};margin-bottom:6px">
场景 ⑥ · 不动的层：IYP archival 缺陷</h3>
这里画的是<b>本该</b>有时间演变的指标——AS 总数、peering 内部边、IXP
本地会员、出向 hegemony 边。但横轴上它们近乎水平——因为 IYP 的
archive dump 只按季度重 crawl BGP / prefix / RPKI / anycast 这些
<i>动态</i>层，AS 目录、peering 图、IXP 成员这些<i>慢变化</i>层实际上是
在多个季度间复用的同一份 crawl 结果。
<br><br>
这意味着：
<ul style="margin:8px 0;padding-left:20px;color:{TEXT_SECONDARY}">
<li>BGP 层（前缀数、RPKI、anycast）的时间序列<b>可信</b></li>
<li>AS/peering/IXP 层的时间序列<b>不可信</b>——看起来在变但实际在复用</li>
<li>要研究"谁多了一个新 AS"或"谁开了新 IXP peering"必须用别的来源</li>
</ul>
这个观察已作为 G10 记录在 <a href="schema_gaps.html"
style="color:{COLORS['cyan']}">schema-gap 清单</a>。
</div>
"""

    banner = (
        '<div class="step-banner">'
        '<h1>10 季度演化叙事 · A Narrative of 11 Quarters</h1>'
        f'<h2>2024-01 → 2026-04 · {len(SNAPS)} real-dump-extracted snapshots · '
        '6-scene story of what moved + what didn\'t</h2>'
        '</div>'
        '<div class="step-footer">evolution_narrative · offline · '
        'builds on SNAPS from new_angles.evolution</div>'
    )

    body = (
        banner + '<div class="content">' + intro
        + prose1 + parts[0]
        + prose2 + parts[1]
        + prose3 + parts[2]
        + prose4 + parts[3]
        + prose5 + parts[4]
        + prose6 + parts[5]
        + '</div>'
    )

    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>10 季度演化叙事 · Evolution Narrative</title>'
        f'{BANNER_CSS}</head><body>{body}</body></html>'
    )
    out_path = OUT / 'evolution_narrative.html'
    out_path.write_text(html, encoding='utf-8')
    mirror = REPO / 'analysis' / 'countries' / 'html' / \
        'evolution_narrative.html'
    mirror.write_text(html, encoding='utf-8')
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    print(f'mirrored to {mirror}')
    print(f'snapshots used: {len(SNAPS)}  span: {span_months} months')
    print(f'CN pfx: {cn_pfx[0]:,} → {cn_pfx[-1]:,}  '
          f'(+{cn_pfx_pct:.1f}%)')
    print(f'CN RPKI 2026 jump: {cn_rpki[-2] or 0}% → {cn_rpki[-1] or 0}%')


if __name__ == '__main__':
    build()
