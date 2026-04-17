"""Shared helpers for China-in-Global-Internet-Hierarchy 20-step HTML analysis.

Extends analysis/complex_network/utils.py with HTML-specific helpers:
 - bilingual Plotly/Pyvis exporters with dark theme
 - Chinese AS scope loaders (CN / HK / TW / MO kept separate)
 - graceful Neo4j fallback that prefers cached CSVs
 - per-step metrics JSON sidecars
"""
import csv
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.complex_network.utils import (  # noqa: E402
    COLORS, DARK_BG, DARK_BORDER, DARK_PANEL, DATA_DIR as GLOBAL_DATA_DIR,
    TEXT_PRIMARY, TEXT_SECONDARY, get_neo4j_driver, run_query,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
HTML_DIR = os.path.join(BASE_DIR, 'html')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(HTML_DIR, exist_ok=True)

CN_COLOR = COLORS['red']
US_COLOR = COLORS['blue']
EU_COLOR = COLORS['purple']
ASIA_COLOR = COLORS['orange']
DEFAULT_COLOR = COLORS['cyan']

REGION_COLOR = {
    'CN': CN_COLOR,
    'HK': COLORS['pink'],
    'TW': COLORS['amber'],
    'MO': COLORS['yellow'],
    'US': US_COLOR,
    'JP': COLORS['orange'],
    'KR': COLORS['teal'],
    'SG': COLORS['green'],
    'DE': EU_COLOR,
    'GB': EU_COLOR,
    'FR': EU_COLOR,
    'NL': EU_COLOR,
    'RU': COLORS['amber'],
    'IN': COLORS['yellow'],
}


def country_color(cc):
    return REGION_COLOR.get(cc, DEFAULT_COLOR)


# ISO-2 → ISO-3 for plotly choropleth
ISO2_TO_ISO3 = {
    'AF': 'AFG', 'AX': 'ALA', 'AL': 'ALB', 'DZ': 'DZA', 'AS': 'ASM', 'AD': 'AND',
    'AO': 'AGO', 'AI': 'AIA', 'AQ': 'ATA', 'AG': 'ATG', 'AR': 'ARG', 'AM': 'ARM',
    'AW': 'ABW', 'AU': 'AUS', 'AT': 'AUT', 'AZ': 'AZE', 'BS': 'BHS', 'BH': 'BHR',
    'BD': 'BGD', 'BB': 'BRB', 'BY': 'BLR', 'BE': 'BEL', 'BZ': 'BLZ', 'BJ': 'BEN',
    'BM': 'BMU', 'BT': 'BTN', 'BO': 'BOL', 'BA': 'BIH', 'BW': 'BWA', 'BR': 'BRA',
    'IO': 'IOT', 'VG': 'VGB', 'BN': 'BRN', 'BG': 'BGR', 'BF': 'BFA', 'BI': 'BDI',
    'KH': 'KHM', 'CM': 'CMR', 'CA': 'CAN', 'CV': 'CPV', 'KY': 'CYM', 'CF': 'CAF',
    'TD': 'TCD', 'CL': 'CHL', 'CN': 'CHN', 'HK': 'HKG', 'MO': 'MAC', 'CX': 'CXR',
    'CC': 'CCK', 'CO': 'COL', 'KM': 'COM', 'CG': 'COG', 'CD': 'COD', 'CK': 'COK',
    'CR': 'CRI', 'CI': 'CIV', 'HR': 'HRV', 'CU': 'CUB', 'CW': 'CUW', 'CY': 'CYP',
    'CZ': 'CZE', 'DK': 'DNK', 'DJ': 'DJI', 'DM': 'DMA', 'DO': 'DOM', 'EC': 'ECU',
    'EG': 'EGY', 'SV': 'SLV', 'GQ': 'GNQ', 'ER': 'ERI', 'EE': 'EST', 'ET': 'ETH',
    'FK': 'FLK', 'FO': 'FRO', 'FJ': 'FJI', 'FI': 'FIN', 'FR': 'FRA', 'GF': 'GUF',
    'PF': 'PYF', 'GA': 'GAB', 'GM': 'GMB', 'GE': 'GEO', 'DE': 'DEU', 'GH': 'GHA',
    'GI': 'GIB', 'GR': 'GRC', 'GL': 'GRL', 'GD': 'GRD', 'GP': 'GLP', 'GU': 'GUM',
    'GT': 'GTM', 'GG': 'GGY', 'GN': 'GIN', 'GW': 'GNB', 'GY': 'GUY', 'HT': 'HTI',
    'VA': 'VAT', 'HN': 'HND', 'HU': 'HUN', 'IS': 'ISL', 'IN': 'IND', 'ID': 'IDN',
    'IR': 'IRN', 'IQ': 'IRQ', 'IE': 'IRL', 'IM': 'IMN', 'IL': 'ISR', 'IT': 'ITA',
    'JM': 'JAM', 'JP': 'JPN', 'JE': 'JEY', 'JO': 'JOR', 'KZ': 'KAZ', 'KE': 'KEN',
    'KI': 'KIR', 'KP': 'PRK', 'KR': 'KOR', 'KW': 'KWT', 'KG': 'KGZ', 'LA': 'LAO',
    'LV': 'LVA', 'LB': 'LBN', 'LS': 'LSO', 'LR': 'LBR', 'LY': 'LBY', 'LI': 'LIE',
    'LT': 'LTU', 'LU': 'LUX', 'MK': 'MKD', 'MG': 'MDG', 'MW': 'MWI', 'MY': 'MYS',
    'MV': 'MDV', 'ML': 'MLI', 'MT': 'MLT', 'MH': 'MHL', 'MQ': 'MTQ', 'MR': 'MRT',
    'MU': 'MUS', 'YT': 'MYT', 'MX': 'MEX', 'FM': 'FSM', 'MD': 'MDA', 'MC': 'MCO',
    'MN': 'MNG', 'ME': 'MNE', 'MS': 'MSR', 'MA': 'MAR', 'MZ': 'MOZ', 'MM': 'MMR',
    'NA': 'NAM', 'NR': 'NRU', 'NP': 'NPL', 'NL': 'NLD', 'NC': 'NCL', 'NZ': 'NZL',
    'NI': 'NIC', 'NE': 'NER', 'NG': 'NGA', 'NU': 'NIU', 'NF': 'NFK', 'MP': 'MNP',
    'NO': 'NOR', 'OM': 'OMN', 'PK': 'PAK', 'PW': 'PLW', 'PS': 'PSE', 'PA': 'PAN',
    'PG': 'PNG', 'PY': 'PRY', 'PE': 'PER', 'PH': 'PHL', 'PN': 'PCN', 'PL': 'POL',
    'PT': 'PRT', 'PR': 'PRI', 'QA': 'QAT', 'RE': 'REU', 'RO': 'ROU', 'RU': 'RUS',
    'RW': 'RWA', 'BL': 'BLM', 'SH': 'SHN', 'KN': 'KNA', 'LC': 'LCA', 'MF': 'MAF',
    'PM': 'SPM', 'VC': 'VCT', 'WS': 'WSM', 'SM': 'SMR', 'ST': 'STP', 'SA': 'SAU',
    'SN': 'SEN', 'RS': 'SRB', 'SC': 'SYC', 'SL': 'SLE', 'SG': 'SGP', 'SX': 'SXM',
    'SK': 'SVK', 'SI': 'SVN', 'SB': 'SLB', 'SO': 'SOM', 'ZA': 'ZAF', 'GS': 'SGS',
    'SS': 'SSD', 'ES': 'ESP', 'LK': 'LKA', 'SD': 'SDN', 'SR': 'SUR', 'SJ': 'SJM',
    'SZ': 'SWZ', 'SE': 'SWE', 'CH': 'CHE', 'SY': 'SYR', 'TW': 'TWN', 'TJ': 'TJK',
    'TZ': 'TZA', 'TH': 'THA', 'TL': 'TLS', 'TG': 'TGO', 'TK': 'TKL', 'TO': 'TON',
    'TT': 'TTO', 'TN': 'TUN', 'TR': 'TUR', 'TM': 'TKM', 'TC': 'TCA', 'TV': 'TUV',
    'UG': 'UGA', 'UA': 'UKR', 'AE': 'ARE', 'GB': 'GBR', 'US': 'USA', 'UM': 'UMI',
    'UY': 'URY', 'UZ': 'UZB', 'VU': 'VUT', 'VE': 'VEN', 'VN': 'VNM', 'VI': 'VIR',
    'WF': 'WLF', 'EH': 'ESH', 'YE': 'YEM', 'ZM': 'ZMB', 'ZW': 'ZWE',
}


def iso2_to_iso3(cc):
    return ISO2_TO_ISO3.get(cc, None)


# ─────────────────────────────────────────────────────────────
# Scope loaders
# ─────────────────────────────────────────────────────────────

def load_as_country_map():
    """Return dict[asn] -> set(country_codes)."""
    path = os.path.join(GLOBAL_DATA_DIR, 'as_country.csv')
    mp = defaultdict(set)
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            asn = int(row['asn'])
            mp[asn].add(row['country'])
    return mp


def load_country_as_map():
    """Return dict[country_code] -> set(asns)."""
    path = os.path.join(GLOBAL_DATA_DIR, 'as_country.csv')
    mp = defaultdict(set)
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            mp[row['country']].add(int(row['asn']))
    return mp


def load_cn_ases(include_hk=False, include_tw=False, include_mo=False):
    """Return set of Chinese ASNs. Mainland CN by default."""
    m = load_country_as_map()
    s = set(m.get('CN', set()))
    if include_hk:
        s |= m.get('HK', set())
    if include_tw:
        s |= m.get('TW', set())
    if include_mo:
        s |= m.get('MO', set())
    return s


def load_greater_china_groups():
    """Return dict of separately-tracked Greater-China groups."""
    m = load_country_as_map()
    return {
        'CN': m.get('CN', set()),
        'HK': m.get('HK', set()),
        'TW': m.get('TW', set()),
        'MO': m.get('MO', set()),
    }


def load_as_metadata():
    """Return dict[asn] -> {'countries': set, 'tags': list}."""
    path = os.path.join(GLOBAL_DATA_DIR, 'as_metadata.csv')
    mp = {}
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            asn = int(row['asn'])
            countries = set(row['countries'].split('|')) if row.get('countries') else set()
            tags = row['tags'].split('|') if row.get('tags') else []
            mp[asn] = {'countries': countries, 'tags': tags}
    return mp


# ─────────────────────────────────────────────────────────────
# Neo4j fallback
# ─────────────────────────────────────────────────────────────

def neo4j_available(timeout=3.0):
    """Ping Neo4j; return True iff reachable."""
    try:
        driver = get_neo4j_driver()
        with driver.session() as sess:
            sess.run('RETURN 1 AS ok').single()
        driver.close()
        return True
    except Exception as e:
        print(f'[neo4j] unavailable: {e}')
        return False


def try_neo4j_or_cached(cypher, cached_path, params=None):
    """Try Neo4j first; on failure or empty, fall back to cached CSV.

    Returns (records, source) where source is 'neo4j', 'csv', or 'none'.
    """
    if neo4j_available():
        try:
            recs = run_query(cypher, params)
            if recs:
                return recs, 'neo4j'
        except Exception as e:
            print(f'[neo4j] query failed: {e}')
    if cached_path and os.path.exists(cached_path):
        with open(cached_path, encoding='utf-8') as f:
            return list(csv.DictReader(f)), 'csv'
    return [], 'none'


# ─────────────────────────────────────────────────────────────
# HTML / Plotly / Pyvis exporters
# ─────────────────────────────────────────────────────────────

PLOTLY_DARK = dict(
    paper_bgcolor=DARK_BG,
    plot_bgcolor=DARK_PANEL,
    font=dict(color=TEXT_PRIMARY, family='-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif'),
    xaxis=dict(gridcolor=DARK_BORDER, zerolinecolor=DARK_BORDER, color=TEXT_SECONDARY),
    yaxis=dict(gridcolor=DARK_BORDER, zerolinecolor=DARK_BORDER, color=TEXT_SECONDARY),
    colorway=[COLORS['red'], COLORS['cyan'], COLORS['blue'], COLORS['orange'],
              COLORS['purple'], COLORS['green'], COLORS['yellow'], COLORS['pink'],
              COLORS['teal'], COLORS['amber']],
    margin=dict(l=50, r=30, t=70, b=50),
)


def apply_plotly_theme(fig):
    fig.update_layout(**PLOTLY_DARK)
    return fig


BANNER_CSS = """
<style>
  body {{ background:{bg}; color:{fg}; margin:0; padding:0;
         font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }}
  .step-banner {{ background:{panel}; border-left:6px solid {accent}; padding:18px 28px;
                  border-bottom:1px solid {border}; }}
  .step-banner h1 {{ margin:0 0 4px 0; font-size:22px; color:{fg}; }}
  .step-banner h2 {{ margin:0; font-size:14px; font-weight:400; color:{muted}; }}
  .step-footer {{ padding:12px 28px; font-size:12px; color:{muted};
                  border-top:1px solid {border}; margin-top:18px; }}
  a {{ color:{accent}; text-decoration:none; }}
  a:hover {{ text-decoration:underline; }}
  .content {{ padding:18px 28px; }}
  .sidebar-note {{ background:{panel}; border:1px solid {border}; padding:10px 14px;
                   margin:10px 0; border-radius:6px; font-size:13px; color:{muted}; }}
  table {{ border-collapse:collapse; width:100%; color:{fg}; font-size:13px; }}
  th, td {{ border:1px solid {border}; padding:6px 10px; text-align:left; }}
  th {{ background:{panel}; }}
</style>
""".format(
    bg=DARK_BG, fg=TEXT_PRIMARY, panel=DARK_PANEL, border=DARK_BORDER,
    accent=CN_COLOR, muted=TEXT_SECONDARY,
)


def _step_banner(step_num, title_zh, title_en, source=None):
    src_line = ''
    if source:
        src_line = f'<span style="margin-left:16px;color:{COLORS["cyan"]};font-size:12px;">[{source}]</span>'
    return (
        f'<div class="step-banner">'
        f'<h1>Step {step_num:02d} · {title_zh}{src_line}</h1>'
        f'<h2>{title_en}</h2></div>'
    )


def _step_footer(step_num):
    return (
        f'<div class="step-footer">'
        f'中国互联网全球位置分析 · Internet Yellow Pages · '
        f'Step {step_num:02d} / 20 · '
        f'<a href="index.html">← 返回目录 / Back to index</a>'
        f'</div>'
    )


def save_plotly_html(fig, name, step_num, title_zh, title_en, source=None, writeup_html=''):
    """Export a Plotly figure to html/<name> with bilingual banner + footer.

    fig can be a single Figure; if a list, they are stacked vertically.
    """
    apply_plotly_theme(fig)
    from plotly.io import to_html
    fig_html = to_html(fig, include_plotlyjs='inline', full_html=False, default_height='720px')
    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        f'<title>Step {step_num:02d} · {title_zh}</title>'
        f'{BANNER_CSS}</head><body>'
        f'{_step_banner(step_num, title_zh, title_en, source)}'
        '<div class="content">'
        f'{writeup_html}'
        f'{fig_html}'
        '</div>'
        f'{_step_footer(step_num)}'
        '</body></html>'
    )
    path = os.path.join(HTML_DIR, name)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'[html] wrote {path} ({os.path.getsize(path)//1024} KB)')
    return path


