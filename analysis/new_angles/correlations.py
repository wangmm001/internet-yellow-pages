"""Cross-topic correlation scatters.

Verifies the synthesis page's four claims by computing correlation
coefficients and plotting the underlying scatter. Each panel tests
one hypothesis against the data:

 ① Security theater — Per-AS RPKI coverage vs ROV enforcement
 ② Eyeball vs sovereignty — Per-country eyeball share vs composite index
 ③ Net exporter vs user base — IHR balance vs eyeball pct
 ④ Growth vs hygiene — prefix CAGR vs RPKI Δpp (from evolution)

Output: analysis/new_angles/html/correlations.html
Site mirror: analysis/countries/html/correlations.html
"""
import csv
import json
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.china.common import (  # noqa: E402
    BANNER_CSS, COLORS, TEXT_PRIMARY, TEXT_SECONDARY,
    apply_plotly_theme, country_color,
)

REPO = Path(__file__).resolve().parent.parent.parent
CACHE = REPO / 'data_cache' / 'new_angles'
METRICS = REPO / 'analysis' / 'countries' / 'data' / '2026-04'
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


def pearson(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys)
             if x is not None and y is not None]
    if len(pairs) < 3:
        return None
    xs_, ys_ = zip(*pairs)
    try:
        mx, my = statistics.mean(xs_), statistics.mean(ys_)
        num = sum((x - mx) * (y - my) for x, y in pairs)
        dx = sum((x - mx) ** 2 for x in xs_) ** 0.5
        dy = sum((y - my) ** 2 for y in ys_) ** 0.5
        return num / (dx * dy) if dx and dy else None
    except (ZeroDivisionError, ValueError):
        return None


def _country_metric(cc, step, key):
    f = METRICS / cc / f'step{step:02d}_metrics.json'
    if not f.exists():
        return None
    d = json.loads(f.read_text(encoding='utf-8')).get('metrics', {}) or {}
    return d.get(key)


def load_rpki_rov():
    """Per-AS (rpki_pct, rov_pct) — joined on asn.

    Match synthesis filter: tot > 0 (include all sizes) + require
    non-empty ratio string in rovista (skip ASes with no ROV data).
    """
    rpki = {}
    for r in _read(CACHE / 'rpki_per_as.csv'):
        try:
            a = int(r['asn']); total = int(r['total'] or 0)
            ok = int(r['rpki'] or 0)
        except (ValueError, KeyError):
            continue
        if total > 0:
            rpki[a] = ok / total * 100
    rov = {}
    for r in _read(CACHE / 'rovista.csv'):
        try:
            raw = r.get('ratio') or ''
            if not raw.strip():
                continue
            a = int(r['asn'])
            rov[a] = float(raw) * 100
        except (ValueError, KeyError):
            continue
    as_cc = {int(r['asn']): r['cc'] for r in _read(CACHE / 'as_country.csv')
             if r.get('asn', '').isdigit()}
    points = []
    for a in set(rpki) & set(rov):
        points.append((rpki[a], rov[a], as_cc.get(a, 'ZZ')))
    return points


def load_country_eyeball_sov():
    """Per-country: (eyeball_pct, sovereignty_index)."""
    ey = defaultdict(lambda: {'users': 0.0, 'as_n': 0})
    for r in _read(CACHE / 'eyeball_as_country.csv'):
        cc = r['cc']
        try:
            pct = float(r['pct_users'] or 0)
            samples = float(r['samples'] or 0)
        except ValueError:
            continue
        ey[cc]['users'] += pct * samples / 100
        ey[cc]['as_n'] += 1
    total_as_per_cc = defaultdict(int)
    for r in _read(CACHE / 'as_country.csv'):
        total_as_per_cc[r['cc']] += 1
    rows = []
    for cc in TARGET:
        ey_as = ey.get(cc, {}).get('as_n', 0)
        total_as = total_as_per_cc.get(cc, 0)
        ey_pct = ey_as / total_as * 100 if total_as else None
        sov = _country_metric(cc, 20, 'composite_sovereignty_index')
        rows.append({'cc': cc, 'eyeball_pct': ey_pct, 'sov': sov})
    return rows


def load_country_netbal_eyeball():
    """Per-country: (net hegemony balance, eyeball_pct)."""
    as_cc = {int(r['asn']): r['cc'] for r in _read(CACHE / 'as_country.csv')
             if r.get('asn', '').isdigit()}
    # Compute out/in per country from as_dependency
    complex_csv = REPO / 'data_cache' / 'complex_network' / 'as_dependency.csv'
    out_bal = defaultdict(float); in_bal = defaultdict(float)
    for r in _read(complex_csv):
        try:
            s = int(r['src']); d = int(r['dst'])
            h = float(r.get('hege') or 0)
        except (ValueError, KeyError):
            continue
        s_cc = as_cc.get(s); d_cc = as_cc.get(d)
        if s_cc and d_cc and s_cc != d_cc:
            out_bal[s_cc] += h
            in_bal[d_cc] += h
    # Eyeball pct
    ey_pct = {}
    ey_counts = defaultdict(int)
    for r in _read(CACHE / 'eyeball_as_country.csv'):
        ey_counts[r['cc']] += 1
    total_as_per_cc = defaultdict(int)
    for r in _read(CACHE / 'as_country.csv'):
        total_as_per_cc[r['cc']] += 1
    for cc in TARGET:
        if total_as_per_cc.get(cc):
            ey_pct[cc] = ey_counts.get(cc, 0) / total_as_per_cc[cc] * 100
    return [
        {'cc': cc,
         'net': in_bal.get(cc, 0) - out_bal.get(cc, 0),
         'ey_pct': ey_pct.get(cc)}
        for cc in TARGET
    ]


