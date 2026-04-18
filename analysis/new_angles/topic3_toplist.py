"""Topic 3: top-list analysis — downgraded from 4-source comparison.

The original plan called for cross-comparing Tranco × Cisco Umbrella ×
Google CrUX × OpenINTEL-Tranco, but the 2024-10 IYP dump only contains
Tranco top-1M (as a `Ranking` node). The other three top-list crawlers
were either not run or use different label patterns in that snapshot.

Fallback scope: Tranco top-10k single-source decomposition —
  ① TLD share (what % of global "important" domains are .com/.cn/.de?)
  ② 9-target country ccTLD presence
  ③ Rank decile concentration (is top-100 of Tranco very stable
     relative to top-10k?)
  ④ Domain-length distribution (typosquat / CDN hints)

When a future snapshot gains Cisco Umbrella + CrUX, extract_data.py
already targets those Ranking names and this module can pivot to the
planned 4-way comparison.
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

# Generic TLDs vs country-code TLDs
GTLD = {'com', 'org', 'net', 'info', 'biz', 'io', 'ai', 'app', 'dev',
        'edu', 'gov', 'co', 'tv', 'me', 'us', 'cc', 'xyz', 'top',
        'online', 'site', 'shop', 'blog', 'cloud', 'news'}

CC_TO_TLD = {'US': 'us', 'CN': 'cn', 'JP': 'jp', 'IN': 'in', 'DE': 'de',
             'GB': 'uk', 'FR': 'fr', 'NL': 'nl', 'RU': 'ru'}


def _read(name):
    p = CACHE / name
    if not p.exists():
        return []
    with open(p, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _tld(domain):
    parts = domain.lower().strip('.').split('.')
    return parts[-1] if parts else ''


def build():
    import plotly.graph_objects as go

    rows = _read('toplist_tranco_top.csv')
    n = len(rows)
    print(f'tranco rows: {n}', flush=True)

    tld_counts = Counter(_tld(r['domain']) for r in rows)
    # Per-decile TLD distribution
    decile_cc = defaultdict(Counter)
    for r in rows:
        try:
            rank = int(r['rank'])
        except (ValueError, KeyError):
            continue
        d = min(rank // 1000, 9)
        decile_cc[d][_tld(r['domain'])] += 1

    # ---- Panel 1: Top-20 TLDs in top-10k ----
    p1 = go.Figure()
    top20 = tld_counts.most_common(20)
    p1.add_trace(go.Bar(
        x=[t for t, _ in top20][::-1],
        y=[c for _, c in top20][::-1],
        marker_color=[
            COLORS['cyan'] if t in GTLD else country_color(
                {v: k for k, v in CC_TO_TLD.items()}.get(t, '??'))
            for t, _ in top20][::-1],
        text=[f'{c} · {c/n*100:.1f}%' for _, c in top20][::-1],
        textposition='outside',
    ))
    p1.update_layout(
        title=f'① Tranco Top-10k 中的 TLD 分布 · '
              f'TLD share across top-{n} domains',
        yaxis=dict(title='# domains'), xaxis=dict(title='TLD'),
        height=460, showlegend=False,
    )

    # ---- Panel 2: 9-country ccTLD presence ----
    p2 = go.Figure()
    order = sorted(TARGET, key=lambda c: -tld_counts.get(CC_TO_TLD[c], 0))
    vals = [tld_counts.get(CC_TO_TLD[c], 0) for c in order]
    p2.add_trace(go.Bar(
        x=[f'{COUNTRY_NAME[c]} {c} (.{CC_TO_TLD[c]})' for c in order],
        y=vals,
        marker_color=[country_color(c) for c in order],
        text=[f'{v}<br>({v/n*100:.2f}%)' for v in vals],
        textposition='outside',
    ))
    p2.update_layout(
        title='② 9 国 ccTLD 在 Tranco Top-10k 的存在感 · '
              'Target-country ccTLD presence',
        yaxis=dict(title='# domains'), xaxis=dict(title='', tickangle=-20),
        height=460, showlegend=False,
    )

    # ---- Panel 3: com vs non-com share by decile ----
    p3 = go.Figure()
    deciles = list(range(10))
    com_pct, cctld_pct, other_gtld = [], [], []
    cctlds = set(CC_TO_TLD.values())
    for d in deciles:
        tot = sum(decile_cc[d].values())
        com = decile_cc[d].get('com', 0)
        cc = sum(c for t, c in decile_cc[d].items() if t in cctlds)
        other = tot - com - cc
        com_pct.append(com / max(tot, 1) * 100)
        cctld_pct.append(cc / max(tot, 1) * 100)
        other_gtld.append(other / max(tot, 1) * 100)
    x_labels = [f'Top-{d*1000+1}-{(d+1)*1000}' for d in deciles]
    p3.add_trace(go.Bar(name='.com', x=x_labels, y=com_pct,
                        marker_color=COLORS['cyan']))
    p3.add_trace(go.Bar(name='9 countries ccTLDs', x=x_labels, y=cctld_pct,
                        marker_color=COLORS['orange']))
    p3.add_trace(go.Bar(name='other', x=x_labels, y=other_gtld,
                        marker_color='#8e8e93'))
    p3.update_layout(
        title='③ 每千排名段内 TLD 组成 · TLD mix by rank-decile',
        barmode='stack', yaxis=dict(title='%', range=[0, 100]),
        xaxis=dict(title='', tickangle=-15), height=460,
    )

    # ---- Panel 4: Domain length distribution ----
    p4 = go.Figure()
    lengths = [len(r['domain']) for r in rows]
    p4.add_trace(go.Histogram(
        x=lengths, nbinsx=30, marker_color=COLORS['purple'],
    ))
    mean_len = sum(lengths) / max(len(lengths), 1)
    p4.add_annotation(x=mean_len, y=0.95, yref='paper',
                      text=f'mean = {mean_len:.1f} chars',
                      showarrow=False, font=dict(color=TEXT_PRIMARY))
    p4.update_layout(
        title='④ Tranco Top-10k 域名字长分布 · Domain-name length histogram',
        xaxis=dict(title='characters'), yaxis=dict(title='# domains'),
        height=420, showlegend=False,
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

    com_share = tld_counts.get('com', 0) / n * 100
    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>原计划：</b>4 个 Top-1M 源对比（Tranco · Cisco Umbrella · '
        f'Google CrUX · OpenINTEL Tranco）— <i>2024-10 IYP dump 只含 '
        f'Tranco</i>，其余 3 个源在该快照未入库，降级为 Tranco 单源深度。'
        f'<br><b>Scope:</b> Tranco Top-10k (2024-10 snapshot) · '
        f'{len(tld_counts)} 个 TLD · <b>.com</b> 占 {com_share:.1f}%。'
        f'</p>'
    )
    intro += (
        f'<p style="margin:4px 16px 12px;padding:10px 14px;'
        f'border-left:3px solid #ff9f0a;background:rgba(255,159,10,0.08);'
        f'color:{TEXT_PRIMARY};font-size:13px;border-radius:4px">'
        f'⚠️ <b>4 源对比待后续快照：</b>当 IYP 引入 Cisco Umbrella 与 '
        f'CrUX Top-1M 后（预期 2026-Q3 快照），本页会自动切换为跨源 '
        f'Jaccard 相似度、rank-correlation 矩阵、地域分化 3 个新面板。'
        f'<br>Cross-source comparison blocked on upstream IYP crawler '
        f'expansion.</p>'
    )

    banner = (
        '<div class="step-banner">'
        '<h1>Tranco Top-10k 深度 · Tranco Top-10k Deep-dive</h1>'
        '<h2>Downgraded from planned 4-source cross-comparison · '
        'TLD mix · ccTLD presence · decile stability</h2>'
        '</div>'
        '<div class="step-footer">topic 3 · 2024-10 snapshot · '
        'single-source fallback</div>'
    )
    out_path = OUT / 'topic3_toplist.html'
    out_path.write_text(
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>Tranco Top-10k 深度 · Top-list Single-source Fallback</title>'
        f'{BANNER_CSS}</head><body>'
        f'{banner}<div class="content">{intro}'
        f'{"".join(parts)}</div></body></html>',
        encoding='utf-8',
    )
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    print(f'top-3 TLDs: {tld_counts.most_common(3)}')
    print(f'.com share: {com_share:.1f}%  · # unique TLDs: {len(tld_counts)}')


if __name__ == '__main__':
    build()