def save_multi_plotly_html(figs, name, step_num, title_zh, title_en, source=None, writeup_html='',
                            subtitles=None):
    """Save multiple plotly figures stacked in one HTML. figs is a list, subtitles optional list."""
    from plotly.io import to_html
    parts = []
    first = True
    for i, fig in enumerate(figs):
        apply_plotly_theme(fig)
        sub = ''
        if subtitles and i < len(subtitles) and subtitles[i]:
            sub = f'<h3 style="color:{TEXT_PRIMARY};margin:24px 0 6px 0">{subtitles[i]}</h3>'
        parts.append(
            sub + to_html(fig, include_plotlyjs=('inline' if first else False),
                          full_html=False, default_height='560px')
        )
        first = False
    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        f'<title>Step {step_num:02d} · {title_zh}</title>'
        f'{BANNER_CSS}</head><body>'
        f'{_step_banner(step_num, title_zh, title_en, source)}'
        f'<div class="content">{writeup_html}{"".join(parts)}</div>'
        f'{_step_footer(step_num)}'
        '</body></html>'
    )
    path = os.path.join(HTML_DIR, name)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'[html] wrote {path} ({os.path.getsize(path)//1024} KB)')
    return path


def save_pyvis_html(net, name, step_num, title_zh, title_en, source=None, writeup_html=''):
    """Save a pyvis Network, then rewrap with bilingual banner."""
    tmp_path = os.path.join(HTML_DIR, f'_pyvis_{name}')
    net.save_graph(tmp_path)
    with open(tmp_path, encoding='utf-8') as f:
        inner = f.read()
    # Extract the <body> content from pyvis output
    body_start = inner.find('<body')
    body_content_start = inner.find('>', body_start) + 1
    body_end = inner.rfind('</body>')
    body = inner[body_content_start:body_end]
    head_end = inner.find('</head>')
    head = inner[:head_end]
    html = (
        f'{head}{BANNER_CSS}</head><body style="background:{DARK_BG};">'
        f'{_step_banner(step_num, title_zh, title_en, source)}'
        f'<div class="content">{writeup_html}<div style="background:{DARK_PANEL};'
        f'border:1px solid {DARK_BORDER};border-radius:8px;">{body}</div></div>'
        f'{_step_footer(step_num)}'
        '</body></html>'
    )
    path = os.path.join(HTML_DIR, name)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    os.remove(tmp_path)
    print(f'[html] wrote {path} ({os.path.getsize(path)//1024} KB)')
    return path


