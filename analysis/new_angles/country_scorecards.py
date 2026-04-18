"""9-country × multi-metric comparison scorecard.

Cross-joins all cached CSVs to produce one compact comparison matrix
distilling each of the 15 new-angle topics into 1-3 per-country numbers.
Offline; rebuilds in seconds.

Output: analysis/new_angles/html/country_scorecards.html
"""
import csv
import json
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
METRICS = REPO / 'analysis' / 'countries' / 'data' / '2026-04'
OUT = REPO / 'analysis' / 'new_angles' / 'html'
OUT.mkdir(parents=True, exist_ok=True)

TARGET = ['US', 'CN', 'JP', 'IN', 'DE', 'GB', 'FR', 'NL', 'RU']
COUNTRY_NAME = {
    'US': '美国', 'CN': '中国', 'JP': '日本', 'IN': '印度', 'DE': '德国',
    'GB': '英国', 'FR': '法国', 'NL': '荷兰', 'RU': '俄罗斯',
}
POP = {
    'US': 336_810_000, 'CN': 1_410_710_000, 'JP': 123_750_000,
    'IN': 1_428_630_000, 'DE': 84_480_000, 'GB': 68_350_000,
    'FR': 68_170_000, 'NL': 17_880_000, 'RU': 143_830_000,
}


def _read(p):
    return list(csv.DictReader(open(p, encoding='utf-8'))) \
        if p.exists() else []


def _int(s, d=0):
    try: return int(s)
    except: return d


def _float(s, d=0.0):
    try: return float(s)
    except: return d


