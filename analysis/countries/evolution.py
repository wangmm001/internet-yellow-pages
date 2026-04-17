"""Time-series evolution dashboard (N quarterly snapshots).

Reads per-snapshot per-country metrics and renders 5 panels:
  ① Trend small-multiples — 9 countries × 12 key metrics across all snapshots
  ② CAGR heatmap — country × metric, monthly-compounded annualized growth
  ③ Sovereignty Index trajectory
  ④ Inflection / volatility table — Top 30 by direction changes + range
  ⑤ Rank fluctuation band — 4 scale metrics, lower rank = better
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.countries.common import (  # noqa: E402
    COLORS, DARK_BG, DARK_BORDER, DARK_PANEL, HTML_DIR, TEXT_PRIMARY, TEXT_SECONDARY,
    TARGET_COUNTRIES, apply_plotly_theme, bilingual, country_color, en,
    list_countries_in_snapshot, list_snapshots, plotly_inline_once,
    read_country_metrics, save_consolidated_html, save_placeholder_html, zh,
)


METRICS_TRACKED = [
    ('AS 数',       1, 'total_ases'),
    ('前缀总数',    4, 'total_prefixes'),
    ('IPv6 前缀',   4, 'v6_prefixes'),
    ('RPKI %',      4, 'rpki_rate_pct'),
    ('Best PR',     6, ('best_ranks', 'pagerank')),
    ('Max k-core',  7, 'deepest_k_in_country'),
    ('入向依赖',    9, 'inbound_edges'),
    ('出向依赖',    8, 'outbound_edges'),
    ('托管主机',   14, 'total_hosted_hostnames'),
    ('DNS 主权 %', 15, 'domestic_pct'),
    ('审查 AS',    18, 'censoring_ases'),
    ('主权指数',   20, 'composite_sovereignty_index'),
]


def _get(data, step, key):
    s = (data or {}).get(step, {}) or {}
    if isinstance(key, tuple):
        cur = s
        for k in key:
            cur = (cur or {}).get(k, None)
            if cur is None:
                return None
        return cur
    return s.get(key, None)


def load_all(snapshots):
    """Return (countries, {snap: {cc: {step: metrics_dict}}})."""
    per_snap = [set(list_countries_in_snapshot(s)) for s in snapshots]
    countries = sorted(set.intersection(*per_snap)) if per_snap else []
    out = {s: {cc: {} for cc in countries} for s in snapshots}
    for s in snapshots:
        for cc in countries:
            for n in range(1, 21):
                m = read_country_metrics(s, cc, n)
                out[s][cc][n] = (m or {}).get('metrics', {}) or {}
    return countries, out


def snapshot_to_months(s):
    """'2025-01' → 0, '2025-04' → 3, '2026-04' → 15."""
    y, m = s.split('-')
    return (int(y) - 2025) * 12 + (int(m) - 1)


def cagr(start_v, end_v, months):
    """Compound monthly growth rate annualized. None if invalid."""
    if start_v is None or end_v is None or months <= 0:
        return None
    try:
        if start_v <= 0 or end_v <= 0:
            return None
        return (end_v / start_v) ** (12.0 / months) - 1.0
    except (ZeroDivisionError, ValueError, TypeError):
        return None


def inflection_count(series):
    """Number of direction reversals in a numeric series (None-tolerant)."""
    vals = [v for v in series if v is not None and isinstance(v, (int, float))]
    if len(vals) < 3:
        return 0
    signs = []
    for a, b in zip(vals, vals[1:]):
        if b > a:
            signs.append(1)
        elif b < a:
            signs.append(-1)
        else:
            signs.append(0)
    reversals = 0
    for a, b in zip(signs, signs[1:]):
        if a != 0 and b != 0 and a != b:
            reversals += 1
    return reversals


def range_over_min(series):
    """(max-min) / |min|; None if insufficient data."""
    vals = [v for v in series if v is not None and isinstance(v, (int, float))]
    if len(vals) < 2:
        return None
    vmin, vmax = min(vals), max(vals)
    if vmin == 0:
        return None
    return (vmax - vmin) / abs(vmin)


def _fmt_num(v):
    if v is None:
        return '—'
    if isinstance(v, float):
        return f'{v:.3f}' if abs(v) < 100 else f'{v:,.0f}'
    return str(v)


def build(snapshots=None):
    import plotly.graph_objects as go
    import plotly.subplots as sp

    all_snaps = list_snapshots()
    snapshots = snapshots or all_snaps
    snapshots = [s for s in snapshots if s in all_snaps]
    if len(snapshots) < 2:
        save_placeholder_html(
            'evolution.html', 0,
            '时序演化 · Time-Series Evolution',
            'Time-Series Evolution',
            f'需要 ≥ 2 个快照，当前只有 {snapshots}',
            f'Need ≥ 2 snapshots, found {snapshots}')
        return

    countries, data = load_all(snapshots)
    if not countries:
        save_placeholder_html(
            'evolution.html', 0,
            '时序演化', 'Evolution',
            '快照之间没有共同国家。', 'No common countries across snapshots.')
        return

    x_labels = snapshots

    # ───── Panel 1 · Trend small-multiples ─────
    n_metrics = len(METRICS_TRACKED)
    cols = 3
    rows = (n_metrics + cols - 1) // cols
    panel1 = sp.make_subplots(
        rows=rows, cols=cols,
        subplot_titles=[m[0] for m in METRICS_TRACKED],
        vertical_spacing=0.06, horizontal_spacing=0.05,
    )
    for i, (label, step, key) in enumerate(METRICS_TRACKED):
        r, c = i // cols + 1, i % cols + 1
        for cc in countries:
            ys = [_get(data[s][cc], step, key) for s in snapshots]
            panel1.add_trace(go.Scatter(
                x=x_labels, y=ys, mode='lines+markers',
                name=cc, legendgroup=cc, showlegend=(i == 0),
                line=dict(color=country_color(cc), width=1.5),
                marker=dict(size=5),
            ), row=r, col=c)
    panel1.update_layout(
        title='① 12 项关键指标趋势 · 9 国 × 季度 · Trend small-multiples',
        height=260 * rows, hovermode='x unified',
    )

    # ───── Panel 2 · CAGR heatmap ─────
    start, end = snapshots[0], snapshots[-1]
    months = snapshot_to_months(end) - snapshot_to_months(start)
    z, text = [], []
    for cc in countries:
        row_z, row_t = [], []
        for label, step, key in METRICS_TRACKED:
            v0 = _get(data[start][cc], step, key)
            v1 = _get(data[end][cc], step, key)
            g = cagr(v0, v1, months)
            row_z.append(None if g is None else round(g * 100, 2))
            row_t.append('—' if g is None else f'{g*100:+.1f}%')
        z.append(row_z)
        text.append(row_t)
    panel2 = go.Figure(go.Heatmap(
        z=z, x=[m[0] for m in METRICS_TRACKED], y=countries,
        text=text, texttemplate='%{text}',
        colorscale='RdBu', zmid=0, reversescale=False,
        colorbar=dict(title='CAGR %'),
        hovertemplate='%{y} × %{x}<br>CAGR: %{text}<extra></extra>',
    ))
    panel2.update_layout(
        title=f'② 复合年增长率 CAGR · {start} → {end}（{months} 个月，按月复利）',
        xaxis=dict(tickangle=-30),
        height=max(360, 40 * len(countries) + 140),
    )

    # ───── Panel 3 · Sovereignty trajectories ─────
    panel3 = go.Figure()
    for cc in countries:
        ys = [_get(data[s][cc], 20, 'composite_sovereignty_index') for s in snapshots]
        panel3.add_trace(go.Scatter(
            x=x_labels, y=ys, mode='lines+markers+text',
            name=cc, line=dict(color=country_color(cc), width=2),
            marker=dict(size=8),
            text=[''] * (len(ys) - 1) + [cc],
            textposition='middle right',
        ))
    panel3.update_layout(
        title='③ Sovereignty Index 时序 · Composite trajectory',
        xaxis=dict(title='Snapshot'),
        yaxis=dict(title='Composite Sovereignty Index', range=[0, 1]),
        height=480, hovermode='x unified',
    )

    # ───── Panel 4 · Inflection / volatility table ─────
    movers = []
    for cc in countries:
        for label, step, key in METRICS_TRACKED:
            series = [_get(data[s][cc], step, key) for s in snapshots]
            reversals = inflection_count(series)
            vol = range_over_min(series)
            vals = [v for v in series if v is not None and isinstance(v, (int, float))]
            if len(vals) < 2:
                continue
            movers.append((cc, label, reversals, vol, series))
    movers.sort(
        key=lambda r: (-(r[2] or 0), -(r[3] if r[3] is not None else 0)))
    top = movers[:30]
    series_cell = [' → '.join(_fmt_num(v) for v in r[4]) for r in top]
    panel4 = go.Figure(go.Table(
        header=dict(
            values=['Country', 'Metric', 'Direction<br>changes',
                    'Range / |min|', 'Series'],
            fill_color=DARK_PANEL,
            font=dict(color=TEXT_PRIMARY, size=13),
            align='left'),
        cells=dict(values=[
            [r[0] for r in top],
            [r[1] for r in top],
            [r[2] for r in top],
            [('—' if r[3] is None else f'{r[3]*100:.0f}%') for r in top],
            series_cell,
        ],
            fill_color=DARK_BG,
            font=dict(color=TEXT_SECONDARY, size=12),
            align='left', height=26)))
    panel4.update_layout(
        title='④ 方向反转与波动榜 · Top 30 by direction changes then range',
        height=820,
    )

    # ───── Panel 5 · Rank fluctuation band ─────
    rank_metrics = [
        ('AS count rank',   3, ('as_count',       'rank')),
        ('Prefix rank',     3, ('prefix_count',   'rank')),
        ('IXP rank',        3, ('ixp_count',      'rank')),
        ('Facility rank',   3, ('facility_count', 'rank')),
    ]
    panel5 = sp.make_subplots(
        rows=1, cols=len(rank_metrics),
        subplot_titles=[m[0] for m in rank_metrics],
        shared_yaxes=False, horizontal_spacing=0.06)
    for i, (label, step, key) in enumerate(rank_metrics, start=1):
        for cc in countries:
            ys = [_get(data[s][cc], step, key) for s in snapshots]
            panel5.add_trace(go.Scatter(
                x=x_labels, y=ys, mode='lines+markers',
                name=cc, legendgroup=cc, showlegend=(i == 1),
                line=dict(color=country_color(cc), width=1.3),
                marker=dict(size=5),
            ), row=1, col=i)
        panel5.update_yaxes(autorange='reversed', row=1, col=i)
    panel5.update_layout(
        title='⑤ 全球排名波动带 · Rank trajectories (lower = better)',
        height=480, hovermode='x unified',
    )

    # ───── Stitch ─────
    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'基于 <b>{len(snapshots)}</b> 个季度快照（{", ".join(snapshots)}）对 '
        f'<b>{len(countries)}</b> 国 × <b>{len(METRICS_TRACKED)}</b> 指标的时序分析。'
        f'CAGR 为按月复利折算到年。<br>'
        f'Time-series analysis across <b>{len(snapshots)}</b> quarterly snapshots '
        f'for <b>{len(countries)}</b> countries × <b>{len(METRICS_TRACKED)}</b> metrics. '
        f'CAGR is monthly-compounded, annualized.'
        f'</p>'
    )
    body = intro + plotly_inline_once(
        [panel1, panel2, panel3, panel4, panel5])
    save_consolidated_html(
        body,
        'evolution.html',
        f'时序演化 · {snapshots[0]} → {snapshots[-1]}（{len(snapshots)} 季度）',
        f'Time-Series Evolution · {snapshots[0]} → {snapshots[-1]} '
        f'({len(snapshots)} quarters)',
        subtitle=(f'{len(countries)} 国 · {len(METRICS_TRACKED)} 指标 · '
                  f'{len(snapshots)} 快照'),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--snapshots', nargs='+', default=None,
                    help='Override auto-detected snapshot list')
    args = ap.parse_args()
    build(snapshots=args.snapshots)


if __name__ == '__main__':
    main()
