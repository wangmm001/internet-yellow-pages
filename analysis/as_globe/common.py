"""Shared helpers for the `as_globe` 3D AS interconnection visualization.

Distinct from analysis/china/common.py: this module owns its own DATA_DIR,
HTML_DIR, and color palette (saturated points on dark globe, not chart traces).

Produces static HTML that is iframed by the unified site under
analysis/web/site/globe/.
"""
from __future__ import annotations

import csv
import json
import math
import os
from typing import Iterable

# Dark theme constants — inlined instead of imported from complex_network.utils
# so this module stays importable without matplotlib in the environment.
DARK_BG = '#0D1117'
DARK_PANEL = '#161B22'
DARK_BORDER = '#30363D'
TEXT_PRIMARY = '#E6EDF3'
TEXT_SECONDARY = '#8B949E'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..', '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
HTML_DIR = os.path.join(BASE_DIR, 'html')
CACHE_DIR = os.path.normpath(os.environ.get(
    'IYP_AS_GLOBE_CACHE_DIR',
    os.path.join(REPO_ROOT, 'data_cache', 'as_globe'),
))

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(HTML_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────
# Region buckets & colors (saturated for dark globe — not the chart palette)
# ─────────────────────────────────────────────────────────────

REGION_ORDER = ['cn', 'na', 'ea', 'eu', 'ot']

REGION_LABEL = {
    'cn': ('中国区', 'Greater China'),
    'na': ('北美', 'North America'),
    'ea': ('东亚', 'East Asia (ex-GC)'),
    'eu': ('欧洲', 'Europe (EU+EEA+UK+CH)'),
    'ot': ('其他', 'Other'),
}

REGION_COLOR = {
    'cn': '#FF453A',
    'na': '#0A84FF',
    'ea': '#FF9F0A',
    'eu': '#30D158',
    'ot': '#8E8E93',
}

_CN_SET = {'CN', 'HK', 'TW', 'MO'}
_NA_SET = {'US', 'CA'}
_EA_SET = {'JP', 'KR'}
_EU_SET = {
    'DE', 'GB', 'FR', 'NL', 'IT', 'ES', 'SE', 'CH', 'IE', 'BE', 'AT', 'DK',
    'NO', 'FI', 'PL', 'PT', 'CZ', 'HU', 'RO', 'GR', 'BG', 'HR', 'SK', 'SI',
    'LT', 'LV', 'EE', 'LU', 'MT', 'CY', 'IS',
}


def region_of(cc: str | None) -> str:
    if not cc:
        return 'ot'
    cc = cc.upper()
    if cc in _CN_SET:
        return 'cn'
    if cc in _NA_SET:
        return 'na'
    if cc in _EA_SET:
        return 'ea'
    if cc in _EU_SET:
        return 'eu'
    return 'ot'


# ─────────────────────────────────────────────────────────────
# Country centroids — fallback geo for ASes lacking LOCATED_IN coords.
# Source: approximate lat/lon for each ISO-2; good enough for ±2° jitter.
# ─────────────────────────────────────────────────────────────

COUNTRY_CENTROIDS: dict[str, tuple[float, float]] = {
    'US': (39.8, -98.6), 'CA': (56.1, -106.3), 'MX': (23.6, -102.6),
    'BR': (-14.2, -51.9), 'AR': (-38.4, -63.6), 'CL': (-35.7, -71.5),
    'CO': (4.6, -74.1), 'PE': (-9.2, -75.0), 'VE': (6.4, -66.6),
    'CN': (35.9, 104.2), 'HK': (22.3, 114.2), 'TW': (23.7, 121.0),
    'MO': (22.2, 113.5), 'JP': (36.2, 138.3), 'KR': (35.9, 127.8),
    'KP': (40.3, 127.5), 'MN': (46.9, 103.8),
    'IN': (20.6, 78.9), 'PK': (30.4, 69.3), 'BD': (23.7, 90.4),
    'ID': (-0.8, 113.9), 'TH': (15.9, 100.9), 'VN': (14.1, 108.3),
    'MY': (4.2, 101.9), 'SG': (1.35, 103.8), 'PH': (12.9, 121.8),
    'KH': (12.6, 104.9), 'LA': (19.9, 102.5), 'MM': (21.9, 95.9),
    'AU': (-25.3, 133.8), 'NZ': (-40.9, 174.9),
    'GB': (55.4, -3.4), 'IE': (53.4, -8.2), 'FR': (46.2, 2.2),
    'DE': (51.2, 10.5), 'NL': (52.1, 5.3), 'BE': (50.5, 4.5),
    'LU': (49.8, 6.1), 'CH': (46.8, 8.2), 'AT': (47.5, 14.6),
    'IT': (41.9, 12.6), 'ES': (40.5, -3.7), 'PT': (39.4, -8.2),
    'SE': (60.1, 18.6), 'NO': (60.5, 8.5), 'FI': (61.9, 25.7),
    'DK': (56.3, 9.5), 'IS': (64.9, -19.0), 'PL': (51.9, 19.1),
    'CZ': (49.8, 15.5), 'SK': (48.7, 19.7), 'HU': (47.2, 19.5),
    'RO': (45.9, 24.9), 'BG': (42.7, 25.5), 'GR': (39.1, 21.8),
    'HR': (45.1, 15.2), 'SI': (46.2, 15.0), 'EE': (58.6, 25.0),
    'LV': (56.9, 24.6), 'LT': (55.2, 23.9), 'MT': (35.9, 14.4),
    'CY': (35.1, 33.4), 'RS': (44.0, 21.0), 'BA': (43.9, 17.7),
    'MK': (41.6, 21.7), 'AL': (41.2, 20.2), 'MD': (47.4, 28.4),
    'UA': (48.4, 31.2), 'BY': (53.7, 27.9), 'RU': (61.5, 105.3),
    'TR': (39.0, 35.2), 'GE': (42.3, 43.4), 'AM': (40.1, 45.0),
    'AZ': (40.1, 47.6), 'KZ': (48.0, 66.9), 'UZ': (41.4, 64.6),
    'KG': (41.2, 74.8), 'TJ': (38.9, 71.3), 'TM': (38.97, 59.6),
    'AF': (33.9, 67.7), 'IR': (32.4, 53.7), 'IQ': (33.2, 43.7),
    'SY': (34.8, 38.9), 'JO': (30.6, 36.2), 'LB': (33.9, 35.9),
    'IL': (31.0, 34.9), 'PS': (31.9, 35.2), 'SA': (23.9, 45.1),
    'AE': (23.4, 53.8), 'OM': (21.5, 55.9), 'YE': (15.6, 48.5),
    'QA': (25.4, 51.2), 'BH': (26.0, 50.6), 'KW': (29.3, 47.5),
    'EG': (26.8, 30.8), 'LY': (26.3, 17.2), 'TN': (33.9, 9.5),
    'DZ': (28.0, 1.7), 'MA': (31.8, -7.1), 'SD': (12.9, 30.2),
    'ET': (9.1, 40.5), 'KE': (-0.02, 37.9), 'TZ': (-6.4, 34.9),
    'UG': (1.4, 32.3), 'RW': (-1.9, 29.9), 'NG': (9.1, 8.7),
    'GH': (7.9, -1.0), 'CI': (7.5, -5.5), 'SN': (14.5, -14.5),
    'ZA': (-30.6, 22.9), 'ZW': (-19.0, 29.2), 'ZM': (-13.1, 27.8),
    'MW': (-13.3, 34.3), 'MZ': (-18.7, 35.5), 'AO': (-11.2, 17.9),
    'CM': (7.4, 12.4), 'GA': (-0.8, 11.6), 'CG': (-0.2, 15.8),
    'CD': (-4.0, 21.8), 'MG': (-18.8, 47.0), 'MU': (-20.3, 57.6),
}


def jitter_latlon(asn: int, lat: float, lon: float, radius_deg: float = 2.0) -> tuple[float, float]:
    """Deterministic small jitter seeded by asn — keeps points distinct."""
    h = (asn * 2654435761) & 0xFFFFFFFF
    dx = ((h & 0xFFFF) / 0xFFFF - 0.5) * 2 * radius_deg
    dy = ((h >> 16) / 0xFFFF - 0.5) * 2 * radius_deg
    return lat + dy, lon + dx


# ─────────────────────────────────────────────────────────────
# IPv4 address count from prefix string
# ─────────────────────────────────────────────────────────────

def ipv4_addresses_for_prefix(prefix: str) -> int:
    """Return 2^(32-plen) for a string like '1.2.3.0/24'.

    Skips IPv6 and malformed prefixes — returns 0 in those cases.
    """
    if not prefix or '/' not in prefix:
        return 0
    net, _, plen_s = prefix.rpartition('/')
    if ':' in net:
        return 0
    try:
        plen = int(plen_s)
    except ValueError:
        return 0
    if plen < 0 or plen > 32:
        return 0
    return 1 << (32 - plen)


def radius_px(ipv4_count: int) -> float:
    """Log-scale node radius in pixels."""
    r = 1.5 + math.log10(ipv4_count + 1) * 1.3
    return max(1.5, min(12.0, r))


# ─────────────────────────────────────────────────────────────
# CSV / JSON I/O
# ─────────────────────────────────────────────────────────────

def write_csv(path: str, rows: Iterable[dict], fieldnames: list[str]) -> str:
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return path


def read_csv(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def write_json(path: str, payload, compact: bool = True) -> str:
    with open(path, 'w', encoding='utf-8') as f:
        if compact:
            json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))
        else:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def write_step_metrics(step_num: int, metrics: dict, title_zh: str = '', title_en: str = '') -> str:
    path = os.path.join(DATA_DIR, f'step{step_num:02d}_metrics.json')
    payload = {'step': step_num, 'title_zh': title_zh, 'title_en': title_en, 'metrics': metrics}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


