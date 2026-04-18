'''Static generator for the unified IYP analysis site.

Reads navigation metadata from ``analysis/web/nav.py``, renders Jinja2 templates,
copies static assets, and writes a self-contained site under
``analysis/web/site/``.

Every iframe source and PNG reference is verified to exist on disk before the
page that references it is written; the build fails loudly if an upstream
artefact was renamed or removed.

Usage::

    python3 -m analysis.web.build          # full rebuild
    python3 -m analysis.web.build --dry    # list intended outputs, no writes
'''
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape

from analysis.web import nav
from analysis.web import explainers

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / 'templates'
STATIC = HERE / 'static'
SITE = HERE / 'site'
REPO_ROOT = HERE.parent.parent

PHASE_VARIANTS = {
    # china phase → css variant
    'A': '', 'B': 'is-red', 'C': 'is-purple',
    'D': 'is-green', 'E': '', 'F': 'is-red',
    # network group → css variant
    'α': 'is-green', 'β': 'is-purple', 'γ': 'is-red',
    # countries
    'profiles': '', 'dashboards': 'is-purple',
}

TRACK_BADGES = {
    'china': 'is-red',
    'countries': '',
    'network': 'is-green',
}


def _assets_prefix(out_path: Path) -> str:
    depth = len(out_path.relative_to(SITE).parts) - 1
    return '../' * depth


