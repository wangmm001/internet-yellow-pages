"""Topic 21: DNS authority consolidation — forward + reverse + root.

Merges three MANAGED_BY sources:
  1. openintel.infra_ns — forward DNS authority (millions of domains → NS hosts)
  2. simulamet.rirdata_rdns — reverse DNS authority (per RDNSPrefix → NS host)
  3. iana.root_zone — root-zone NS (TLD → NS host)

Asks: does the same small set of operators run all three, or are forward and
reverse authority universes distinct?
"""
import csv
import os
import re
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


def _read(p):
    return list(csv.DictReader(open(p, encoding='utf-8'))) \
        if p.exists() else []


def _operator(host):
    """Extract 2nd-level domain as operator stand-in."""
    if not host:
        return '?'
    parts = host.strip('.').split('.')
    return '.'.join(parts[-2:]) if len(parts) >= 2 else host


def _placeholder(reason):
    banner = (
        '<div class="step-banner">'
        '<h1>DNS 权威深度图 · DNS Authority Consolidation</h1>'
        '<h2>Forward (infra_ns) + Reverse (rirdata_rdns) + Root '
        '(iana.root_zone)</h2>'
        '</div><div class="step-footer">topic 21 · placeholder</div>'
    )
    intro = warning_block(reason, title='数据缺口 · Data gap')
    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>DNS 权威深度图 · DNS Authority Consolidation</title>'
        f'{BANNER_CSS}</head><body>{banner}'
        f'<div class="content">{intro}</div></body></html>'
    )
    for dest in (OUT / 'topic21_dns_authority_deep.html',
                 REPO / 'analysis' / 'countries' / 'html' /
                 'topic21_dns_authority_deep.html'):
        dest.write_text(html, encoding='utf-8')
    print(f'topic 21: placeholder ({reason})')