# ─────────────────────────────────────────────────────────────
# HTML scaffolding for globe/force pages
# ─────────────────────────────────────────────────────────────

def save_placeholder_html(out_path: str, title_zh: str, title_en: str,
                          cause: str = '') -> str:
    """Emit a small 'waiting for data' HTML so the unified site build never fails
    on a fresh checkout. Rendering scripts overwrite this once data/ is populated.
    """
    msg_zh = ('运行 step01_extract（需 Neo4j）与 step02_decimate 生成 '
              'data/nodes.json 与 data/links.json，然后重跑本渲染步骤。')
    msg_en = ('Run step01_extract (needs Neo4j) and step02_decimate to produce '
              'data/nodes.json and data/links.json, then re-run this render step.')
    cause_html = f'<p style="color:#FF453A;margin-top:12px">{cause}</p>' if cause else ''
    html = f"""<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<title>{title_zh}</title>
<style>
  html,body {{ margin:0; padding:0; width:100%; height:100%;
    background:{DARK_BG}; color:{TEXT_PRIMARY};
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',sans-serif;
    display:flex; align-items:center; justify-content:center; }}
  .card {{ max-width:480px; padding:28px 32px; background:{DARK_PANEL};
    border:1px solid {DARK_BORDER}; border-radius:14px; text-align:center; }}
  h1 {{ margin:0 0 4px 0; font-size:20px; color:{TEXT_PRIMARY}; }}
  h2 {{ margin:0 0 18px 0; font-size:13px; font-weight:400; color:{TEXT_SECONDARY}; }}
  p {{ color:{TEXT_SECONDARY}; font-size:13px; line-height:1.55; margin:0 0 6px; }}
  code {{ background:{DARK_BG}; padding:2px 6px; border-radius:4px;
    color:{TEXT_PRIMARY}; font-size:12px; }}
</style></head>
<body><div class="card">
  <h1>{title_zh}</h1>
  <h2>{title_en}</h2>
  <p>{msg_zh}</p>
  <p style="margin-top:10px">{msg_en}</p>
  {cause_html}
  <p style="margin-top:14px"><code>python3 -m analysis.as_globe.step01_extract</code></p>
  <p><code>python3 -m analysis.as_globe.step02_decimate</code></p>
</div></body></html>
"""
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return out_path


