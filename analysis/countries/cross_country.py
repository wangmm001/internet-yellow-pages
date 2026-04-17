"""Cross-country comparison dashboard.

Reads per-country metrics JSONs and produces cross_country.html with:
 1. Heatmap: country × normalized metrics
 2. Parallel coordinates: 9 countries × 20 normalized metrics
 3. Radar overlay: 9 countries' sovereignty components
 4. Grouped bars: scale metrics
 5. Country profile card grid (3×3)
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.countries.common import (  # noqa: E402
    COLORS, DARK_BG, DARK_BORDER, DARK_PANEL, HTML_DIR, TEXT_PRIMARY, TEXT_SECONDARY,
    TARGET_COUNTRIES, apply_plotly_theme, bilingual, country_color, en,
    list_countries_in_snapshot, plotly_inline_once, read_country_metrics,
    save_consolidated_html, zh,
)


def load_snapshot(snapshot, countries):
    """Load all step metrics for given countries.

    Returns dict[cc] -> dict[step] -> metrics_dict.
    """
    out = {}
    for cc in countries:
        per = {}
        for n in range(1, 21):
            meta = read_country_metrics(snapshot, cc, n)
            per[n] = (meta or {}).get('metrics', {}) or {}
        out[cc] = per
    return out


def normalize(values, invert=False):
    """Normalize list of values to [0, 1]. `invert=True` means lower=better → higher score."""
    vals = [(v if v is not None else 0) for v in values]
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return [0.5 for _ in vals]
    norm = [(v - lo) / (hi - lo) for v in vals]
    if invert:
        norm = [1 - n for n in norm]
    return norm


# Metric definitions for cross-country comparison (label, step, key, invert-low-is-good)
METRICS = [
    ('AS 数 · AS count', 1, 'total_ases', False),
    ('前缀总数 · Prefix count', 4, 'total_prefixes', False),
    ('IPv6 前缀 · v6 prefix count', 4, 'v6_prefixes', False),
    ('RPKI 覆盖率% · RPKI rate', 4, 'rpki_rate_pct', False),
    ('最佳 PageRank · Best PR rank', 6, ('best_ranks', 'pagerank'), True),
    ('最深 k-core · Max k', 7, 'deepest_k_in_country', False),
    ('入向 Hegemony · Inbound edges', 9, 'inbound_edges', False),
    ('出向 Hegemony · Outbound edges', 8, 'outbound_edges', False),
    ('前缀 HHI · Prefix HHI', 10, 'hhi_prefix', True),
    ('前缀 Gini · Prefix Gini', 10, 'gini_prefix', True),
    ('境内 IXP 会员 · Domestic IXP', 11, 'ixp_memberships_domestic', False),
    ('境外 IXP 会员 · Foreign IXP', 11, 'ixp_memberships_foreign', False),
    ('机房记录 · Facility records', 12, 'total_facility_records', False),
    ('托管主机 · Hosted hostnames', 14, 'total_hosted_hostnames', False),
    ('DNS 主权% · DNS sovereignty', 15, 'domestic_pct', False),
    ('CNAME 源 · Alias sources', 16, 'alias_sources', False),
    ('审查 AS · Censoring ASes', 18, 'censoring_ases', False),
    ('审查次数 · Detections', 18, 'total_detections', False),
    ('Atlas 探针 · Atlas probes', 19, 'probes_count', False),
    ('主权指数 · Sovereignty Idx', 20, 'composite_sovereignty_index', False),
]


def get_metric(data_cc, step, key):
    step_data = data_cc.get(step, {}) or {}
    if isinstance(key, tuple):
        cur = step_data
        for k in key:
            cur = (cur or {}).get(k, None)
            if cur is None:
                return None
        return cur
    return step_data.get(key, None)


def build_matrix(all_data, countries):
    """Return (metric_labels, country_list, matrix, raw_matrix)."""
    labels = [m[0] for m in METRICS]
    raw = []
    for cc in countries:
        row = []
        for label, step, key, _ in METRICS:
            row.append(get_metric(all_data[cc], step, key))
        raw.append(row)
    # Transpose raw: row = metric, col = country
    trans = list(zip(*raw))
    norm = []
    for i, (_, _, _, invert) in enumerate(METRICS):
        norm.append(normalize(list(trans[i]), invert=invert))
    # Transpose back so rows = country, cols = metric
    norm_matrix = list(zip(*norm))
    return labels, countries, norm_matrix, raw


def build_cross_country(snapshot):
    countries = [cc for cc in TARGET_COUNTRIES
                 if cc in list_countries_in_snapshot(snapshot)]
    data = load_snapshot(snapshot, countries)
    labels, _, norm_matrix, raw = build_matrix(data, countries)

    import plotly.graph_objects as go
    import plotly.subplots as sp

    # Panel 1: Heatmap
    hm = go.Figure(go.Heatmap(
        z=[list(row) for row in norm_matrix],
        x=labels, y=countries,
        colorscale='RdBu_r',
        colorbar=dict(title='Normalized<br>(higher=<br>relatively<br>stronger)'),
        text=[[f'{v:.2f}' if v is not None else '—' for v in r] for r in raw],
        hovertemplate='%{y} × %{x}<br>raw=%{text}<br>norm=%{z:.2f}<extra></extra>',
    ))
    hm.update_layout(
        title='① 国家 × 指标 热图 · Country × Metric heatmap (normalized 0-1)',
        xaxis=dict(tickangle=-45),
        height=500,
    )

    # Panel 2: Parallel coordinates (all 20 metrics × 9 countries)
    dims = []
    for i, label in enumerate(labels):
        col_vals = [norm_matrix[j][i] or 0 for j in range(len(countries))]
        dims.append(dict(label=label[:18], values=col_vals, range=[0, 1]))
    country_idx = {cc: i for i, cc in enumerate(countries)}
    parcoords = go.Figure(go.Parcoords(
        line=dict(
            color=[country_idx[cc] for cc in countries],
            colorscale=[[i / max(len(countries) - 1, 1), country_color(cc)]
                        for i, cc in enumerate(countries)],
        ),
        dimensions=dims,
    ))
    parcoords.update_layout(
        title='② 9 国多指标平行坐标 · Parallel coordinates (color = country)',
        height=500,
    )

    # Panel 3: Radar overlay of sovereignty components
    radar = go.Figure()
    comp_order = ['hosting_sovereignty', 'dns_sovereignty', 'rpki_adoption',
                  'ixp_domesticization', 'hub_ratio']
    comp_labels = ['Hosting', 'DNS Sov', 'RPKI', 'IXP Domes', 'Hub Ratio']
    for cc in countries:
        comps = (data[cc].get(20) or {}).get('components', {}) or {}
        vals = [comps.get(k, 0) for k in comp_order]
        radar.add_trace(go.Scatterpolar(
            r=vals + [vals[0]],
            theta=comp_labels + [comp_labels[0]],
            name=cc,
            line=dict(color=country_color(cc), width=2),
            fill='toself',
            fillcolor=f'rgba({",".join(str(int(x*255)) for x in (0.3, 0.3, 0.3))},0.05)',
        ))
    radar.update_layout(
        title='③ 主权指数五分项雷达图 · Sovereignty Index Radar (all 9 countries)',
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1], gridcolor=DARK_BORDER),
            bgcolor=DARK_PANEL,
            angularaxis=dict(gridcolor=DARK_BORDER),
        ),
        height=620,
    )

    # Panel 4: Grouped bars — scale metrics
    scale_fig = sp.make_subplots(
        rows=2, cols=2, subplot_titles=(
            'AS 数 · AS count', '前缀数 · Prefix count',
            'IXP 会员(境内+境外) · IXP memberships', '托管主机 · Hosted hostnames'))
    # AS count from Step 1
    as_counts = [data[cc].get(1, {}).get('total_ases', 0) for cc in countries]
    scale_fig.add_trace(go.Bar(
        x=countries, y=as_counts,
        marker_color=[country_color(cc) for cc in countries],
        showlegend=False, text=[f'{v:,}' for v in as_counts], textposition='outside',
    ), row=1, col=1)
    pfx = [data[cc].get(4, {}).get('total_prefixes', 0) for cc in countries]
    scale_fig.add_trace(go.Bar(
        x=countries, y=pfx, marker_color=[country_color(cc) for cc in countries],
        showlegend=False, text=[f'{v:,}' for v in pfx], textposition='outside',
    ), row=1, col=2)
    ixp_total = [(data[cc].get(11, {}).get('ixp_memberships_domestic', 0) +
                  data[cc].get(11, {}).get('ixp_memberships_foreign', 0))
                 for cc in countries]
    scale_fig.add_trace(go.Bar(
        x=countries, y=ixp_total, marker_color=[country_color(cc) for cc in countries],
        showlegend=False, text=[str(v) for v in ixp_total], textposition='outside',
    ), row=2, col=1)
    host = [data[cc].get(14, {}).get('total_hosted_hostnames', 0) for cc in countries]
    scale_fig.add_trace(go.Bar(
        x=countries, y=host, marker_color=[country_color(cc) for cc in countries],
        showlegend=False, text=[f'{v:,}' for v in host], textposition='outside',
    ), row=2, col=2)
    scale_fig.update_layout(title='④ 规模指标对比 · Scale metrics (grouped bars)',
                            height=540)
    scale_fig.update_yaxes(type='log')

    # Panel 5: Sovereignty index bar
    sov_vals = [(data[cc].get(20) or {}).get('composite_sovereignty_index', 0) or 0
                for cc in countries]
    sov_fig = go.Figure(go.Bar(
        x=countries, y=sov_vals,
        marker_color=[country_color(cc) for cc in countries],
        text=[f'{v:.3f}' for v in sov_vals], textposition='outside',
    ))
    sov_fig.update_layout(
        title='⑤ 综合主权指数排行 · Sovereignty Index ranking (range 0-1)',
        yaxis=dict(range=[0, 1]), height=340)

    # Panel 6: KPI summary table
    table = go.Figure(go.Table(
        header=dict(values=['Country', '中文', 'AS #', 'Prefix #', 'RPKI%',
                            'Best PR', 'k-core', 'DNS Sov%', 'Sov Idx'],
                    fill_color=DARK_PANEL,
                    font=dict(color=TEXT_PRIMARY), align='left'),
        cells=dict(values=[
            countries,
            [zh(cc) for cc in countries],
            [f'{data[cc].get(1, {}).get("total_ases", 0):,}' for cc in countries],
            [f'{data[cc].get(4, {}).get("total_prefixes", 0):,}' for cc in countries],
            [f'{data[cc].get(4, {}).get("rpki_rate_pct", 0):.1f}' for cc in countries],
            [f'#{(data[cc].get(6, {}).get("best_ranks") or {}).get("pagerank", "?")}'
             for cc in countries],
            [data[cc].get(7, {}).get('deepest_k_in_country', '?') for cc in countries],
            [f'{data[cc].get(15, {}).get("domestic_pct", 0):.1f}' for cc in countries],
            [f'{(data[cc].get(20) or {}).get("composite_sovereignty_index", 0):.3f}'
             for cc in countries],
        ], fill_color=[['#0D1117', '#161B22'] * len(countries)],
           font=dict(color=TEXT_PRIMARY), align='left'),
    ))
    table.update_layout(title='⑥ 九国指标速览表 · Summary table', height=400)

    # Compose HTML
    narr = f'''
    <div class="sidebar-note">
    <b>跨国对比分析 · Cross-Country Comparison</b><br><br>
    快照 {snapshot} · 对比国家: {", ".join(bilingual(cc) for cc in countries)}<br>
    20 个维度指标跨 9 国归一化对比；主权指数由五个子分量（托管自给率、DNS 主权、RPKI、IXP 本地化、Hub 比率）加权平均。<br>
    <br>
    Snapshot {snapshot} · {len(countries)} countries compared across 20 metrics. Composite
    Sovereignty Index is the arithmetic mean of 5 sub-components.
    </div>
    '''

    figs = [hm, parcoords, radar, scale_fig, sov_fig, table]
    for f in figs:
        apply_plotly_theme(f)
    body = narr + plotly_inline_once(figs)
    save_consolidated_html(
        body, 'cross_country.html',
        title_zh='九国互联网分层跨国对比',
        title_en=f'Nine-Country Cross-Country Comparison · {snapshot}',
        subtitle=f'{len(countries)} countries × 20 metrics · {snapshot} snapshot',
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--snapshot', default='2026-04')
    args = ap.parse_args()
    build_cross_country(args.snapshot)


if __name__ == '__main__':
    main()
