"""Topic 7: OONI censorship measurement coverage (degraded).

Originally planned as a 13-test × 9-country matrix. Extraction uncovered
two limitations in the 2024-10 dump:
  1. Only 10 of the 13 OONI crawlers appear (facebookmessenger, signal,
     psiphon, httpinvalidrequestline, httpheaderfieldmanipulation,
     whatsapp, telegram, vanillator, torsf, riseupvpn).
  2. The `country_code` edge property is empty in all 11,804 rows
     (crawler produced the data but the property didn't land) — so
     country-level matrix is impossible. Falls back to per-test AS-level
     blocking prevalence.
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


def _read(name):
    p = CACHE / name
    if not p.exists():
        return []
    with open(p, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _to_f(s, default=None):
    try:
        return float(s)
    except (ValueError, TypeError):
        return default


def load():
    as_cc = {}
    for r in _read('as_country.csv'):
        try:
            as_cc[int(r['asn'])] = r['cc']
        except (ValueError, KeyError):
            pass

    by_test = defaultdict(list)
    per_as_blocked = defaultdict(set)  # asn -> set of tests where AS has >50% blocked
    for r in _read('ooni_censored.csv'):
        test = r.get('test', '')
        try:
            asn = int(r['asn'])
        except (ValueError, KeyError):
            continue
        total = _to_f(r.get('total'), 0) or 0
        pct_ok = _to_f(r.get('pct_ok'))
        pct_dns = _to_f(r.get('pct_dns'))
        pct_tcp = _to_f(r.get('pct_tcp'))
        pct_both = _to_f(r.get('pct_both'))
        blocked_pct = None
        if pct_ok is not None:
            blocked_pct = max(0, 100 - pct_ok)
        by_test[test].append({
            'asn': asn, 'total': total, 'blocked': blocked_pct,
            'dns': pct_dns, 'tcp': pct_tcp, 'both': pct_both,
        })
        if blocked_pct is not None and blocked_pct >= 50:
            per_as_blocked[asn].add(test)
    return as_cc, by_test, per_as_blocked


def build():
    import plotly.graph_objects as go

    as_cc, by_test, per_as_blocked = load()
    tests = sorted(by_test.keys(), key=lambda t: -len(by_test[t]))
    print(f'tests observed: {len(tests)}')
    total_pairs = sum(len(v) for v in by_test.values())

    # Per-test coverage + median blocking
    rows = []
    for test in tests:
        data = by_test[test]
        n = len(data)
        valid = [d for d in data if d['blocked'] is not None]
        med_block = sorted([d['blocked'] for d in valid])[len(valid) // 2] \
            if valid else 0
        severe = sum(1 for d in valid if d['blocked'] >= 50)
        rows.append({
            'test': test.replace('OONI ', '').replace(' Test', ''),
            'n_measurements': n, 'n_valid': len(valid),
            'median_blocked': med_block, 'severe_blocking': severe,
            'severe_pct': severe / max(len(valid), 1) * 100,
        })

    # ---- Panel 1: per-test measurement count + severe blocking pct ----
    p1 = go.Figure()
    p1.add_trace(go.Bar(
        y=[r['test'] for r in rows][::-1],
        x=[r['n_measurements'] for r in rows][::-1],
        orientation='h', name='measurements',
        marker_color=COLORS['cyan'],
        text=[str(r['n_measurements']) for r in rows][::-1],
        textposition='outside',
    ))
    p1.update_layout(
        title=f'① OONI 10 项测试覆盖量 · Measurement count per test '
              f'(total {total_pairs:,} AS-test pairs)',
        xaxis=dict(title='# AS measured'),
        height=480, margin=dict(l=220), showlegend=False,
    )

    # ---- Panel 2: severe blocking % per test ----
    p2 = go.Figure()
    srt = sorted(rows, key=lambda r: -r['severe_pct'])
    p2.add_trace(go.Bar(
        x=[r['test'] for r in srt], y=[r['severe_pct'] for r in srt],
        marker_color=[COLORS['red'] if r['severe_pct'] > 5 else COLORS['orange']
                      for r in srt],
        text=[f'{r["severe_pct"]:.1f}%<br>({r["severe_blocking"]}/{r["n_valid"]})'
              for r in srt],
        textposition='outside',
    ))
    p2.update_layout(
        title='② 各测试 severe 阻断占比 · % AS with >50% blocking per test',
        yaxis=dict(title='% of measured AS'),
        xaxis=dict(title='', tickangle=-25),
        height=480, showlegend=False,
    )

    # ---- Panel 3: 9-country per-test measurement distribution ----
    p3 = go.Figure()
    # Use as_cc as best-effort country attribution
    per_cc_test = defaultdict(Counter)
    for test, data in by_test.items():
        for d in data:
            cc = as_cc.get(d['asn'])
            if cc:
                per_cc_test[cc][test] += 1
    z = []
    short_tests = [t.replace('OONI ', '').replace(' Test', '') for t in tests]
    for test in tests:
        row = [per_cc_test[cc].get(test, 0) for cc in TARGET]
        z.append(row)
    p3.add_trace(go.Heatmap(
        z=z, x=TARGET, y=short_tests,
        colorscale=[[0, '#0d1117'], [0.4, COLORS['purple']], [1, COLORS['yellow']]],
        colorbar=dict(title='# AS'),
        text=[[str(v) for v in row] for row in z],
        texttemplate='%{text}', textfont=dict(color=TEXT_PRIMARY, size=10),
    ))
    p3.update_layout(
        title='③ 9 国 AS × 10 测试 · AS-based country attribution '
              '(as_country.csv fallback since OONI cc edge prop was empty)',
        height=560, xaxis=dict(title=''),
    )

    # ---- Panel 4: multi-test blocked AS ("suspicious" Ases) ----
    p4 = go.Figure()
    multi = sorted(per_as_blocked.items(), key=lambda kv: -len(kv[1]))[:20]
    p4.add_trace(go.Bar(
        y=[f'AS{asn} ({as_cc.get(asn, "??")})'
           for asn, _ in multi][::-1],
        x=[len(tests) for _, tests in multi][::-1],
        orientation='h', marker_color=COLORS['red'],
        text=['·'.join(sorted(
            t.replace('OONI ', '').replace(' Test', '')[:14]
            for t in tests)) for _, tests in multi][::-1],
        textposition='outside',
    ))
    p4.update_layout(
        title='④ Top-20 多测试 severe 阻断 AS · ASes blocking on ≥ N tests',
        xaxis=dict(title='# tests with >50% blocking'),
        height=560, margin=dict(l=220), showlegend=False,
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

    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>原计划：</b>13 个 OONI 测试 × 9 国阻断矩阵。'
        f'<i>2024-10 dump 只含 10 个测试，且 CENSORED 边上 '
        f'<code>country_code</code> 属性未写入</i>——测试国家归属从边属性'
        f'（缺失）降级为 AS→Country 反推（Panel ③）。'
        f'<br><b>Scope:</b> {total_pairs:,} AS-测试 pairs · 10 tests · '
        f'2024-10 snapshot.'
        f'</p>'
        f'<p style="margin:4px 16px 12px;padding:10px 14px;'
        f'border-left:3px solid #ff9f0a;background:rgba(255,159,10,0.08);'
        f'color:{TEXT_PRIMARY};font-size:13px;border-radius:4px">'
        f'⚠️ <b>OONI 边属性缺口：</b>'
        f'<code>r.country_code</code> 在所有 11,804 行都是 null。'
        f'Panel ③ 用 AS→Country 映射替代（测试来源 AS 所在国，不等于测试目标国）。'
        f'待 crawler 修复后可升级。</p>'
    )

    banner = (
        '<div class="step-banner">'
        '<h1>OONI 审查测试图谱 · OONI Censorship Tests</h1>'
        '<h2>10-test measurement coverage + severe blocking prevalence · '
        'AS-based country fallback</h2>'
        '</div>'
        '<div class="step-footer">topic 7 · 2024-10 snapshot · OONI × 10 tests</div>'
    )
    out_path = OUT / 'topic7_ooni.html'
    out_path.write_text(
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>OONI 审查测试图谱 · OONI Tests</title>'
        f'{BANNER_CSS}</head><body>'
        f'{banner}<div class="content">{intro}'
        f'{"".join(parts)}</div></body></html>',
        encoding='utf-8',
    )
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')


if __name__ == '__main__':
    build()