def compute():
    scorecards = {cc: {} for cc in TARGET}

    # T1 + existing sovereignty
    as_cc = {_int(r['asn']): r['cc'] for r in _read(CACHE / 'as_country.csv')}
    country_as = Counter(as_cc.values())
    eyeball = defaultdict(set)
    for r in _read(CACHE / 'eyeball_as_country.csv'):
        try: eyeball[r['cc']].add(int(r['asn']))
        except: pass
    for cc in TARGET:
        n_as = country_as.get(cc, 0)
        n_eye = len(eyeball.get(cc, set()))
        scorecards[cc]['n_as'] = n_as
        scorecards[cc]['n_eyeball'] = n_eye
        scorecards[cc]['eyeball_pct'] = n_eye / max(n_as, 1) * 100
        scorecards[cc]['as_per_m'] = n_as / (POP.get(cc, 1) / 1e6)
        # Sovereignty index from step20
        p = METRICS / cc / 'step20_metrics.json'
        if p.exists():
            m = json.loads(p.read_text()).get('metrics') or {}
            scorecards[cc]['sov'] = m.get('composite_sovereignty_index')
            scorecards[cc]['sov_components'] = m.get('components', {})

    # T1.5: k-core distortion (CN-focus but compute for all)
    coreness = {}
    for r in _read(COMPLEX / 'step08_coreness.csv'):
        coreness[_int(r['asn'])] = _int(r['coreness'])
    for cc in TARGET:
        country_set = {a for a, c in as_cc.items() if c == cc}
        eye_sub = eyeball.get(cc, set()) & country_set
        d_infra = sum(1 for a in country_set if coreness.get(a, 0) >= 30) \
            / max(len(country_set), 1) * 100
        d_user = sum(1 for a in eye_sub if coreness.get(a, 0) >= 30) \
            / max(len(eye_sub), 1) * 100
        scorecards[cc]['kcore_infra'] = d_infra
        scorecards[cc]['kcore_user'] = d_user

    # T1.6: IXP domestic membership (user-view)
    ixp_cc = defaultdict(set)
    for r in _read(COMPLEX / 'as_ixp_membership.csv'):
        try:
            asn = int(r['asn'])
            for c in (r.get('ixp_countries') or '').split(';'):
                c = c.strip()
                if c: ixp_cc[asn].add(c)
        except: pass
    for cc in TARGET:
        country_set = {a for a, c in as_cc.items() if c == cc}
        eye_sub = eyeball.get(cc, set()) & country_set
        dom_user = sum(1 for a in eye_sub if cc in ixp_cc.get(a, set())) \
            / max(len(eye_sub), 1) * 100
        scorecards[cc]['ixp_local_user'] = dom_user

    # T2: RPKI × ROVISTA per-country
    rpki = {}
    for r in _read(CACHE / 'rpki_per_as.csv'):
        try:
            asn = int(r['asn']); tot = int(r['total']); val = int(r['rpki'])
            if tot > 0: rpki[asn] = val / tot * 100
        except: pass
    rov = {}
    for r in _read(CACHE / 'rovista.csv'):
        try:
            asn = int(r['asn']); raw = r.get('ratio') or ''
            if raw.strip(): rov[asn] = float(raw)
        except: pass
    for cc in TARGET:
        country_set = {a for a, c in as_cc.items() if c == cc}
        joined = [a for a in country_set if a in rpki and a in rov]
        signed = [a for a in joined if rpki[a] >= 50]
        gap = [a for a in signed if rov[a] < 0.5]
        mean_rpki = sum(rpki[a] for a in joined) / max(len(joined), 1)
        mean_rov = sum(rov[a] for a in joined) / max(len(joined), 1) * 100
        scorecards[cc]['rpki_mean'] = mean_rpki
        scorecards[cc]['rov_mean'] = mean_rov
        scorecards[cc]['gap_rate'] = len(gap) / max(len(signed), 1) * 100 \
            if signed else 0

    # T4: Stanford ASDB — dominant category
    # T5: archetype
    # T6: bgptools.tags — behavioral tag counts
    top_tags = defaultdict(Counter)    # cc -> tag count
    archetype = defaultdict(Counter)   # cc -> Carrier/Content/Eyeball
    asdb_cats = defaultdict(Counter)   # cc -> Stanford cat
    for r in _read(CACHE / 'as_categorized.csv'):
        try:
            asn = int(r['asn']); tag = r.get('tag', ''); src = r.get('source', '')
            cc = as_cc.get(asn)
            if not cc or cc not in TARGET: continue
            if src == 'bgptools.tags':
                top_tags[cc][tag] += 1
            elif src == 'bgptools.as_names':
                archetype[cc][tag] += 1
            elif src == 'stanford.asdb' and r.get('layer') == '1':
                asdb_cats[cc][tag] += 1
        except: pass
    for cc in TARGET:
        if asdb_cats[cc]:
            name, n = asdb_cats[cc].most_common(1)[0]
            scorecards[cc]['asdb_top'] = name[:30]
        scorecards[cc]['content_as'] = archetype[cc].get('Content', 0)
        scorecards[cc]['eyeball_arch'] = archetype[cc].get('Eyeball', 0)
        scorecards[cc]['crit_infra'] = top_tags[cc].get('Internet Critical Infra', 0)
        scorecards[cc]['tor'] = top_tags[cc].get('ToR Services', 0)

    # T12: top hegemony AS per country
    ihr = []
    for r in _read(CACHE / 'ihr_hegemony_incoming.csv'):
        try:
            asn = int(r['asn']); inc = float(r.get('incoming') or 0)
            ihr.append((asn, inc))
        except: pass
    ihr.sort(key=lambda t: -t[1])
    for cc in TARGET:
        top_in_cc = next(((a, i) for a, i in ihr
                         if as_cc.get(a) == cc), None)
        if top_in_cc:
            scorecards[cc]['top_hege_as'] = top_in_cc[0]
            scorecards[cc]['top_hege_inc'] = top_in_cc[1]
        # Count how many in top-100
        scorecards[cc]['in_top100'] = sum(1 for a, _ in ihr[:100]
                                           if as_cc.get(a) == cc)

    # T15: net dep balance in 9×9
    matrix = defaultdict(float)
    for r in _read(COMPLEX / 'as_dependency.csv'):
        try:
            s = as_cc.get(int(r['src']))
            d = as_cc.get(int(r['dst']))
            h = float(r.get('hege') or 0)
            if s in TARGET and d in TARGET:
                matrix[(s, d)] += h
        except: pass
    for cc in TARGET:
        inn = sum(matrix.get((s, cc), 0) for s in TARGET if s != cc)
        out = sum(matrix.get((cc, d), 0) for d in TARGET if d != cc)
        scorecards[cc]['net_dep'] = inn - out
        scorecards[cc]['dep_in'] = inn
        scorecards[cc]['dep_out'] = out

    # T13: multinational footprint — inbound presence + outbound span
    org_asns = defaultdict(list)
    for r in _read(COMPLEX / 'as_organization.csv'):
        try: org_asns[r['org_name']].append(int(r['asn']))
        except: pass
    inbound_multi = Counter(); outbound_multi = Counter()
    for org, asns in org_asns.items():
        ccs = Counter(as_cc.get(a) for a in asns if as_cc.get(a))
        if len(ccs) > 1:
            hq = ccs.most_common(1)[0][0]
            for c in ccs:
                if c and c != hq: inbound_multi[c] += 1
            outbound_multi[hq] += len(ccs) - 1
    for cc in TARGET:
        scorecards[cc]['multi_in'] = inbound_multi.get(cc, 0)
        scorecards[cc]['multi_out'] = outbound_multi.get(cc, 0)

    # T9: Atlas probe count
    atlas_cc = Counter()
    for r in _read(CACHE / 'atlas_probes.csv'):
        cc = r.get('cc') or ''
        if cc: atlas_cc[cc] += 1
    for cc in TARGET:
        scorecards[cc]['atlas_n'] = atlas_cc.get(cc, 0)
        scorecards[cc]['atlas_per_m'] = atlas_cc.get(cc, 0) / (POP.get(cc, 1) / 1e6)

    return scorecards


