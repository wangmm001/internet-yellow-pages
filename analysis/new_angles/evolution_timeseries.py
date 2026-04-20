"""Aggregate per-snapshot new_angles CSVs into time-series evolution page.

Reads `data_cache/new_angles/<YYYY-MM-DD>/*.csv` for every snapshot that
was extracted (see run_timeseries.sh) and plots "real" 10+-point curves
for:

  1. AS inventory totals (how much of IYP the new_angles extract covers)
  2. Hegemony concentration (top-20 share of incoming dependency)
  3. IXP live membership (total active sessions — from alice-lg)
  4. BGP visibility (v4 vs v6 distinct peer edges from bgpkit)
  5. Archetype mix (Eyeball / Content / Carrier / T1 counts)
  6. RPKI + ROV enforcement (% AS signed, % AS enforcing)
  7. RIR allocation (country count + v4/v6 split) — restored from nro fix
  8. PeeringDB openness (avg info_ratio, policy_general distribution)

Also surfaces which sources are consistently absent (MANRS, PCH, CF DNS)
and which became available mid-series (PeeringDB fixed, LACES lat/lng).

Output: analysis/new_angles/html/evolution_timeseries.html (+ countries
mirror).
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
    apply_plotly_theme, warning_block,
)

REPO = Path(__file__).resolve().parent.parent.parent
CACHE = REPO / 'data_cache' / 'new_angles'
OUT = REPO / 'analysis' / 'new_angles' / 'html'
OUT.mkdir(parents=True, exist_ok=True)


def _read(path):
    if not path.exists() or path.stat().st_size < 5:
        return []
    return list(csv.DictReader(open(path, encoding='utf-8')))


def discover_snapshots():
    """Find YYYY-MM-DD subdirs with at least as_country.csv."""
    out = []
    for d in sorted(CACHE.iterdir()):
        if not d.is_dir():
            continue
        name = d.name
        if not (len(name) == 10 and name[4] == '-' and name[7] == '-'):
            continue
        if (d / 'as_country.csv').exists():
            out.append(name)
    return out


def metrics(snap):
    """Compute all per-snapshot metrics from the cached CSVs."""
    d = CACHE / snap
    m = {'snap': snap}

    # --- 1. Inventory totals ---
    m['n_as'] = len(_read(d / 'as_country.csv'))
    m['n_aws_prefix'] = len(_read(d / 'aws_prefixes.csv'))
    m['n_atlas_probe'] = len(_read(d / 'atlas_probes.csv'))
    m['n_ixp_members'] = len(_read(d / 'ixp_live_members.csv'))
    m['n_rir_prefix'] = len(_read(d / 'nro_country_prefixes.csv'))
    m['n_peeringdb_org'] = len(_read(d / 'peeringdb_orgs.csv'))
    m['n_laces_row'] = len(_read(d / 'laces_geoprefix_countries.csv'))

    # --- 2. Hegemony concentration ---
    hh = _read(d / 'ihr_hegemony_incoming.csv')
    if hh:
        vals = sorted(
            (float(r.get('incoming') or 0) for r in hh), reverse=True,
        )
        tot = sum(vals)
        m['hege_top20_share'] = sum(vals[:20]) / tot * 100 if tot else 0
        m['hege_gini'] = _gini(vals) if tot else 0
    else:
        m['hege_top20_share'] = None
        m['hege_gini'] = None

    # --- 3. IXP active sessions ---
    # alice-lg state field is lowercase: up/down/established/start/active
    ixp = _read(d / 'ixp_live_members.csv')
    m['n_ixp_active'] = sum(
        1 for r in ixp
        if (r.get('state') or '').lower() in {'up', 'established', 'active'}
    )
    m['n_ixp_declared'] = len(ixp)

    # --- 4. BGP visibility (bgpkit v4/v6) ---
    obs = _read(d / 'collector_observations.csv')
    v4 = {r['asn'] for r in obs if r.get('src') == 'bgpkit.as2rel_v4'}
    v6 = {r['asn'] for r in obs if r.get('src') == 'bgpkit.as2rel_v6'}
    m['n_as_v4'] = len(v4)
    m['n_as_v6'] = len(v6)
    m['n_as_dual'] = len(v4 & v6)

    # --- 5. Archetype mix ---
    cat = _read(d / 'as_categorized.csv')
    tag_counts = Counter()
    for r in cat:
        tag = (r.get('tag') or '').strip()
        if tag in {'Eyeball', 'Content', 'Carrier', 'T1'}:
            tag_counts[tag] += 1
    for k in ('Eyeball', 'Content', 'Carrier', 'T1'):
        m[f'arch_{k}'] = tag_counts.get(k, 0)

    # --- 6. RPKI + ROV ---
    rpki = _read(d / 'rpki_per_as.csv')
    if rpki:
        signed = sum(1 for r in rpki
                     if _frac(r, 'rpki', 'total') >= 0.5)
        m['rpki_signed_as'] = signed
        m['rpki_total_as'] = len(rpki)
        m['rpki_pct'] = signed / len(rpki) * 100
    else:
        m['rpki_signed_as'] = 0
        m['rpki_total_as'] = 0
        m['rpki_pct'] = None

    rov = _read(d / 'rovista.csv')
    enforcing = sum(
        1 for r in rov
        if (r.get('label') == 'Validating RPKI ROV'
            and float(r.get('ratio') or 0) >= 0.5)
    )
    m['rov_enforcing'] = enforcing
    m['rov_total'] = len(rov)

    # --- 7. PeeringDB presence ---
    pdb = _read(d / 'peeringdb_orgs.csv')
    m['pdb_open'] = sum(1 for r in pdb if r.get('policy_general') == 'Open')
    m['pdb_selective'] = sum(
        1 for r in pdb if r.get('policy_general') == 'Selective'
    )
    m['pdb_restrictive'] = sum(
        1 for r in pdb if r.get('policy_general') == 'Restrictive'
    )

    # --- 8. Absent-crawler flags ---
    m['has_manrs'] = bool(_read(d / 'manrs.csv'))
    m['has_pch'] = bool(_read(d / 'pch_prefix_collectors.csv'))
    m['has_cf_dns'] = bool(_read(d / 'cf_dns_top_countries.csv'))
    m['has_hyperscaler'] = bool(_read(d / 'hyperscaler_originators.csv'))

    return m


def _frac(row, num, den):
    try:
        n = float(row.get(num) or 0)
        d = float(row.get(den) or 0)
        return n / d if d else 0
    except (TypeError, ValueError):
        return 0


def _gini(values):
    """Gini coefficient of a non-negative value list."""
    vs = sorted(v for v in values if v > 0)
    if not vs:
        return 0
    n = len(vs)
    cum = 0
    for i, v in enumerate(vs, 1):
        cum += i * v
    return (2 * cum) / (n * sum(vs)) - (n + 1) / n


def build():
    import plotly.graph_objects as go
    from plotly.io import to_html

    snaps = discover_snapshots()
    if len(snaps) < 2:
        print(f'only {len(snaps)} snapshot(s) — need 2+ to plot time-series')
        return

    data = [metrics(s) for s in snaps]
    print(f'computed metrics for {len(snaps)} snapshots:')
    for m in data:
        print(f'  {m["snap"]}: AS={m["n_as"]:,}, '
              f'hege_top20={m["hege_top20_share"] or 0:.1f}%, '
              f'IXP active={m["n_ixp_active"]:,}, '
              f'RPKI signed={m["rpki_signed_as"]:,}')

    x = snaps

    # --- P1: inventory totals ---
    p1 = go.Figure()
    for key, label, col in [
        ('n_as', 'AS inventory', COLORS['cyan']),
        ('n_atlas_probe', 'Atlas probes', COLORS['green']),
        ('n_peeringdb_org', 'PeeringDB orgs', COLORS['purple']),
        ('n_ixp_declared', 'IXP declared members', COLORS['orange']),
    ]:
        p1.add_trace(go.Scatter(
            x=x, y=[m[key] for m in data], mode='lines+markers',
            name=label, line=dict(color=col, width=2),
        ))
    p1.update_layout(
        title='① 登记层规模 · Inventory growth · AS / Atlas / PeeringDB / IXP',
        height=440, yaxis=dict(title='# entities'),
    )

    # --- P2: hegemony concentration (top-20 share + gini) ---
    p2 = go.Figure()
    p2.add_trace(go.Scatter(
        x=x, y=[m['hege_top20_share'] for m in data], mode='lines+markers',
        name='Top-20 share of incoming hege (%)',
        line=dict(color=COLORS['red'], width=3),
    ))
    p2.add_trace(go.Scatter(
        x=x, y=[100 * (m['hege_gini'] or 0) for m in data],
        mode='lines+markers', yaxis='y2',
        name='Gini × 100',
        line=dict(color=COLORS['orange'], width=2, dash='dash'),
    ))
    p2.update_layout(
        title='② Hegemony 集中度 · How consolidated is AS dependency?',
        height=460,
        yaxis=dict(title='Top-20 share (%)'),
        yaxis2=dict(title='Gini × 100', overlaying='y', side='right'),
    )

    # --- P3: IXP active vs declared ---
    p3 = go.Figure()
    p3.add_trace(go.Scatter(
        x=x, y=[m['n_ixp_declared'] for m in data], mode='lines+markers',
        name='Declared members (alice-lg)',
        line=dict(color=COLORS['cyan']),
    ))
    p3.add_trace(go.Scatter(
        x=x, y=[m['n_ixp_active'] for m in data], mode='lines+markers',
        name='Active sessions (Established)',
        line=dict(color=COLORS['green']),
    ))
    p3.update_layout(
        title='③ IXP 声称 vs 活跃 · Declared-vs-active gap over time',
        height=440, yaxis=dict(title='# member rows'),
    )

    # --- P4: BGP visibility v4 vs v6 ---
    p4 = go.Figure()
    p4.add_trace(go.Scatter(
        x=x, y=[m['n_as_v4'] for m in data], mode='lines+markers',
        name='v4-visible AS', line=dict(color=COLORS['blue']),
    ))
    p4.add_trace(go.Scatter(
        x=x, y=[m['n_as_v6'] for m in data], mode='lines+markers',
        name='v6-visible AS', line=dict(color=COLORS['purple']),
    ))
    p4.add_trace(go.Scatter(
        x=x, y=[m['n_as_dual'] for m in data], mode='lines+markers',
        name='dual-stack', line=dict(color=COLORS['green']),
    ))
    p4.update_layout(
        title='④ BGP 观测 v4 vs v6 · dual-stack visibility',
        height=460, yaxis=dict(title='# AS'),
    )

    # --- P5: RPKI signed + ROV enforcing ---
    p5 = go.Figure()
    p5.add_trace(go.Scatter(
        x=x, y=[m['rpki_signed_as'] for m in data], mode='lines+markers',
        name='RPKI signed (≥50% prefixes)',
        line=dict(color=COLORS['green']),
    ))
    p5.add_trace(go.Scatter(
        x=x, y=[m['rov_enforcing'] for m in data], mode='lines+markers',
        name='ROV enforcing (≥50%)',
        line=dict(color=COLORS['orange']),
    ))
    p5.update_layout(
        title='⑤ RPKI 签名 vs ROV 执行 · signed-vs-enforced gap',
        height=440, yaxis=dict(title='# AS'),
    )

    # --- P6: Archetype mix ---
    p6 = go.Figure()
    for k, col in [
        ('Eyeball', COLORS['cyan']), ('Content', COLORS['green']),
        ('Carrier', COLORS['orange']), ('T1', COLORS['red']),
    ]:
        p6.add_trace(go.Scatter(
            x=x, y=[m[f'arch_{k}'] for m in data], mode='lines+markers',
            name=k, line=dict(color=col),
        ))
    p6.update_layout(
        title='⑥ Archetype 分布 · Eyeball / Content / Carrier / T1 over time',
        height=440, yaxis=dict(title='# AS'),
    )

    # --- P7: PeeringDB peering policy ---
    p7 = go.Figure()
    for k, col in [
        ('open', COLORS['green']),
        ('selective', COLORS['orange']),
        ('restrictive', COLORS['red']),
    ]:
        p7.add_trace(go.Scatter(
            x=x, y=[m[f'pdb_{k}'] for m in data], mode='lines+markers',
            name=k.capitalize(),
            line=dict(color=col),
        ))
    p7.update_layout(
        title='⑦ PeeringDB 开放度 · peering policy distribution '
              '(Open / Selective / Restrictive)',
        height=440, yaxis=dict(title='# orgs'),
    )

    # --- P8: crawler availability heatmap ---
    p8 = go.Figure()
    crawlers = ['has_manrs', 'has_pch', 'has_cf_dns', 'has_hyperscaler']
    labels = ['MANRS', 'PCH', 'CF DNS', 'Hyperscaler']
    z = [[1 if m[k] else 0 for m in data] for k in crawlers]
    p8.add_trace(go.Heatmap(
        z=z, x=x, y=labels,
        colorscale=[[0, COLORS['red']], [1, COLORS['green']]],
        text=[['✓' if v else '✗' for v in row] for row in z],
        texttemplate='%{text}', showscale=False,
    ))
    p8.update_layout(
        title='⑧ Crawler 可用性 · which sources populated per snapshot',
        height=280,
    )

    figs = [p1, p2, p3, p4, p5, p6, p7, p8]
    for f in figs:
        apply_plotly_theme(f)

    parts = []
    first = True
    for f in figs:
        parts.append(to_html(
            f, include_plotlyjs=('inline' if first else False),
            full_html=False, default_height='460px'))
        first = False

    # Intro
    latest = data[-1]
    earliest = data[0]
    delta_as = latest['n_as'] - earliest['n_as']
    delta_rpki = latest['rpki_signed_as'] - earliest['rpki_signed_as']
    intro = (
        f'<p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px">'
        f'<b>范围：</b>对 <b>{len(snaps)}</b> 个季度快照'
        f'（{earliest["snap"]} → {latest["snap"]}）'
        f'每个 dump 重新装载 Neo4j 后，以 <code>extract_data.py</code> '
        f'（修正过 schema 后）重新抽取全部 26 张 CSV。'
        f'<br><b>范围增长：</b>登记 AS '
        f'{earliest["n_as"]:,} → {latest["n_as"]:,} '
        f'(Δ {delta_as:+,}); RPKI 签名 AS '
        f'{earliest["rpki_signed_as"]:,} → {latest["rpki_signed_as"]:,} '
        f'(Δ {delta_rpki:+,}).'
        f'<br><b>全新：</b>以前 evolution 页只画 BGP 层；本页加上 hegemony 集中度、'
        f'IXP 活跃/声称差、v4/v6 平衡、ROV 执行、archetype 演化、'
        f'PeeringDB 开放度——都是前面坦承过的"冻结层"，'
        f'如今有 {len(snaps)} 个真实点。'
        f'</p>'
    )
    # Classify each crawler: never | always | regressed | new
    crawler_status = {}
    for k, lab in [('has_manrs', 'MANRS'), ('has_pch', 'PCH'),
                   ('has_cf_dns', 'CF DNS'),
                   ('has_hyperscaler', 'hyperscaler')]:
        present = [m['snap'] for m in data if m[k]]
        absent = [m['snap'] for m in data if not m[k]]
        if not present:
            crawler_status[lab] = ('never', absent)
        elif not absent:
            crawler_status[lab] = ('always', present)
        elif present == [m['snap'] for m in data[-len(present):]]:
            crawler_status[lab] = ('new', present)
        elif absent == [m['snap'] for m in data[-len(absent):]]:
            crawler_status[lab] = ('regressed', absent)
        else:
            crawler_status[lab] = ('spotty', absent)

    lines = []
    for lab, (status, snaps_) in crawler_status.items():
        if status == 'never':
            lines.append(f'<b>{lab}</b>：全 11 季度从未填充（建议: '
                         f'crawler 从未正常运行）')
        elif status == 'regressed':
            lines.append(f'<b>{lab}</b>：{snaps_[0]} 起连续 '
                         f'{len(snaps_)} 个季度缺失——pipeline 回归')
        elif status == 'new':
            lines.append(f'<b>{lab}</b>：{snaps_[0]} 首次出现，'
                         f'近 {len(snaps_)} 季度可用——新上线')
        elif status == 'spotty':
            lines.append(f'<b>{lab}</b>：{len(snaps_)} 个季度间歇性缺失 '
                         f'({", ".join(snaps_)})')
    if lines:
        intro += warning_block(
            '<br>'.join(lines) + '。完整可用性热图见 Panel ⑧。',
            title='Crawler 可用性分类 · Source availability classification',
        )

    banner = (
        '<div class="step-banner">'
        '<h1>10 季度时序 · Real Quarterly Evolution</h1>'
        '<h2>Hegemony · IXP reality · BGP v4/v6 · ROV · Archetype · '
        'PeeringDB · Crawler availability</h2>'
        '</div><div class="step-footer">evolution_timeseries · '
        'rebuilt from per-snapshot data_cache/new_angles/'
        '&lt;YYYY-MM-DD&gt;/</div>'
    )
    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>10 季度时序 · Real Quarterly Evolution</title>'
        f'{BANNER_CSS}</head><body>{banner}'
        f'<div class="content">{intro}{"".join(parts)}</div></body></html>'
    )
    out_path = OUT / 'evolution_timeseries.html'
    out_path.write_text(html, encoding='utf-8')
    mirror = REPO / 'analysis' / 'countries' / 'html' / 'evolution_timeseries.html'
    mirror.write_text(html, encoding='utf-8')

    # Also write metrics JSON for provenance
    metrics_path = REPO / 'analysis' / 'new_angles' / 'data' \
        / 'evolution_timeseries_metrics.json'
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(
        json.dumps({'snaps': snaps, 'data': data}, indent=2, default=str),
        encoding='utf-8',
    )

    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')
    print(f'wrote {mirror}')
    print(f'wrote {metrics_path}')


if __name__ == '__main__':
    build()