PAGE_CSS = f"""
  :root {{
    --bg:{DARK_BG}; --panel:{DARK_PANEL}; --border:{DARK_BORDER};
    --fg:{TEXT_PRIMARY}; --muted:{TEXT_SECONDARY};
  }}
  html, body {{
    margin:0; padding:0; width:100%; height:100%;
    background:var(--bg); color:var(--fg); overflow:hidden;
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',sans-serif;
  }}
  #viz {{ position:absolute; inset:0; }}
  .overlay {{
    position:absolute; z-index:10; background:rgba(22,27,34,0.85);
    border:1px solid var(--border); border-radius:10px;
    backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
    padding:14px 16px; font-size:13px; line-height:1.45;
  }}
  .overlay.top-left   {{ top:18px; left:18px; max-width:380px; }}
  .overlay.top-right  {{ top:18px; right:18px; max-width:240px; }}
  .overlay.bottom     {{ bottom:18px; left:18px; right:18px;
                         max-width:none; display:flex; gap:18px;
                         align-items:center; flex-wrap:wrap; }}
  .overlay h1 {{ margin:0 0 2px 0; font-size:16px; color:var(--fg); font-weight:600; }}
  .overlay h2 {{ margin:0 0 8px 0; font-size:12px; color:var(--muted); font-weight:400; }}
  .overlay p  {{ margin:6px 0; color:var(--muted); font-size:12px; }}
  .legend {{ display:flex; gap:14px; flex-wrap:wrap; }}
  .legend .chip {{ display:flex; align-items:center; gap:6px; cursor:pointer;
                   user-select:none; color:var(--fg); }}
  .legend .chip .dot {{ width:10px; height:10px; border-radius:50%; }}
  .legend .chip.off {{ opacity:0.35; }}
  .slider-row {{ display:flex; gap:8px; align-items:center; color:var(--muted); }}
  .slider-row input[type=range] {{ width:140px; accent-color:#5E5CE6; }}
  .tooltip {{
    position:absolute; z-index:20; pointer-events:none;
    background:rgba(13,17,23,0.95); border:1px solid var(--border);
    border-radius:8px; padding:8px 12px; font-size:12px; color:var(--fg);
    display:none; max-width:260px;
  }}
  .tooltip .asn {{ color:#5E5CE6; font-weight:600; }}
  .tooltip .kv  {{ color:var(--muted); }}
  .info-fab {{
    position:absolute; top:18px; left:18px; z-index:12;
    background:rgba(22,27,34,0.85); border:1px solid var(--border);
    border-radius:6px; color:var(--fg); cursor:pointer;
    font-size:12px; padding:6px 10px; line-height:1;
    backdrop-filter:blur(10px); -webkit-backdrop-filter:blur(10px);
  }}
  .info-fab:hover {{ background:rgba(255,255,255,0.16); }}
  .overlay.info-panel {{ top:52px; left:18px; max-width:380px;
                         transition:opacity 0.18s ease, transform 0.18s ease; }}
  .overlay.info-panel.collapsed {{ opacity:0; transform:translateY(-6px);
                                   pointer-events:none; }}
"""
