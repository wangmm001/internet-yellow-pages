#!/usr/bin/env python3
"""Regenerate step16_cname_chains.html as a Plotly Sankey (cloud-provider flow).

Reads analysis/china/data/cn_cname_chains.csv, aggregates into
TLD → cloud-family flows, and writes a self-contained Plotly Sankey
HTML to analysis/china/html/step16_cname_chains.html.  Idempotent.

Requires plotly (see .venv).  Run from repo root:

    .venv/bin/python3 analysis/web/patch_step16_html.py
"""
import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from analysis.china.common import (  # noqa: E402
    COLORS, DARK_BG, DARK_PANEL, TEXT_PRIMARY, TEXT_SECONDARY, country_color,
)
from analysis.china.step16_cname_chains import classify_target

try:
    import plotly.graph_objects as go
except ImportError:
    sys.exit('plotly not installed; activate venv first (source .venv/bin/activate)')

HTML = Path('analysis/china/html/step16_cname_chains.html')
CSV = Path('analysis/china/data/cn_cname_chains.csv')

FAMILY_COLOR = {
    'Aliyun': COLORS['orange'], 'Aliyun CDN': COLORS['orange'],
    'Tencent': COLORS['blue'], 'Tencent Cloud': COLORS['blue'],
    'Tencent DNSPod': COLORS['blue'], 'Tencent DNS': COLORS['blue'],
    'Huawei': COLORS['red'], 'Huawei Cloud': COLORS['red'], 'Huawei CDN': COLORS['red'],
    'Baidu': COLORS['purple'],
    'NetEase': COLORS['pink'],
    'JD': COLORS['amber'], 'JD Cloud': COLORS['amber'],
    'ChinaCache': COLORS['green'], 'ChinaNetCenter': COLORS['green'],
    'Wangsu': COLORS['cyan'], 'Wangsu CDN': COLORS['cyan'],
    'Other CN': COLORS['teal'],
}

TOP_TLDS = 12


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f'rgba({r}, {g}, {b}, {alpha})'


def main():
    if not CSV.exists():
        sys.exit(f'missing {CSV}')

    fam_target_count = Counter()
    tld_edge_count_raw = Counter()
    pairs_raw = Counter()
    total_rows = 0
    with CSV.open() as f:
        for row in csv.DictReader(f):
            src = row['src']
            dst = row['dst']
            fam = classify_target(dst) or 'Other CN'
            tld = src.rsplit('.', 1)[-1].lower() if '.' in src else 'none'
            fam_target_count[fam] += 1
            tld_edge_count_raw[tld] += 1
            pairs_raw[(tld, fam)] += 1
            total_rows += 1

    main_tlds = {t for t, _ in tld_edge_count_raw.most_common(TOP_TLDS)}
    pairs = Counter()
    tld_edges = Counter()
    for (t, f), c in pairs_raw.items():
        bucket = t if t in main_tlds else 'other'
        pairs[(bucket, f)] += c
        tld_edges[bucket] += c

    # Order nodes: TLDs first (sorted by volume desc), then families (sorted by target count desc)
    left_tlds = [t for t, _ in tld_edges.most_common()]
    right_fams = [f for f, _ in fam_target_count.most_common()]

    nodes_labels = []
    nodes_colors = []
    node_index = {}

    for tld in left_tlds:
        label_text = f'.{tld}' if tld not in ('other', 'none') else tld
        cc = tld.upper() if len(tld) == 2 else ''
        color = country_color(cc) if cc else COLORS['cyan']
        node_index[('tld', tld)] = len(nodes_labels)
        nodes_labels.append(f'{label_text} ({tld_edges[tld]})')
        nodes_colors.append(color)

    for fam in right_fams:
        color = FAMILY_COLOR.get(fam, COLORS['teal'])
        node_index[('fam', fam)] = len(nodes_labels)
        nodes_labels.append(f'{fam} ({fam_target_count[fam]})')
        nodes_colors.append(color)

    # Edges
    link_src = []
    link_tgt = []
    link_val = []
    link_colors = []
    for (tld, fam), count in pairs.items():
        link_src.append(node_index[('tld', tld)])
        link_tgt.append(node_index[('fam', fam)])
        link_val.append(count)
        # link color from source TLD's color with alpha
        tld_color = nodes_colors[node_index[('tld', tld)]]
        link_colors.append(_hex_to_rgba(tld_color, 0.45))

    fig = go.Figure(go.Sankey(
        arrangement='snap',
        node=dict(
            pad=18,
            thickness=18,
            line=dict(color='#30363D', width=0.5),
            label=nodes_labels,
            color=nodes_colors,
            hovertemplate='<b>%{label}</b><br>总量 · Total: %{value}<extra></extra>',
        ),
        link=dict(
            source=link_src,
            target=link_tgt,
            value=link_val,
            color=link_colors,
            hovertemplate='<b>%{source.label}</b> → <b>%{target.label}</b><br>边数 · Edges: %{value}<extra></extra>',
        ),
    ))

    fig.update_layout(
        title=dict(
            text=(
                '<b>跨境 CNAME 别名链 · 按云服务商聚类</b><br>'
                f'<span style="font-size:13px;color:#8B949E">CNAME Chains Crossing China · '
                f'clustered by cloud provider · {total_rows:,} edges · '
                f'{len(left_tlds)} TLDs × {len(right_fams)} families</span>'
            ),
            x=0.5, xanchor='center', font=dict(size=18, color=TEXT_PRIMARY),
        ),
        paper_bgcolor=DARK_BG,
        plot_bgcolor=DARK_PANEL,
        font=dict(color=TEXT_PRIMARY, size=13),
        margin=dict(l=20, r=20, t=100, b=40),
        height=820,
    )

    fig.write_html(
        HTML,
        include_plotlyjs='inline',
        full_html=True,
        config={'displayModeBar': False, 'responsive': True},
    )

    print(f'wrote Sankey HTML to {HTML}')
    print(f'  {len(nodes_labels)} nodes ({len(left_tlds)} TLDs + {len(right_fams)} families)')
    print(f'  {len(link_src)} flows · {total_rows:,} total edges')


if __name__ == '__main__':
    main()
