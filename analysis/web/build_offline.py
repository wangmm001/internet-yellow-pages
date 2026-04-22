"""Build an offline, click-to-view bundle of the IYP analysis site.

Produces <out>/ (default: offline-site/) containing:
  analysis/web/site/                  — 89 HTMLs (Galaxy excluded)
  analysis/china/html/                — 31 Plotly pages
  analysis/countries/html/            — 47 pages
  analysis/complex_network_images/    — 13 PNGs + evolution.html
  analysis/as_globe/html/             — 3 WebGL views
  analysis/vendor/                    — vendored CDN JS/CSS

Every external CDN URL is rewritten to point at the vendored copy.
Runs idempotently; re-runs overwrite the target cleanly.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / 'offline-site'

# Source trees copied into the offline bundle.  Paths are relative to REPO_ROOT.
SOURCE_TREES = [
    'analysis/web/site',
    'analysis/china/html',
    'analysis/countries/html',
    'analysis/complex_network_images',
    'analysis/as_globe/html',
]

# CDN URLs → local vendor paths (relative to <out>/analysis/vendor/).
VENDOR_MAP = {
    'https://unpkg.com/3d-force-graph@1.77/dist/3d-force-graph.min.js':
        '3d-force-graph@1.77/dist/3d-force-graph.min.js',
    'https://unpkg.com/globe.gl@2.32/dist/globe.gl.min.js':
        'globe.gl@2.32/dist/globe.gl.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/vis-network.min.js':
        'vis-network@9.1.2/dist/vis-network.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/dist/vis-network.min.css':
        'vis-network@9.1.2/dist/vis-network.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/css/bootstrap.min.css':
        'bootstrap@5.0.0-beta3/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/js/bootstrap.bundle.min.js':
        'bootstrap@5.0.0-beta3/dist/js/bootstrap.bundle.min.js',
    'https://unpkg.com/three@0.160.0/build/three.module.js':
        'three@0.160.0/build/three.module.js',
    'https://unpkg.com/three@0.160.0/examples/jsm/controls/OrbitControls.js':
        'three@0.160.0/examples/jsm/controls/OrbitControls.js',
    'https://unpkg.com/three@0.160.0/examples/jsm/renderers/CSS2DRenderer.js':
        'three@0.160.0/examples/jsm/renderers/CSS2DRenderer.js',
    'https://unpkg.com/three-globe@2.31/example/img/earth-dark.jpg':
        'three-globe@2.31/example/img/earth-dark.jpg',
    # IMPORTANT: this base-URL entry MUST come AFTER the two full jsm/... file
    # entries above, so the file URLs are rewritten first and only the
    # bare importmap base remains to be rewritten.
    'https://unpkg.com/three@0.160.0/examples/jsm/':
        'three@0.160.0/examples/jsm/',
}

# External URLs we accept staying as dead links in the offline bundle
# (license/attribution links, optional decorative icons).
EXTERNAL_ALLOWLIST_PREFIXES = (
    'https://plotly.com',
    'https://carto.com',
    'https://stamen.com',
    'https://www.mapbox.com',
    'https://maplibre.org',
    'https://openstreetmap.org',
    'https://www.openstreetmap.org',
    'https://creativecommons.org',
    'https://unpkg.com/maki@2.1.0/icons/',  # folium map-marker icons (optional)
    'https://github.com/zloirock/core-js',  # core-js LICENSE reference inside pyvis bundle
    'http://www.esri.com',  # ESRI tile attribution link embedded in map JS bundles
)


def vendor_local_path(url: str) -> str:
    """Return the vendor-local path for a CDN URL (relative to vendor/)."""
    return VENDOR_MAP[url]


def download_vendor(vendor_dir: Path, skip: bool = False) -> None:
    """Download every URL in VENDOR_MAP into <vendor_dir>/<local_path>.

    Skips any file that already exists when ``skip`` is True.
    Entries whose URL ends with '/' are base-URL rewrite anchors only —
    they have no file to download and are silently skipped.
    """
    vendor_dir.mkdir(parents=True, exist_ok=True)
    for url, rel in VENDOR_MAP.items():
        if url.endswith('/'):
            # Base-URL entry: used only for string replacement, not a downloadable file.
            continue
        dst = vendor_dir / rel
        if skip and dst.exists() and dst.stat().st_size > 0:
            print(f'  reuse  {rel}')
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        print(f'  fetch  {url}')
        req = urllib.request.Request(url, headers={'User-Agent': 'iyp-offline-build'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            dst.write_bytes(resp.read())


def run_site_build() -> None:
    """Invoke analysis.web.build as a subprocess with Galaxy suppressed."""
    env = os.environ.copy()
    env['IYP_EXCLUDE_GALAXY'] = '1'
    result = subprocess.run(
        [sys.executable, '-m', 'analysis.web.build'],
        env=env, cwd=REPO_ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise RuntimeError(f'site build failed (exit {result.returncode})')
    print(result.stdout.strip().splitlines()[-1] if result.stdout else 'site built')


def copy_sources(out: Path) -> None:
    """Copy all SOURCE_TREES into <out>/<tree>/, preserving structure."""
    for rel in SOURCE_TREES:
        src = REPO_ROOT / rel
        dst = out / rel
        if dst.exists():
            shutil.rmtree(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst, symlinks=False)
        size_mb = sum(f.stat().st_size for f in dst.rglob('*') if f.is_file()) / (1024 * 1024)
        print(f'  copy   {rel} ({size_mb:.1f} MB)')


def rewrite_cdn_refs(html: str, depth_from_vendor: int) -> str:
    """Replace every CDN URL in VENDOR_MAP with its vendor-relative path.

    ``depth_from_vendor`` is the number of directory levels the HTML file
    sits above <out>/analysis/vendor/.  E.g. a file at
    <out>/analysis/countries/html/foo.html is 2 levels below
    <out>/analysis/, so depth_from_vendor=2 and the vendor prefix becomes
    ``../../vendor/``.
    """
    prefix = '../' * depth_from_vendor + 'vendor/'
    for url, local in VENDOR_MAP.items():
        html = html.replace(url, prefix + local)
    return html


def _depth_from_vendor(html_path: Path, out: Path) -> int:
    """How many directory levels does html_path sit below out/analysis/?"""
    rel = html_path.relative_to(out / 'analysis')
    return len(rel.parts) - 1


def rewrite_file(html_path: Path, out: Path) -> int:
    """Rewrite CDN + tile refs in one HTML file.  Returns substitutions."""
    original = html_path.read_text(encoding='utf-8')
    depth = _depth_from_vendor(html_path, out)
    new = rewrite_cdn_refs(original, depth_from_vendor=depth)
    new, tile_n = rewrite_tile_urls(new, depth_from_vendor=depth)
    if new != original:
        html_path.write_text(new, encoding='utf-8')
    cdn_n = sum(1 for url in VENDOR_MAP if url in original and url not in new)
    return cdn_n + tile_n


# --- OSM tile vendoring ---------------------------------------------------
# Fetch zoom-0..3 tiles (85 total) and unify all tile-server URLs in the
# copied HTMLs to this local set.  Low zoom covers global → country-level
# views, which is all the analysis charts need.

OSM_TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
OSM_MAX_ZOOM = 3  # inclusive; 1+4+16+64 = 85 tiles
OSM_USER_AGENT = 'iyp-offline-atlas/1.0 (internet-yellow-pages; one-time-fetch)'
OSM_FETCH_DELAY_SEC = 0.2  # respect tile.openstreetmap.org usage policy


def download_osm_tiles(vendor_dir: Path, skip: bool = False) -> None:
    """Fetch zoom 0..OSM_MAX_ZOOM OSM tiles into <vendor_dir>/tiles/osm/.

    Layout matches Leaflet's URL template: <vendor>/tiles/osm/{z}/{x}/{y}.png.
    Respects OSM tile usage policy via a descriptive User-Agent and a
    small inter-request delay.  Skips files that already exist when
    ``skip`` is True (so --skip-download reuses cached tiles).
    """
    tiles_dir = vendor_dir / 'tiles' / 'osm'
    tiles_dir.mkdir(parents=True, exist_ok=True)
    total = sum(4 ** z for z in range(OSM_MAX_ZOOM + 1))
    fetched = 0
    reused = 0
    for z in range(OSM_MAX_ZOOM + 1):
        for x in range(2 ** z):
            for y in range(2 ** z):
                dst = tiles_dir / str(z) / str(x) / f'{y}.png'
                if skip and dst.exists() and dst.stat().st_size > 0:
                    reused += 1
                    continue
                dst.parent.mkdir(parents=True, exist_ok=True)
                url = OSM_TILE_URL.format(z=z, x=x, y=y)
                req = urllib.request.Request(
                    url, headers={'User-Agent': OSM_USER_AGENT})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    dst.write_bytes(resp.read())
                fetched += 1
                time.sleep(OSM_FETCH_DELAY_SEC)
    print(f'  OSM tiles: {fetched} fetched, {reused} reused (total {total})')


# Tile-server URL patterns in Leaflet/folium HTML. The {z}/{x}/{y} braces
# are literal placeholders in the HTML that Leaflet substitutes at runtime
# — we preserve them in the replacement so Leaflet still does its job.
_TILE_URL_PATTERNS = [
    # OpenStreetMap — both {s} subdomain template and resolved [a-c] form
    re.compile(
        r'https?://(?:\{s\}|[a-c])\.tile\.openstreetmap\.org/\{z\}/\{x\}/\{y\}\.png'),
    # Stadia Maps / Stamen — may have ?api_key=... suffix
    re.compile(
        r'https?://tiles\.stadiamaps\.com/tiles/[a-z_-]+/\{z\}/\{x\}/\{y\}\.(?:png|jpg)'
        r'(?:\?[^"\'\\s]*)?'),
    # Carto basemaps
    re.compile(
        r'https?://(?:\{s\}|[a-d])\.basemaps\.cartocdn\.com/[a-z_-]+/\{z\}/\{x\}/\{y\}(?:@2x)?\.png'),
]


def rewrite_tile_urls(html: str, depth_from_vendor: int) -> tuple[str, int]:
    """Replace public tile-server URLs with the local OSM vendor path.

    All recognised tile servers are unified to the same local OSM set —
    offline bundles prioritise 'it works' over style variety.
    """
    local = '../' * depth_from_vendor + 'vendor/tiles/osm/{z}/{x}/{y}.png'
    count = 0
    for pat in _TILE_URL_PATTERNS:
        html, n = pat.subn(local, html)
        count += n
    return html, count


# Match URLs inside actual-network-loading HTML/CSS constructs:
#   src="URL", src='URL', href="URL", href='URL', and url(URL) or url("URL").
# This deliberately skips URL-shaped strings inside inline SVG xmlns= attributes,
# inline JS string literals, and comment URLs — none of which trigger network fetches.
_EXTERNAL_URL_RE = re.compile(
    rb'''(?:src|href)\s*=\s*["'](https?://[^"']+)["']'''
    rb'''|url\(\s*["']?(https?://[^"')]+?)["']?\s*\)'''
)


def is_allowlisted(url: str) -> bool:
    return any(url.startswith(prefix) for prefix in EXTERNAL_ALLOWLIST_PREFIXES)


def verify_no_external_urls(out: Path) -> list[tuple[Path, str]]:
    """Scan every HTML/JS/CSS under <out> for un-allowlisted external URLs.

    Only flags URLs that appear inside src="…"/href="…"/url(…) constructs
    (i.e., URLs that actually trigger a network load).  Inline SVG xmlns=
    attributes, JS string literals, and documentation comment URLs are
    intentionally ignored because they don't cause browser requests.

    Returns a list of (file, url) findings.  Empty list = clean.
    """
    findings: list[tuple[Path, str]] = []
    for path in out.rglob('*'):
        if not path.is_file():
            continue
        if path.suffix not in {'.html', '.htm', '.css', '.js'}:
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        for m in _EXTERNAL_URL_RE.finditer(data):
            # One of the two groups matched; take the non-None one.
            raw = m.group(1) or m.group(2)
            if raw is None:
                continue
            url = raw.decode('utf-8', errors='replace').rstrip('.,;:')
            if is_allowlisted(url):
                continue
            findings.append((path, url))
    return findings


def restore_committed_site() -> None:
    """Restore analysis/web/site/ to its committed state.

    run_site_build() regenerates the committed site/ tree with Galaxy
    excluded as a side-effect.  After we've copied that regenerated tree
    into offline-site/, revert the in-repo site/ back to HEAD so the
    working tree stays clean.
    """
    subprocess.run(
        ['git', 'checkout', '--', 'analysis/web/site/'],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    print('  restored committed analysis/web/site/ state')


# Python launcher that starts a local HTTP server and opens the browser.
# Shipped inside the offline bundle so the user can sidestep Chrome's
# progressively-stricter file:// restrictions (ES modules, fetch(), cross-
# origin iframes all degrade on file:// in Chrome 130+).
_LAUNCHER_PY = '''#!/usr/bin/env python3
"""Start a local HTTP server for the IYP offline analysis atlas.

