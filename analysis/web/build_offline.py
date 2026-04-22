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
)


def vendor_local_path(url: str) -> str:
    """Return the vendor-local path for a CDN URL (relative to vendor/)."""
    return VENDOR_MAP[url]


def download_vendor(vendor_dir: Path, skip: bool = False) -> None:
    """Download every URL in VENDOR_MAP into <vendor_dir>/<local_path>.

    Skips any file that already exists when ``skip`` is True.
    """
    vendor_dir.mkdir(parents=True, exist_ok=True)
    for url, rel in VENDOR_MAP.items():
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
    """Rewrite CDN refs in one HTML file.  Returns number of substitutions."""
    original = html_path.read_text(encoding='utf-8')
    depth = _depth_from_vendor(html_path, out)
    new = rewrite_cdn_refs(original, depth_from_vendor=depth)
    if new != original:
        html_path.write_text(new, encoding='utf-8')
    count = sum(1 for url in VENDOR_MAP if url in original and url not in new)
    return count


_EXTERNAL_URL_RE = re.compile(rb'https?://[^\s"\'<>()]+')


def is_allowlisted(url: str) -> bool:
    return any(url.startswith(prefix) for prefix in EXTERNAL_ALLOWLIST_PREFIXES)


def verify_no_external_urls(out: Path) -> list[tuple[Path, str]]:
    """Scan every HTML/JS/CSS under <out> for un-allowlisted external URLs.

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
            url = m.group(0).decode('utf-8', errors='replace').rstrip('.,;:')
            if is_allowlisted(url):
                continue
            findings.append((path, url))
    return findings


def main():
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
        return

    raise NotImplementedError('pipeline not yet implemented')


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


if __name__ == '__main__':
    main()
