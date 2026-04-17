"""Step 10: Assortativity and degree-degree correlation analysis."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.complex_network.utils import *

import numpy as np
import csv
import networkx as nx
from collections import defaultdict

def load_bgp_graph():
    G = nx.Graph()
    with open(os.path.join(DATA_DIR, 'bgp_peering.csv')) as f:
        for row in csv.DictReader(f):
            G.add_edge(int(row['src']), int(row['dst']))
    return G

def load_as_metadata():
    meta = {}
    path = os.path.join(DATA_DIR, 'as_metadata.csv')
    if not os.path.exists(path):
        return meta
    with open(path) as f:
        for row in csv.DictReader(f):
            meta[int(row['asn'])] = {
                'tags': row.get('tags', '').split('|') if row.get('tags') else [],
            }
    return meta

def get_as_type(asn, meta):
    if asn not in meta:
        return 'Unknown'
    tags = set(t.lower() for t in meta[asn]['tags'])
    if any(t in tags for t in ['tier-1', 'transit']):
        return 'Transit'
    elif any(t in tags for t in ['cdn', 'content']):
        return 'CDN'
    elif any(t in tags for t in ['cloud']):
        return 'Cloud'
    elif any(t in tags for t in ['isp', 'access']):
        return 'ISP'
    else:
        return 'Other'

def main():
    print('Loading BGP graph...')
    G = load_bgp_graph()
    meta = load_as_metadata()

    # Degree assortativity
    print('Computing degree assortativity...')
    r = nx.degree_assortativity_coefficient(G)
    print(f'  Degree assortativity r = {r:.4f}')

    # Nearest-neighbor average degree knn(k)
    print('Computing knn(k)...')
    degrees = dict(G.degree())
    knn_per_node = {}
    for n in G.nodes():
        neighbor_degs = [degrees[nb] for nb in G.neighbors(n)]
        knn_per_node[n] = np.mean(neighbor_degs) if neighbor_degs else 0

    # Bin by degree
    knn_bins = defaultdict(list)
    for n, knn in knn_per_node.items():
        knn_bins[degrees[n]].append(knn)

    bin_k = sorted(knn_bins.keys())
    bin_knn_mean = [np.mean(knn_bins[k]) for k in bin_k]

    # Log-binned version for smoother plot
    log_bins = np.logspace(0, np.log10(max(bin_k) + 1), 40)
    binned_k = []
    binned_knn = []
    for i in range(len(log_bins) - 1):
        mask = [(k >= log_bins[i]) and (k < log_bins[i+1]) for k in bin_k]
        ks = [bin_k[j] for j in range(len(bin_k)) if mask[j]]
        knns = [bin_knn_mean[j] for j in range(len(bin_k)) if mask[j]]
        if ks:
            binned_k.append(np.mean(ks))
            binned_knn.append(np.mean(knns))

    # Mixing matrix by AS type
    print('Computing type mixing matrix...')
    type_map = {n: get_as_type(n, meta) for n in G.nodes()}
    type_labels = ['Transit', 'CDN', 'Cloud', 'ISP', 'Other', 'Unknown']
    type_to_idx = {t: i for i, t in enumerate(type_labels)}

    mixing = np.zeros((len(type_labels), len(type_labels)))
    for u, v in G.edges():
        ti = type_to_idx.get(type_map.get(u, 'Unknown'), 5)
        tj = type_to_idx.get(type_map.get(v, 'Unknown'), 5)
        mixing[ti, tj] += 1
        mixing[tj, ti] += 1

    # Normalize rows
    row_sums = mixing.sum(axis=1, keepdims=True)
    mixing_norm = np.divide(mixing, row_sums, where=row_sums > 0, out=np.zeros_like(mixing))

    # ── Visualization ──
    fig = plt.figure(figsize=(28, 10))
    fig.patch.set_facecolor(DARK_BG)
    gs = fig.add_gridspec(1, 3, wspace=0.35, left=0.06, right=0.96, top=0.85, bottom=0.08)

    # Panel 1: knn(k) plot
    ax1 = fig.add_subplot(gs[0, 0])
    style_ax(ax1, 'Average Nearest-Neighbor Degree knn(k)', 'Degree k', 'knn(k)')
    ax1.scatter(bin_k, bin_knn_mean, s=1, alpha=0.2, color=COLORS['blue'])
    ax1.plot(binned_k, binned_knn, 'o-', color=COLORS['red'], linewidth=2, markersize=5)
    ax1.set_xscale('log')
    ax1.set_yscale('log')

    # Add reference line for neutral (constant knn)
    mean_knn = np.mean(list(knn_per_node.values()))
    ax1.axhline(mean_knn, color=COLORS['yellow'], linestyle='--',
                label=f'<knn>={mean_knn:.0f} (neutral)', linewidth=1)

    # Fit slope
    log_k = np.log10(np.array(binned_k))
    log_knn = np.log10(np.array(binned_knn))
    valid = np.isfinite(log_k) & np.isfinite(log_knn)
    if sum(valid) > 2:
        slope, intercept = np.polyfit(log_k[valid], log_knn[valid], 1)
        ax1.text(0.95, 0.95, f'Slope = {slope:.2f}\nr = {r:.4f}\n'
                 f'{"Disassortative" if r < 0 else "Assortative"}',
                 transform=ax1.transAxes, ha='right', va='top',
                 fontsize=11, color=TEXT_PRIMARY, fontweight='bold',
                 bbox=dict(boxstyle='round,pad=0.3', facecolor=DARK_BG, edgecolor=DARK_BORDER))
    ax1.legend(fontsize=9, facecolor=DARK_PANEL, edgecolor=DARK_BORDER, labelcolor=TEXT_MUTED)

    # Panel 2: Mixing matrix heatmap
    ax2 = fig.add_subplot(gs[0, 1])
    style_ax(ax2, 'AS Type Mixing Matrix\n(row-normalized peering probability)')
    im = ax2.imshow(mixing_norm, cmap='YlOrRd', vmin=0, vmax=1.0)
    ax2.set_xticks(range(len(type_labels)))
    ax2.set_yticks(range(len(type_labels)))
    ax2.set_xticklabels(type_labels, fontsize=9, color=TEXT_MUTED, rotation=30, ha='right')
    ax2.set_yticklabels(type_labels, fontsize=9, color=TEXT_MUTED)
    for i in range(len(type_labels)):
        for j in range(len(type_labels)):
            val = mixing_norm[i, j]
            ax2.text(j, i, f'{val:.2f}', ha='center', va='center',
                     fontsize=9, color='white' if val > 0.4 else TEXT_MUTED)
    plt.colorbar(im, ax=ax2, shrink=0.8)

    # Panel 3: Degree-degree scatter (sampled)
    ax3 = fig.add_subplot(gs[0, 2])
    style_ax(ax3, 'Edge Degree-Degree Scatter\n(sampled 50K edges)', 'Degree of node u', 'Degree of node v')
    import random
    random.seed(42)
    edges = list(G.edges())
    sample_edges = random.sample(edges, min(50000, len(edges)))
    x_degs = [degrees[u] for u, v in sample_edges]
    y_degs = [degrees[v] for u, v in sample_edges]
    ax3.scatter(x_degs, y_degs, s=1, alpha=0.05, color=COLORS['purple'])
    ax3.set_xscale('log')
    ax3.set_yscale('log')
    ax3.plot([1, max(degrees.values())], [1, max(degrees.values())],
             '--', color=DARK_BORDER, alpha=0.5)

    # Type distribution
    type_counts = defaultdict(int)
    for n in G.nodes():
        type_counts[type_map.get(n, 'Unknown')] += 1
    type_info = ', '.join(f'{t}: {type_counts[t]:,}' for t in type_labels if type_counts[t] > 0)
    ax3.text(0.02, 0.02, f'AS Types: {type_info}',
             transform=ax3.transAxes, fontsize=7, color=TEXT_SECONDARY,
             bbox=dict(boxstyle='round,pad=0.3', facecolor=DARK_BG, edgecolor=DARK_BORDER))

    fig.suptitle(
        f'Assortativity Analysis of AS-Level Internet Topology\n'
        f'Degree Assortativity r = {r:.4f} ({"disassortative" if r < 0 else "assortative"}) | IYP 2026-04-08',
        fontsize=16, fontweight='bold', color=TEXT_PRIMARY, y=0.96
    )

    save_fig(fig, 'step10_assortativity.png')
    print(f'Degree assortativity: r = {r:.4f}')


if __name__ == '__main__':
    main()
