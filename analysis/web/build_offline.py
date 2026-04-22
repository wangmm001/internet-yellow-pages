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


if __name__ == '__main__':
    main()
