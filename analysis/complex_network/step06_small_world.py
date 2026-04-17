"""Step 6: Small-world properties and basic network metrics dashboard."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.complex_network.utils import *

import numpy as np
import csv
import networkx as nx
import random

def load_bgp_graph():
    G = nx.Graph()
    path = os.path.join(DATA_DIR, 'bgp_peering.csv')
    with open(path) as f:
        for row in csv.DictReader(f):
            G.add_edge(int(row['src']), int(row['dst']))
    return G

def sampled_avg_path_length(G, n_samples=2000, seed=42):
    """Approximate average path length by sampling node pairs in GCC."""
    gcc_nodes = max(nx.connected_components(G), key=len)
    gcc = G.subgraph(gcc_nodes).copy()
    rng = random.Random(seed)
    nodes = list(gcc.nodes())
    total = 0
    count = 0
    for _ in range(n_samples):
        u, v = rng.sample(nodes, 2)
        try:
            d = nx.shortest_path_length(gcc, u, v)
            total += d
            count += 1
        except nx.NetworkXNoPath:
            pass
    return total / count if count > 0 else float('inf'), count

def main():
    print('Loading BGP peering graph...')
    G = load_bgp_graph()
    N = G.number_of_nodes()
    M = G.number_of_edges()
    print(f'  N={N:,}, M={M:,}')

    # Basic metrics
    print('Computing basic metrics...')
    degrees = [d for _, d in G.degree()]
    avg_degree = 2 * M / N
    max_degree = max(degrees)
    density = 2 * M / (N * (N - 1))

    # Connected components
    components = list(nx.connected_components(G))
    gcc_size = max(len(c) for c in components)
    n_components = len(components)
    print(f'  Components: {n_components:,}, GCC: {gcc_size:,} ({gcc_size/N*100:.1f}%)')

    # Clustering coefficient (global transitivity)
    print('Computing transitivity...')
    transitivity = nx.transitivity(G)
    print(f'  Transitivity: {transitivity:.6f}')

    # Average clustering coefficient (sampled for speed)
    print('Computing avg clustering (sampled 10000 nodes)...')
    sampled_nodes = random.sample(list(G.nodes()), min(10000, N))
    cc_vals = [nx.clustering(G, n) for n in sampled_nodes]
    avg_clustering = np.mean(cc_vals)
    print(f'  Avg clustering: {avg_clustering:.6f}')

    # Approximate average path length (sampled)
    print('Computing sampled avg path length (2000 pairs)...')
    avg_pl, n_pairs = sampled_avg_path_length(G, n_samples=2000)
    print(f'  Avg path length: {avg_pl:.3f} (from {n_pairs} pairs)')

    # ── Erdős–Rényi comparison ──
    print('Generating ER random graph for comparison...')
    p_er = 2 * M / (N * (N - 1))
    # Theoretical values for ER(N, p)
    C_er = p_er  # expected clustering
    L_er = np.log(N) / np.log(avg_degree)  # expected avg path length

    # Small-world coefficient
    sigma_sw = (avg_clustering / C_er) / (avg_pl / L_er) if C_er > 0 and L_er > 0 else 0
    print(f'\n── Small-World Analysis ──')
    print(f'  C_real = {avg_clustering:.6f}, C_random = {C_er:.6f}, ratio = {avg_clustering/C_er:.1f}')
    print(f'  L_real = {avg_pl:.3f}, L_random = {L_er:.3f}, ratio = {avg_pl/L_er:.2f}')
    print(f'  σ_SW = {sigma_sw:.2f} (>> 1 = small world)')

    # ── Visualization ──
    fig = plt.figure(figsize=(28, 10))
    fig.patch.set_facecolor(DARK_BG)
    gs = fig.add_gridspec(1, 3, wspace=0.3, left=0.05, right=0.97, top=0.85, bottom=0.08)

    # Panel 1: Degree histogram
    ax1 = fig.add_subplot(gs[0, 0])
    style_ax(ax1, 'Degree Distribution (Log-binned)', 'Degree k', 'Count')
    bins = np.logspace(0, np.log10(max_degree + 1), 60)
    ax1.hist(degrees, bins=bins, color=COLORS['red'], alpha=0.8, edgecolor=DARK_BORDER)
    ax1.set_xscale('log')
    ax1.set_yscale('log')
    ax1.axvline(avg_degree, color=COLORS['yellow'], linestyle='--', linewidth=1.5, label=f'<k>={avg_degree:.1f}')
    ax1.legend(fontsize=10, facecolor=DARK_PANEL, edgecolor=DARK_BORDER, labelcolor=TEXT_MUTED)

    # Panel 2: Clustering coefficient distribution
    ax2 = fig.add_subplot(gs[0, 1])
    style_ax(ax2, 'Local Clustering Coefficient Distribution', 'Clustering Coefficient', 'Count')
    ax2.hist(cc_vals, bins=50, color=COLORS['cyan'], alpha=0.8, edgecolor=DARK_BORDER)
    ax2.axvline(avg_clustering, color=COLORS['yellow'], linestyle='--', linewidth=1.5,
                label=f'<C>={avg_clustering:.4f}')
    ax2.axvline(C_er, color=COLORS['orange'], linestyle=':', linewidth=1.5,
                label=f'C_ER={C_er:.6f}')
    ax2.legend(fontsize=10, facecolor=DARK_PANEL, edgecolor=DARK_BORDER, labelcolor=TEXT_MUTED)

    # Panel 3: Summary statistics card
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.set_facecolor(DARK_PANEL)
    ax3.axis('off')
    ax3.set_title('Network Topology Summary', fontsize=14, fontweight='bold', color=TEXT_PRIMARY, pad=12)

    stats = [
        ('Metric', 'AS Peering', 'ER Random'),
        ('─' * 20, '─' * 12, '─' * 12),
        ('Nodes N', f'{N:,}', f'{N:,}'),
        ('Edges M', f'{M:,}', f'{M:,}'),
        ('Density', f'{density:.2e}', f'{p_er:.2e}'),
        ('<k> avg degree', f'{avg_degree:.1f}', f'{avg_degree:.1f}'),
        ('k_max', f'{max_degree:,}', f'~{int(avg_degree+3*np.sqrt(avg_degree))}'),
        ('Components', f'{n_components:,}', '~1'),
        ('GCC / N', f'{gcc_size/N*100:.1f}%', '~100%'),
        ('Clustering C', f'{avg_clustering:.4f}', f'{C_er:.6f}'),
        ('Transitivity', f'{transitivity:.4f}', f'{C_er:.6f}'),
        ('Avg Path L', f'{avg_pl:.2f}', f'{L_er:.2f}'),
        ('', '', ''),
        ('C/C_rand', f'{avg_clustering/C_er:.0f}x', '1x'),
        ('L/L_rand', f'{avg_pl/L_er:.2f}x', '1x'),
        ('σ_SW', f'{sigma_sw:.1f}', '~1'),
        ('', '', ''),
        ('VERDICT', 'SMALL WORLD' if sigma_sw > 1 else 'NOT small world', ''),
    ]

    text_lines = []
    for row in stats:
        text_lines.append(f'{row[0]:<20} {row[1]:>14} {row[2]:>14}')

    ax3.text(0.05, 0.95, '\n'.join(text_lines), transform=ax3.transAxes,
             fontsize=10, color=TEXT_MUTED, va='top', family='monospace',
             bbox=dict(boxstyle='round,pad=0.5', facecolor=DARK_BG, edgecolor=DARK_BORDER))

    fig.suptitle(
        'Small-World Properties of the AS-Level Internet Topology\n'
        f'σ_SW = (C/C_rand)/(L/L_rand) = {sigma_sw:.1f} | IYP 2026-04-08',
        fontsize=16, fontweight='bold', color=TEXT_PRIMARY, y=0.96
    )

    save_fig(fig, 'step06_small_world.png')

    # Save metrics
    metrics_path = os.path.join(DATA_DIR, 'step06_metrics.csv')
    with open(metrics_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['metric', 'value'])
        for name, val in [('N', N), ('M', M), ('avg_degree', avg_degree),
                          ('max_degree', max_degree), ('density', density),
                          ('n_components', n_components), ('gcc_size', gcc_size),
                          ('transitivity', transitivity), ('avg_clustering', avg_clustering),
                          ('avg_path_length', avg_pl), ('C_er', C_er), ('L_er', L_er),
                          ('sigma_sw', sigma_sw)]:
            w.writerow([name, val])
    print(f'Saved metrics to {metrics_path}')


if __name__ == '__main__':
    main()
