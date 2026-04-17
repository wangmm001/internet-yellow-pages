"""Orchestrator for cross-country + time-series analysis.

Usage:
  python3 -m analysis.countries.run_all --snapshot 2026-04
  python3 -m analysis.countries.run_all --snapshot 2026-04 --countries US,CN,JP
  python3 -m analysis.countries.run_all --verify
  python3 -m analysis.countries.run_all --report   # regenerate index.html + README
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.countries.common import (  # noqa: E402
    BANNER_CSS, COLORS, DARK_BG, DARK_BORDER, DARK_PANEL, DATA_DIR, HTML_DIR,
    TARGET_COUNTRIES, TEXT_PRIMARY, TEXT_SECONDARY, bilingual,
    list_countries_in_snapshot, list_snapshots, read_country_metrics, zh,
)


def run_one(country, snapshot):
    from analysis.countries.country_pipeline import build_profile
    from analysis.countries.step_lib import run_all_for_country
    results = run_all_for_country(country, snapshot)
    build_profile(country, snapshot, results)
    return results


def run_all(countries, snapshot):
    for cc in countries:
        print(f'\n=== {cc} / {snapshot} ===')
        run_one(cc, snapshot)


def verify(snapshot=None):
    snapshots = [snapshot] if snapshot else list_snapshots()
    print(f'{"Country":<8} {"Snapshot":<12} {"Steps OK":<10} {"Sovereignty":<14} {"Profile HTML":<20}')
    print('-' * 80)
    for snap in snapshots:
        for cc in list_countries_in_snapshot(snap):
            ok = 0
            for n in range(1, 21):
                m = read_country_metrics(snap, cc, n)
                if m and not (m.get('metrics') or {}).get('_error'):
                    ok += 1
            sov_meta = read_country_metrics(snap, cc, 20) or {}
            sov = (sov_meta.get('metrics') or {}).get(
                'composite_sovereignty_index', '—')
            html_path = os.path.join(HTML_DIR, f'profile_{cc}.html')
            html_ok = 'OK' if os.path.exists(html_path) else 'MISS'
            size_kb = (os.path.getsize(html_path) // 1024) if os.path.exists(html_path) else 0
            print(f'{cc:<8} {snap:<12} {ok:>2}/20      '
                  f'{str(sov):<14} {html_ok}({size_kb} KB)')


def build_index():
    """Master navigation page listing all snapshots/countries + dashboard links."""
    snaps = list_snapshots()
    tiles_per_snap = []
    for snap in snaps:
        rows = ''
        for cc in list_countries_in_snapshot(snap):
            z = zh(cc)
            sov_meta = read_country_metrics(snap, cc, 20) or {}
            sov = (sov_meta.get('metrics') or {}).get(
                'composite_sovereignty_index', '—')
            sov_str = f'{sov:.3f}' if isinstance(sov, float) else str(sov)
            html_rel = f'profile_{cc}.html'
            html_path = os.path.join(HTML_DIR, html_rel)
            if os.path.exists(html_path):
                rows += (
                    f'<li><a href="{html_rel}">'
                    f'<span class="cc">{cc}</span> <b>{z}</b>'
                    f'<span class="sov">主权 {sov_str}</span></a></li>'
                )
        tiles_per_snap.append((snap, rows))

    dashes = []
    for filename, title in [
        ('cross_country.html', '跨国对比 · Cross-Country Dashboard (2026-04)'),
        ('evolution.html', '时序演化 · Time-Series Evolution (2025→2026)'),
        ('dependency_matrix.html', '跨国依赖矩阵 · Dependency Matrix'),
        ('content_geography.html', '内容地理 · Content Geography'),
    ]:
        path = os.path.join(HTML_DIR, filename)
        if os.path.exists(path):
            size = os.path.getsize(path) // 1024
            dashes.append(f'<li><a href="{filename}">{title}</a> '
                          f'<span style="color:#8B949E">({size} KB)</span></li>')

    tile_html = ''
    for snap, rows in tiles_per_snap:
        tile_html += f'<h3 class="phase">快照 {snap} · Country Profiles</h3><ul class="grid">{rows}</ul>'

    html = f'''<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>九国互联网分层 · 跨国+时序综合分析</title>
{BANNER_CSS}
<style>
  .headline {{ background:{DARK_PANEL}; padding:32px 28px 20px;
               border-bottom:2px solid {COLORS['red']}; }}
  .headline h1 {{ margin:0 0 4px 0; color:{TEXT_PRIMARY}; font-size:26px; }}
  .headline h2 {{ margin:0; color:{TEXT_SECONDARY}; font-size:15px; font-weight:400; }}
  .phase {{ color:{COLORS['cyan']}; margin-top:22px; padding-bottom:4px;
            border-bottom:1px solid {DARK_BORDER}; font-size:16px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr));
           gap:8px; list-style:none; padding:0; margin:10px 0; }}
  .grid li a {{ display:block; background:{DARK_PANEL}; padding:14px;
                border:1px solid {DARK_BORDER}; border-left:4px solid {COLORS['red']};
                border-radius:6px; color:{TEXT_PRIMARY}; text-decoration:none;
                font-size:14px; }}
  .grid li a:hover {{ border-left-color:{COLORS['cyan']}; background:#1a2028; }}
  .cc {{ display:inline-block; color:{COLORS['cyan']}; font-weight:700;
         min-width:34px; }}
  .sov {{ float:right; color:{COLORS['yellow']}; font-size:11px; }}
  ul.dash {{ list-style:none; padding:0; }}
  ul.dash li {{ margin:6px 0; padding:10px 16px; background:{DARK_PANEL};
                border:1px solid {DARK_BORDER}; border-left:4px solid {COLORS['cyan']};
                border-radius:6px; }}
  ul.dash a {{ color:{TEXT_PRIMARY}; text-decoration:none; font-weight:500; }}
</style></head><body>
<div class="headline">
<h1>九国互联网分层 · 跨国对比与时序演化</h1>
<h2>Nine-Country Internet Hierarchy · Cross-Country + Time-Series Analysis</h2>
</div>
<div class="content">

<h3 class="phase">综合仪表板 · Synthesis Dashboards</h3>
<ul class="dash">
{''.join(dashes) or '<li style="color:#8B949E">(dashboards not yet generated)</li>'}
</ul>

{tile_html}

<div class="step-footer">
基于 Internet Yellow Pages (IYP) Neo4j 知识图谱 ·
  对比国家：US / CN / JP / IN / DE / GB / FR / NL / RU · 20 指标 × 2 快照<br>
Based on the IYP Neo4j knowledge graph · 9 countries × 20 metrics × 2 snapshots
</div>

</div></body></html>'''
    path = os.path.join(HTML_DIR, 'index.html')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'[index] wrote {path} ({os.path.getsize(path) // 1024} KB)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--snapshot', default='2026-04')
    ap.add_argument('--countries', default=','.join(TARGET_COUNTRIES))
    ap.add_argument('--verify', action='store_true')
    ap.add_argument('--report', action='store_true')
    args = ap.parse_args()

    if args.verify:
        verify()
        return
    if args.report:
        build_index()
        return

    ccs = [c.strip() for c in args.countries.split(',') if c.strip()]
    run_all(ccs, args.snapshot)
    build_index()


if __name__ == '__main__':
    main()
