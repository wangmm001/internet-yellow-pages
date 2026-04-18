"""Topic 9: RIPE Atlas probe geographic coverage (degraded).

Originally planned as "probe coverage + capability tags per country"
(IPv6, anchor, system-probe, etc). The 2024-10 Neo4j extract returned
45,578 probes across 217 countries but the `status` and tag properties
came back empty — the atlas_probes crawler schema on this dump doesn't
expose those via the query we wrote. Falls back to probe-density
inequality map.
"""
import csv
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.china.common import (  # noqa: E402
    BANNER_CSS, COLORS, DARK_BG, DARK_BORDER, DARK_PANEL,
    TEXT_PRIMARY, TEXT_SECONDARY, apply_plotly_theme, country_color,
    ISO2_TO_ISO3,
)

REPO = Path(__file__).resolve().parent.parent.parent
CACHE = REPO / 'data_cache' / 'new_angles'
OUT = REPO / 'analysis' / 'new_angles' / 'html'
OUT.mkdir(parents=True, exist_ok=True)

TARGET = ['US', 'CN', 'JP', 'IN', 'DE', 'GB', 'FR', 'NL', 'RU']
COUNTRY_NAME = {
    'US': '美国', 'CN': '中国', 'JP': '日本', 'IN': '印度', 'DE': '德国',
    'GB': '英国', 'FR': '法国', 'NL': '荷兰', 'RU': '俄罗斯',
}

# Static 2024 populations for per-capita calculations (same as Topic 1).
POP_2024 = {
    'US': 336_810_000, 'CN': 1_410_710_000, 'JP': 123_750_000,
    'IN': 1_428_630_000, 'DE': 84_480_000, 'GB': 68_350_000,
    'FR': 68_170_000, 'NL': 17_880_000, 'RU': 143_830_000,
    'IT': 58_760_000, 'CA': 40_440_000, 'CH': 8_850_000,
    'SE': 10_540_000, 'AU': 26_470_000, 'BR': 215_310_000,
}


