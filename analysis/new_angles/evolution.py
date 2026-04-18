"""Evolution: 10-quarter × 9-country time-series dashboard.

Reads the per-snapshot metrics JSONs under analysis/countries/data/{snap}/{cc}/
and plots the metrics that show genuine per-snapshot variation. Many IYP
layers (AS inventory, peering topology, IXP memberships) are frozen across
older dumps — this page honestly focuses on the layers that *do* evolve:
prefix footprint, RPKI adoption, anycast deployment, and CAIDA rank.

Output: analysis/new_angles/html/evolution.html
Site mirror: analysis/countries/html/evolution.html (supersedes the older
countries/evolution.py which plotted 12 metrics including sticky layers).
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.china.common import (  # noqa: E402
    BANNER_CSS, COLORS, TEXT_PRIMARY, TEXT_SECONDARY,
    apply_plotly_theme, country_color,
)

REPO = Path(__file__).resolve().parent.parent.parent
SNAP_ROOT = REPO / 'analysis' / 'countries' / 'data'
OUT = REPO / 'analysis' / 'new_angles' / 'html'
OUT.mkdir(parents=True, exist_ok=True)

SNAPS = ['2024-01', '2024-04', '2024-07', '2024-10', '2025-01',
         '2025-04', '2025-07', '2025-10', '2026-01', '2026-04']
COUNTRIES = ['US', 'CN', 'JP', 'IN', 'DE', 'GB', 'FR', 'NL', 'RU']
COUNTRY_NAME = {
    'US': '美国', 'CN': '中国', 'JP': '日本', 'IN': '印度', 'DE': '德国',
    'GB': '英国', 'FR': '法国', 'NL': '荷兰', 'RU': '俄罗斯',
}


def _load(snap, cc, step):
    f = SNAP_ROOT / snap / cc / f'step{step:02d}_metrics.json'
    if not f.exists():
        return {}
    return json.loads(f.read_text(encoding='utf-8')).get('metrics', {}) or {}


def _gap_snaps_rpki():
    """Snapshots where RPKI is 0 for ALL 9 countries — Tag-label mismatch."""
    gaps = set()
    for snap in SNAPS:
        zero_count = sum(
            1 for cc in COUNTRIES
            if _load(snap, cc, 4).get('rpki_rate_pct') == 0
        )
        if zero_count >= 7:
            gaps.add(snap)
    return gaps


def collect():
    """Return {metric_key: {cc: [val @ snap0, val @ snap1, ...]}}."""
    series = {
        'total_prefixes': {}, 'v4_prefixes': {}, 'v6_prefixes': {},
        'v6_share_pct': {}, 'rpki_rate_pct': {}, 'anycast_prefixes': {},
        'best_caida_rank': {}, 'alias_sources': {}, 'domestic_pct': {},
    }
    rpki_gaps = _gap_snaps_rpki()
    for cc in COUNTRIES:
        for key in series:
            series[key][cc] = []
        for snap in SNAPS:
            s02 = _load(snap, cc, 2)
            s04 = _load(snap, cc, 4)
            s15 = _load(snap, cc, 15)
            s16 = _load(snap, cc, 16)
            total = s04.get('total_prefixes') or 0
            v4 = s04.get('v4_prefixes') or 0
            v6 = s04.get('v6_prefixes') or 0
            series['total_prefixes'][cc].append(total)
            series['v4_prefixes'][cc].append(v4)
            series['v6_prefixes'][cc].append(v6)
            series['v6_share_pct'][cc].append(
                round(v6 / total * 100, 2) if total else None)
            rpki = s04.get('rpki_rate_pct')
            series['rpki_rate_pct'][cc].append(
                None if snap in rpki_gaps else rpki)
            series['anycast_prefixes'][cc].append(s04.get('anycast_prefixes'))
            series['best_caida_rank'][cc].append(s02.get('best_caida_rank'))
            series['alias_sources'][cc].append(s16.get('alias_sources'))
            series['domestic_pct'][cc].append(s15.get('domestic_pct'))
    return series


def _line_trace(go, cc, y, name_suffix='', dash=None):
    vis_y = [v if v is not None else None for v in y]
    return go.Scatter(
        x=SNAPS, y=vis_y, name=f'{COUNTRY_NAME[cc]} {cc}{name_suffix}',
        mode='lines+markers',
        line=dict(color=country_color(cc), width=2.3, dash=dash),
        marker=dict(size=7, color=country_color(cc)),
        connectgaps=False, hovertemplate='%{x}: %{y}<extra></extra>',
    )


def build():
    import plotly.graph_objects as go
    series = collect()

    # --- P1: total prefixes growth (log scale for cross-country comparison)
    p1 = go.Figure()
    for cc in COUNTRIES:
        p1.add_trace(_line_trace(go, cc, series['total_prefixes'][cc]))
    p1.update_layout(
        title='① BGP 前缀总量轨迹 · Total advertised prefix count per quarter',
        yaxis=dict(title='# prefixes (log)', type='log'),
        xaxis=dict(title=''),
        height=520,
        legend=dict(orientation='h', y=-0.22),
    )

    # --- P2: IPv6 share trajectory
    p2 = go.Figure()
    for cc in COUNTRIES:
        p2.add_trace(_line_trace(go, cc, series['v6_share_pct'][cc]))
    p2.update_layout(
        title='② IPv6 前缀占比 · IPv6 share of total prefixes (%)',
        yaxis=dict(title='v6 / (v4+v6) · %', rangemode='tozero'),
        xaxis=dict(title=''),
        height=480,
        legend=dict(orientation='h', y=-0.22),
    )

    # --- P3: RPKI adoption trajectory  (with gap annotations)
    p3 = go.Figure()
    for cc in COUNTRIES:
        p3.add_trace(_line_trace(go, cc, series['rpki_rate_pct'][cc]))
    # Mark broken-extract snapshots with annotation
    gap_snaps = []
    for i, snap in enumerate(SNAPS):
        vals = [series['rpki_rate_pct'][cc][i] for cc in COUNTRIES]
        if sum(1 for v in vals if v is None) >= 5:
            gap_snaps.append(snap)
    if gap_snaps:
        p3.add_annotation(
            xref='paper', yref='paper', x=0.02, y=1.08,
            text=f'⚠ {", ".join(gap_snaps)} 点 Tag schema 失配 '
                 f'(留白, not interpolated)',
            showarrow=False, bgcolor='rgba(255,159,10,0.12)',
            bordercolor=COLORS['orange'], borderwidth=1,
            font=dict(color=COLORS['orange'], size=11),
        )
    p3.update_layout(
        title='③ RPKI ROA 覆盖率 · RPKI Valid share of total prefixes (%)',
        yaxis=dict(title='RPKI Valid · %', rangemode='tozero'),
        xaxis=dict(title=''),
        height=500,
        legend=dict(orientation='h', y=-0.22),
    )

    # --- P4: anycast prefix count (log)
    p4 = go.Figure()
    for cc in COUNTRIES:
        p4.add_trace(_line_trace(go, cc, series['anycast_prefixes'][cc]))
    p4.update_layout(
        title='④ Anycast 前缀数量 · Anycast-tagged prefix count',
        yaxis=dict(title='# anycast prefixes'),
        xaxis=dict(title=''),
        height=480,
        legend=dict(orientation='h', y=-0.22),
    )

    # --- P5: best CAIDA rank (lower = better, inverted y)
    p5 = go.Figure()
    for cc in COUNTRIES:
        vals = series['best_caida_rank'][cc]
        # skip countries with identical/sticky values
        if len(set(v for v in vals if v is not None)) >= 3:
            p5.add_trace(_line_trace(go, cc, vals))
    p5.update_layout(
        title='⑤ 最强 AS 的 CAIDA 全球排名 · Best-ranked AS trajectory '
              '(lower = better)',
        yaxis=dict(title='CAIDA ASRank (↓ better)', autorange='reversed'),
        xaxis=dict(title=''),
        height=460,
        legend=dict(orientation='h', y=-0.25),
    )

    # --- P6: CNAME alias_sources growth (content-geography)
    p6 = go.Figure()
    for cc in COUNTRIES:
        vals = series['alias_sources'][cc]
        if any(v for v in vals if v):
            p6.add_trace(_line_trace(go, cc, vals))
    p6.update_layout(
        title='⑥ 跨境 CNAME 源数量 · Cross-border CNAME source count '
              '(content-geography signal)',
        yaxis=dict(title='# alias source hostnames'),
        xaxis=dict(title=''),
        height=460,
        legend=dict(orientation='h', y=-0.25),
    )

    from plotly.io import to_html
    figs = [p1, p2, p3, p4, p5, p6]
    for f in figs:
        apply_plotly_theme(f)
    parts = []; first = True
    for f in figs:
        parts.append(to_html(
            f, include_plotlyjs=('inline' if first else False),
            full_html=False, default_height='500px'))
        first = False

    # Compute a few hero numbers for the intro
    def _delta(cc, key):
        vals = [v for v in series[key][cc] if v is not None]
        if len(vals) < 2:
            return None
        return vals[-1] - vals[0]

    cn_pfx_delta = _delta('CN', 'total_prefixes')
    cn_pfx_start = series['total_prefixes']['CN'][0]
    cn_pfx_end = series['total_prefixes']['CN'][-1]
    us_pfx_start = series['total_prefixes']['US'][0]
    us_pfx_end = series['total_prefixes']['US'][-1]
    cn_rpki_end = next((v for v in reversed(series['rpki_rate_pct']['CN'])
                        if v is not None), None)
    us_rpki_end = next((v for v in reversed(series['rpki_rate_pct']['US'])
                        if v is not None), None)

    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>数据：</b>analysis/countries/data/&lt;snap&gt;/&lt;cc&gt;/ 下的 '
        f'per-country metrics JSON，共 10 季度 × 9 国 × 20 step。'
        f'本页仅展示 <i>真正逐快照变化</i> 的指标——BGP 前缀、RPKI、anycast、'
        f'CAIDA 排名、内容溯源 CNAME。'
        f'<br><b>关键变化 (2024-01 → 2026-04)：</b> '
        f'CN 前缀 {cn_pfx_start:,}→{cn_pfx_end:,} (+{cn_pfx_delta:,}, '
        f'+{cn_pfx_delta / cn_pfx_start * 100:.1f}%)；'
        f'US {us_pfx_start:,}→{us_pfx_end:,}。'
        f'CN RPKI 最新 {cn_rpki_end or "—"}%，US {us_rpki_end or "—"}%。'
        f'</p>'
        f'<p style="padding:0 16px;margin:8px 0 16px;color:{COLORS["orange"]};'
        f'border-left:3px solid {COLORS["orange"]};padding-left:14px;'
        f'font-size:13px">'
        f'⚠️ <b>坦承：</b>IYP 历史 dump 存档里 <b>AS 清册 / peering / '
        f'IXP 成员 / hegemony 依赖图</b> 这些层没有按季度重新 crawl——'
        f'6/10 快照在这些层完全相同。本页只画 BGP 层 + CAIDA + CNAME，'
        f'确保线条的拐点是真实变化。全矩阵（含 sticky 指标）见 '
        f'<a href="../countries/scorecards.html" style="color:{COLORS["cyan"]}">'
        f'国家积分牌</a>。'
        f'</p>'
    )

    banner = (
        '<div class="step-banner">'
        '<h1>10 季度演化 · Evolution Dashboard</h1>'
        '<h2>2024-01 → 2026-04 · BGP 前缀 · RPKI · anycast · CAIDA rank · '
        'CNAME 溯源</h2>'
        '</div>'
        '<div class="step-footer">evolution · offline · '
        'per-snapshot metrics JSON</div>'
    )
    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>10 季度演化 · Evolution Dashboard</title>'
        f'{BANNER_CSS}</head><body>'
        f'{banner}<div class="content">{intro}'
        f'{"".join(parts)}</div></body></html>'
    )
    out_path = OUT / 'evolution.html'
    out_path.write_text(html, encoding='utf-8')
    mirror = REPO / 'analysis' / 'countries' / 'html' / 'evolution.html'
    mirror.write_text(html, encoding='utf-8')
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    print(f'mirrored to {mirror}')
    # Diagnostic summary
    for key in ('total_prefixes', 'rpki_rate_pct', 'anycast_prefixes'):
        print(f'\n{key} trajectory:')
        for cc in COUNTRIES:
            print(f'  {cc}: {series[key][cc]}')


if __name__ == '__main__':
    build()
