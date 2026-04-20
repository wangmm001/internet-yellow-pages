"""Topic 19: App-level censorship — 12 OONI probes beyond webconnectivity.

Topic 7 used only OONI Web Connectivity. The 12 other OONI tests measure
specific apps: Telegram, WhatsApp, FacebookMessenger, Signal, Tor, Psiphon,
RiseupVPN, TorSF, VanillaTor, STUN reachability, HTTP-invalid, HTTP-header.
This topic asks: which countries block which apps, and how similar are
their blocking patterns?
"""
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.china.common import (  # noqa: E402
    BANNER_CSS, COLORS, TEXT_PRIMARY, TEXT_SECONDARY,
    apply_plotly_theme, country_color, warning_block,
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


def _read(p):
    return list(csv.DictReader(open(p, encoding='utf-8'))) \
        if p.exists() else []


def _short_app(tag):
    """Extract app name from 'OONI Telegram Test' → 'Telegram'."""
    s = tag.replace('OONI ', '').replace(' Test', '').strip()
    return s or tag


def _placeholder(reason):
    banner = (
        '<div class="step-banner">'
        '<h1>应用级封锁矩阵 · App-Level Censorship Matrix</h1>'
        '<h2>12 OONI app-specific probes × 9 target countries</h2>'
        '</div><div class="step-footer">topic 19 · placeholder</div>'
    )
    intro = warning_block(reason, title='数据缺口 · Data gap')
    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>应用级封锁矩阵 · App Censorship</title>'
        f'{BANNER_CSS}</head><body>{banner}'
        f'<div class="content">{intro}</div></body></html>'
    )
    for dest in (OUT / 'topic19_app_censorship.html',
                 REPO / 'analysis' / 'countries' / 'html' /
                 'topic19_app_censorship.html'):
        dest.write_text(html, encoding='utf-8')
    print(f'topic 19: placeholder ({reason})')


