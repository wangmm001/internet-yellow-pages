"""Topic 13: Multinational organizations' AS footprint.

Cross-joins as_organization.csv × as_country.csv to find orgs whose ASes
are distributed across multiple countries. Complementary to Topic 12
(global dependency) — this is "who owns the wires in multiple countries"
rather than "who do the wires depend on".

Pure offline; no Neo4j.
"""
import csv
import os
import sys
from collections import defaultdict, Counter
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.china.common import (  # noqa: E402
    BANNER_CSS, COLORS, DARK_BG, DARK_BORDER, DARK_PANEL,
    TEXT_PRIMARY, TEXT_SECONDARY, apply_plotly_theme, country_color,
)

REPO = Path(__file__).resolve().parent.parent.parent
CACHE = REPO / 'data_cache' / 'new_angles'
COMPLEX = REPO / 'data_cache' / 'complex_network'
OUT = REPO / 'analysis' / 'new_angles' / 'html'
OUT.mkdir(parents=True, exist_ok=True)

TARGET = ['US', 'CN', 'JP', 'IN', 'DE', 'GB', 'FR', 'NL', 'RU']
COUNTRY_NAME = {
    'US': '美国', 'CN': '中国', 'JP': '日本', 'IN': '印度', 'DE': '德国',
    'GB': '英国', 'FR': '法国', 'NL': '荷兰', 'RU': '俄罗斯',
}


def _read(p):
    return list(csv.DictReader(open(p, encoding='utf-8'))) \
        if p.exists() else []


def load():
    as_cc = {int(r['asn']): r['cc'] for r in _read(CACHE / 'as_country.csv')
             if r.get('asn', '').isdigit()}
    org_asns = defaultdict(list)
    for r in _read(COMPLEX / 'as_organization.csv'):
        try:
            org_asns[r['org_name']].append(int(r['asn']))
        except (ValueError, KeyError):
            pass

    # Multinational = orgs with ASes in >1 country
    multi = []
    for org, asns in org_asns.items():
        ccs = Counter(as_cc.get(a) for a in asns if as_cc.get(a))
        if len(ccs) > 1:
            multi.append({'org': org, 'n_cc': len(ccs), 'n_as': len(asns),
                          'countries': ccs})
    multi.sort(key=lambda r: (-r['n_cc'], -r['n_as']))
    return multi, len(org_asns)