Usage: double-click this file, or run: python3 start.py

Falls back through ports 8765, 8766, 8767 if earlier ones are busy.
Stop with Ctrl+C. Requires Python 3.7+ (stdlib only).
"""
import http.server
import os
import socketserver
import sys
import webbrowser
from functools import partial

PORTS = [8765, 8766, 8767, 8768, 8769]
INDEX_PATH = 'analysis/web/site/index.html'


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)

    for port in PORTS:
        try:
            handler = partial(http.server.SimpleHTTPRequestHandler, directory=here)
            # allow_reuse_address avoids TIME_WAIT binding errors on restart.
            socketserver.TCPServer.allow_reuse_address = True
            with socketserver.TCPServer(('127.0.0.1', port), handler) as httpd:
                url = f'http://127.0.0.1:{port}/{INDEX_PATH}'
                print(f'IYP offline atlas · serving {here}')
                print(f'  → {url}')
                print(f'  Press Ctrl+C to stop.')
                try:
                    webbrowser.open_new_tab(url)
                except Exception:
                    pass
                httpd.serve_forever()
                return 0
        except OSError as exc:
            if port == PORTS[-1]:
                sys.stderr.write(f'All ports {PORTS} busy: {exc}\\n')
                return 1
            print(f'port {port} busy, trying {PORTS[PORTS.index(port) + 1]}', file=sys.stderr)


if __name__ == '__main__':
    try:
        raise SystemExit(main() or 0)
    except KeyboardInterrupt:
        print()
        sys.exit(0)
'''

_LAUNCHER_SH = '''#!/bin/sh
# IYP offline atlas launcher (Unix/macOS)
cd "$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then
    exec python3 start.py
elif command -v python >/dev/null 2>&1; then
    exec python start.py
else
    echo "Python 3 is required. Install from https://www.python.org/ then re-run."
    read -p "Press Enter to close."
fi
'''

_LAUNCHER_BAT = '''@echo off
REM IYP offline atlas launcher (Windows)
cd /d "%~dp0"
where python >nul 2>nul
if %errorlevel%==0 (
    python start.py
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        py start.py
    ) else (
        echo Python 3 is required.  Install from https://www.python.org/ then re-run.
        pause
    )
)
'''


def emit_launchers(out: Path) -> None:
    """Write start.py + start.sh + start.bat to the offline bundle."""
    py = out / 'start.py'
    py.write_text(_LAUNCHER_PY, encoding='utf-8')
    py.chmod(0o755)

    sh = out / 'start.sh'
    sh.write_text(_LAUNCHER_SH, encoding='utf-8')
    sh.chmod(0o755)

    bat = out / 'start.bat'
    bat.write_text(_LAUNCHER_BAT, encoding='utf-8')

    print('  wrote  start.py / start.sh / start.bat')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', type=Path, default=DEFAULT_OUT,
                    help='Target directory (default: offline-site/ at repo root)')
    ap.add_argument('--skip-download', action='store_true',
                    help='Reuse existing vendor/ (skip network fetch)')
    ap.add_argument('--verify-only', action='store_true',
                    help='Scan <out> for external URLs, exit 0 if none (minus allowlist)')
    ap.add_argument('--self-test', action='store_true',
                    help='Run built-in assertion tests and exit')
    args = ap.parse_args()

    if args.self_test:
        self_test()
        print('self-test OK')
        return 0

    out: Path = args.out.resolve()
    vendor_dir = out / 'analysis' / 'vendor'

    if args.verify_only:
        if not out.exists():
            sys.stderr.write(f'{out} does not exist\n')
            return 1
        findings = verify_no_external_urls(out)
        if findings:
            print(f'{len(findings)} un-allowlisted external URL(s):')
            for path, url in findings[:20]:
                print(f'  {path.relative_to(out)}: {url}')
            if len(findings) > 20:
                print(f'  … and {len(findings) - 20} more')
            return 1
        print('verify-only: clean (no external URLs outside allowlist).')
        return 0

    print(f'Building offline bundle at {out}')
    out.mkdir(parents=True, exist_ok=True)

    print('→ fetching vendor libraries …')
    download_vendor(vendor_dir, skip=args.skip_download)

    print('→ fetching OSM tiles (zoom 0–3) …')
    download_osm_tiles(vendor_dir, skip=args.skip_download)

    print('→ regenerating site with Galaxy excluded …')
    run_site_build()

    print('→ copying source trees …')
    copy_sources(out)

    print('→ restoring committed site/ state …')
    restore_committed_site()

    print('→ rewriting CDN refs …')
    total_rewrites = 0
    rewritten_files = 0
    for html in (out / 'analysis').rglob('*.html'):
        n = rewrite_file(html, out)
        if n > 0:
            total_rewrites += n
            rewritten_files += 1
    print(f'  rewrote {total_rewrites} refs across {rewritten_files} files')

    # Also rewrite any CSS that references CDN URLs (rare — some pyvis bundles)
    for css in (out / 'analysis').rglob('*.css'):
        rel = css.relative_to(out / 'analysis')
        depth = len(rel.parts) - 1
        try:
            original = css.read_text(encoding='utf-8', errors='ignore')
        except OSError:
            continue
        new = rewrite_cdn_refs(original, depth_from_vendor=depth)
        if new != original:
            css.write_text(new, encoding='utf-8')

    print('→ verifying no un-allowlisted external URLs …')
    findings = verify_no_external_urls(out)
    if findings:
        sys.stderr.write(f'!! {len(findings)} un-allowlisted external URL(s) — fix before shipping:\n')
        for path, url in findings[:20]:
            sys.stderr.write(f'   {path.relative_to(out)}: {url}\n')
        return 1

    readme = out / 'README.txt'
    readme.write_text(
        'IYP Offline Analysis Atlas\n'
        '==========================\n\n'
        '推荐使用方式 · Recommended (fixes all browser file:// limitations):\n'
        '  1. 双击 start.sh (macOS/Linux) 或 start.bat (Windows)\n'
        '     Double-click start.sh (macOS/Linux) or start.bat (Windows)\n'
        '  2. 浏览器会自动打开 http://127.0.0.1:8765/...\n'
        '     Browser opens automatically at http://127.0.0.1:8765/...\n'
        '  3. Ctrl+C 停止服务 · Ctrl+C in the terminal to stop\n\n'
        '直接双击打开（有限制）· Direct double-click (limited):\n'
        '  打开 · Open:  analysis/web/site/index.html\n\n'
        '  ⚠️  Chrome 130+ 在 file:// 下会静默阻止 ES 模块与跨源 iframe,\n'
        '     导致 3D 分层图 (Strata) 无法渲染. 建议使用 start.sh/.bat.\n'
        '     Firefox 不受影响.\n'
        '  ⚠️  Chrome 130+ silently blocks ES modules and cross-origin\n'
        '     iframes on file://, so the Strata 3D view won\'t render.\n'
        '     Prefer start.sh/.bat. Firefox is unaffected.\n\n'
        '所有交互图表 (中国 / 九国 / 复杂网络 / Globe) 均已本地化;\n'
        'Galaxy 127K-AS 视图因浏览器安全限制未包含.\n\n'
        'All interactive charts (China / Countries / Complex Network / Globe)\n'
        'are fully localised. The Galaxy 127K-AS view is excluded because\n'
        'browser security limits its fetch() calls on file://.\n',
        encoding='utf-8')

    print('→ writing launchers …')
    emit_launchers(out)

    print(f'\nDone. Open: {out / "analysis/web/site/index.html"}')
    return 0


def self_test():
    # --- vendor_local_path helper ---
    assert vendor_local_path(
        'https://unpkg.com/globe.gl@2.32/dist/globe.gl.min.js'
    ) == 'globe.gl@2.32/dist/globe.gl.min.js'
    assert vendor_local_path(
        'https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/vis-network.min.js'
    ) == 'vis-network@9.1.2/dist/vis-network.min.js'
    assert vendor_local_path(
        'https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/dist/vis-network.min.css'
    ) == 'vis-network@9.1.2/dist/vis-network.min.css'
    try:
        vendor_local_path('https://example.com/foo.js')
    except KeyError:
        pass
    else:
        raise AssertionError('expected KeyError for unmapped URL')

    # --- rewrite_cdn_refs core ---
    # Case 1: file in analysis/countries/html/ → vendor/ is 2 levels up
    html = '<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/js/bootstrap.bundle.min.js"></script>'
    out = rewrite_cdn_refs(html, depth_from_vendor=2)
    assert out == '<script src="../../vendor/bootstrap@5.0.0-beta3/dist/js/bootstrap.bundle.min.js"></script>', repr(out)

    # Case 2: file at root of offline-site/ (0 levels from vendor/) — unrealistic but handles the edge
    out = rewrite_cdn_refs(
        '<link href="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/dist/vis-network.min.css">',
        depth_from_vendor=0)
    assert out == '<link href="vendor/vis-network@9.1.2/dist/vis-network.min.css">', repr(out)

    # Case 3: unmapped URL stays untouched
    out = rewrite_cdn_refs('<a href="https://plotly.com/">plotly</a>', depth_from_vendor=2)
    assert out == '<a href="https://plotly.com/">plotly</a>'

    # --- is_allowlisted ---
    assert is_allowlisted('https://plotly.com/python/')
    assert is_allowlisted('https://openstreetmap.org/copyright')
    assert is_allowlisted('https://unpkg.com/maki@2.1.0/icons/circle-15.svg')
    assert not is_allowlisted('https://unpkg.com/3d-force-graph@1.77/dist/3d-force-graph.min.js')
    assert not is_allowlisted('https://example.com/evil.js')

    # --- verify_no_external_urls filters non-fetch URL strings ---
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        # namespace attribute — should NOT be flagged
        (td_path / 'a.html').write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"></svg>', encoding='utf-8')
        # actual script src — should BE flagged
        (td_path / 'b.html').write_text(
            '<script src="https://unpkg.com/evil@1/dist/evil.min.js"></script>',
            encoding='utf-8')
        # href attribute — should BE flagged (if not allowlisted)
        (td_path / 'c.html').write_text(
            '<link href="https://cdnjs.cloudflare.com/x.css">', encoding='utf-8')
        # string literal inside JS — should NOT be flagged
        (td_path / 'd.js').write_text(
            'const API = "https://api.example.com/v1";', encoding='utf-8')
        findings = verify_no_external_urls(td_path)
        urls = sorted(u for _, u in findings)
        assert urls == [
            'https://cdnjs.cloudflare.com/x.css',
            'https://unpkg.com/evil@1/dist/evil.min.js',
        ], f'unexpected findings: {urls}'

    # --- rewrite_tile_urls ---
    # OSM with {s} subdomain template
    src = 'L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png")'
    out_, n = rewrite_tile_urls(src, depth_from_vendor=2)
    assert out_ == 'L.tileLayer("../../vendor/tiles/osm/{z}/{x}/{y}.png")', repr(out_)
    assert n == 1

    # Stadia/Stamen with api_key suffix
    src = '"https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}.png?api_key="'
    out_, n = rewrite_tile_urls(src, depth_from_vendor=2)
    assert out_ == '"../../vendor/tiles/osm/{z}/{x}/{y}.png"', repr(out_)
    assert n == 1

    # Carto basemaps with resolved subdomain
    src = '"https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"'
    out_, n = rewrite_tile_urls(src, depth_from_vendor=2)
    assert out_ == '"../../vendor/tiles/osm/{z}/{x}/{y}.png"', repr(out_)
    assert n == 1

    # Non-tile URL untouched
    src = '"https://example.com/image.png"'
    out_, n = rewrite_tile_urls(src, depth_from_vendor=2)
    assert out_ == src and n == 0


if __name__ == '__main__':
    raise SystemExit(main())
