"""Topic 6: bgptools.tags — AS behavioral labels per country.

18 tag vocabulary across 15,350 rows covers behavior (ToR/VPN/Anycast/
DDoS Mitigation), role (Home ISP/Academic/Government/Business Broadband)
and risk (Internet Critical Infra). These are complementary to
Stanford ASDB (industry) and bgptools.as_names (archetype).

4 panels:
  ① 9-country matrix heatmap over top-10 tags
  ② Security/privacy-relevant tags per country (stacked)
  ③ Internet Critical Infra concentration
  ④ Top-20 tag vocabulary (global)
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

SECURITY_TAGS = ('ToR Services', 'VPN Host', 'Anycast',
                 'DDoS Mitigation', 'Content Delivery Network',
                 'Internet Critical Infra')
SEC_COLOR = {
    'ToR Services': COLORS['purple'],
    'VPN Host': COLORS['pink'],
    'Anycast': COLORS['green'],
    'DDoS Mitigation': COLORS['red'],
    'Content Delivery Network': COLORS['orange'],
    'Internet Critical Infra': COLORS['amber'],
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

    tags_per_cc = defaultdict(Counter)  # cc -> tag -> count
    global_tags = Counter()
    asns_by_tag = defaultdict(set)
    for r in _read('as_categorized.csv'):
        if r.get('source') != 'bgptools.tags':
            continue
        try:
            asn = int(r['asn'])
        except (ValueError, KeyError):
            continue
        tag = r.get('tag') or ''
        if not tag:
            continue
        cc = as_cc.get(asn)
        if cc:
            tags_per_cc[cc][tag] += 1
        global_tags[tag] += 1
        asns_by_tag[tag].add(asn)
    return tags_per_cc, global_tags, asns_by_tag


def build():
    import plotly.graph_objects as go

    tags_per_cc, global_tags, asns_by_tag = load()
    top_tags = [t for t, _ in global_tags.most_common(12)]

    # ---- Panel 1: 9-country × top-10 tags heatmap ----
    p1 = go.Figure()
    top10 = top_tags[:10]
    z = []
    for tag in top10:
        row = []
        for cc in TARGET:
            total = sum(tags_per_cc[cc].values()) or 1
            row.append(tags_per_cc[cc].get(tag, 0) / total * 100)
        z.append(row)
    p1.add_trace(go.Heatmap(
        z=z,
        x=[f'{COUNTRY_NAME[c]} {c}' for c in TARGET],
        y=top10,
        colorscale=[[0, '#0d1117'], [0.3, COLORS['purple']], [1, COLORS['yellow']]],
        colorbar=dict(title='% of country<br>bgp-tagged ASes'),
        text=[[f'{cell:.1f}%' for cell in row] for row in z],
        texttemplate='%{text}', textfont=dict(color=TEXT_PRIMARY, size=10),
    ))
    p1.update_layout(
        title='① 9 国 × Top-10 bgptools 标签矩阵 · Country × tag share (%)',
        height=540, xaxis=dict(title='', tickangle=-20),
    )

    # ---- Panel 2: security/privacy tag stacked per country ----
    p2 = go.Figure()
    order2 = sorted(TARGET, key=lambda c: -sum(
        tags_per_cc[c].get(t, 0) for t in SECURITY_TAGS))
    for tag in SECURITY_TAGS:
        ys = [tags_per_cc[cc].get(tag, 0) for cc in order2]
        p2.add_trace(go.Bar(
            x=[f'{COUNTRY_NAME[c]} {c}' for c in order2],
            y=ys, name=tag, marker_color=SEC_COLOR[tag],
            text=[str(y) if y > 0 else '' for y in ys],
            textposition='inside',
        ))
    p2.update_layout(
        title='② 安全/隐私相关标签分布 · Security & privacy tags per country',
        barmode='stack', yaxis=dict(title='# of ASes'),
        xaxis=dict(title='', tickangle=-20),
        height=500, legend=dict(orientation='h', y=-0.2),
    )

    # ---- Panel 3: Internet Critical Infra concentration ----
    p3 = go.Figure()
    crit_rows = []
    for cc in TARGET:
        crit = tags_per_cc[cc].get('Internet Critical Infra', 0)
        anycast = tags_per_cc[cc].get('Anycast', 0)
        crit_rows.append((cc, crit, anycast))
    crit_rows.sort(key=lambda r: -r[1])
    xs = [f'{COUNTRY_NAME[r[0]]} {r[0]}' for r in crit_rows]
    p3.add_trace(go.Bar(
        x=xs, y=[r[1] for r in crit_rows], name='Internet Critical Infra',
        marker_color=COLORS['amber'],
        text=[str(r[1]) for r in crit_rows], textposition='outside',
    ))
    p3.add_trace(go.Bar(
        x=xs, y=[r[2] for r in crit_rows], name='Anycast',
        marker_color=COLORS['green'],
        text=[str(r[2]) for r in crit_rows], textposition='outside',
    ))
    p3.update_layout(
        title='③ 关键基础设施 AS 分布 · Critical-infra + Anycast ASes per country',
        yaxis=dict(title='# of ASes'),
        xaxis=dict(title='', tickangle=-20),
        barmode='group', height=500,
    )

    # ---- Panel 4: global tag vocabulary bars ----
    p4 = go.Figure()
    p4.add_trace(go.Bar(
        orientation='h',
        y=[t for t, _ in global_tags.most_common(18)][::-1],
        x=[n for _, n in global_tags.most_common(18)][::-1],
        marker_color=[
            SEC_COLOR[t] if t in SEC_COLOR
            else (COLORS['cyan'] if 'RPKI' in t else COLORS['blue'])
            for t, _ in global_tags.most_common(18)][::-1],
        text=[str(n) for _, n in global_tags.most_common(18)][::-1],
        textposition='outside',
    ))
    p4.update_layout(
        title='④ 全球 bgptools 标签词汇表 · Global tag vocabulary (18 labels)',
        xaxis=dict(title='# of ASes'),
        height=560, margin=dict(l=200), showlegend=False,
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

    total_tags = sum(global_tags.values())
    tor_total = global_tags.get('ToR Services', 0)
    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>数据源：</b>bgp.tools 手工维护的 18 个 AS 行为标签，涵盖角色 '
        f'（Home ISP · Academic · Government · Server Hosting …）、安全 '
        f'（ToR · VPN · DDoS Mitigation · Anycast）与关键基础设施。'
        f'<br><b>Scope:</b> bgptools.tags · 2024-10 snapshot · '
        f'{total_tags:,} tags across {sum(1 for _ in asns_by_tag.values())} '
        f'unique AS entries. 全球 ToR Services 标签 AS <b>{tor_total}</b> 个。'
        f'</p>'
    )

    banner = (
        '<div class="step-banner">'
        '<h1>AS 行为标签地图 · AS Behavioral Tags</h1>'
        '<h2>bgp.tools 18-tag vocabulary across 9 countries · '
        'security × role × critical-infra lens</h2>'
        '</div>'
        '<div class="step-footer">topic 6 · 2024-10 snapshot · bgptools.tags</div>'
    )
    out_path = OUT / 'topic6_bgptools_tags.html'
    out_path.write_text(
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>AS 行为标签地图 · BGP-tools AS Tags</title>'
        f'{BANNER_CSS}</head><body>'
        f'{banner}<div class="content">{intro}'
        f'{"".join(parts)}</div></body></html>',
        encoding='utf-8',
    )
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    print(f'top-5 global tags: {global_tags.most_common(5)}')


if __name__ == '__main__':
    build()
