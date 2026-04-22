"""as_galaxy/common.py — paths, presets, shared helpers.

Re-exports the stable helpers from as_globe/common.py so each step only
imports from this one module. Adds as_galaxy's own CACHE_DIR / DATA_DIR /
HTML_DIR and the authoritative PRESETS definition used by step11+ and by
the frontend preset switcher.

The raw BGPKit / NRO / asnames downloads are shared with as_globe via
data_cache/as_globe/raw/ by default — running as_galaxy's step10_bgpkit
after as_globe's step01_bgpkit skips re-downloading. Override with
IYP_SHARED_RAW_DIR env var.
"""
from __future__ import annotations

import os
import sys

# Make the repo root importable so relative-style imports resolve when this
# module is run via `python -m analysis.as_galaxy.step10_*`.
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..')))

from analysis.as_globe.common import (  # noqa: E402 — deliberate late import
    REGION_COLOR,
    REGION_LABEL,
    REGION_ORDER,
    ipv4_addresses_for_prefix,
    read_csv,
    region_of,
    write_csv,
    write_json,
)

BASE_DIR = _HERE
REPO_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..', '..'))
# DATA_DIR / CACHE_DIR are env-overridable so smoke_test and CI can redirect
# them to a temp location and not pollute the committed tree.
DATA_DIR = os.path.normpath(os.environ.get(
    'IYP_AS_GALAXY_DATA_DIR',
    os.path.join(BASE_DIR, 'data'),
))
HTML_DIR = os.path.normpath(os.environ.get(
    'IYP_AS_GALAXY_HTML_DIR',
    os.path.join(BASE_DIR, 'html'),
))
CACHE_DIR = os.path.normpath(os.environ.get(
    'IYP_AS_GALAXY_CACHE_DIR',
    os.path.join(REPO_ROOT, 'data_cache', 'as_galaxy'),
))
RAW_DIR = os.path.normpath(os.environ.get(
    'IYP_SHARED_RAW_DIR',
    # Default to as_globe's raw cache so BGPKit downloads are shared.
    os.path.join(REPO_ROOT, 'data_cache', 'as_globe', 'raw'),
))

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(HTML_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(RAW_DIR, exist_ok=True)


# Preset weight vectors — authoritative source. Mirrored in manifest.json
# (by step15) and in the frontend preset switcher (P6). Components:
#   v       — log10(IPv4 advertised + 1), normalized
#   prefix  — log10(prefix_count + 1), normalized
#   kcore   — k-core number of the peering graph, normalized
#   eigen   — eigenvector centrality, normalized
#   cone    — IHR Hegemony customer-cone size (optional — zero if unavailable)
PRESETS = [
    {
        'name': 'economy',
        'label_zh': '经济',
        'label_en': 'Economy',
        'weights': {'v': 0.60, 'prefix': 0.20, 'kcore': 0.10, 'eigen': 0.10, 'cone': 0.00},
    },
    {
        'name': 'structure',
        'label_zh': '结构',
        'label_en': 'Structure',
        'weights': {'v': 0.15, 'prefix': 0.05, 'kcore': 0.50, 'eigen': 0.30, 'cone': 0.00},
    },
    {
        'name': 'reach',
        'label_zh': '到达度',
        'label_en': 'Reach',
        # If cone data isn't available, step11 re-normalizes to
        # {eigen: 0.7, kcore: 0.3} and records that in manifest.
        'weights': {'v': 0.10, 'prefix': 0.00, 'kcore': 0.20, 'eigen': 0.30, 'cone': 0.40},
    },
]


def preset_by_name(name: str) -> dict:
    """Look up a preset by short name; raises KeyError if unknown."""
    for p in PRESETS:
        if p['name'] == name:
            return p
    raise KeyError(f'unknown preset: {name!r} (known: {[p["name"] for p in PRESETS]})')


def write_step_metrics(step_num: int, metrics: dict,
                       title_zh: str = '', title_en: str = '') -> str:
    """as_galaxy's own metrics writer — writes under DATA_DIR, not as_globe's.

    The as_globe equivalent writes to as_globe/data/. Re-exporting that here
    would leak step11/12_metrics.json into the neighbouring view's directory
    and corrupt its dashboard. Keep this local.
    """
    import json
    path = os.path.join(DATA_DIR, f'step{step_num:02d}_metrics.json')
    payload = {'step': step_num, 'title_zh': title_zh, 'title_en': title_en,
               'metrics': metrics}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


__all__ = [
    # re-exported from as_globe
    'REGION_COLOR', 'REGION_LABEL', 'REGION_ORDER',
    'ipv4_addresses_for_prefix', 'read_csv', 'region_of',
    'write_csv', 'write_json', 'write_step_metrics',
    # as_galaxy-specific
    'BASE_DIR', 'REPO_ROOT', 'DATA_DIR', 'HTML_DIR', 'CACHE_DIR', 'RAW_DIR',
    'PRESETS', 'preset_by_name',
]
