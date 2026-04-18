"""Topic 4: Stanford ASDB business-category map of the 9-country AS footprint.

Reads as_categorized.csv + as_country.csv from data_cache/new_angles/.
Filters to source='stanford.asdb' (layer=1 = top-level category).

4 panels:
  ① 9-country × 8 top-level categories stacked percentages
  ② Most concentrated category per country (bar)
  ③ Global distribution of AS top-level categories
  ④ Top-10 sub-categories for a notable pair (CN vs US)
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

    # Stanford layer=1 = top-level (8 categories).
    asdb = defaultdict(lambda: defaultdict(set))  # cc -> cat -> {asn}
    sub_by_cat = defaultdict(lambda: defaultdict(Counter))  # cc -> cat -> sub:count
    cur_cat_of_as = defaultdict(dict)  # asn -> layer1 category (for sub lookup)
    for r in _read('as_categorized.csv'):
        if r.get('source') != 'stanford.asdb':
            continue
        try:
            asn = int(r['asn'])
            tag = r['tag']
            layer = int(r['layer']) if r.get('layer') else 0
        except (ValueError, KeyError):
            continue
        cc = as_cc.get(asn)
        if not cc:
            continue
        if layer == 1:
            asdb[cc][tag].add(asn)
            cur_cat_of_as[asn] = tag
        elif layer == 2:
            # Stash sub-cats for later drill-downs (CN vs US panel)
            sub_by_cat[cc].setdefault('_all', Counter())[tag] += 1

    # Global totals
    global_cat = Counter()
    for cc, d in asdb.items():
        for cat, asns in d.items():
            global_cat[cat] += len(asns)

    return asdb, global_cat, sub_by_cat


def build():
    import plotly.graph_objects as go

    asdb, global_cat, sub_by_cat = load()
    top_cats = [c for c, _ in global_cat.most_common(8)]
    print(f'top-level categories (global): {top_cats}')

    # Category-color palette
    cat_palette = [COLORS['cyan'], COLORS['orange'], COLORS['green'],
                   COLORS['purple'], COLORS['red'], COLORS['yellow'],
                   COLORS['pink'], '#8e8e93']
    cat_color = {cat: cat_palette[i] for i, cat in enumerate(top_cats)}

    # ---- Panel 1: 9-country × top-level category % stacked ----
    p1 = go.Figure()
    order1 = sorted(TARGET, key=lambda c: -sum(
        len(asdb[c].get(cat, [])) for cat in top_cats))
    xs = [f'{COUNTRY_NAME[c]} {c}' for c in order1]
    for cat in top_cats:
        ys = []
        for cc in order1:
            total = sum(len(asdb[cc].get(x, [])) for x in top_cats)
            ys.append(len(asdb[cc].get(cat, [])) / max(total, 1) * 100)
        p1.add_trace(go.Bar(
            x=xs, y=ys, name=cat[:30] + ('…' if len(cat) > 30 else ''),
            marker_color=cat_color[cat],
            text=[f'{y:.0f}%' if y >= 5 else '' for y in ys],
            textposition='inside',
        ))
    p1.update_layout(
        title='① 9 国 AS 业务类型分布 · Per-country breakdown of top-level ASDB categories',
        barmode='stack', yaxis=dict(title='% of AS with ASDB category',
                                     range=[0, 100]),
        xaxis=dict(title='', tickangle=-20),
        height=520, legend=dict(orientation='h', y=-0.22),
    )

    # ---- Panel 2: dominant category per country ----
    p2 = go.Figure()
    rows = []
    for cc in TARGET:
        cat_counts = {cat: len(asdb[cc].get(cat, set())) for cat in top_cats}
        if not any(cat_counts.values()):
            continue
        top = max(cat_counts.items(), key=lambda kv: kv[1])
        second = sorted(cat_counts.items(), key=lambda kv: -kv[1])[1] \
            if len(cat_counts) > 1 else (None, 0)
        total = sum(cat_counts.values())
        rows.append((cc, top[0], top[1] / total * 100, second[0], total))
    rows.sort(key=lambda r: -r[2])
    p2.add_trace(go.Bar(
        x=[f'{COUNTRY_NAME[r[0]]} {r[0]}' for r in rows],
        y=[r[2] for r in rows],
        marker_color=[cat_color.get(r[1], '#ccc') for r in rows],
        text=[f'{r[1][:24]}<br>{r[2]:.0f}%' for r in rows],
        textposition='outside',
    ))
    p2.update_layout(
        title='② 最占优类别占比 · Dominant category share per country',
        xaxis=dict(title='', tickangle=-20),
        yaxis=dict(title='% of country ASes', range=[0, 100]),
        height=480, showlegend=False,
    )

    # ---- Panel 3: global category distribution ----
    p3 = go.Figure()
    total_g = sum(global_cat.values())
    p3.add_trace(go.Pie(
        labels=[c[:35] + ('…' if len(c) > 35 else '') for c, _ in
                global_cat.most_common(10)],
        values=[n for _, n in global_cat.most_common(10)],
        marker=dict(colors=[cat_color.get(c, '#777')
                             for c, _ in global_cat.most_common(10)]),
        textinfo='label+percent', textposition='outside',
    ))
    p3.update_layout(
        title=f'③ 全球 AS 业务类型分布（Top-10）· Global ASDB category share '
              f'(total={total_g:,})',
        height=520, showlegend=False,
    )

    # ---- Panel 4: CN vs US category overlap ----
    p4 = go.Figure()
    cn_cnt = Counter({c: len(asdb['CN'].get(c, set())) for c in top_cats})
    us_cnt = Counter({c: len(asdb['US'].get(c, set())) for c in top_cats})
    cn_total = sum(cn_cnt.values()) or 1
    us_total = sum(us_cnt.values()) or 1
    cats_ordered = sorted(top_cats, key=lambda c: -(us_cnt[c] / us_total))
    p4.add_trace(go.Bar(
        y=[c[:40] + ('…' if len(c) > 40 else '') for c in cats_ordered],
        x=[cn_cnt[c] / cn_total * 100 for c in cats_ordered],
        name='CN %', orientation='h', marker_color=COLORS['red'],
        text=[f'{cn_cnt[c]} ({cn_cnt[c]/cn_total*100:.1f}%)'
              for c in cats_ordered], textposition='outside',
    ))
    p4.add_trace(go.Bar(
        y=[c[:40] + ('…' if len(c) > 40 else '') for c in cats_ordered],
        x=[us_cnt[c] / us_total * 100 for c in cats_ordered],
        name='US %', orientation='h', marker_color=COLORS['cyan'],
        text=[f'{us_cnt[c]} ({us_cnt[c]/us_total*100:.1f}%)'
              for c in cats_ordered], textposition='outside',
    ))
    p4.update_layout(
        title='④ CN vs US 类别对比 · CN and US across ASDB top-level categories',
        barmode='group',
        xaxis=dict(title='% of country ASes'),
        height=520, margin=dict(l=260),
    )

    from plotly.io import to_html
    for fig in (p1, p2, p3, p4):
        apply_plotly_theme(fig)
    parts = []
    first = True
    for fig in (p1, p2, p3, p4):
        parts.append(to_html(fig, include_plotlyjs=('inline' if first else False),
                             full_html=False, default_height='540px'))
        first = False

    covered_asn = sum(sum(len(asns) for asns in asdb[cc].values())
                      for cc in TARGET)
    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>问题：</b>现有所有分析把 AS 视作同质。Stanford 的 ASDB 数据集'
        f'把每个 AS 手工标注成 7+ 个业务大类（Computer & IT · Manufacturing · '
        f'Service · Government · Construction …）。本页用业务维度切 9 国 AS 组成。'
        f'<br><b>Scope:</b> stanford.asdb (layer=1 top-level) · 2024-10 snapshot · '
        f'{covered_asn:,} (cc,AS) pairs covered across the 9 target countries.'
        f'</p>'
    )

    banner = (
        '<div class="step-banner">'
        '<h1>AS 业务类型图谱 · AS Business Category Map</h1>'
        '<h2>Stanford ASDB 9-country top-level category breakdown</h2>'
        '</div>'
        '<div class="step-footer">topic 4 · 2024-10 snapshot · Stanford ASDB</div>'
    )
    out_path = OUT / 'topic4_asdb.html'
    out_path.write_text(
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>AS 业务类型图谱 · ASDB Category Map</title>'
        f'{BANNER_CSS}</head><body>'
        f'{banner}<div class="content">{intro}'
        f'{"".join(parts)}</div></body></html>',
        encoding='utf-8',
    )
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    print(f'top-3 global categories: {global_cat.most_common(3)}')


if __name__ == '__main__':
    build()