def build():
    import plotly.graph_objects as go
    from plotly.io import to_html

    data = _read(CACHE / 'ooni_apps_matrix.csv')
    if not data:
        return _placeholder(
            '<code>ooni_apps_matrix.csv</code> 为空——12 个 OONI app '
            'crawler 未运行，或 Tag 标签命名不符合 "OONI ... Test" 模式。')

    as_cc = {int(r['asn']): r['cc'] for r in _read(CACHE / 'as_country.csv')
             if r.get('asn', '').isdigit()}

    # Data shape: {asn, app_tag, cc, total, pct_blocked, ...}
    # For country-level aggregation, prefer r.cc (edge prop). If empty,
    # fall back to as_cc lookup (same fallback as topic 7).
    # Build: (cc, app) -> (sum_blocked, sum_total)
    agg = defaultdict(lambda: {'blocked': 0.0, 'ok': 0.0, 'total': 0})
    apps_seen = set()
    for r in data:
        cc = r.get('cc') or ''
        if not cc:
            try:
                cc = as_cc.get(int(r['asn']), '')
            except (ValueError, KeyError):
                cc = ''
        if not cc:
            continue
        app = _short_app(r.get('app_tag') or '')
        apps_seen.add(app)
        try:
            total = int(float(r.get('total') or 0))
            pb = float(r.get('pct_blocked') or 0)
            po = float(r.get('pct_ok') or 0)
        except (ValueError, KeyError):
            continue
        d = agg[(cc, app)]
        d['total'] += total
        d['blocked'] += pb * total / 100  # reconstruct count
        d['ok'] += po * total / 100

    apps = sorted(apps_seen)

    # --- P1: 12-app × 9-country heatmap of %-blocked ---
    z = []; text = []
    for cc in TARGET:
        row_z = []; row_t = []
        for app in apps:
            d = agg.get((cc, app), None)
            if not d or d['total'] == 0:
                row_z.append(None); row_t.append('—')
            else:
                pct = d['blocked'] / d['total'] * 100
                row_z.append(round(pct, 1))
                row_t.append(f'{pct:.0f}%')
        z.append(row_z); text.append(row_t)

    p1 = go.Figure(data=go.Heatmap(
        z=z, x=apps, y=[f'{COUNTRY_NAME[c]} {c}' for c in TARGET],
        colorscale=[[0, '#0d1117'], [0.3, COLORS['cyan']],
                    [0.6, COLORS['orange']], [1, COLORS['red']]],
        colorbar=dict(title='% blocked'),
        text=text, texttemplate='%{text}',
        textfont=dict(color=TEXT_PRIMARY, size=11),
    ))
    p1.update_layout(
        title='① 12-app × 9-country 封锁率矩阵 · '
              'percentage of measurements blocked',
        xaxis=dict(title='app', tickangle=-25),
        yaxis=dict(title='country', autorange='reversed'),
        height=540,
    )

    # --- P2: top-10 "most-blocked" apps globally ---
    app_global = defaultdict(lambda: {'blocked': 0.0, 'total': 0})
    for (cc, app), d in agg.items():
        app_global[app]['blocked'] += d['blocked']
        app_global[app]['total'] += d['total']
    app_pct = [(a, d['blocked'] / d['total'] * 100)
               for a, d in app_global.items() if d['total'] > 50]
    app_pct.sort(key=lambda t: -t[1])
    p2 = go.Figure()
    if app_pct:
        p2.add_trace(go.Bar(
            orientation='h',
            y=[a for a, _ in app_pct][::-1],
            x=[p for _, p in app_pct][::-1],
            marker_color=[COLORS['red'] if p > 20 else COLORS['orange']
                          if p > 5 else COLORS['green']
                          for _, p in app_pct][::-1],
            text=[f'{p:.1f}%' for _, p in app_pct][::-1],
            textposition='outside',
        ))
    p2.update_layout(
        title='② 全球 12 app 封锁率排行 · global blocking rate per app',
        xaxis=dict(title='% blocked (averaged across all observed AS-country)'),
        height=540, margin=dict(l=180), showlegend=False,
    )

    # --- P3: top-15 AS with most "3-circumvention-tools blocked" records ---
    circ = {'Tor', 'Psiphon', 'RiseupVPN', 'TorSF', 'VanillaTor'}
    as_heavy = Counter()
    for r in data:
        app = _short_app(r.get('app_tag') or '')
        if app not in circ:
            continue
        try:
            asn = int(r['asn']); pb = float(r.get('pct_blocked') or 0)
        except (ValueError, KeyError):
            continue
        if pb > 50:
            as_heavy[asn] += 1
    top_as = as_heavy.most_common(15)
    p3 = go.Figure()
    if top_as:
        p3.add_trace(go.Bar(
            orientation='h',
            y=[f'AS{a} ({as_cc.get(a, "?")})' for a, _ in top_as][::-1],
            x=[c for _, c in top_as][::-1],
            marker_color=[country_color(as_cc.get(a, '?'))
                          if as_cc.get(a) in TARGET else COLORS['purple']
                          for a, _ in top_as][::-1],
            text=[f'{c}/5' for _, c in top_as][::-1],
            textposition='outside',
        ))
    p3.update_layout(
        title='③ 封锁规避工具最严厉的 Top-15 AS · '
              'ASes blocking ≥3 of {Tor, Psiphon, RiseupVPN, TorSF, Vanilla}',
        xaxis=dict(title='# circumvention apps blocked >50%'),
        height=520, margin=dict(l=180), showlegend=False,
    )

    # --- P4: country similarity heatmap (Jaccard on blocked apps) ---
    cc_apps = defaultdict(set)  # cc -> set of app with pct>20
    for (cc, app), d in agg.items():
        if d['total'] > 10 and d['blocked'] / d['total'] > 0.2:
            cc_apps[cc].add(app)
    jaccard = []; ylabs = []
    ccs = [c for c in TARGET if cc_apps.get(c)]
    for c1 in ccs:
        ylabs.append(f'{COUNTRY_NAME[c1]} {c1}')
        row = []
        for c2 in ccs:
            a = cc_apps[c1]; b = cc_apps[c2]
            u = a | b
            row.append(round(len(a & b) / len(u), 2) if u else 0)
        jaccard.append(row)
    p4 = go.Figure()
    if jaccard:
        p4.add_trace(go.Heatmap(
            z=jaccard, x=ylabs, y=ylabs,
            colorscale=[[0, '#0d1117'], [0.5, COLORS['cyan']],
                        [1, COLORS['red']]],
            colorbar=dict(title='Jaccard'),
            text=[[f'{v:.2f}' for v in row] for row in jaccard],
            texttemplate='%{text}',
            textfont=dict(color=TEXT_PRIMARY, size=11),
        ))
    p4.update_layout(
        title='④ 各国封锁模式相似度 · Jaccard similarity of '
              'apps blocked (>20% rate) pairwise',
        xaxis=dict(tickangle=-25),
        yaxis=dict(autorange='reversed'),
        height=500,
    )

    figs = [p1, p2, p3, p4]
    for f in figs:
        apply_plotly_theme(f)
    parts = []; first = True
    for f in figs:
        parts.append(to_html(
            f, include_plotlyjs=('inline' if first else False),
            full_html=False, default_height='500px'))
        first = False

    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>数据：</b>OONI 12 个应用专用探针——共 <b>{len(data):,}</b> 条 '
        f'CENSORED 边，横跨 <b>{len(apps)}</b> 个 app、'
        f'<b>{len({r.get("cc") for r in data if r.get("cc")})}</b> 个国家。'
        f'<br><b>注意：</b>与 topic 7 webconnectivity 一样，部分 crawler 的 '
        f'<code>country_code</code> 边属性可能为空；此时回退到 AS → 国家'
        f'映射。Panel ③ 的规避工具=Tor/Psiphon/RiseupVPN/TorSF/Vanilla。'
        f'Panel ④ 阈值=单 app 封锁率 >20% 才计入该国的"封锁集"。'
        f'</p>'
    )

    banner = (
        '<div class="step-banner">'
        '<h1>应用级封锁矩阵 · App-Level Censorship Matrix</h1>'
        '<h2>12 OONI app-specific probes · who blocks what</h2>'
        '</div><div class="step-footer">topic 19 · offline · '
        'ooni.{telegram, whatsapp, tor, psiphon, ...}</div>'
    )

    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>应用级封锁矩阵 · App Censorship</title>'
        f'{BANNER_CSS}</head><body>{banner}'
        f'<div class="content">{intro}{"".join(parts)}</div></body></html>'
    )
    out_path = OUT / 'topic19_app_censorship.html'
    out_path.write_text(html, encoding='utf-8')
    mirror = REPO / 'analysis' / 'countries' / 'html' / \
        'topic19_app_censorship.html'
    mirror.write_text(html, encoding='utf-8')
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    print(f'rows={len(data)}  apps={len(apps)}  target_countries=9')


if __name__ == '__main__':
    build()
