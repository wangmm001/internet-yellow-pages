"""Time-series evolution dashboard (2025-04 vs 2026-04).

Reads per-snapshot per-country metrics and computes:
 - Per-metric absolute + percent deltas
 - Sovereignty Index delta
 - Global rank change

Produces evolution.html with 4 panels:
 1. Slope chart per sovereignty component
 2. Delta heatmap (country × metric, color = YoY change)
 3. Rank change bump chart
 4. Narrative callouts
"""
import argparse
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.countries.common import (  # noqa: E402
    COLORS, DARK_BG, DARK_BORDER, DARK_PANEL, HTML_DIR, TEXT_PRIMARY, TEXT_SECONDARY,
    TARGET_COUNTRIES, apply_plotly_theme, bilingual, country_color, en,
    list_countries_in_snapshot, list_snapshots, plotly_inline_once,
    read_country_metrics, save_consolidated_html, save_placeholder_html, zh,
)


METRICS_TRACKED = [
    ('AS 数', 1, 'total_ases'),
    ('前缀总数', 4, 'total_prefixes'),
    ('IPv6 前缀', 4, 'v6_prefixes'),
    ('RPKI %', 4, 'rpki_rate_pct'),
    ('Best PR', 6, ('best_ranks', 'pagerank')),
    ('Max k-core', 7, 'deepest_k_in_country'),
    ('入向依赖', 9, 'inbound_edges'),
    ('出向依赖', 8, 'outbound_edges'),
    ('托管主机', 14, 'total_hosted_hostnames'),
    ('DNS 主权 %', 15, 'domestic_pct'),
    ('审查 AS', 18, 'censoring_ases'),
    ('主权指数', 20, 'composite_sovereignty_index'),
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


def load_both(snap_old, snap_new):
    """Return {cc: {step_num: metrics}} for both."""
    countries = sorted(set(list_countries_in_snapshot(snap_old))
                       & set(list_countries_in_snapshot(snap_new)))
    def load(snap):
        out = {}
        for cc in countries:
            out[cc] = {}
            for n in range(1, 21):
                m = read_country_metrics(snap, cc, n)
                out[cc][n] = (m or {}).get('metrics', {}) or {}
        return out
    return countries, load(snap_old), load(snap_new)


def build(snap_old='2025-04', snap_new='2026-04'):
    snaps = list_snapshots()
    if snap_old not in snaps or snap_new not in snaps:
        save_placeholder_html(
            'evolution.html', 0,
            f'时序演化 · Time-Series Evolution ({snap_old}→{snap_new})',
            'Time-Series Evolution',
            f'缺少快照 {snap_old} 或 {snap_new}. 请先完成数据提取。',
            f'Missing snapshot {snap_old} or {snap_new}.')
        return

    countries, old, new = load_both(snap_old, snap_new)
    if not countries:
        save_placeholder_html(
            'evolution.html', 0, '时序演化', 'Evolution',
            '两个快照没有共同国家。', 'No common countries.')
        return

    import plotly.graph_objects as go
    import plotly.subplots as sp

    # Panel 1: Slope chart for sovereignty index
    slope = go.Figure()
    for cc in countries:
        old_v = _get(old[cc], 20, 'composite_sovereignty_index') or 0
        new_v = _get(new[cc], 20, 'composite_sovereignty_index') or 0
        slope.add_trace(go.Scatter(
            x=[snap_old, snap_new], y=[old_v, new_v],
            mode='lines+markers+text',
            text=['', f'{cc} {new_v:.3f}'], textposition='middle right',
            line=dict(color=country_color(cc), width=2),
            marker=dict(size=10), name=cc,
        ))
    slope.update_layout(
        title=f'① 主权综合指数演化 Slope Chart ({snap_old} → {snap_new})',
        xaxis=dict(title='Snapshot'),
        yaxis=dict(title='Composite Sovereignty Index', range=[0, 1]),
        height=560,
    )

    # Panel 2: Delta heatmap
    def pct_change(old_v, new_v):
        if old_v in (None, 0) or new_v is None:
            return None
        return (new_v - old_v) / abs(old_v) * 100
    labels = [m[0] for m in METRICS_TRACKED]
    matrix = []
    texts = []
    for cc in countries:
        row = []
        trow = []
        for _, step, key in METRICS_TRACKED:
            o = _get(old[cc], step, key)
            n = _get(new[cc], step, key)
            delta = pct_change(o, n)
            row.append(delta if delta is not None else 0)
            trow.append(f'{o}→{n}' if o is not None and n is not None else '—')
        matrix.append(row)
        texts.append(trow)
    hm = go.Figure(go.Heatmap(
        z=matrix, x=labels, y=countries,
        colorscale='RdBu', zmid=0,
        colorbar=dict(title='YoY %<br>change'),
        text=texts,
        hovertemplate='%{y} × %{x}<br>%{text}<br>%{z:.1f}%<extra></extra>',
    ))
    hm.update_layout(
        title=f'② YoY Δ% 热图 ({snap_old} → {snap_new})',
        xaxis=dict(tickangle=-30),
        height=500,
    )

    # Panel 3: Sovereignty components side-by-side
    comp_names = ['hosting_sovereignty', 'dns_sovereignty', 'rpki_adoption',
                  'ixp_domesticization', 'hub_ratio']
    comp_labels = ['Hosting', 'DNS Sov', 'RPKI', 'IXP Domes', 'Hub Ratio']
    comp_fig = sp.make_subplots(
        rows=1, cols=5, subplot_titles=comp_labels, shared_yaxes=True)
    for i, ck in enumerate(comp_names):
        for cc in countries:
            o = ((old[cc].get(20) or {}).get('components') or {}).get(ck, 0) or 0
            n = ((new[cc].get(20) or {}).get('components') or {}).get(ck, 0) or 0
            comp_fig.add_trace(go.Scatter(
                x=[snap_old, snap_new], y=[o, n],
                mode='lines+markers', name=cc, legendgroup=cc,
                showlegend=(i == 0),
                line=dict(color=country_color(cc), width=2),
                marker=dict(size=6),
            ), row=1, col=i + 1)
    comp_fig.update_layout(
        title='③ 五分项主权指数演化 · Per-component slope',
        height=380, showlegend=True,
    )
    comp_fig.update_yaxes(range=[0, 1])

    # Panel 4: Scale metric bump chart (AS count rank evolution)
    def rank_series(snapshot_data, key, is_step_3=True):
        """Return {cc: rank} for a given metric from Step 3."""
        vals = [(cc, (snapshot_data[cc].get(3, {}) or {}).get(key, {}).get('value', 0))
                for cc in countries]
        srt = sorted(vals, key=lambda t: -t[1])
        return {cc: i + 1 for i, (cc, _) in enumerate(srt)}
    bump_fig = sp.make_subplots(
        rows=2, cols=2, subplot_titles=(
            'AS count rank', 'Prefix count rank',
            'IXP count rank', 'Facility count rank'))
    for panel_i, (metric, mr, mc) in enumerate([
        ('as_count', 1, 1), ('prefix_count', 1, 2),
        ('ixp_count', 2, 1), ('facility_count', 2, 2),
    ]):
        old_r = rank_series(old, metric)
        new_r = rank_series(new, metric)
        for cc in countries:
            bump_fig.add_trace(go.Scatter(
                x=[snap_old, snap_new],
                y=[old_r.get(cc, len(countries)), new_r.get(cc, len(countries))],
                mode='lines+markers+text',
                text=['', cc], textposition='middle right',
                line=dict(color=country_color(cc), width=2),
                marker=dict(size=8),
                showlegend=(panel_i == 0), legendgroup=cc, name=cc,
            ), row=mr, col=mc)
    bump_fig.update_layout(
        title='④ 排名演化 Bump Chart · Rank change within 9-country group',
        height=560,
    )
    bump_fig.update_yaxes(autorange='reversed')

    # Narrative summary: biggest movers
    def biggest_movers(key, step):
        moves = []
        for cc in countries:
            o = _get(old[cc], step, key)
            n = _get(new[cc], step, key)
            if o is None or n is None:
                continue
            moves.append((cc, o, n, pct_change(o, n)))
        moves.sort(key=lambda t: abs(t[3] or 0), reverse=True)
        return moves[:3]

    sov_moves = biggest_movers('composite_sovereignty_index', 20)
    as_moves = biggest_movers('total_ases', 1)
    pfx_moves = biggest_movers('total_prefixes', 4)

    narr = f'''
    <div class="sidebar-note">
    <b>时序演化摘要 · Time-Series Evolution Summary</b><br><br>
    对比快照 {snap_old} → {snap_new}，九国参与对比。<br>
    <b>主权指数最大变动 · biggest sovereignty movers:</b><br>
    {"<br>".join(f"  {cc} {o:.3f}→{n:.3f} ({d:+.1f}%)" for cc, o, n, d in sov_moves)}
    <br><br>
    <b>AS 数量最大变动 · biggest AS-count movers:</b><br>
    {"<br>".join(f"  {cc} {o:,}→{n:,} ({d:+.1f}%)" for cc, o, n, d in as_moves)}
    <br><br>
    <b>前缀数最大变动 · biggest prefix-count movers:</b><br>
    {"<br>".join(f"  {cc} {o:,}→{n:,} ({d:+.1f}%)" for cc, o, n, d in pfx_moves)}
    </div>
    '''

    figs = [slope, hm, comp_fig, bump_fig]
    for f in figs:
        apply_plotly_theme(f)
    body = narr + plotly_inline_once(figs)
    save_consolidated_html(
        body, 'evolution.html',
        title_zh=f'时序演化 · {snap_old} → {snap_new}',
        title_en=f'Time-Series Evolution · {snap_old} vs {snap_new}',
        subtitle=f'{len(countries)} common countries · 20 metrics · 2 snapshots',
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--old', default='2025-04')
    ap.add_argument('--new', default='2026-04')
    args = ap.parse_args()
    build(args.old, args.new)


if __name__ == '__main__':
    main()
