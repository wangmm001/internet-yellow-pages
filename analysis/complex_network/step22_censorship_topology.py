"""Step 22: Censorship topology pattern analysis."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.complex_network.utils import *

import numpy as np
import csv
import networkx as nx
from collections import Counter, defaultdict

def load_bgp_graph():
    G = nx.Graph()
    with open(os.path.join(DATA_DIR, 'bgp_peering.csv')) as f:
        for row in csv.DictReader(f):
            G.add_edge(int(row['src']), int(row['dst']))
    return G

def load_censorship():
    censor = defaultdict(lambda: defaultdict(int))  # asn -> test_name -> count
    with open(os.path.join(DATA_DIR, 'censorship.csv')) as f:
        for row in csv.DictReader(f):
            asn = int(row['asn'])
            test = row['test_name']
            cnt = int(row['detection_count']) if row['detection_count'] else 1
            censor[asn][test] += cnt
    return censor

def load_as_country():
    as_cc = {}
    with open(os.path.join(DATA_DIR, 'as_country.csv')) as f:
        for row in csv.DictReader(f):
            asn = int(row['asn'])
            if asn not in as_cc:
                as_cc[asn] = row['country']
    return as_cc

def load_coreness():
    core = {}
    path = os.path.join(DATA_DIR, 'step08_coreness.csv')
    if not os.path.exists(path):
        return core
    with open(path) as f:
        for row in csv.DictReader(f):
            core[int(row['asn'])] = int(row['coreness'])
    return core

def main():
    print('Loading data...')
    G = load_bgp_graph()
    censor = load_censorship()
    as_cc = load_as_country()
    coreness = load_coreness()

    censoring_ases = set(censor.keys())
    all_tests = set()
    for asn_tests in censor.values():
        all_tests.update(asn_tests.keys())
    all_tests = sorted(all_tests)

    print(f'  Censoring ASes: {len(censoring_ases):,}')
    print(f'  Tests detected: {len(all_tests)}')

    # Country-level censorship
    country_censor = defaultdict(lambda: Counter())
    country_as_censor_count = Counter()
    for asn, tests in censor.items():
        cc = as_cc.get(asn, 'Unknown')
        country_as_censor_count[cc] += 1
        for test, cnt in tests.items():
            country_censor[cc][test] += 1

    top_countries = country_as_censor_count.most_common(20)
    print(f'  Top censoring countries: {[(c, n) for c, n in top_countries[:5]]}')

    # Censorship vs network position
    censoring_degrees = [G.degree(n) for n in censoring_ases if n in G]
    non_censoring = [n for n in G.nodes() if n not in censoring_ases]
    non_censoring_degrees = [G.degree(n) for n in non_censoring]

    censoring_cores = [coreness.get(n, 0) for n in censoring_ases]
    non_censoring_cores = [coreness.get(n, 0) for n in non_censoring]

    # ── Visualization ──
    fig = plt.figure(figsize=(30, 18))
    fig.patch.set_facecolor(DARK_BG)
    gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.35,
                          left=0.06, right=0.96, top=0.90, bottom=0.06)

    # Panel 1: Country × Test heatmap
    ax1 = fig.add_subplot(gs[0, :2])
    style_ax(ax1, 'Internet Censorship Heatmap\n(ASes with OONI anomalies per country × test)')

    top_cc = [c for c, _ in top_countries[:15]]
    # Select tests with most detections
    test_totals = Counter()
    for cc_data in country_censor.values():
        for t, n in cc_data.items():
            test_totals[t] += n
    top_tests = [t for t, _ in test_totals.most_common(12)]

    heat = np.zeros((len(top_cc), len(top_tests)))
    for i, cc in enumerate(top_cc):
        for j, test in enumerate(top_tests):
            heat[i, j] = country_censor[cc].get(test, 0)

    # Shorten test names
    test_short = [t.split('.')[-1][:20] for t in top_tests]

    im = ax1.imshow(heat, cmap='YlOrRd', aspect='auto')
    ax1.set_xticks(range(len(top_tests)))
    ax1.set_yticks(range(len(top_cc)))
    ax1.set_xticklabels(test_short, fontsize=8, color=TEXT_MUTED, rotation=45, ha='right')
    ax1.set_yticklabels(top_cc, fontsize=10, color=TEXT_MUTED)
    for i in range(len(top_cc)):
        for j in range(len(top_tests)):
            if heat[i, j] > 0:
                ax1.text(j, i, f'{int(heat[i,j])}', ha='center', va='center',
                         fontsize=7, color='white' if heat[i,j] > heat.max()*0.5 else TEXT_MUTED)
    plt.colorbar(im, ax=ax1, shrink=0.6, label='# ASes with anomalies')

    # Panel 2: Censoring ASes per country bar
    ax2 = fig.add_subplot(gs[0, 2])
    style_ax(ax2, 'Censoring ASes by Country\n(Top 15)', '', 'Number of ASes')
    cc_labels = [c for c, _ in top_countries[:15]]
    cc_vals = [n for _, n in top_countries[:15]]
    bars = ax2.barh(range(len(cc_labels)), cc_vals, color=COLORS['red'],
                    edgecolor=DARK_BORDER, height=0.6)
    ax2.set_yticks(range(len(cc_labels)))
    ax2.set_yticklabels(cc_labels, fontsize=10, color=TEXT_MUTED)
    for bar, val in zip(bars, cc_vals):
        ax2.text(bar.get_width() + 2, bar.get_y() + bar.get_height()/2,
                 str(val), va='center', fontsize=9, color=TEXT_PRIMARY)

    # Panel 3: Degree distribution comparison (censoring vs non-censoring)
    ax3 = fig.add_subplot(gs[1, 0])
    style_ax(ax3, 'Degree Distribution: Censoring vs Non-Censoring ASes',
             'Degree', 'Density')
    bins = np.logspace(0, np.log10(max(max(censoring_degrees, default=1),
                                        max(non_censoring_degrees, default=1)) + 1), 40)
    ax3.hist(censoring_degrees, bins=bins, density=True, alpha=0.6,
             color=COLORS['red'], label=f'Censoring ({len(censoring_degrees):,})', edgecolor=DARK_BORDER)
    ax3.hist(non_censoring_degrees, bins=bins, density=True, alpha=0.4,
             color=COLORS['blue'], label=f'Non-censoring ({len(non_censoring_degrees):,})', edgecolor=DARK_BORDER)
    ax3.set_xscale('log')
    ax3.legend(fontsize=10, facecolor=DARK_PANEL, edgecolor=DARK_BORDER, labelcolor=TEXT_MUTED)

    # Panel 4: Coreness distribution comparison
    ax4 = fig.add_subplot(gs[1, 1])
    style_ax(ax4, 'k-Core Distribution: Censoring vs Non-Censoring',
             'Coreness', 'Density')
    max_core = max(max(censoring_cores, default=1), max(non_censoring_cores, default=1))
    bins_core = np.linspace(0, min(max_core + 1, 100), 50)
    ax4.hist(censoring_cores, bins=bins_core, density=True, alpha=0.6,
             color=COLORS['red'], label='Censoring', edgecolor=DARK_BORDER)
    ax4.hist(non_censoring_cores, bins=bins_core, density=True, alpha=0.4,
             color=COLORS['blue'], label='Non-censoring', edgecolor=DARK_BORDER)
    ax4.legend(fontsize=10, facecolor=DARK_PANEL, edgecolor=DARK_BORDER, labelcolor=TEXT_MUTED)

    from scipy.stats import mannwhitneyu
    if censoring_cores and non_censoring_cores:
        u_stat, p_val = mannwhitneyu(censoring_cores, non_censoring_cores, alternative='two-sided')
        ax4.text(0.95, 0.95, f'Mann-Whitney U\np = {p_val:.2e}',
                 transform=ax4.transAxes, ha='right', va='top',
                 fontsize=10, color=TEXT_PRIMARY,
                 bbox=dict(boxstyle='round,pad=0.3', facecolor=DARK_BG, edgecolor=DARK_BORDER))

    # Panel 5: Summary
    ax5 = fig.add_subplot(gs[1, 2])
    ax5.set_facecolor(DARK_PANEL)
    ax5.axis('off')
    ax5.set_title('Censorship Topology Analysis', fontsize=14, fontweight='bold',
                  color=TEXT_PRIMARY, pad=12)

    lines = [
        f'Total censoring ASes: {len(censoring_ases):,}',
        f'Total OONI tests: {len(all_tests)}',
        f'Countries with censorship: {len(country_as_censor_count)}',
        '',
        'NETWORK POSITION COMPARISON:',
        '─' * 40,
        f'{"Metric":<20} {"Censoring":>12} {"Non-Censor":>12}',
        f'{"Mean degree":<20} {np.mean(censoring_degrees):>12.1f} {np.mean(non_censoring_degrees):>12.1f}',
        f'{"Median degree":<20} {np.median(censoring_degrees):>12.0f} {np.median(non_censoring_degrees):>12.0f}',
        f'{"Mean coreness":<20} {np.mean(censoring_cores):>12.1f} {np.mean(non_censoring_cores):>12.1f}',
        f'{"Median coreness":<20} {np.median(censoring_cores):>12.0f} {np.median(non_censoring_cores):>12.0f}',
        '',
        'TOP CENSORED SERVICES:',
        '─' * 40,
    ]
    for test, cnt in test_totals.most_common(8):
        lines.append(f'  {test.split(".")[-1]:<25} {cnt:>5} ASes')

    ax5.text(0.05, 0.95, '\n'.join(lines), transform=ax5.transAxes,
             fontsize=9, color=TEXT_MUTED, va='top', family='monospace',
             bbox=dict(boxstyle='round,pad=0.5', facecolor=DARK_BG, edgecolor=DARK_BORDER))

    fig.suptitle(
        'Internet Censorship Topology Analysis (OONI Data)\n'
        f'{len(censoring_ases):,} Censoring ASes | {len(all_tests)} Test Types | IYP 2026-04-08',
        fontsize=16, fontweight='bold', color=TEXT_PRIMARY, y=0.96
    )

    save_fig(fig, 'step22_censorship_topology.png')


if __name__ == '__main__':
    main()
