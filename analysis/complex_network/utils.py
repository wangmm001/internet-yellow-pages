"""Shared utilities for complex network analysis."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import os

# ── Neo4j connection ──
NEO4J_URI = 'bolt://localhost:7687'
NEO4J_USER = 'neo4j'
NEO4J_PASS = 'neo4j'

# ── Paths ──
# Raw / derived CSVs live in a repo-root data_cache/ directory that is
# git-ignored (they're large regeneratable query results). Analysis PNGs
# live alongside the analysis code.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..', '..'))
IMG_DIR = os.path.join(os.path.dirname(BASE_DIR), 'complex_network_images')
DATA_DIR = os.environ.get(
    'IYP_ANALYSIS_DATA_DIR',
    os.path.join(REPO_ROOT, 'data_cache', 'complex_network'),
)
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


def get_neo4j_driver():
    from neo4j import GraphDatabase
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))


def run_query(query, params=None):
    """Run a Cypher query and return list of record dicts."""
    driver = get_neo4j_driver()
    with driver.session() as session:
        result = session.run(query, params or {})
        records = [dict(r) for r in result]
    driver.close()
    return records


def run_query_to_csv(query, filepath, params=None):
    """Run query and save results as CSV."""
    import csv
    records = run_query(query, params)
    if not records:
        print(f'WARNING: query returned 0 records for {filepath}')
        return records
    keys = list(records[0].keys())
    with open(filepath, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(records)
    print(f'Saved {len(records)} rows to {filepath}')
    return records


# ── Dark theme style ──
DARK_BG = '#0D1117'
DARK_PANEL = '#161B22'
DARK_BORDER = '#30363D'
TEXT_PRIMARY = '#E6EDF3'
TEXT_SECONDARY = '#8B949E'
TEXT_MUTED = '#C9D1D9'

COLORS = {
    'red': '#FF6B6B',
    'cyan': '#4ECDC4',
    'blue': '#45B7D1',
    'orange': '#FFA07A',
    'purple': '#B39DDB',
    'green': '#66BB6A',
    'yellow': '#FFD54F',
    'pink': '#F48FB1',
    'teal': '#26A69A',
    'amber': '#FFAB40',
}

COLOR_LIST = list(COLORS.values())


def dark_figure(rows=1, cols=1, figsize=None, **kwargs):
    """Create a dark-themed figure with subplots."""
    if figsize is None:
        figsize = (8 * cols, 6 * rows)
    fig, axes = plt.subplots(rows, cols, figsize=figsize, **kwargs)
    fig.patch.set_facecolor(DARK_BG)
    return fig, axes


def style_ax(ax, title='', xlabel='', ylabel=''):
    """Apply dark theme to an axis."""
    ax.set_facecolor(DARK_PANEL)
    if title:
        ax.set_title(title, fontsize=14, fontweight='bold', color=TEXT_PRIMARY, pad=12)
    if xlabel:
        ax.set_xlabel(xlabel, color=TEXT_SECONDARY, fontsize=11)
    if ylabel:
        ax.set_ylabel(ylabel, color=TEXT_SECONDARY, fontsize=11)
    ax.tick_params(colors=TEXT_SECONDARY, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(DARK_BORDER)


def save_fig(fig, name, dpi=180):
    """Save figure to the images directory."""
    path = os.path.join(IMG_DIR, name)
    fig.savefig(path, dpi=dpi, bbox_inches='tight', facecolor=DARK_BG, edgecolor='none')
    plt.close(fig)
    print(f'Saved: {path}')


def fmt_millions(x, _):
    return f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K' if x >= 1e3 else str(int(x))
