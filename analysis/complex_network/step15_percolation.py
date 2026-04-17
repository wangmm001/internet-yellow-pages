"""Step 15: Percolation analysis — random failure vs targeted attack."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.complex_network.utils import *

import numpy as np
import csv
import networkx as nx
import random

def load_bgp_graph():
    G = nx.Graph()
    with open(os.path.join(DATA_DIR, 'bgp_peering.csv')) as f:
        for row in csv.DictReader(f):
            G.add_edge(int(row['src']), int(row['dst']))
    return G

def gcc_fraction(G, original_size):
    """Compute GCC size as fraction of original graph."""
    if G.number_of_nodes() == 0:
        return 0
    comps = nx.connected_components(G)
    gcc_size = max(len(c) for c in comps)
    return gcc_size / original_size

def percolation_curve(G, removal_order, steps=50):
    """Remove nodes in order, measure GCC at each step.
    Returns (fractions_removed, gcc_fractions).
    """
    N = G.number_of_nodes()
    G_copy = G.copy()
    n_remove_total = min(len(removal_order), int(N * 0.3))  # up to 30%
    step_size = max(1, n_remove_total // steps)

    fracs = [0]
    gccs = [gcc_fraction(G_copy, N)]

    removed = 0
    for i in range(0, n_remove_total, step_size):
        batch = removal_order[i:i+step_size]
        existing = [n for n in batch if n in G_copy]
        G_copy.remove_nodes_from(existing)
        removed += len(existing)
        fracs.append(removed / N)
        gccs.append(gcc_fraction(G_copy, N))

    return np.array(fracs), np.array(gccs)

def main():
    print('Loading BGP graph...')
    G = load_bgp_graph()
    N = G.number_of_nodes()
    print(f'  N={N:,}, M={G.number_of_edges():,}')

    steps = 60

    # ── Strategy 1: Degree attack ──
    print('Strategy 1: Degree-based targeted attack...')
    degree_order = sorted(G.nodes(), key=lambda n: G.degree(n), reverse=True)
    f_deg, g_deg = percolation_curve(G, degree_order, steps)

    # ── Strategy 2: Approximate betweenness attack ──
    print('Strategy 2: Betweenness-based targeted attack (approx k=2000)...')
    bet_c = nx.betweenness_centrality(G, k=2000, seed=42)
    bet_order = sorted(bet_c, key=bet_c.get, reverse=True)
    f_bet, g_bet = percolation_curve(G, bet_order, steps)

    # ── Strategy 3: PageRank attack ──
    print('Strategy 3: PageRank-based targeted attack...')
    pr = nx.pagerank(G, alpha=0.85)
    pr_order = sorted(pr, key=pr.get, reverse=True)
    f_pr, g_pr = percolation_curve(G, pr_order, steps)

    # ── Strategy 4: k-core attack (remove highest coreness first) ──
    print('Strategy 4: k-core-based targeted attack...')
    core_numbers = nx.core_number(G)
    core_order = sorted(core_numbers, key=core_numbers.get, reverse=True)
    f_core, g_core = percolation_curve(G, core_order, steps)

    # ── Strategy 5: Random failure (30 trials) ──
    print('Strategy 5: Random failure (30 trials)...')
    n_trials = 30
    all_random = []
    nodes_list = list(G.nodes())
    for trial in range(n_trials):
        if trial % 10 == 0:
            print(f'  Trial {trial+1}/{n_trials}...')
        rng = random.Random(42 + trial)
        rand_order = nodes_list.copy()
        rng.shuffle(rand_order)
        f_r, g_r = percolation_curve(G, rand_order, steps)
        all_random.append((f_r, g_r))

    # Average random curves (interpolated to common x)
    f_common = np.linspace(0, 0.3, steps + 1)
    g_rand_all = []
    for f_r, g_r in all_random:
        g_interp = np.interp(f_common, f_r, g_r)
        g_rand_all.append(g_interp)
    g_rand_mean = np.mean(g_rand_all, axis=0)
    g_rand_std = np.std(g_rand_all, axis=0)

    # ── Compute critical thresholds (GCC drops below 50%) ──
    def find_threshold(f_arr, g_arr, threshold=0.5):
        for i, g in enumerate(g_arr):
            if g < threshold:
                return f_arr[i]
        return f_arr[-1]

    thresholds = {
        'Degree': find_threshold(f_deg, g_deg),
        'Betweenness': find_threshold(f_bet, g_bet),
        'PageRank': find_threshold(f_pr, g_pr),
        'k-Core': find_threshold(f_core, g_core),
        'Random': find_threshold(f_common, g_rand_mean),
    }

    print('\n── Percolation Thresholds (GCC < 50%) ──')
    for name, t in thresholds.items():
        print(f'  {name}: {t*100:.1f}% removed')

    # ── R-index (area under GCC curve, normalized) ──
    def r_index(f_arr, g_arr):
        try:
            return np.trapezoid(g_arr, f_arr) / (f_arr[-1] - f_arr[0])
        except AttributeError:
            # Fallback for older numpy
            return np.trapz(g_arr, f_arr) / (f_arr[-1] - f_arr[0])

    r_indices = {
        'Degree': r_index(f_deg, g_deg),
        'Betweenness': r_index(f_bet, g_bet),
        'PageRank': r_index(f_pr, g_pr),
        'k-Core': r_index(f_core, g_core),
        'Random': r_index(f_common, g_rand_mean),
    }

    print('\n── R-index (Area Under Curve, 0-1) ──')
    for name, r in r_indices.items():
        print(f'  {name}: {r:.4f}')

    # ── Visualization ──
    fig = plt.figure(figsize=(30, 18))
    fig.patch.set_facecolor(DARK_BG)
    gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.35,
                          left=0.06, right=0.96, top=0.90, bottom=0.06)

    # Panel 1: All percolation curves
    ax1 = fig.add_subplot(gs[0, :2])
    style_ax(ax1, 'Percolation Analysis: GCC Size Under Node Removal',
             'Fraction of Nodes Removed', 'GCC / Original Size')
    ax1.plot(f_deg * 100, g_deg, '-', color=COLORS['red'], linewidth=2.5, label='Degree Attack')
    ax1.plot(f_bet * 100, g_bet, '-', color=COLORS['cyan'], linewidth=2.5, label='Betweenness Attack')
    ax1.plot(f_pr * 100, g_pr, '-', color=COLORS['purple'], linewidth=2.5, label='PageRank Attack')
    ax1.plot(f_core * 100, g_core, '-', color=COLORS['orange'], linewidth=2.5, label='k-Core Attack')
    ax1.plot(f_common * 100, g_rand_mean, '-', color=COLORS['green'], linewidth=2.5, label='Random Failure')
    ax1.fill_between(f_common * 100,
                     g_rand_mean - 2 * g_rand_std,
                     g_rand_mean + 2 * g_rand_std,
                     color=COLORS['green'], alpha=0.15)
    ax1.axhline(0.5, color=DARK_BORDER, linestyle='--', linewidth=1, alpha=0.5)
    ax1.set_xlim(0, 30)
    ax1.set_ylim(0, 1.05)
    ax1.legend(fontsize=11, facecolor=DARK_PANEL, edgecolor=DARK_BORDER, labelcolor=TEXT_MUTED,
               loc='upper right')

    # Add threshold markers
    for name, t in thresholds.items():
        if t < 0.3:
            ax1.axvline(t * 100, color=DARK_BORDER, linestyle=':', linewidth=0.5, alpha=0.3)

    # Panel 2: Threshold bar chart
    ax2 = fig.add_subplot(gs[0, 2])
    style_ax(ax2, 'Critical Threshold\n(% removed for GCC < 50%)', '', 'Nodes Removed (%)')
    names_list = list(thresholds.keys())
    thresh_vals = [thresholds[n] * 100 for n in names_list]
    colors_bar = [COLORS['red'], COLORS['cyan'], COLORS['purple'], COLORS['orange'], COLORS['green']]
    bars = ax2.barh(range(len(names_list)), thresh_vals, color=colors_bar,
                    edgecolor=DARK_BORDER, height=0.6)
    ax2.set_yticks(range(len(names_list)))
    ax2.set_yticklabels(names_list, fontsize=11, color=TEXT_MUTED)
    for bar, val in zip(bars, thresh_vals):
        ax2.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                 f'{val:.1f}%', va='center', fontsize=11, color=TEXT_PRIMARY, fontweight='bold')

    # Panel 3: R-index comparison
    ax3 = fig.add_subplot(gs[1, 0])
    style_ax(ax3, 'Resilience Index (R)\n(AUC of GCC curve, 0-1)', '', 'R-Index')
    r_vals = [r_indices[n] for n in names_list]
    bars3 = ax3.barh(range(len(names_list)), r_vals, color=colors_bar,
                     edgecolor=DARK_BORDER, height=0.6)
    ax3.set_yticks(range(len(names_list)))
    ax3.set_yticklabels(names_list, fontsize=11, color=TEXT_MUTED)
    for bar, val in zip(bars3, r_vals):
        ax3.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height()/2,
                 f'{val:.4f}', va='center', fontsize=10, color=TEXT_PRIMARY, fontweight='bold')

    # Panel 4: Number of components during attack
    ax4 = fig.add_subplot(gs[1, 1])
    style_ax(ax4, 'Network Fragmentation\n(components vs removal)', 'Fraction Removed (%)', 'Number of Components')

    # Recompute component counts for degree attack
    G_copy = G.copy()
    n_remove_total = int(N * 0.3)
    step_size = max(1, n_remove_total // steps)
    comp_fracs = [0]
    comp_counts = [nx.number_connected_components(G_copy)]
    removed = 0
    for i in range(0, n_remove_total, step_size):
        batch = degree_order[i:i+step_size]
        existing = [n for n in batch if n in G_copy]
        G_copy.remove_nodes_from(existing)
        removed += len(existing)
        comp_fracs.append(removed / N * 100)
        comp_counts.append(nx.number_connected_components(G_copy))

    ax4.plot(comp_fracs, comp_counts, '-', color=COLORS['red'], linewidth=2, label='Degree Attack')
    ax4.set_yscale('log')
    ax4.legend(fontsize=10, facecolor=DARK_PANEL, edgecolor=DARK_BORDER, labelcolor=TEXT_MUTED)

    # Panel 5: Key findings summary
    ax5 = fig.add_subplot(gs[1, 2])
    ax5.set_facecolor(DARK_PANEL)
    ax5.axis('off')
    ax5.set_title('Resilience Analysis Summary', fontsize=14, fontweight='bold',
                  color=TEXT_PRIMARY, pad=12)

    most_effective = min(thresholds.items(), key=lambda x: x[1])
    most_resilient = max(thresholds.items(), key=lambda x: x[1])

    lines = [
        'PERCOLATION THRESHOLDS (GCC < 50%):',
        '─' * 40,
    ]
    for name in names_list:
        t = thresholds[name]
        n_nodes = int(t * N)
        lines.append(f'  {name:<15} {t*100:>5.1f}% ({n_nodes:>6,} ASes)')
    lines.extend([
        '',
        'KEY FINDINGS:',
        '─' * 40,
        f'Most effective attack: {most_effective[0]}',
        f'  → Only {most_effective[1]*100:.1f}% removal to fragment',
        f'Most resilient to: {most_resilient[0]}',
        f'  → Tolerates {most_resilient[1]*100:.1f}% removal',
        '',
        f'Vulnerability ratio:',
        f'  random/targeted = {thresholds["Random"]/most_effective[1]:.1f}x',
        '',
        'INTERPRETATION:',
        'Scale-free network: resilient to',
        'random failure but fragile to',
        'targeted attacks on high-degree hubs.',
    ])

    ax5.text(0.05, 0.95, '\n'.join(lines), transform=ax5.transAxes,
             fontsize=9, color=TEXT_MUTED, va='top', family='monospace',
             bbox=dict(boxstyle='round,pad=0.5', facecolor=DARK_BG, edgecolor=DARK_BORDER))

    fig.suptitle(
        'Internet Resilience: Percolation Analysis of AS Topology\n'
        f'{N:,} ASes | {G.number_of_edges():,} Edges | 5 Attack Strategies | {n_trials} Random Trials | IYP 2026-04-08',
        fontsize=16, fontweight='bold', color=TEXT_PRIMARY, y=0.96
    )

    save_fig(fig, 'step15_percolation.png')

    # Save percolation data
    perc_path = os.path.join(DATA_DIR, 'step15_percolation.csv')
    with open(perc_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['strategy', 'threshold_pct', 'r_index'])
        for name in names_list:
            w.writerow([name, thresholds[name] * 100, r_indices[name]])
    print(f'Saved percolation data to {perc_path}')


if __name__ == '__main__':
    main()