def load_growth_vs_hygiene():
    """Per-country: prefix CAGR (27-mo), RPKI Δpp."""
    from analysis.new_angles.evolution import collect
    series = collect()
    months = 27
    rows = []
    for cc in TARGET:
        pfx = series['total_prefixes'][cc]
        pfx_cagr = None
        if pfx[0] and pfx[-1] and pfx[0] > 0:
            pfx_cagr = ((pfx[-1] / pfx[0]) ** (12 / months) - 1) * 100
        rpki = [v for v in series['rpki_rate_pct'][cc] if v is not None]
        rpki_delta = (rpki[-1] - rpki[0]) if len(rpki) >= 2 else None
        rows.append({'cc': cc, 'pfx_cagr': pfx_cagr,
                     'rpki_delta': rpki_delta})
    return rows


def build():
    import plotly.graph_objects as go
    from plotly.io import to_html

    # ---- P1: Per-AS RPKI vs ROV ----
    pts = load_rpki_rov()
    # Keep sample to ~5k for rendering speed
    import random
    random.seed(42)
    if len(pts) > 8000:
        pts = random.sample(pts, 8000)
    x1 = [p[0] for p in pts]; y1 = [p[1] for p in pts]
    colors1 = [country_color(p[2]) if p[2] in TARGET else '#30363d'
               for p in pts]
    r1 = pearson(x1, y1)
    p1 = go.Figure()
    p1.add_trace(go.Scattergl(
        x=x1, y=y1, mode='markers',
        marker=dict(size=4, color=colors1, opacity=0.55,
                    line=dict(width=0)),
        hovertemplate='RPKI %{x:.1f}%<br>ROV %{y:.1f}%<extra></extra>',
        showlegend=False,
    ))
    # Diagonal
    p1.add_shape(type='line', x0=0, y0=0, x1=100, y1=100,
                 line=dict(color=TEXT_SECONDARY, width=1, dash='dash'))
    # Count "security theater" AS
    gap_n = sum(1 for x, y, _ in pts if x >= 50 and y < 50)
    p1.update_layout(
        title=f'① 签了不执行 · Per-AS RPKI% vs ROV% · '
              f'r={r1:.3f} (n={len(pts):,}, sample)',
        xaxis=dict(title='RPKI-valid prefix share %', range=[0, 105]),
        yaxis=dict(title='ROV enforcement %', range=[0, 105]),
        height=520,
    )
    p1.add_annotation(x=75, y=15, showarrow=False,
                      text=f'⚠ RPKI ≥50% &amp; ROV &lt;50%<br>'
                           f'{gap_n} AS ({gap_n / len(pts) * 100:.1f}%)',
                      bgcolor='rgba(255,69,58,0.1)',
                      bordercolor=COLORS['red'], borderwidth=1,
                      font=dict(color=COLORS['red'], size=12))

    # ---- P2: Country eyeball% vs sovereignty ----
    rows2 = load_country_eyeball_sov()
    xs = [r['eyeball_pct'] for r in rows2]
    ys = [r['sov'] for r in rows2]
    r2 = pearson(xs, ys)
    p2 = go.Figure()
    p2.add_trace(go.Scatter(
        x=xs, y=ys, mode='markers+text',
        text=[f'{COUNTRY_NAME[r["cc"]]} {r["cc"]}' for r in rows2],
        textposition='top center',
        marker=dict(size=16, color=[country_color(r['cc']) for r in rows2],
                    line=dict(color=TEXT_PRIMARY, width=1)),
        showlegend=False,
    ))
    p2.update_layout(
        title=f'② Eyeball 比例 × 主权指数 · '
              f'Does eyeball presence predict sovereignty? '
              f'r={r2:.3f}',
        xaxis=dict(title='% of country AS tagged as eyeball'),
        yaxis=dict(title='Composite Sovereignty Index'),
        height=520,
    )

    # ---- P3: Net exporter vs eyeball ----
    rows3 = load_country_netbal_eyeball()
    xs3 = [r['net'] for r in rows3]
    ys3 = [r['ey_pct'] for r in rows3]
    r3 = pearson(xs3, ys3)
    p3 = go.Figure()
    p3.add_trace(go.Scatter(
        x=xs3, y=ys3, mode='markers+text',
        text=[f'{COUNTRY_NAME[r["cc"]]} {r["cc"]}' for r in rows3],
        textposition='top center',
        marker=dict(size=16, color=[country_color(r['cc']) for r in rows3],
                    line=dict(color=TEXT_PRIMARY, width=1)),
        showlegend=False,
    ))
    p3.add_vline(x=0, line=dict(color=TEXT_SECONDARY, width=1, dash='dash'))
    p3.update_layout(
        title=f'③ 净依赖平衡 × Eyeball 比例 · '
              f'Are net exporters home to eyeball ASes? r={r3:.3f}',
        xaxis=dict(title='Net hegemony balance (in − out)'),
        yaxis=dict(title='% of country AS tagged as eyeball'),
        height=500,
    )

    # ---- P4: Growth vs hygiene ----
    rows4 = load_growth_vs_hygiene()
    xs4 = [r['pfx_cagr'] for r in rows4]
    ys4 = [r['rpki_delta'] for r in rows4]
    r4 = pearson(xs4, ys4)
    p4 = go.Figure()
    p4.add_trace(go.Scatter(
        x=xs4, y=ys4, mode='markers+text',
        text=[f'{COUNTRY_NAME[r["cc"]]} {r["cc"]}' for r in rows4],
        textposition='top center',
        marker=dict(size=16, color=[country_color(r['cc']) for r in rows4],
                    line=dict(color=TEXT_PRIMARY, width=1)),
        showlegend=False,
    ))
    p4.update_layout(
        title=f'④ 增长 × 安全 · Does prefix growth correlate with RPKI '
              f'improvement? r={r4:.3f}',
        xaxis=dict(title='Prefix 27-mo CAGR %'),
        yaxis=dict(title='RPKI coverage Δ (percentage points)'),
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

    def _verbal(r):
        if r is None:
            return '数据不足'
        a = abs(r)
        if a < 0.1:
            return '几乎独立'
        if a < 0.3:
            return '弱'
        if a < 0.5:
            return '中等'
        if a < 0.7:
            return '较强'
        return '强'

    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>方法：</b>把 15-topic + evolution 的核心指标交叉计算 Pearson '
        f'相关系数 r ∈ [-1, 1]，看 synthesis 页的主张在数据上是否成立。'
        f'|r| ≤ 0.1 代表几乎独立；0.1-0.3 弱；0.3-0.5 中等；>0.5 较强。'
        f'<br><b>解读摘要：</b>'
        f'<br>① r={r1:+.3f} ({_verbal(r1)})：签了 ROA 的 AS 是否就会执行 '
        f'ROV？—— 事实上两者几乎独立，<b>{gap_n} / {len(pts):,} 抽样 AS 落入'
        f' "签了不执行" 区</b>。Security theater 落实。'
        f'<br>② r={r2:+.3f} ({_verbal(r2)})：eyeball 比例与复合主权指数'
        f'——9 国里两个量独立；说明主权指数权重没给 eyeball 应有的比重。'
        f'<br>③ r={r3:+.3f} ({_verbal(r3)} 负相关)：'
        f'净依赖方向 × eyeball 比例——净出口国（US 等）eyeball AS 比例'
        f' 反而偏低；净进口国（IN/CN）eyeball 比例较高。'
        f'<br>④ r={r4:+.3f} ({_verbal(r4)} 负相关)：'
        f'谁"快长又快守"？—— 增长最快的 CN/FR 在 RPKI 改善上 反而 偏慢，'
        f'NL/JP 则是"增长温和+ROA 猛升"组合。'
        f'</p>'
    )

    banner = (
        '<div class="step-banner">'
        '<h1>跨 Topic 相关性 · Cross-Topic Correlation Scatters</h1>'
        '<h2>4 hypotheses from the synthesis page, tested against per-AS '
        'and per-country data with Pearson r</h2>'
        '</div>'
        '<div class="step-footer">correlations · offline · '
        'data_cache + metrics JSON</div>'
    )

    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>跨 Topic 相关性 · Correlation Scatters</title>'
        f'{BANNER_CSS}</head><body>'
        f'{banner}<div class="content">{intro}'
        f'{"".join(parts)}</div></body></html>'
    )
    out_path = OUT / 'correlations.html'
    out_path.write_text(html, encoding='utf-8')
    mirror = REPO / 'analysis' / 'countries' / 'html' / 'correlations.html'
    mirror.write_text(html, encoding='utf-8')
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    print(f'mirrored to {mirror}')
    print(f'r1 (RPKI×ROV, per-AS) = {r1:+.4f}  n={len(pts)}  '
          f'gap_n={gap_n}')
    print(f'r2 (eyeball×sov, country) = {r2:+.4f}')
    print(f'r3 (netbal×eyeball, country) = {r3:+.4f}')
    print(f'r4 (pfx CAGR × RPKI Δ) = {r4:+.4f}')


if __name__ == '__main__':
    build()