def _read(name):
    p = CACHE / name
    if not p.exists():
        return []
    with open(p, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load():
    cc_count = Counter()
    no_cc = 0
    for r in _read('atlas_probes.csv'):
        cc = r.get('cc') or ''
        if cc:
            cc_count[cc] += 1
        else:
            no_cc += 1
    return cc_count, no_cc


def build():
    import plotly.graph_objects as go

    cc_count, no_cc = load()
    total = sum(cc_count.values())
    rows = sorted(
        ({'cc': cc, 'n': n,
          'pop': POP_2024.get(cc),
          'per_million': n / (POP_2024[cc] / 1e6) if cc in POP_2024 else None}
         for cc, n in cc_count.items()),
        key=lambda r: -r['n']
    )
    print(f'total probes: {total}  · countries: {len(rows)}  · no_cc: {no_cc}')

    # ---- Panel 1: global choropleth ----
    p1 = go.Figure(data=go.Choropleth(
        locations=[ISO2_TO_ISO3.get(r['cc'], r['cc']) for r in rows],
        z=[r['n'] for r in rows],
        text=[f'{r["cc"]}<br>{r["n"]:,} probes' for r in rows],
        hoverinfo='text',
        colorscale=[[0, '#2c1e2a'], [0.3, COLORS['purple']],
                    [0.7, COLORS['orange']], [1, COLORS['yellow']]],
        colorbar=dict(title='# probes'),
    ))
    p1.update_layout(
        title=f'① 全球 Atlas 探针覆盖（{total:,} probes in {len(rows)} 国）· '
              f'Global probe distribution',
        geo=dict(showframe=False, projection_type='natural earth',
                 bgcolor=DARK_BG, coastlinecolor=DARK_BORDER,
                 landcolor=DARK_PANEL, lakecolor=DARK_BG),
        paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG, height=560,
    )

    # ---- Panel 2: top-20 countries by absolute count ----
    p2 = go.Figure()
    top20 = rows[:20]
    p2.add_trace(go.Bar(
        y=[f'{r["cc"]}' for r in top20][::-1],
        x=[r['n'] for r in top20][::-1],
        orientation='h',
        marker_color=[country_color(r['cc']) if r['cc'] in TARGET
                      else COLORS['purple'] for r in top20][::-1],
        text=[f'{r["n"]:,}' for r in top20][::-1],
        textposition='outside',
    ))
    p2.update_layout(
        title='② Top-20 国家绝对探针数 · Absolute probe count',
        xaxis=dict(title='# probes'),
        height=560, margin=dict(l=80), showlegend=False,
    )

    # ---- Panel 3: 9 target countries — per capita + absolute ----
    p3 = go.Figure()
    tgt_rows = sorted([
        {'cc': cc, 'n': cc_count.get(cc, 0),
         'pop': POP_2024.get(cc),
         'per_million': cc_count.get(cc, 0) / (POP_2024[cc] / 1e6)
         if cc in POP_2024 else None}
        for cc in TARGET
    ], key=lambda r: -(r['per_million'] or 0))
    p3.add_trace(go.Bar(
        x=[f'{COUNTRY_NAME[r["cc"]]} {r["cc"]}' for r in tgt_rows],
        y=[r['per_million'] for r in tgt_rows],
        marker_color=[country_color(r['cc']) for r in tgt_rows],
        text=[f'{r["per_million"]:.2f}<br>({r["n"]:,} probes)'
              if r['per_million'] else '—' for r in tgt_rows],
        textposition='outside', name='probes per million people',
    ))
    p3.update_layout(
        title='③ 9 国探针密度 · Probes per million residents '
              '(bar height = probes/M · label = absolute)',
        yaxis=dict(title='probes / million people'),
        xaxis=dict(title='', tickangle=-20),
        height=480, showlegend=False,
    )

    # ---- Panel 4: cumulative share (Gini / Pareto) ----
    import math
    p4 = go.Figure()
    xs = list(range(1, len(rows) + 1))
    counts = [r['n'] for r in rows]
    cum = []
    running = 0
    for n in counts:
        running += n
        cum.append(running / total * 100)
    p4.add_trace(go.Scatter(
        x=xs, y=cum, mode='lines',
        line=dict(color=COLORS['cyan'], width=2.5),
        fill='tozeroy', fillcolor='rgba(0,208,201,0.08)',
    ))
    # Mark 50% and 80% horizontal
    for pct, col in [(50, COLORS['orange']), (80, COLORS['red'])]:
        n_needed = next((i + 1 for i, v in enumerate(cum) if v >= pct), None)
        if n_needed:
            p4.add_shape(type='line', x0=0, x1=n_needed, y0=pct, y1=pct,
                         line=dict(color=col, dash='dash', width=1.5))
            p4.add_annotation(x=n_needed, y=pct, showarrow=False,
                              text=f'{pct}% 集中于前 {n_needed} 国',
                              xanchor='left', font=dict(color=col, size=12))
    p4.update_layout(
        title='④ 累积占比曲线 · Cumulative share across 217 countries',
        xaxis=dict(title='rank (countries sorted by probe count)'),
        yaxis=dict(title='cumulative % of global probes', range=[0, 101]),
        height=440, showlegend=False,
    )

    from plotly.io import to_html
    for fig in (p1, p2, p3, p4):
        apply_plotly_theme(fig)
    parts = []
    first = True
    for fig in (p1, p2, p3, p4):
        parts.append(to_html(fig, include_plotlyjs=('inline' if first else False),
                             full_html=False, default_height='520px'))
        first = False

    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>数据：</b>RIPE Atlas 是全球最大的主动 Internet 测量网络。'
        f'本页看 <b>{total:,}</b> 个探针在 {len(rows)} 国的分布——'
        f'测量能力的地理不平等是路由/DNS/拥塞研究的隐性偏差来源。'
        f'<br><b>Scope:</b> ripe.atlas_probes · 2024-10 snapshot · '
        f'{no_cc:,} probes with unknown country (excluded).'
        f'</p>'
        f'<p style="margin:4px 16px 12px;padding:10px 14px;'
        f'border-left:3px solid #ff9f0a;background:rgba(255,159,10,0.08);'
        f'color:{TEXT_PRIMARY};font-size:13px;border-radius:4px">'
        f'⚠️ <b>能力标签缺失：</b>原计划用 AtlasProbe 节点的 <code>status</code> '
        f'和 ASSIGNED-Tag 关系拆分 IPv6/anchor/system 能力，'
        f'但 2024-10 dump 中两者均为空。降级为纯地理分布视图。</p>'
    )

    banner = (
        '<div class="step-banner">'
        '<h1>Atlas 探针全球覆盖 · RIPE Atlas Global Coverage</h1>'
        '<h2>45,578 probes across 217 countries · '
        'measurement-infrastructure inequality</h2>'
        '</div>'
        '<div class="step-footer">topic 9 · 2024-10 snapshot · '
        'RIPE Atlas probes</div>'
    )
    out_path = OUT / 'topic9_atlas.html'
    out_path.write_text(
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>Atlas 探针全球覆盖 · Atlas Probes</title>'
        f'{BANNER_CSS}</head><body>'
        f'{banner}<div class="content">{intro}'
        f'{"".join(parts)}</div></body></html>',
        encoding='utf-8',
    )
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    print(f'top-5 by count: {[(r["cc"], r["n"]) for r in rows[:5]]}')


if __name__ == '__main__':
    build()
