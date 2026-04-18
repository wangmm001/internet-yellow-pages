"""Topic 5: AS business archetype (Carrier/Content/Eyeball/Tier-1).

Originally planned as AWS hyperscaler footprint per country, but
2024-10 IYP dump lacks the GeoPrefix label (Amazon crawler not run).
Pivoted to bgptools.as_names, which bins ASes into:
  · Eyeball (~8,332): ISPs serving residential/mobile users
  · Content (~1,173): CDNs, hyperscalers, large content hosts
  · Carrier (~557):   backbone/transit operators
  · T1 (~15):         Tier-1 transit

The mix per country is a lens on "is this country's internet consumer-
facing or export-heavy content?" — orthogonal to our existing
sovereignty and per-capita axes.
"""
import csv
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.china.common import (  # noqa: E402
    BANNER_CSS, COLORS, DARK_BG, DARK_BORDER, DARK_PANEL,
    TEXT_PRIMARY, TEXT_SECONDARY, apply_plotly_theme, country_color,
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

ARCHETYPE_COLOR = {
    'Eyeball': COLORS['cyan'],
    'Content': COLORS['orange'],
    'Carrier': COLORS['purple'],
    'T1': COLORS['red'],
}


def _read(name):
    p = CACHE / name
    if not p.exists():
        return []
    with open(p, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load():
    as_cc = {}
    for r in _read('as_country.csv'):
        try:
            as_cc[int(r['asn'])] = r['cc']
        except (ValueError, KeyError):
            pass

    # bgptools.as_names — one AS may have multiple archetypes
    asn_types = defaultdict(set)
    for r in _read('as_categorized.csv'):
        if r.get('source') != 'bgptools.as_names':
            continue
        try:
            asn = int(r['asn'])
        except (ValueError, KeyError):
            continue
        asn_types[asn].add(r.get('tag', ''))
    return as_cc, asn_types


def build():
    import plotly.graph_objects as go
    import plotly.subplots as sp

    as_cc, asn_types = load()

    # Per-country archetype counts
    per_cc = defaultdict(Counter)
    for asn, types in asn_types.items():
        cc = as_cc.get(asn)
        if not cc:
            continue
        for t in types:
            per_cc[cc][t] += 1

    total_asn_by_cc = defaultdict(int)
    for asn in asn_types:
        cc = as_cc.get(asn)
        if cc:
            total_asn_by_cc[cc] += 1

    # ---- Panel 1: 9-country archetype mix (stacked %) ----
    p1 = go.Figure()
    order = sorted(TARGET, key=lambda c: -total_asn_by_cc.get(c, 0))
    for arche in ('Eyeball', 'Content', 'Carrier', 'T1'):
        ys = []
        for cc in order:
            total = sum(per_cc[cc].values()) or 1
            ys.append(per_cc[cc].get(arche, 0) / total * 100)
        p1.add_trace(go.Bar(
            x=[f'{COUNTRY_NAME[c]} {c}' for c in order],
            y=ys, name=arche, marker_color=ARCHETYPE_COLOR[arche],
            text=[f'{per_cc[c].get(arche, 0)}' for c in order],
            textposition='inside',
        ))
    p1.update_layout(
        title='① 9 国 AS 原型占比 · Per-country archetype mix (Eyeball/Content/Carrier/T1)',
        barmode='stack', height=480,
        yaxis=dict(title='% of archetype-tagged ASes', range=[0, 100]),
        xaxis=dict(title='', tickangle=-20),
    )

    # ---- Panel 2: Content-AS density (content AS / total country AS) ----
    p2 = go.Figure()
    # Need per-country TOTAL AS count, not just tagged
    cc_total = Counter(as_cc.values())
    rows = []
    for cc in TARGET:
        content = per_cc[cc].get('Content', 0)
        total = cc_total.get(cc, 1)
        rows.append((cc, content, total, content / total * 100))
    rows.sort(key=lambda r: -r[3])
    p2.add_trace(go.Bar(
        x=[f'{COUNTRY_NAME[r[0]]} {r[0]}' for r in rows],
        y=[r[3] for r in rows],
        marker_color=[country_color(r[0]) for r in rows],
        text=[f'{r[1]}/{r[2]:,}<br>({r[3]:.2f}%)' for r in rows],
        textposition='outside',
    ))
    p2.update_layout(
        title='② Content AS 密度 · Content-AS share of country AS footprint',
        yaxis=dict(title='Content AS / total country AS (%)'),
        xaxis=dict(title='', tickangle=-20),
        height=480, showlegend=False,
    )

    # ---- Panel 3: Eyeball vs Content ratio (log-log) ----
    p3 = go.Figure()
    xs, ys, labs = [], [], []
    for cc in TARGET:
        eb = per_cc[cc].get('Eyeball', 0)
        ct = per_cc[cc].get('Content', 0)
        if eb > 0 and ct > 0:
            xs.append(eb)
            ys.append(ct)
            labs.append(cc)
    p3.add_trace(go.Scatter(
        x=xs, y=ys, mode='markers+text',
        text=[f'{c}' for c in labs], textposition='top center',
        marker=dict(
            size=[16 + (per_cc[c].get('Carrier', 0) + per_cc[c].get('T1', 0)) * 2
                  for c in labs],
            color=[country_color(c) for c in labs],
            line=dict(color='#fff', width=1.5),
        ),
        textfont=dict(color=TEXT_PRIMARY, size=14),
    ))
    p3.update_layout(
        title='③ Eyeball 数量 × Content 数量 · User-facing vs content-facing AS '
              '(size = Carrier+T1)',
        xaxis=dict(title='Eyeball AS count', type='log'),
        yaxis=dict(title='Content AS count', type='log'),
        height=520, showlegend=False,
    )

    # ---- Panel 4: global archetype breakdown ----
    p4 = go.Figure()
    global_arche = Counter()
    for asn, types in asn_types.items():
        for t in types:
            global_arche[t] += 1
    ordered = ['Eyeball', 'Content', 'Carrier', 'T1']
    p4.add_trace(go.Pie(
        labels=ordered,
        values=[global_arche.get(t, 0) for t in ordered],
        marker=dict(colors=[ARCHETYPE_COLOR[t] for t in ordered]),
        textinfo='label+percent+value', textposition='outside',
        hole=0.4,
    ))
    p4.update_layout(
        title=f'④ 全球 AS 原型分布 · Global archetype distribution '
              f'({sum(global_arche.values()):,} tagged ASes)',
        height=480, showlegend=False,
    )

    from plotly.io import to_html
    for fig in (p1, p2, p3, p4):
        apply_plotly_theme(fig)
    parts = []
    first = True
    for fig in (p1, p2, p3, p4):
        parts.append(to_html(fig, include_plotlyjs=('inline' if first else False),
                             full_html=False, default_height='500px'))
        first = False

    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>原计划：</b>AWS IP-range → 各国云依赖足迹。<i>2024-10 dump 缺 '
        f'<code>GeoPrefix</code> 标签（amazon crawler 未在此快照运行）</i>，'
        f'降级为 bgptools.as_names 的 <b>Carrier / Content / Eyeball / T1</b> '
        f'四分法：看每国 AS 是偏用户端还是偏内容端。'
        f'<br><b>Scope:</b> bgptools.as_names · 2024-10 snapshot · '
        f'{sum(len(t) for t in asn_types.values()):,} archetype tags across '
        f'{len(asn_types):,} unique ASes.'
        f'</p>'
    )
    intro += (
        f'<p style="margin:4px 16px 12px;padding:10px 14px;'
        f'border-left:3px solid #ff9f0a;background:rgba(255,159,10,0.08);'
        f'color:{TEXT_PRIMARY};font-size:13px;border-radius:4px">'
        f'⚠️ <b>AWS 维度待后续快照：</b>当 IYP 引入 amazon.aws_ip_ranges '
        f'crawler 的输出后，本页会扩展为"Archetype × 云依赖"双维度。'
        f'<br>AWS hyperscaler footprint blocked on upstream crawler '
        f'availability.</p>'
    )

    banner = (
        '<div class="step-banner">'
        '<h1>AS 业务原型 · AS Business Archetype</h1>'
        '<h2>Carrier × Content × Eyeball × T1 per-country mix · '
        'downgraded from AWS hyperscaler view</h2>'
        '</div>'
        '<div class="step-footer">topic 5 · 2024-10 snapshot · '
        'bgptools.as_names fallback</div>'
    )
    out_path = OUT / 'topic5_archetype.html'
    out_path.write_text(
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>AS 业务原型 · AS Business Archetype</title>'
        f'{BANNER_CSS}</head><body>'
        f'{banner}<div class="content">{intro}'
        f'{"".join(parts)}</div></body></html>',
        encoding='utf-8',
    )
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    print(f'global archetype: {dict(global_arche)}')


if __name__ == '__main__':
    build()
