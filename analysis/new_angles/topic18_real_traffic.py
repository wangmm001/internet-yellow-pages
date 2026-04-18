"""Topic 18: Counter-eyeball — real DNS traffic via Cloudflare + CRUX.

APNIC's eyeball estimate is derived from a Google Ads + DNS trick that
undercounts users behind public DNS resolvers (1.1.1.1, 8.8.8.8) and
corporate gateways. Cloudflare's DNS top-100 per country + Google
CRUX (Chrome browsing data per country) give us two alternative
demand-side signals. This topic asks: are they consistent with APNIC,
or does a different picture emerge?
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
    apply_plotly_theme, country_color,
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


def _placeholder(reason):
    banner = (
        '<div class="step-banner">'
        '<h1>反 eyeball 对照 · Counter-Eyeball Demand Signal</h1>'
        '<h2>Cloudflare DNS + Google CRUX vs APNIC eyeball</h2>'
        '</div><div class="step-footer">topic 18 · placeholder</div>'
    )
    intro = (
        f'<p style="padding:0 16px;margin:16px 0;color:{COLORS["orange"]};'
        f'border-left:3px solid {COLORS["orange"]};padding-left:14px;'
        f'font-size:13px">⚠️ <b>数据缺口：</b>{reason}</p>'
    )
    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>反 eyeball 对照 · Counter-Eyeball</title>'
        f'{BANNER_CSS}</head><body>{banner}'
        f'<div class="content">{intro}</div></body></html>'
    )
    for dest in (OUT / 'topic18_real_traffic.html',
                 REPO / 'analysis' / 'countries' / 'html' /
                 'topic18_real_traffic.html'):
        dest.write_text(html, encoding='utf-8')
    print(f'topic 18: placeholder ({reason})')


def build():
    import plotly.graph_objects as go
    from plotly.io import to_html

    cf_cc = _read(CACHE / 'cf_dns_top_countries.csv')
    cf_as = _read(CACHE / 'cf_dns_top_ases.csv')
    crux = _read(CACHE / 'crux_top_by_country.csv')

    if not cf_cc and not cf_as and not crux:
        return _placeholder(
            'cf_dns_top_*.csv / crux_top_by_country.csv 全空——'
            'Cloudflare DNS 与 Google CRUX crawler 未运行。')

    # --- P1: CF DNS traffic share — top 12 countries (by domain count) ---
    dom_per_cc = Counter()
    traffic_per_cc = defaultdict(float)  # sum of value_pct per cc
    for r in cf_cc:
        try:
            cc = r['cc']; v = float(r.get('value_pct') or 0)
        except (ValueError, KeyError):
            continue
        dom_per_cc[cc] += 1
        traffic_per_cc[cc] += v

    top_cc = dom_per_cc.most_common(15)
    p1 = go.Figure()
    if top_cc:
        p1.add_trace(go.Bar(
            x=[cc for cc, _ in top_cc],
            y=[dom_per_cc[cc] for cc, _ in top_cc],
            marker_color=[country_color(cc) if cc in TARGET
                          else COLORS['purple']
                          for cc, _ in top_cc],
            text=[f'{dom_per_cc[cc]:,}' for cc, _ in top_cc],
            textposition='outside',
        ))
    p1.update_layout(
        title='① Cloudflare DNS top 域名覆盖 · '
              '# of top-ranked domains per country',
        xaxis=dict(title='country'), yaxis=dict(title='# domains'),
        height=460, showlegend=False,
    )

    # --- P2: APNIC eyeball % vs CF DNS domain count scatter ---
    # Build APNIC per-country eyeball AS count
    ey = defaultdict(int)
    for r in _read(CACHE / 'eyeball_as_country.csv'):
        ey[r['cc']] += 1
    as_total_per_cc = defaultdict(int)
    for r in _read(CACHE / 'as_country.csv'):
        as_total_per_cc[r['cc']] += 1

    rows2 = []
    for cc in TARGET:
        ey_pct = ey[cc] / as_total_per_cc[cc] * 100 \
            if as_total_per_cc[cc] else None
        rows2.append({
            'cc': cc, 'ey_pct': ey_pct,
            'cf_domains': dom_per_cc.get(cc, 0),
            'cf_traffic': traffic_per_cc.get(cc, 0),
        })
    p2 = go.Figure()
    p2.add_trace(go.Scatter(
        x=[r['ey_pct'] for r in rows2],
        y=[r['cf_domains'] for r in rows2],
        mode='markers+text',
        text=[f'{COUNTRY_NAME[r["cc"]]} {r["cc"]}' for r in rows2],
        textposition='top center',
        marker=dict(size=16, color=[country_color(r['cc']) for r in rows2],
                    line=dict(color=TEXT_PRIMARY, width=1)),
        showlegend=False,
    ))
    p2.update_layout(
        title='② APNIC eyeball% × CF DNS 域名覆盖 · '
              'Do the two signals agree?',
        xaxis=dict(title='APNIC eyeball AS / total AS (%)'),
        yaxis=dict(title='# CF DNS top domains in country'),
        height=500,
    )

    # --- P3: Top-20 ASes by CF DNS traffic (across all domains) ---
    as_traffic = defaultdict(float)
    for r in cf_as:
        try:
            asn = int(r['asn']); v = float(r.get('value_pct') or 0)
        except (ValueError, KeyError):
            continue
        as_traffic[asn] += v
    as_cc = {int(r['asn']): r['cc'] for r in _read(CACHE / 'as_country.csv')
             if r.get('asn', '').isdigit()}
    top_as = sorted(as_traffic.items(), key=lambda t: -t[1])[:20]
    p3 = go.Figure()
    if top_as:
        p3.add_trace(go.Bar(
            orientation='h',
            y=[f'AS{a} ({as_cc.get(a, "?")})' for a, _ in top_as][::-1],
            x=[v for _, v in top_as][::-1],
            marker_color=[country_color(as_cc.get(a, '?'))
                          if as_cc.get(a) in TARGET else COLORS['purple']
                          for a, _ in top_as][::-1],
            text=[f'{v:.1f}' for _, v in top_as][::-1],
            textposition='outside',
        ))
    p3.update_layout(
        title='③ CF DNS 流量源 Top-20 AS · '
              'Top ASes driving Cloudflare DNS queries',
        xaxis=dict(title='sum value_pct across domains'),
        height=560, margin=dict(l=180), showlegend=False,
    )

    # --- P4: CRUX per-country coverage ---
    crux_per_cc = Counter()
    for r in crux:
        cc = r.get('cc')
        if cc:
            crux_per_cc[cc] += 1
    top_crux = crux_per_cc.most_common(15)
    p4 = go.Figure()
    if top_crux:
        p4.add_trace(go.Bar(
            x=[cc for cc, _ in top_crux],
            y=[crux_per_cc[cc] for cc, _ in top_crux],
            marker_color=[country_color(cc) if cc in TARGET
                          else COLORS['purple']
                          for cc, _ in top_crux],
            text=[f'{crux_per_cc[cc]:,}' for cc, _ in top_crux],
            textposition='outside',
        ))
    p4.update_layout(
        title='④ Google CRUX 每国 top 1M 数量 · '
              'CRUX real-browser ranking coverage',
        xaxis=dict(title='country'), yaxis=dict(title='# hostnames in CRUX top-1M'),
        height=460, showlegend=False,
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
        f'<b>数据：</b>Cloudflare 1.1.1.1 DNS top-100 域名 per country '
        f'<b>{len(cf_cc):,}</b> 行 + per AS <b>{len(cf_as):,}</b> 行；'
        f'Google CRUX top-1M <b>{len(crux):,}</b> 行。'
        f'<br><b>对照：</b>APNIC eyeball 是基于 Google Ads + DNS 测量，'
        f'对公共 DNS（1.1.1.1/8.8.8.8）用户计数偏低。'
        f'Cloudflare 自家 DNS 流量 + Google 自家 CRUX 是独立的需求侧信号。'
        f'Panel ② 的散点若不在对角线附近，说明两类 eyeball 信号不一致。'
        f'</p>'
    )

    banner = (
        '<div class="step-banner">'
        '<h1>反 eyeball 对照 · Counter-Eyeball Demand Signal</h1>'
        '<h2>Cloudflare DNS + Google CRUX vs APNIC eyeball</h2>'
        '</div><div class="step-footer">topic 18 · offline · '
        'cloudflare.dns_top_* + google.crux_top1m_country</div>'
    )

    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>反 eyeball 对照 · Counter-Eyeball</title>'
        f'{BANNER_CSS}</head><body>{banner}'
        f'<div class="content">{intro}{"".join(parts)}</div></body></html>'
    )
    out_path = OUT / 'topic18_real_traffic.html'
    out_path.write_text(html, encoding='utf-8')
    mirror = REPO / 'analysis' / 'countries' / 'html' / \
        'topic18_real_traffic.html'
    mirror.write_text(html, encoding='utf-8')
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    print(f'cf_cc rows={len(cf_cc)}  cf_as rows={len(cf_as)}  '
          f'crux rows={len(crux)}')


if __name__ == '__main__':
    build()
