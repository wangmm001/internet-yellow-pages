"""Step 9: Rich-club coefficient analysis."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.complex_network.utils import *

import numpy as np
import csv
import networkx as nx
from collections import Counter

def load_bgp_graph():
    G = nx.Graph()
    with open(os.path.join(DATA_DIR, 'bgp_peering.csv')) as f:
        for row in csv.DictReader(f):
            G.add_edge(int(row['src']), int(row['dst']))
    return G

def main():
    print('Loading BGP graph...')
    G = load_bgp_graph()
    N = G.number_of_nodes()
    degrees = dict(G.degree())

    # Compute rich-club coefficient
    print('Computing rich-club coefficient...')
    rc = nx.rich_club_coefficient(G, normalized=False)
    k_values = sorted(rc.keys())
    rc_values = [rc[k] for k in k_values]

    # Generate configuration model for normalization (10 randomizations)
    print('Generating configuration model baseline (10 randomizations)...')
    n_rand = 10
    rc_rand_all = []

    for i in range(n_rand):
        print(f'  Randomization {i+1}/{n_rand}...')
        # Degree-preserving random rewiring
        G_rand = G.copy()
        # Use double-edge swap
        n_swaps = G.number_of_edges() * 10
        try:
            nx.double_edge_swap(G_rand, nswap=n_swaps, max_tries=n_swaps * 10, seed=42 + i)
        except nx.NetworkXAlgorithmError:
            pass
        rc_r = nx.rich_club_coefficient(G_rand, normalized=False)
        rc_rand_all.append(rc_r)

    # Compute normalized rich-club
    print('Computing normalized rich-club coefficient...')
    rc_norm = {}
    rc_rand_mean = {}
    rc_rand_std = {}
    for k in k_values:
        rand_vals = [r.get(k, 0) for r in rc_rand_all if k in r]
        if rand_vals and np.mean(rand_vals) > 0:
            rc_rand_mean[k] = np.mean(rand_vals)
            rc_rand_std[k] = np.std(rand_vals)
            rc_norm[k] = rc[k] / rc_rand_mean[k]
        else:
            rc_norm[k] = 1.0
            rc_rand_mean[k] = rc[k]
            rc_rand_std[k] = 0

    # Find rich-club regime
    rich_club_start = None
    for k in k_values:
        if k > 10 and rc_norm.get(k, 0) > 1.1:
            rich_club_start = k
            break

    # ── Visualization ──
    fig = plt.figure(figsize=(28, 10))
    fig.patch.set_facecolor(DARK_BG)
    gs = fig.add_gridspec(1, 3, wspace=0.3, left=0.06, right=0.96, top=0.85, bottom=0.08)

    # Panel 1: Raw rich-club coefficient
    ax1 = fig.add_subplot(gs[0, 0])
    style_ax(ax1, 'Rich-Club Coefficient φ(k)', 'Degree k', 'φ(k)')
    # Filter for reasonable k range
    k_plot = [k for k in k_values if k <= 500]
    ax1.plot(k_plot, [rc[k] for k in k_plot], '-', color=COLORS['red'],
             linewidth=2, label='Real network')
    rand_mean_plot = [rc_rand_mean.get(k, 0) for k in k_plot]
    rand_std_plot = [rc_rand_std.get(k, 0) for k in k_plot]
    ax1.plot(k_plot, rand_mean_plot, '--', color=COLORS['blue'],
             linewidth=1.5, label='Config model (mean)')
    ax1.fill_between(k_plot,
                     [m - 2*s for m, s in zip(rand_mean_plot, rand_std_plot)],
                     [m + 2*s for m, s in zip(rand_mean_plot, rand_std_plot)],
                     color=COLORS['blue'], alpha=0.15, label='±2σ')
    ax1.set_xscale('log')
    ax1.legend(fontsize=9, facecolor=DARK_PANEL, edgecolor=DARK_BORDER, labelcolor=TEXT_MUTED)

    # Panel 2: Normalized rich-club coefficient
    ax2 = fig.add_subplot(gs[0, 1])
    style_ax(ax2, 'Normalized Rich-Club ρ(k) = φ(k)/φ_rand(k)', 'Degree k', 'ρ(k)')
    rc_norm_plot = [rc_norm.get(k, 1) for k in k_plot]
    ax2.plot(k_plot, rc_norm_plot, '-', color=COLORS['cyan'], linewidth=2)
    ax2.axhline(1.0, color=DARK_BORDER, linestyle='--', linewidth=1)
    ax2.fill_between(k_plot, 1.0, rc_norm_plot,
                     where=[v > 1 for v in rc_norm_plot],
                     alpha=0.2, color=COLORS['red'], label='Rich-club regime')
    if rich_club_start:
        ax2.axvline(rich_club_start, color=COLORS['yellow'], linestyle=':',
                    label=f'Rich-club starts at k={rich_club_start}')
    ax2.set_xscale('log')
    ax2.set_ylim(0.5, max(2.5, max(rc_norm_plot[:len(k_plot)]) * 1.1))
    ax2.legend(fontsize=9, facecolor=DARK_PANEL, edgecolor=DARK_BORDER, labelcolor=TEXT_MUTED)

    # Panel 3: Rich-club members
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.set_facecolor(DARK_PANEL)
    ax3.axis('off')
    ax3.set_title('Rich-Club Interpretation', fontsize=14, fontweight='bold',
                  color=TEXT_PRIMARY, pad=12)

    # Count ASes at various k thresholds
    deg_counter = Counter(degrees.values())
    lines = [f'{"k threshold":>12} {"ASes with k≥":>14} {"% of total":>12}']
    lines.append('─' * 42)
    for k_thresh in [10, 50, 100, 200, 500, 1000, 5000, 10000]:
        n_above = sum(1 for d in degrees.values() if d >= k_thresh)
        if n_above > 0:
            lines.append(f'{k_thresh:>12,} {n_above:>14,} {n_above/N*100:>11.3f}%')

    lines.append('')
    lines.append('Rich-club phenomenon:')
    if rich_club_start:
        lines.append(f'  Starts at k ≥ {rich_club_start}')
        n_rc = sum(1 for d in degrees.values() if d >= rich_club_start)
        lines.append(f'  Rich-club size: {n_rc} ASes')
        lines.append(f'  = {n_rc/N*100:.2f}% of all ASes')
        lines.append('')
        lines.append('Interpretation:')
        lines.append('  High-degree ASes interconnect')
        lines.append('  MORE than expected by chance.')
        lines.append('  This creates a resilient core')
        lines.append('  but also concentration risk.')
    else:
        lines.append('  No clear rich-club detected')

    ax3.text(0.05, 0.95, '\n'.join(lines), transform=ax3.transAxes,
             fontsize=10, color=TEXT_MUTED, va='top', family='monospace',
             bbox=dict(boxstyle='round,pad=0.5', facecolor=DARK_BG, edgecolor=DARK_BORDER))

    fig.suptitle(
        'Rich-Club Analysis of AS-Level Internet Topology\n'
        f'{N:,} ASes | {n_rand} Configuration Model Randomizations | IYP 2026-04-08',
        fontsize=16, fontweight='bold', color=TEXT_PRIMARY, y=0.96
    )

    save_fig(fig, 'step09_rich_club.png')

    # Save data
    rc_path = os.path.join(DATA_DIR, 'step09_rich_club.csv')
    with open(rc_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['k', 'phi_real', 'phi_rand_mean', 'phi_rand_std', 'rho_normalized'])
        for k in k_values:
            w.writerow([k, rc[k], rc_rand_mean.get(k, 0), rc_rand_std.get(k, 0), rc_norm.get(k, 1)])
    print(f'Saved rich-club data to {rc_path}')


if __name__ == '__main__':
    main()
