"""Shared infrastructure for cross-country + time-series analysis.

Extends analysis/china/common.py by adding:
 - COUNTRY_NAME bilingual map for 9 target countries (+ HK/TW/MO extras)
 - load_country_ases(cc) — generalization of load_cn_ases()
 - per-country / per-snapshot metrics JSON writer/reader
 - save_consolidated_plotly_html() — single HTML with dropdown + year slider
 - get_snapshot_dirs() — resolves path to data/<snapshot>/<country>/

Reuses HTML exporters, theme constants, and country color map from china/common.py.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Re-export china/common helpers for backward-compat
from analysis.china.common import (  # noqa: E402, F401
    BANNER_CSS, COLORS, DARK_BG, DARK_BORDER, DARK_PANEL, DEFAULT_COLOR,
    PLOTLY_DARK, REGION_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, apply_plotly_theme,
    country_color, iso2_to_iso3, load_as_country_map, load_as_metadata,
    load_country_as_map, neo4j_available, save_multi_plotly_html,
    save_placeholder_html, save_plotly_html, save_pyvis_html,
    try_neo4j_or_cached, writeup,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
HTML_DIR = os.path.join(BASE_DIR, 'html')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(HTML_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────
# Country name map (bilingual)
# ─────────────────────────────────────────────────────────────
COUNTRY_NAME = {
    'US': ('美国', 'United States'),
    'CN': ('中国', 'China'),
    'JP': ('日本', 'Japan'),
    'IN': ('印度', 'India'),
    'DE': ('德国', 'Germany'),
    'GB': ('英国', 'United Kingdom'),
    'FR': ('法国', 'France'),
    'NL': ('荷兰', 'Netherlands'),
    'RU': ('俄罗斯', 'Russia'),
    'HK': ('香港', 'Hong Kong'),
    'TW': ('台湾', 'Taiwan'),
    'KR': ('韩国', 'South Korea'),
    'SG': ('新加坡', 'Singapore'),
    'BR': ('巴西', 'Brazil'),
}

TARGET_COUNTRIES = ['US', 'CN', 'JP', 'IN', 'DE', 'GB', 'FR', 'NL', 'RU']


def zh(cc):
    return COUNTRY_NAME.get(cc, (cc, cc))[0]


def en(cc):
    return COUNTRY_NAME.get(cc, (cc, cc))[1]


def bilingual(cc):
    """Return '中国 (China)' style string."""
    z, e = COUNTRY_NAME.get(cc, (cc, cc))
    return f'{z} ({e})'


# ─────────────────────────────────────────────────────────────
# Snapshot-keyed paths
# ─────────────────────────────────────────────────────────────
def snapshot_country_dir(snapshot, country):
    """Return path analysis/global/data/<snapshot>/<country>/, creating it."""
    p = Path(DATA_DIR) / snapshot / country
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_country_metrics(snapshot, country, step_num, metrics, title_zh='', title_en=''):
    """Write analysis/global/data/<snapshot>/<country>/step<NN>_metrics.json."""
    path = snapshot_country_dir(snapshot, country) / f'step{step_num:02d}_metrics.json'
    payload = {
        'step': step_num,
        'country': country,
        'snapshot': snapshot,
        'title_zh': title_zh,
        'title_en': title_en,
        'metrics': metrics,
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def read_country_metrics(snapshot, country, step_num):
    path = snapshot_country_dir(snapshot, country) / f'step{step_num:02d}_metrics.json'
    if not path.exists():
        return None
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def write_country_csv(snapshot, country, name, rows, fieldnames=None):
    """Write analysis/global/data/<snapshot>/<country>/<name>."""
    import csv
    if not rows:
        return None
    path = snapshot_country_dir(snapshot, country) / name
    if fieldnames is None:
        fieldnames = list(rows[0].keys())
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return path


# ─────────────────────────────────────────────────────────────
# Scope loader (country-agnostic)
# ─────────────────────────────────────────────────────────────
def load_country_ases(cc):
    """Load the set of ASNs registered for country code cc."""
    return load_country_as_map().get(cc, set())


def load_all_target_country_ases():
    """Return dict[cc] -> set(ASNs) for TARGET_COUNTRIES."""
    m = load_country_as_map()
    return {cc: m.get(cc, set()) for cc in TARGET_COUNTRIES}


# ─────────────────────────────────────────────────────────────
# Master / consolidated HTML helpers
# ─────────────────────────────────────────────────────────────
def build_banner(title_zh, title_en, subtitle=''):
    sub = f'<div class="step-footer">{subtitle}</div>' if subtitle else ''
    return (
        '<div class="step-banner">'
        f'<h1>{title_zh}</h1>'
        f'<h2>{title_en}</h2>'
        '</div>' + sub
    )


def save_consolidated_html(body_html, name, title_zh, title_en, subtitle=''):
    """Save a consolidated HTML page (already-rendered body) with dark theme banner."""
    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        f'<title>{title_zh}</title>'
        f'{BANNER_CSS}</head><body>'
        f'{build_banner(title_zh, title_en, subtitle)}'
        f'<div class="content">{body_html}</div>'
        '</body></html>'
    )
    path = os.path.join(HTML_DIR, name)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'[html] wrote {path} ({os.path.getsize(path) // 1024} KB)')
    return path


def plotly_inline_once(figs, default_height='560px'):
    """Render list of Plotly figures as a single HTML snippet.

    Only the first figure bundles plotly.js inline; rest reuse.
    Returns the joined HTML fragment.
    """
    from plotly.io import to_html
    out = []
    first = True
    for fig in figs:
        apply_plotly_theme(fig)
        out.append(to_html(
            fig,
            include_plotlyjs=('inline' if first else False),
            full_html=False,
            default_height=default_height,
        ))
        first = False
    return '\n'.join(out)


# ─────────────────────────────────────────────────────────────
# Snapshot registry (for evolution)
# ─────────────────────────────────────────────────────────────
def list_snapshots():
    """Return sorted list of snapshot dirs (e.g. ['2025-04', '2026-04'])."""
    if not os.path.isdir(DATA_DIR):
        return []
    return sorted(d for d in os.listdir(DATA_DIR)
                  if os.path.isdir(os.path.join(DATA_DIR, d)) and '-' in d)


def list_countries_in_snapshot(snapshot):
    p = Path(DATA_DIR) / snapshot
    if not p.is_dir():
        return []
    return sorted(d.name for d in p.iterdir() if d.is_dir())