def build():
    import plotly.graph_objects as go
    multi, total_orgs = load()
    print(f'total orgs: {total_orgs:,} · multinational: {len(multi):,}')

    # ---- Panel 1: Top-20 multinational orgs by country span ----
    top20 = multi[:20]
    p1 = go.Figure()
    p1.add_trace(go.Bar(
        orientation='h',
        y=[f'{m["org"][:48]}' for m in top20][::-1],
        x=[m['n_cc'] for m in top20][::-1],
        marker_color=COLORS['orange'],
        text=[f'{m["n_cc"]} 国 · {m["n_as"]} AS' for m in top20][::-1],
        textposition='outside',
    ))
    p1.update_layout(
        title='① Top-20 跨国组织 · Organizations spanning the most countries',
        xaxis=dict(title='# countries'), height=620,
        margin=dict(l=320), showlegend=False,
    )

    # ---- Panel 2: Per-target-country inbound / outbound multinationals ----
    # inbound = orgs HQ'd elsewhere that have AS in target country
    # outbound = orgs HQ'd in target country that span others
    # Approximation: "headquarters" = country with most AS in org
    inbound = Counter(); outbound = Counter()
    for m in multi:
        hq_cc = m['countries'].most_common(1)[0][0]
        for cc in m['countries']:
            if cc and cc != hq_cc:
                inbound[cc] += 1
        if hq_cc:
            outbound[hq_cc] += m['n_cc'] - 1
    rows = [{'cc': cc, 'inbound': inbound[cc], 'outbound': outbound[cc]}
            for cc in TARGET]
    rows.sort(key=lambda r: -(r['inbound'] + r['outbound']))
    p2 = go.Figure()
    p2.add_trace(go.Bar(
        x=[f'{COUNTRY_NAME[r["cc"]]} {r["cc"]}' for r in rows],
        y=[r['inbound'] for r in rows], name='inbound (foreign orgs here)',
        marker_color=COLORS['cyan'],
        text=[str(r['inbound']) for r in rows], textposition='inside',
    ))
    p2.add_trace(go.Bar(
        x=[f'{COUNTRY_NAME[r["cc"]]} {r["cc"]}' for r in rows],
        y=[r['outbound'] for r in rows], name='outbound (domestic orgs abroad)',
        marker_color=COLORS['orange'],
        text=[str(r['outbound']) for r in rows], textposition='inside',
    ))
    p2.update_layout(
        title='② 9 国跨国组织出入向 · Inbound foreign vs outbound domestic',
        barmode='group', yaxis=dict(title='# of inbound/outbound links'),
        xaxis=dict(title='', tickangle=-20),
        height=480, legend=dict(orientation='h', y=-0.18),
    )

    # ---- Panel 3: chord-like flow between target pairs (simplified as bar) ----
    pair_count = Counter()
    for m in multi:
        tgt_ccs = [c for c in m['countries'] if c in TARGET]
        if len(tgt_ccs) < 2:
            continue
        for i in range(len(tgt_ccs)):
            for j in range(i + 1, len(tgt_ccs)):
                a, b = sorted([tgt_ccs[i], tgt_ccs[j]])
                pair_count[(a, b)] += 1
    top_pairs = pair_count.most_common(15)
    p3 = go.Figure()
    if top_pairs:
        p3.add_trace(go.Bar(
            orientation='h',
            y=[f'{a} ↔ {b}' for (a, b), _ in top_pairs][::-1],
            x=[n for _, n in top_pairs][::-1],
            marker_color=COLORS['purple'],
            text=[str(n) for _, n in top_pairs][::-1],
            textposition='outside',
        ))
    p3.update_layout(
        title='③ 跨 9 国常见组合 · Target-9 country pairs most often '
              'co-owned by same organization',
        xaxis=dict(title='# of orgs spanning both'),
        height=540, margin=dict(l=120), showlegend=False,
    )

    # ---- Panel 4: Span distribution (histogram) ----
    p4 = go.Figure()
    p4.add_trace(go.Histogram(
        x=[m['n_cc'] for m in multi], nbinsx=18,
        marker_color=COLORS['green'],
    ))
    p4.update_layout(
        title='④ 跨国组织覆盖广度分布 · Country-span histogram',
        xaxis=dict(title='# countries per multinational org'),
        yaxis=dict(title='# orgs'),
        height=420, showlegend=False,
    )

    from plotly.io import to_html
    for fig in (p1, p2, p3, p4):
        apply_plotly_theme(fig)
    parts = []; first = True
    for fig in (p1, p2, p3, p4):
        parts.append(to_html(
            fig, include_plotlyjs=('inline' if first else False),
            full_html=False, default_height='520px'))
        first = False

    top3 = multi[:3]
    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>数据：</b>交叉 caida.as2org 的 <code>as_organization.csv</code> '
        f'与 <code>as_country.csv</code>，找出同一组织名下 AS 跨多国的 '
        f'<b>{len(multi):,}</b> 个跨国组织（{total_orgs:,} 个组织中的 '
        f'{len(multi)/total_orgs*100:.1f}%）。'
        f'<br><b>Top-3:</b> '
        + ' · '.join(f'{m["org"][:35]}（{m["n_cc"]} 国，{m["n_as"]} AS）'
                     for m in top3) +
        '</p>'
    )

    banner = (
        '<div class="step-banner">'
        '<h1>跨国组织 AS 足迹 · Multinational Org Footprint</h1>'
        '<h2>Orgs whose ASes span multiple countries · CAIDA as2org derivative</h2>'
        '</div>'
        '<div class="step-footer">topic 13 · offline from cache · '
        '814 multinational orgs</div>'
    )
    out_path = OUT / 'topic13_multinational.html'
    out_path.write_text(
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>跨国组织 AS 足迹 · Multinational Footprint</title>'
        f'{BANNER_CSS}</head><body>'
        f'{banner}<div class="content">{intro}'
        f'{"".join(parts)}</div></body></html>',
        encoding='utf-8',
    )
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')


if __name__ == '__main__':
    build()