def _rank_in(values):
    """Return dict[cc] = rank (1=best/highest)."""
    sr = sorted(values.items(), key=lambda kv: -kv[1])
    return {c: i + 1 for i, (c, _) in enumerate(sr)}


def build():
    import plotly.graph_objects as go
    sc = compute()

    # ---- Comparison heatmap: 12 rows × 9 cols ----
    METRICS_TABLE = [
        ('AS 数', 'n_as', lambda x: f'{x:,}', True),
        ('Eyeball AS', 'n_eyeball', lambda x: f'{x}', True),
        ('Eyeball %', 'eyeball_pct', lambda x: f'{x:.1f}%', True),
        ('AS / 百万人', 'as_per_m', lambda x: f'{x:.1f}', True),
        ('主权指数', 'sov', lambda x: f'{x:.3f}' if x else '—', True),
        ('K-core user%', 'kcore_user', lambda x: f'{x:.1f}%', True),
        ('IXP 本地 user%', 'ixp_local_user', lambda x: f'{x:.1f}%', True),
        ('RPKI 平均%', 'rpki_mean', lambda x: f'{x:.1f}%', True),
        ('ROV 平均%', 'rov_mean', lambda x: f'{x:.1f}%', True),
        ('签了不执行%', 'gap_rate', lambda x: f'{x:.0f}%', False),
        ('Content AS', 'content_as', lambda x: f'{x}', True),
        ('Critical Infra', 'crit_infra', lambda x: f'{x}', True),
        ('ToR AS', 'tor', lambda x: f'{x}', None),
        ('Atlas 探针', 'atlas_n', lambda x: f'{x:,}', True),
        ('Atlas 密度', 'atlas_per_m', lambda x: f'{x:.2f}', True),
        ('全球 Top-100 AS', 'in_top100', lambda x: f'{x}', True),
        ('跨国 in/out', 'multi_in',
         lambda x: '', True),  # special row
        ('净依赖平衡', 'net_dep', lambda x: f'{x:+.0f}', True),
    ]

    # Build heatmap z-values (per-row min-max normalized)
    z, text, y_labels = [], [], []
    for label, key, fmt, higher_better in METRICS_TABLE:
        if higher_better is None:  # skip rows where direction is ambiguous
            # still include for display but don't colorize
            vals = [sc[cc].get(key, 0) for cc in TARGET]
            text.append([fmt(v) if v is not None else '—' for v in vals])
            z.append([0] * len(TARGET))  # neutral gray
            y_labels.append(label)
            continue
        if label == '跨国 in/out':
            vals_text = [f'{sc[cc].get("multi_in", 0)}/{sc[cc].get("multi_out", 0)}'
                         for cc in TARGET]
            text.append(vals_text)
            z.append([sc[cc].get('multi_in', 0) + sc[cc].get('multi_out', 0)
                      for cc in TARGET])
            y_labels.append(label)
            continue
        vals = [sc[cc].get(key) or 0 for cc in TARGET]
        mn, mx = min(vals), max(vals)
        rng = mx - mn or 1
        if higher_better:
            z_row = [(v - mn) / rng for v in vals]
        else:
            z_row = [(mx - v) / rng for v in vals]
        z.append(z_row)
        text.append([fmt(v) for v in vals])
        y_labels.append(label)

    p1 = go.Figure(data=go.Heatmap(
        z=z, x=[f'{COUNTRY_NAME[c]}<br>{c}' for c in TARGET],
        y=y_labels,
        colorscale=[[0, '#2d1b1b'], [0.5, DARK_PANEL], [1, '#143b2a']],
        showscale=False,
        text=text, texttemplate='%{text}',
        textfont=dict(color=TEXT_PRIMARY, size=12),
        hovertemplate='%{y} · %{x}<br>%{text}<extra></extra>',
    ))
    p1.update_layout(
        title='9 国 × 新角度综合 scorecard · 每行色阶按该行方向归一化 '
              '（深绿=相对优 · 深红=相对弱）',
        xaxis=dict(side='top'),
        yaxis=dict(autorange='reversed'),
        height=720, margin=dict(l=180),
    )
    apply_plotly_theme(p1)
    from plotly.io import to_html
    heatmap_html = to_html(p1, include_plotlyjs='inline',
                            full_html=False, default_height='720px')

    # ---- Per-country cards ----
    def fmt(v, spec):
        if v is None: return '—'
        try: return format(v, spec)
        except (TypeError, ValueError): return str(v)

    def card_for(cc):
        s = sc[cc]
        comp = s.get('sov_components', {}) or {}
        return f"""
        <div style="flex:1;min-width:320px;max-width:420px;
                    background:{DARK_PANEL};border:1px solid {DARK_BORDER};
                    border-top:3px solid {country_color(cc)};
                    border-radius:8px;padding:16px;margin:8px">
          <div style="display:flex;justify-content:space-between;align-items:baseline">
            <div style="font-size:20px;color:{TEXT_PRIMARY};font-weight:600">
              {COUNTRY_NAME[cc]} {cc}
            </div>
            <div style="font-size:14px;color:{TEXT_SECONDARY}">
              {fmt(s.get('n_as'), ',')} AS · {fmt(s.get('n_eyeball'), 'd')} eyeball
            </div>
          </div>
          <div style="margin-top:10px;font-size:13px;line-height:1.7;color:{TEXT_PRIMARY}">
            <b>主权指数</b>: {fmt(s.get('sov'), '.3f')}
            {'<br>hosting ' + fmt(comp.get('hosting_sovereignty', 0), '.2f') + ' · dns ' + fmt(comp.get('dns_sovereignty', 0), '.2f') + ' · rpki ' + fmt(comp.get('rpki_adoption', 0), '.2f') + ' · ixp ' + fmt(comp.get('ixp_domesticization', 0), '.2f') + ' · hub ' + fmt(comp.get('hub_ratio', 0), '.2f') if comp else ''}
            <br><b>用户视角 k-core</b>: {fmt(s.get('kcore_user'), '.1f')}%
            (vs {fmt(s.get('kcore_infra'), '.2f')}% infra)
            <br><b>IXP 本地 user</b>: {fmt(s.get('ixp_local_user'), '.1f')}%
            <br><b>RPKI / ROV</b>: {fmt(s.get('rpki_mean'), '.1f')}% /
            {fmt(s.get('rov_mean'), '.1f')}% · gap
            {fmt(s.get('gap_rate'), '.0f')}%
            <br><b>Archetype</b>: {fmt(s.get('eyeball_arch'), 'd')} Eyeball ·
            {fmt(s.get('content_as'), 'd')} Content
            <br><b>Critical / ToR</b>: {fmt(s.get('crit_infra'), 'd')} /
            {fmt(s.get('tor'), 'd')}
            <br><b>全球 Top-100 AS</b>: {fmt(s.get('in_top100'), 'd')}
            <br><b>多国组织 in/out</b>: {fmt(s.get('multi_in'), 'd')} /
            {fmt(s.get('multi_out'), 'd')}
            <br><b>净依赖平衡</b>: <span style="color:{COLORS['red'] if s.get('net_dep', 0) < 0 else COLORS['green']};font-weight:600">
            {fmt(s.get('net_dep'), '+,.0f')}</span>
            ({fmt(s.get('dep_in'), '.0f')} in / {fmt(s.get('dep_out'), '.0f')} out)
            <br><b>Atlas</b>: {fmt(s.get('atlas_n'), ',')}
            (密度 {fmt(s.get('atlas_per_m'), '.2f')}/百万)
            <br><b>主要 ASDB</b>: {s.get('asdb_top', '—')}
          </div>
        </div>"""

    cards = ''.join(card_for(cc) for cc in TARGET)

    # Ranking summary — top-1 per metric
    def rank_cell(metric_key, higher=True):
        vals = {cc: sc[cc].get(metric_key) for cc in TARGET
                if sc[cc].get(metric_key) is not None}
        if not vals: return '—'
        srt = sorted(vals.items(), key=lambda kv: -kv[1] if higher else kv[1])
        return ' > '.join(f'<span style="color:{country_color(c)}">{c}</span>'
                          for c, _ in srt[:3])

    top3_lines = '<br>'.join([
        f'<b>eyeball% 最高</b>: {rank_cell("eyeball_pct")}',
        f'<b>AS 密度 最高</b>: {rank_cell("as_per_m")}',
        f'<b>用户视角 k-core 最高</b>: {rank_cell("kcore_user")}',
        f'<b>IXP 本地 user 最高</b>: {rank_cell("ixp_local_user")}',
        f'<b>RPKI 平均最高</b>: {rank_cell("rpki_mean")}',
        f'<b>ROV 平均最高</b>: {rank_cell("rov_mean")}',
        f'<b>"签了不执行"最严重</b>: {rank_cell("gap_rate")}',
        f'<b>Content AS 最多</b>: {rank_cell("content_as")}',
        f'<b>Critical Infra AS 最多</b>: {rank_cell("crit_infra")}',
        f'<b>全球 Top-100 占位最多</b>: {rank_cell("in_top100")}',
        f'<b>跨国 org 总出入向</b>: {rank_cell("multi_in")}',
        f'<b>净依赖平衡最强</b>: {rank_cell("net_dep")}',
        f'<b>Atlas 密度最高</b>: {rank_cell("atlas_per_m")}',
    ])

    banner = (
        '<div class="step-banner">'
        '<h1>9 国 × 新角度综合 · 9-Country Scorecard</h1>'
        '<h2>15 topics distilled into a per-country comparison matrix</h2>'
        '</div>'
        '<div class="step-footer">scorecard · offline · reads data_cache + '
        'analysis/countries/data/2026-04</div>'
    )

    body = f"""
    {banner}
    <div class="content">
    <p style="color:{TEXT_SECONDARY};padding:0 16px;font-size:14px;line-height:1.7">
    每行 color-coded 按方向归一化：深绿 = 相对强 · 深红 = 相对弱
    · 中性灰 = 方向性模糊的指标（ToR）。hover 看每格数字。
    </p>
    <p style="background:{DARK_PANEL};padding:14px 18px;margin:8px 16px;
               border-left:3px solid {COLORS['cyan']};border-radius:4px;
               color:{TEXT_PRIMARY};font-size:13px;line-height:1.8">
    <b>Top-3 每项排名速览：</b><br>{top3_lines}
    </p>
    {heatmap_html}
    <h2 style="color:{TEXT_PRIMARY};margin-top:24px">每国详细卡片 · Per-country details</h2>
    <div style="display:flex;flex-wrap:wrap;margin:0 -8px">
    {cards}
    </div>
    </div>
    """

    out_path = OUT / 'country_scorecards.html'
    out_path.write_text(
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<title>9 国综合 scorecard · Country Scorecards</title>'
        f'{BANNER_CSS}</head><body>{body}</body></html>',
        encoding='utf-8',
    )
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')


if __name__ == '__main__':
    build()
