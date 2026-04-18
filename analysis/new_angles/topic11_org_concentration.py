"""Topic 11 (substitute): AS → Organization ownership concentration per country.

Originally planned as IANA/NRO allocation-vs-actual gap, but 2024-10
dump lacks both IANAPrefix and RIRPrefix labels. Pivoted to
as_organization.csv (from the complex_network extract) to answer a
different but related question: how concentrated is AS ownership per
country? Few orgs owning many ASes = high concentration, many orgs
each with 1 AS = low concentration.

Gini/HHI per country reveals telecom market structure.
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
COMPLEX = REPO / 'data_cache' / 'complex_network'
OUT = REPO / 'analysis' / 'new_angles' / 'html'
OUT.mkdir(parents=True, exist_ok=True)

TARGET = ['US', 'CN', 'JP', 'IN', 'DE', 'GB', 'FR', 'NL', 'RU']
COUNTRY_NAME = {
    'US': '美国', 'CN': '中国', 'JP': '日本', 'IN': '印度', 'DE': '德国',
    'GB': '英国', 'FR': '法国', 'NL': '荷兰', 'RU': '俄罗斯',
}


def _read(path):
    if not path.exists():
        return []
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _hhi(counts):
    total = sum(counts)
    if not total:
        return 0.0
    return sum((c / total) ** 2 for c in counts) * 10000  # classic HHI scale


def _gini(xs):
    xs = sorted(xs); n = len(xs); s = sum(xs)
    if not n or not s:
        return 0.0
    cum = sum((i + 1) * x for i, x in enumerate(xs))
    return (2 * cum) / (n * s) - (n + 1) / n


def load():
    as_cc = {int(r['asn']): r['cc'] for r in _read(CACHE / 'as_country.csv')
             if r.get('asn', '').isdigit()}
    # as_organization (from complex_network cache)
    asn_org = {}
    for r in _read(COMPLEX / 'as_organization.csv'):
        try:
            asn_org[int(r['asn'])] = r.get('org_name', '') or '<unknown>'
        except (ValueError, KeyError):
            pass
    # Per country, count AS per org
    per_cc = defaultdict(Counter)  # cc -> {org: count}
    for asn, cc in as_cc.items():
        org = asn_org.get(asn)
        if org and cc:
            per_cc[cc][org] += 1
    return per_cc


def build():
    import plotly.graph_objects as go
    per_cc = load()

    # Summary rows
    rows = []
    for cc in TARGET:
        orgs = per_cc.get(cc, Counter())
        if not orgs:
            continue
        counts = list(orgs.values())
        n_as = sum(counts)
        n_orgs = len(orgs)
        hhi = _hhi(counts)
        gini = _gini(counts)
        top5_share = sum(n for _, n in orgs.most_common(5)) / max(n_as, 1) * 100
        rows.append({
            'cc': cc, 'n_as': n_as, 'n_orgs': n_orgs,
            'hhi': hhi, 'gini': gini, 'top5_share': top5_share,
            'top5': orgs.most_common(5),
        })
    rows.sort(key=lambda r: -r['hhi'])

    # ---- Panel 1: HHI per country ----
    p1 = go.Figure()
    p1.add_trace(go.Bar(
        x=[f'{COUNTRY_NAME[r["cc"]]} {r["cc"]}' for r in rows],
        y=[r['hhi'] for r in rows],
        marker_color=[country_color(r['cc']) for r in rows],
        text=[f'HHI {r["hhi"]:.0f}<br>({r["n_orgs"]:,} orgs / {r["n_as"]:,} AS)'
              for r in rows], textposition='outside',
    ))
    p1.update_layout(
        title='① AS 所有权集中度（HHI）· Ownership concentration per country',
        yaxis=dict(title='HHI (0=perfectly diffuse, 10000=monopoly)'),
        xaxis=dict(title='', tickangle=-20),
        height=480, showlegend=False,
    )

    # ---- Panel 2: top-5 org share per country ----
    p2 = go.Figure()
    ordered = sorted(rows, key=lambda r: -r['top5_share'])
    p2.add_trace(go.Bar(
        x=[f'{COUNTRY_NAME[r["cc"]]} {r["cc"]}' for r in ordered],
        y=[r['top5_share'] for r in ordered],
        marker_color=[country_color(r['cc']) for r in ordered],
        text=[f'{r["top5_share"]:.1f}%' for r in ordered],
        textposition='outside',
    ))
    p2.update_layout(
        title='② Top-5 Org 的 AS 数占比 · Share of country AS '
              'in the top-5 orgs',
        yaxis=dict(title='% of country AS', range=[0, 100]),
        xaxis=dict(title='', tickangle=-20),
        height=460, showlegend=False,
    )

    # ---- Panel 3: Gini / HHI scatter ----
    p3 = go.Figure()
    for r in rows:
        p3.add_trace(go.Scatter(
            x=[r['gini']], y=[r['hhi']],
            mode='markers+text', text=[r['cc']],
            textposition='top center',
            marker=dict(
                size=16 + (r['n_as'] / 1000),
                color=country_color(r['cc']),
                line=dict(color='#fff', width=1.5),
            ),
            textfont=dict(color=TEXT_PRIMARY, size=13),
            showlegend=False,
        ))
    p3.update_layout(
        title='③ Gini × HHI 散点 · 两种集中度指标相互校验 '
              '(size = AS count)',
        xaxis=dict(title='Gini coefficient (AS per org)', range=[0, 1]),
        yaxis=dict(title='HHI', range=[0, max(r["hhi"] for r in rows) * 1.1]),
        height=480,
    )

    # ---- Panel 4: Top-5 orgs list per country ----
    p4 = go.Figure()
    # Show as annotated text grid
    text_block = ''
    for r in rows:
        text_block += f'<b>{COUNTRY_NAME[r["cc"]]} {r["cc"]}</b> · HHI={r["hhi"]:.0f} · Top-5:<br>'
        for org, n in r['top5']:
            org_short = (org[:55] + '…') if len(org) > 55 else org
            text_block += f'&nbsp;&nbsp;{org_short} · {n} AS<br>'
        text_block += '<br>'

    p4.add_annotation(
        x=0, y=1, xref='paper', yref='paper',
        xanchor='left', yanchor='top',
        text=text_block, align='left', showarrow=False,
        font=dict(color=TEXT_PRIMARY, size=12, family='monospace'),
    )
    p4.update_xaxes(visible=False)
    p4.update_yaxes(visible=False)
    p4.update_layout(
        title='④ 每国 Top-5 所有者 · Top-5 org owners per country',
        height=640, plot_bgcolor=DARK_BG, paper_bgcolor=DARK_BG,
    )

    from plotly.io import to_html
    for fig in (p1, p2, p3, p4):
        apply_plotly_theme(fig)
    parts = []; first = True
    for fig in (p1, p2, p3, p4):
        parts.append(to_html(
            fig, include_plotlyjs=('inline' if first else False),
            full_html=False, default_height='540px'))
        first = False

    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>问题：</b>AS 数本身可能被企业账号稀释（参考 Topic 1），'
        f'但"AS 被几家公司控制"是另一个角度——高集中度意味 ISP 市场寡头。'
        f'<br><b>Scope:</b> <code>caida.as2org</code> 派生 '
        f'<code>as_organization.csv</code> · 2024-10 复用。'
        f'HHI < 1500 = diffuse · 1500-2500 = moderate · >2500 = concentrated.'
        f'</p>'
        f'<p style="margin:4px 16px 12px;padding:10px 14px;'
        f'border-left:3px solid #ff9f0a;background:rgba(255,159,10,0.08);'
        f'color:{TEXT_PRIMARY};font-size:13px;border-radius:4px">'
        f'⚠️ <b>IANA/NRO 路线缺失：</b>原计划"登记分配 vs 实际宣告"对比，'
        f'但 2024-10 dump 里 <code>:IANAPrefix</code> / <code>:RIRPrefix</code> '
        f'标签不存在。替换为 AS-Org ownership concentration。'
        f'</p>'
    )

    banner = (
        '<div class="step-banner">'
        '<h1>AS 所有权集中度 · AS Ownership Concentration</h1>'
        '<h2>Organization-level HHI + Gini across 9 countries · '
        'substitute for IANA/NRO allocation map</h2>'
        '</div>'
        '<div class="step-footer">topic 11 · caida.as2org derivation · '
        '2024-10 snapshot</div>'
    )
    out_path = OUT / 'topic11_org_concentration.html'
    out_path.write_text(
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>AS 所有权集中度 · AS Ownership Concentration</title>'
        f'{BANNER_CSS}</head><body>'
        f'{banner}<div class="content">{intro}'
        f'{"".join(parts)}</div></body></html>',
        encoding='utf-8',
    )
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    for r in rows[:3]:
        print(f'  {r["cc"]}: HHI={r["hhi"]:.0f}  top5_share={r["top5_share"]:.1f}%'
              f'  n_orgs={r["n_orgs"]:,}')


if __name__ == '__main__':
    build()
