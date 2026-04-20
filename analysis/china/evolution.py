"""CN time-series evolution across 6 quarterly snapshots.

Reuses per-snapshot CN metrics already extracted into
analysis/countries/data/{snap}/CN/step*_metrics.json. No Neo4j calls.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from pathlib import Path  # noqa: E402

from analysis.china.common import (  # noqa: E402
    BANNER_CSS, COLORS, DARK_BG, DARK_BORDER, DARK_PANEL, TEXT_PRIMARY,
    TEXT_SECONDARY, apply_plotly_theme, save_placeholder_html as _china_placeholder,
    warning_block,
)
from analysis.countries.common import (  # noqa: E402
    list_snapshots, read_country_metrics,
)

CHINA_HTML_DIR = Path(__file__).resolve().parent / 'html'


def _plotly_inline(figs):
    """Local plotly_inline_once equivalent that writes to this module."""
    from plotly.io import to_html
    out = []
    first = True
    for fig in figs:
        apply_plotly_theme(fig)
        out.append(to_html(
            fig,
            include_plotlyjs=('inline' if first else False),
            full_html=False,
            default_height='560px',
        ))
        first = False
    return '\n'.join(out)


def _banner(title_zh, title_en, subtitle=''):
    sub = f'<div class="step-footer">{subtitle}</div>' if subtitle else ''
    return (
        '<div class="step-banner">'
        f'<h1>{title_zh}</h1>'
        f'<h2>{title_en}</h2>'
        '</div>' + sub
    )


def _write_html(body_html, name, title_zh, title_en, subtitle=''):
    CHINA_HTML_DIR.mkdir(parents=True, exist_ok=True)
    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        f'<title>{title_zh}</title>'
        f'{BANNER_CSS}</head><body>'
        f'{_banner(title_zh, title_en, subtitle)}'
        f'<div class="content">{body_html}</div>'
        '</body></html>'
    )
    path = CHINA_HTML_DIR / name
    path.write_text(html, encoding='utf-8')
    print(f'[html] wrote {path} ({path.stat().st_size // 1024} KB)')
    return path

CC = 'CN'

METRICS_TRACKED = [
    ('AS 数',       1, 'total_ases'),
    ('IPv4 前缀',   4, 'v4_prefixes'),
    ('IPv6 前缀',   4, 'v6_prefixes'),
    ('总前缀',      4, 'total_prefixes'),
    ('RPKI %',      4, 'rpki_rate_pct'),
    ('Anycast',     4, 'anycast_prefixes'),
    ('Best PR',     6, ('best_ranks', 'pagerank')),
    ('Best deg',    6, ('best_ranks', 'degree')),
    ('Max k-core',  7, 'deepest_k_in_country'),
    ('出向依赖',    8, 'outbound_edges'),
    ('入向依赖',    9, 'inbound_edges'),
    ('IXP 成员',   11, 'ixp_memberships_domestic'),
    ('托管主机',   14, 'total_hosted_hostnames'),
    ('DNS 主权 %', 15, 'domestic_pct'),
    ('审查 AS',    18, 'censoring_ases'),
    ('主权指数',   20, 'composite_sovereignty_index'),
]

SOV_COMPONENTS = [
    ('hosting_sovereignty', '托管 Hosting'),
    ('dns_sovereignty',     'DNS'),
    ('rpki_adoption',       'RPKI'),
    ('ixp_domesticization', 'IXP 本地化'),
    ('hub_ratio',           'Hub ratio'),
]

RANK_METRICS = [
    ('AS count',  3, ('as_count',       'rank')),
    ('Prefix',    3, ('prefix_count',   'rank')),
    ('IXP',       3, ('ixp_count',      'rank')),
    ('Facility',  3, ('facility_count', 'rank')),
    ('Best PR',   6, ('best_ranks',     'pagerank')),
    ('k-core',    7, 'cn_deepest_coreness'),
]


def _get(step_map, step, key):
    s = (step_map or {}).get(step, {}) or {}
    if isinstance(key, tuple):
        cur = s
        for k in key:
            cur = (cur or {}).get(k, None)
            if cur is None:
                return None
        return cur
    return s.get(key, None)


def load_cn_series(snapshots):
    out = {}
    for s in snapshots:
        per_step = {}
        for n in range(1, 21):
            m = read_country_metrics(s, CC, n)
            per_step[n] = (m or {}).get('metrics', {}) or {}
        out[s] = per_step
    return out


def build(snapshots=None):
    import plotly.graph_objects as go
    import plotly.subplots as sp

    all_snaps = list_snapshots()
    snapshots = snapshots or all_snaps
    snapshots = [s for s in snapshots if s in all_snaps]
    snapshots = [s for s in snapshots
                 if (read_country_metrics(s, CC, 1) or {}).get('metrics')]
    if len(snapshots) < 2:
        _write_html(
            f'<p>需要 ≥ 2 个快照，当前只有 {snapshots}</p>'
            f'<p>Need ≥ 2 snapshots, found {snapshots}</p>',
            'evolution.html',
            '中国时序演化', 'China Time-Series Evolution',
        )
        return

    data = load_cn_series(snapshots)
    x = snapshots
    red = COLORS['red']
    cyan = COLORS['cyan']

    # ---- Panel 1: 16-indicator sparkline grid 4×4 ----
    panel1 = sp.make_subplots(
        rows=4, cols=4,
        subplot_titles=[m[0] for m in METRICS_TRACKED],
        vertical_spacing=0.08, horizontal_spacing=0.05,
    )
    for i, (label, step, key) in enumerate(METRICS_TRACKED):
        r, c = i // 4 + 1, i % 4 + 1
        ys = [_get(data[s], step, key) for s in snapshots]
        panel1.add_trace(go.Scatter(
            x=x, y=ys, mode='lines+markers',
            line=dict(color=red, width=1.7),
            marker=dict(size=5), showlegend=False,
        ), row=r, col=c)
    panel1.update_layout(
        title='① CN 16 项关键指标趋势 · Per-metric trajectory',
        height=780, hovermode='x unified',
    )

    # ---- Panel 2: Sovereignty Index + 5 components ----
    panel2 = go.Figure()
    main = [_get(data[s], 20, 'composite_sovereignty_index') for s in snapshots]
    panel2.add_trace(go.Scatter(
        x=x, y=main, mode='lines+markers',
        name='Sovereignty Index',
        line=dict(color=red, width=3),
        marker=dict(size=9),
    ))
    comp_colors = [cyan, COLORS['orange'], COLORS['purple'],
                   COLORS['green'], COLORS['yellow']]
    for (ckey, clabel), color in zip(SOV_COMPONENTS, comp_colors):
        ys = [(data[s].get(20, {}).get('components') or {}).get(ckey)
              for s in snapshots]
        panel2.add_trace(go.Scatter(
            x=x, y=ys, mode='lines+markers',
            name=clabel,
            line=dict(color=color, width=1.5, dash='dot'),
            marker=dict(size=6),
        ))
    panel2.update_layout(
        title='② 主权指数 + 5 分项 · Composite vs components',
        yaxis=dict(title='0 – 1', range=[0, 1]),
        height=500, hovermode='x unified',
    )

    # ---- Panel 3: Global rank trajectory (y reversed, rank #1 top) ----
    panel3 = go.Figure()
    rank_colors = [COLORS['red'], COLORS['orange'], COLORS['purple'],
                   COLORS['cyan'], COLORS['green'], COLORS['yellow']]
    for (label, step, key), color in zip(RANK_METRICS, rank_colors):
        ys = [_get(data[s], step, key) for s in snapshots]
        panel3.add_trace(go.Scatter(
            x=x, y=ys, mode='lines+markers',
            name=label,
            line=dict(color=color, width=2),
            marker=dict(size=7),
        ))
    panel3.update_layout(
        title='③ CN 全球排名轨迹 · Global rank trajectory (lower=better)',
        yaxis=dict(title='rank', autorange='reversed'),
        height=500, hovermode='x unified',
    )

    # ---- Panel 4: Outbound dependency composition (stacked bar) ----
    def top5_shift(step, key):
        cat = {}
        for s in snapshots:
            d = (data[s].get(step, {}) or {}).get(key, {}) or {}
            for k, v in d.items():
                cat.setdefault(k, {})[s] = v
        totals = [(k, sum(vs.values())) for k, vs in cat.items()]
        top = [k for k, _ in sorted(totals, key=lambda t: -t[1])[:5]]
        return top, {k: cat[k] for k in top}

    out_top, out_data = top5_shift(8, 'top_destination_countries')
    panel4 = go.Figure()
    out_colors = [COLORS['cyan'], COLORS['blue'], COLORS['purple'],
                  COLORS['orange'], COLORS['red']]
    for cc, color in zip(out_top, out_colors):
        ys = [out_data[cc].get(s, 0) for s in snapshots]
        panel4.add_trace(go.Bar(
            x=x, y=ys, name=cc, marker_color=color,
        ))
    panel4.update_layout(
        title='④ CN 出向依赖 Top-5 国家组成 · Outbound dependency mix',
        barmode='stack',
        yaxis=dict(title='edges'),
        height=440, hovermode='x unified',
    )

    # ---- Panel 5: Inbound dependency composition ----
    in_top, in_data = top5_shift(9, 'top_source_countries')
    panel5 = go.Figure()
    in_colors = [COLORS['yellow'], COLORS['green'], COLORS['cyan'],
                 COLORS['purple'], COLORS['red']]
    for cc, color in zip(in_top, in_colors):
        ys = [in_data[cc].get(s, 0) for s in snapshots]
        panel5.add_trace(go.Bar(
            x=x, y=ys, name=cc, marker_color=color,
        ))
    panel5.update_layout(
        title='⑤ CN 入向依赖 Top-5 国家组成 · Inbound dependency mix',
        barmode='stack',
        yaxis=dict(title='edges'),
        height=440, hovermode='x unified',
    )

    # ---- Narrative ----
    start_sov = main[0] if main[0] is not None else float('nan')
    end_sov = main[-1] if main[-1] is not None else float('nan')
    delta = ((end_sov - start_sov) if main[0] is not None
             and main[-1] is not None else 0.0)
    narrative = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'快照区间：<b>{snapshots[0]} → {snapshots[-1]}</b>（{len(snapshots)} 季度）。'
        f'综合主权指数：<b>{start_sov:.3f} → {end_sov:.3f}</b>（Δ {delta:+.3f}）。'
        f'本页聚焦 <b>CN</b> 单一国家跨 6 快照的深度视角——由 '
        f'analysis/countries/data/ 缓存直接装配，无需新 Neo4j 查询。'
        f'<br>Six quarterly snapshots focused on <b>CN</b>, rebuilt from the '
        f'existing per-country cache.'
        f'</p>'
    )

    no_prefix, no_rpki = [], []
    for s in snapshots:
        step4 = (data.get(s, {}).get(4) or {})
        tot = step4.get('total_prefixes')
        rpki = step4.get('rpki_rate_pct')
        if tot in (None, 0):
            no_prefix.append(s)
        elif rpki in (None, 0):
            no_rpki.append(s)
    if no_prefix or no_rpki:
        bits = []
        if no_prefix:
            bits.append(
                f'快照 <code>{", ".join(no_prefix)}</code> 缺 '
                f'<code>:BGPPrefix</code>/<code>:Prefix</code> 节点 → '
                f'① IPv4/IPv6/总前缀 · RPKI % 全部读 0')
        if no_rpki:
            bits.append(
                f'快照 <code>{", ".join(no_rpki)}</code> 有前缀但缺 '
                f'<code>(:Prefix)-[:CATEGORIZED]->(Tag "RPKI Valid")</code> → '
                f'① RPKI % 单独读 0（IPv4/IPv6/总前缀正常）')
        narrative += warning_block(
            '；'.join(bits) + '。依赖边面板 ④⑤ 不受影响。'
            '<br>Prefix/RPKI gaps: the affected panels show 0 at those '
            'points — not real dips. Dependency panels are unaffected.',
            title='数据空洞 · Snapshot data gaps',
        )

    body = narrative + _plotly_inline(
        [panel1, panel2, panel3, panel4, panel5])
    _write_html(
        body,
        'evolution.html',
        f'中国时序演化 · {snapshots[0]} → {snapshots[-1]}（{len(snapshots)} 季度）',
        f'China Time-Series · {snapshots[0]} → {snapshots[-1]} '
        f'({len(snapshots)} quarters)',
        subtitle='CN-only deep view · reuses countries/ per-snapshot JSONs',
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--snapshots', nargs='+', default=None)
    args = ap.parse_args()
    build(snapshots=args.snapshots)


if __name__ == '__main__':
    main()