def save_placeholder_html(name, step_num, title_zh, title_en, message_zh, message_en):
    """Emit placeholder HTML when data is unavailable."""
    html = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        f'<title>Step {step_num:02d} · {title_zh}</title>'
        f'{BANNER_CSS}</head><body>'
        f'{_step_banner(step_num, title_zh, title_en, "unavailable")}'
        f'<div class="content"><div class="sidebar-note">'
        f'<b>{message_zh}</b><br><br>{message_en}</div></div>'
        f'{_step_footer(step_num)}'
        '</body></html>'
    )
    path = os.path.join(HTML_DIR, name)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'[html] wrote placeholder {path}')
    return path


# ─────────────────────────────────────────────────────────────
# Metrics sidecars
# ─────────────────────────────────────────────────────────────

def write_step_metrics(step_num, metrics, title_zh='', title_en=''):
    path = os.path.join(DATA_DIR, f'step{step_num:02d}_metrics.json')
    payload = {'step': step_num, 'title_zh': title_zh, 'title_en': title_en, 'metrics': metrics}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f'[metrics] wrote {path}')
    return path


def read_step_metrics(step_num):
    path = os.path.join(DATA_DIR, f'step{step_num:02d}_metrics.json')
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def write_csv(name, rows, fieldnames=None):
    """Utility: write list-of-dicts to data/<name>."""
    if not rows:
        print(f'[csv] {name}: empty, skipping write')
        return None
    path = os.path.join(DATA_DIR, name)
    if fieldnames is None:
        fieldnames = list(rows[0].keys())
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f'[csv] wrote {path} ({len(rows)} rows)')
    return path


# ─────────────────────────────────────────────────────────────
# Scientific panel writeup helper
# ─────────────────────────────────────────────────────────────

def writeup(hypothesis, finding, reference=''):
    """Return an HTML sidebar-note with established-science hypothesis and CN result."""
    ref = f'<br><i style="color:{TEXT_SECONDARY}">参考 Reference: {reference}</i>' if reference else ''
    return (
        f'<div class="sidebar-note">'
        f'<b>假设 Hypothesis:</b> {hypothesis}<br><br>'
        f'<b>中国数据结果 CN Finding:</b> {finding}{ref}'
        f'</div>'
    )