def _sha1(path: Path) -> str:
    h = hashlib.sha1()
    try:
        with path.open('rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
    except FileNotFoundError:
        return 'MISSING'
    return h.hexdigest()[:12]


def _resolve_src(out_path: Path, rel_src: str) -> Path:
    return (out_path.parent / rel_src).resolve()


def _country_delta_strip(page: nav.Page) -> list[dict]:
    ctx = page.extra
    strip: list[dict] = []

    # Sovereignty index
    sov_now = ctx.get('sov_now')
    sov_prev = ctx.get('sov_prev')
    if sov_now is not None:
        row = {
            'label_zh': '主权指数',
            'label_en': 'Sovereignty idx',
            'value': f'{sov_now:.3f}',
        }
        if sov_prev is not None:
            delta = sov_now - sov_prev
            row['delta'] = f'Δ {delta:+.3f} vs {nav.SNAPSHOT_PREV}'
            row['delta_cls'] = 'up' if delta > 0 else ('down' if delta < 0 else '')
        strip.append(row)

    # Total ASes
    tot_now = ctx.get('tot_now')
    tot_prev = ctx.get('tot_prev')
    if tot_now is not None:
        row = {
            'label_zh': 'AS 数',
            'label_en': 'Total ASes',
            'value': f'{tot_now:,}',
        }
        if tot_prev is not None:
            delta = tot_now - tot_prev
            row['delta'] = f'Δ {delta:+,} vs {nav.SNAPSHOT_PREV}'
            row['delta_cls'] = 'up' if delta > 0 else ('down' if delta < 0 else '')
        strip.append(row)

    # Snapshot label chip
    strip.append({
        'label_zh': '快照',
        'label_en': 'Snapshot',
        'value': nav.SNAPSHOT_LATEST,
        'hint': f'prior {nav.SNAPSHOT_PREV}',
    })

    # Region tag (cc)
    strip.append({
        'label_zh': '国家代码',
        'label_en': 'ISO',
        'value': ctx.get('cc', ''),
        'hint': ctx.get('country_en', ''),
    })

    return strip


_HREF_RE = re.compile(r'''<a\s[^>]*href=["']([^"']+)["']''', re.IGNORECASE)


def _scan_site_links(site_root: Path) -> list[dict]:
    '''Walk every rendered HTML under site_root and return broken local links.

    Skips: external URLs, fragments, mailto:, tel:, javascript:, data: URIs.
    For directory-style hrefs ending in '/', accepts either the directory or
    its index.html. For anchor links with a fragment, strips it before
    filesystem resolution.
    '''
    broken: list[dict] = []
    for html_path in site_root.rglob('*.html'):
        text = html_path.read_text(encoding='utf-8', errors='replace')
        seen: set[str] = set()
        for raw in _HREF_RE.findall(text):
            if raw in seen:
                continue
            seen.add(raw)
            parsed = urlparse(raw)
            if parsed.scheme or parsed.netloc:
                continue
            href = parsed.path
            if not href or href.startswith('#'):
                continue
            if raw.startswith(('mailto:', 'tel:', 'javascript:', 'data:')):
                continue
            target = (html_path.parent / href).resolve()
            if target.is_dir():
                target = target / 'index.html'
            if not target.exists():
                broken.append({
                    'page': str(html_path.relative_to(site_root)),
                    'href': raw,
                    'resolved': str(target),
                })
    return broken


def build(dry: bool = False) -> dict:
    model = nav.build_site_model()
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(['html']),
        trim_blocks=False,
        lstrip_blocks=False,
    )

    t_start = time.time()
    manifest: dict = {
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'pages': [],
        'missing': [],
    }

    def write(rel_out: str, html: str) -> Path:
        out = SITE / rel_out
        out.parent.mkdir(parents=True, exist_ok=True)
        if not dry:
            out.write_text(html, encoding='utf-8')
        return out

    # ---- static assets ----
    assets_dir = SITE / 'assets'
    if not dry:
        assets_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(STATIC / 'site.css', assets_dir / 'site.css')
        shutil.copy2(STATIC / 'site.js', assets_dir / 'site.js')

    def common_ctx(out_path: Path, page_title: str, active_track: str | None) -> dict:
        return {
            'assets_prefix': _assets_prefix(out_path),
            'page_title': page_title,
            'active_track': active_track,
            'tracks_list': model['tracks_list'],
            'snapshot_latest': model['snapshot_latest'],
            'snapshot_prev': model['snapshot_prev'],
            'snapshot_baseline': model['snapshot_baseline'],
            'snapshots_all': model['snapshots_all'],
            'totals': model['totals'],
        }

    # ---- home ----
    out = write('index.html', '')  # placeholder to compute prefix
    html = env.get_template('home.html').render(
        **common_ctx(out, 'IYP · 分析全景', None),
        leaderboard=model['leaderboard'],
    )
    write('index.html', html)
    manifest['pages'].append({'url': '/', 'out': 'index.html', 'src_sha': None})

    # ---- track hubs + step pages ----
    for track in model['tracks_list']:
        if track.slug == 'countries':
            hub_tpl = 'countries_hub.html'
            hub_out = write(f'{track.slug}/index.html', '')
            profile_pages = [p for p in track.all_pages() if p.phase == 'profiles']
            dashboard_pages = [p for p in track.all_pages() if p.phase == 'dashboards']
            html = env.get_template(hub_tpl).render(
                **common_ctx(hub_out, f'{track.title_zh} · IYP', track.slug),
                track=track,
                profile_pages=profile_pages,
                dashboard_pages=dashboard_pages,
                pages_total=len(track.all_pages()),
            )
            write(f'{track.slug}/index.html', html)
        else:
            hub_out = write(f'{track.slug}/index.html', '')
            html = env.get_template('track_hub.html').render(
                **common_ctx(hub_out, f'{track.title_zh} · IYP', track.slug),
                track=track,
                badge_variant=TRACK_BADGES[track.slug],
                phase_variants=PHASE_VARIANTS,
                show_phase_filter=(track.slug == 'china'),
                pages_total=len(track.all_pages()),
            )
            write(f'{track.slug}/index.html', html)

        manifest['pages'].append({'url': f'/{track.slug}/', 'out': f'{track.slug}/index.html', 'src_sha': None})

        for page in track.all_pages():
            rel_out = page.url.lstrip('/') + 'index.html'
            out = write(rel_out, '')

            src_abs = _resolve_src(out, page.src) if page.src else None
            if src_abs and not src_abs.exists():
                manifest['missing'].append({'page': page.url, 'src': page.src, 'resolved': str(src_abs)})
                print(f'  !! MISSING src for {page.url}: {page.src} (resolved: {src_abs})', file=sys.stderr)

            prev_p, next_p = model['prev_next'].get(page.url, (None, None))

            template_name = 'step_plotly.html' if page.kind == 'plotly' else 'step_png.html'
            delta_strip = _country_delta_strip(page) if (track.slug == 'countries' and page.phase == 'profiles') else None
            explainer = explainers.get(page.url)

            html = env.get_template(template_name).render(
                **common_ctx(out, f'{page.title_zh} · {track.title_zh}', track.slug),
                track=track,
                page=page,
                prev_page=prev_p,
                next_page=next_p,
                badge_variant=TRACK_BADGES[track.slug],
                delta_strip=delta_strip,
                explainer=explainer,
            )
            write(rel_out, html)
            manifest['pages'].append({
                'url': page.url,
                'out': rel_out,
                'track': track.slug,
                'src': page.src,
                'src_sha': _sha1(src_abs) if src_abs else None,
            })

    # ---- link checker (only meaningful when files are actually written) ----
    manifest['broken_links'] = [] if dry else _scan_site_links(SITE)

    # ---- manifest ----
    manifest['stats'] = {
        'pages': len(manifest['pages']),
        'missing': len(manifest['missing']),
        'broken_links': len(manifest['broken_links']),
        'elapsed_sec': round(time.time() - t_start, 3),
    }
    if not dry:
        (HERE / 'build_manifest.json').write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding='utf-8',
        )
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='Build the unified IYP analysis site.')
    ap.add_argument('--dry', action='store_true', help='resolve paths but do not write files')
    args = ap.parse_args(argv)

    result = build(dry=args.dry)
    print('')
    print(f"wrote {result['stats']['pages']} pages in {result['stats']['elapsed_sec']}s")
    if result['missing']:
        print(f"!! {len(result['missing'])} missing iframe/img sources — fix before shipping", file=sys.stderr)
        for row in result['missing'][:10]:
            print(f"   - {row['page']} → {row['src']}", file=sys.stderr)
        return 1
    if result.get('broken_links'):
        print(f"!! {len(result['broken_links'])} broken <a href> targets — fix before shipping", file=sys.stderr)
        for row in result['broken_links'][:10]:
            print(f"   - {row['page']} → {row['href']}", file=sys.stderr)
        return 1
    print(f'site root: {SITE}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