def build():
    import plotly.graph_objects as go
    from plotly.io import to_html

    fwd = _read(CACHE / 'ns_authority_forward.csv')
    rdns = _read(CACHE / 'rdns_authority.csv')
    root = _read(CACHE / 'root_zone_ns.csv')

    if not (fwd or rdns or root):
        return _placeholder(
            '所有 3 个 CSV 都为空——infra_ns / rirdata_rdns / iana.root_zone '
            'crawler 均未运行。')

    # Operator aggregations (2LD of NS host)
    fwd_op = Counter()
    for r in fwd:
        fwd_op[_operator(r.get('ns_host'))] += 1
    rdns_op = Counter()
    for r in rdns:
        rdns_op[_operator(r.get('ns_host'))] += 1
    root_op = Counter()
    for r in root:
        root_op[_operator(r.get('ns_host'))] += 1

    # --- P1: Top-20 forward DNS operators ---
    top_fwd = fwd_op.most_common(20)
    p1 = go.Figure()
    if top_fwd:
        p1.add_trace(go.Bar(
            orientation='h',
            y=[op for op, _ in top_fwd][::-1],
            x=[c for _, c in top_fwd][::-1],
            marker_color=COLORS['cyan'],
            text=[f'{c:,}' for _, c in top_fwd][::-1],
            textposition='outside',
        ))
    p1.update_layout(
        title='① Top-20 正向 DNS 运营商 · Forward DNS authority '
              '(infra_ns) · domain count per 2LD operator',
        xaxis=dict(title='# domains'),
        height=600, margin=dict(l=200), showlegend=False,
    )

    # --- P2: Top-20 reverse DNS operators ---
    top_rdns = rdns_op.most_common(20)
    p2 = go.Figure()
    if top_rdns:
        p2.add_trace(go.Bar(
            orientation='h',
            y=[op for op, _ in top_rdns][::-1],
            x=[c for _, c in top_rdns][::-1],
            marker_color=COLORS['orange'],
            text=[f'{c:,}' for _, c in top_rdns][::-1],
            textposition='outside',
        ))
    p2.update_layout(
        title='② Top-20 反向 DNS 运营商 · Reverse DNS authority '
              '(rirdata_rdns) · prefix count per 2LD operator',
        xaxis=dict(title='# prefixes'),
        height=600, margin=dict(l=200), showlegend=False,
    )

    # --- P3: Forward vs reverse operator overlap ---
    fwd_set = set(fwd_op)
    rdns_set = set(rdns_op)
    common = fwd_set & rdns_set
    only_fwd = fwd_set - rdns_set
    only_rdns = rdns_set - fwd_set
    p3 = go.Figure()
    p3.add_trace(go.Bar(
        x=['forward-only', 'both', 'reverse-only'],
        y=[len(only_fwd), len(common), len(only_rdns)],
        marker_color=[COLORS['cyan'], COLORS['green'], COLORS['orange']],
        text=[f'{len(only_fwd):,}', f'{len(common):,}',
              f'{len(only_rdns):,}'],
        textposition='outside',
    ))
    p3.update_layout(
        title='③ 正向 vs 反向 运营商宇宙重叠 · '
              'Forward/reverse DNS operator overlap',
        yaxis=dict(title='# distinct 2LD operators'),
        height=420, showlegend=False,
    )

    # --- P4: Root zone NS diversity per TLD ---
    tld_ns = defaultdict(set)
    for r in root:
        tld = r.get('tld', '')
        ns = r.get('ns_host', '')
        if tld and ns:
            tld_ns[tld].add(ns)
    # Distribution of diversity
    diversity_dist = Counter(len(s) for s in tld_ns.values())
    p4 = go.Figure()
    if diversity_dist:
        xs = sorted(diversity_dist.keys())
        p4.add_trace(go.Bar(
            x=xs, y=[diversity_dist[x] for x in xs],
            marker_color=COLORS['purple'],
            text=[diversity_dist[x] for x in xs],
            textposition='outside',
        ))
    p4.update_layout(
        title='④ Root zone TLD 的 NS 多样性分布 · '
              '# distinct NS hosts per TLD in root zone',
        xaxis=dict(title='# distinct NS hosts'),
        yaxis=dict(title='# TLDs'),
        height=440, showlegend=False,
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
        f'<b>数据：</b>3 类 MANAGED_BY：forward (infra_ns) '
        f'<b>{len(fwd):,}</b> 行；reverse (rirdata_rdns) '
        f'<b>{len(rdns):,}</b> 行；root zone (iana.root_zone) '
        f'<b>{len(root):,}</b> 行。运营商 = NS 主机名的 2LD。'
        f'<br><b>发现预期：</b>Panel ① 正向集中度极高（Cloudflare / '
        f'AWS Route53 / Google 前列）；Panel ② 反向通常是 ISP 自己的 NS '
        f'而不是 DNS 大厂；Panel ③ 两者重叠小说明两套宇宙互相独立；'
        f'Panel ④ root zone 历来高度多样（每 TLD 6-13 个 NS 是常态）。'
        f'</p>'
    )

    banner = (
        '<div class="step-banner">'
        '<h1>DNS 权威深度图 · DNS Authority Consolidation</h1>'
        '<h2>Forward · Reverse · Root — three universes, '
        'mostly disjoint</h2>'
        '</div><div class="step-footer">topic 21 · offline · '
        'openintel.infra_ns + simulamet.rirdata_rdns + iana.root_zone</div>'
    )

    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>DNS 权威深度图 · DNS Authority Consolidation</title>'
        f'{BANNER_CSS}</head><body>{banner}'
        f'<div class="content">{intro}{"".join(parts)}</div></body></html>'
    )
    out_path = OUT / 'topic21_dns_authority_deep.html'
    out_path.write_text(html, encoding='utf-8')
    mirror = REPO / 'analysis' / 'countries' / 'html' / \
        'topic21_dns_authority_deep.html'
    mirror.write_text(html, encoding='utf-8')
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    print(f'forward rows={len(fwd)}  reverse rows={len(rdns)}  '
          f'root rows={len(root)}')
    if top_fwd:
        print(f'top forward op: {top_fwd[0]}')
    if top_rdns:
        print(f'top reverse op: {top_rdns[0]}')


if __name__ == '__main__':
    build()
