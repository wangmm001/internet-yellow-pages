"""Step 11: Louvain community detection on AS peering graph."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.complex_network.utils import *

import numpy as np
import csv
import networkx as nx
import community as community_louvain
from collections import Counter, defaultdict

def load_bgp_graph():
    G = nx.Graph()
    with open(os.path.join(DATA_DIR, 'bgp_peering.csv')) as f:
        for row in csv.DictReader(f):
            G.add_edge(int(row['src']), int(row['dst']))
    return G

def load_as_country():
    as_cc = {}
    path = os.path.join(DATA_DIR, 'as_country.csv')
    if not os.path.exists(path):
        return as_cc
    with open(path) as f:
        for row in csv.DictReader(f):
            asn = int(row['asn'])
            if asn not in as_cc:
                as_cc[asn] = row['country']
    return as_cc

def main():
    print('Loading BGP graph...')
    G = load_bgp_graph()
    as_cc = load_as_country()

    # Louvain community detection
    print('Running Louvain community detection...')
    partition = community_louvain.best_partition(G, random_state=42)
    modularity = community_louvain.modularity(partition, G)
    print(f'  Modularity Q = {modularity:.4f}')

    # Community statistics
    comm_sizes = Counter(partition.values())
    n_communities = len(comm_sizes)
    print(f'  Communities: {n_communities}')

    # Top-20 communities by size
    top_comms = comm_sizes.most_common(20)
    print(f'  Top-5 community sizes: {[s for _, s in top_comms[:5]]}')

    # Country composition of top communities
    comm_countries = defaultdict(lambda: Counter())
    for asn, comm_id in partition.items():
        cc = as_cc.get(asn, 'Unknown')
        comm_countries[comm_id][cc] += 1

    # ── Visualization ──
    fig = plt.figure(figsize=(30, 18))
    fig.patch.set_facecolor(DARK_BG)
    gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.35,
                          left=0.06, right=0.96, top=0.90, bottom=0.06)

    # Panel 1: Community size distribution (rank-size)
    ax1 = fig.add_subplot(gs[0, 0])
    style_ax(ax1, 'Community Size Distribution\n(Rank-Size Plot)', 'Community Rank', 'Number of ASes')
    sizes = sorted(comm_sizes.values(), reverse=True)
    ax1.plot(range(1, len(sizes) + 1), sizes, 'o-', color=COLORS['red'],
             markersize=3, linewidth=1.5)
    ax1.set_xscale('log')
    ax1.set_yscale('log')
    ax1.text(0.95, 0.95, f'Q = {modularity:.4f}\n{n_communities} communities',
             transform=ax1.transAxes, ha='right', va='top',
             fontsize=12, color=TEXT_PRIMARY, fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.3', facecolor=DARK_BG, edgecolor=DARK_BORDER))

    # Panel 2: Top-15 communities bar chart with country coloring
    ax2 = fig.add_subplot(gs[0, 1])
    style_ax(ax2, 'Top-15 Communities\n(colored by dominant country)', 'Community', 'Number of ASes')
    top15 = comm_sizes.most_common(15)
    comm_ids = [c for c, _ in top15]
    comm_vals = [s for _, s in top15]

    # Get dominant country per community
    dom_countries = []
    for cid in comm_ids:
        cc_counter = comm_countries[cid]
        cc_counter.pop('Unknown', None)
        if cc_counter:
            top_cc = cc_counter.most_common(1)[0]
            dom_countries.append(f'{top_cc[0]} ({top_cc[1]/sum(cc_counter.values())*100:.0f}%)')
        else:
            dom_countries.append('Unknown')

    colors_bar = plt.cm.Set3(np.linspace(0, 1, 15))
    bars = ax2.bar(range(15), comm_vals, color=colors_bar, edgecolor=DARK_BORDER)
    ax2.set_xticks(range(15))
    ax2.set_xticklabels([f'C{cid}\n{dc}' for cid, dc in zip(comm_ids, dom_countries)],
                         fontsize=7, color=TEXT_MUTED, rotation=45, ha='right')
    ax2.set_yscale('log')

    for bar, val in zip(bars, comm_vals):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 1.1,
                 f'{val:,}', ha='center', fontsize=7, color=TEXT_MUTED)

    # Panel 3: Country-community heatmap (top 10 communities x top 10 countries)
    ax3 = fig.add_subplot(gs[0, 2])
    style_ax(ax3, 'Community-Country Composition\n(Top 10 × Top 10)')

    # Get top-10 countries overall
    all_countries = Counter()
    for asn in G.nodes():
        cc = as_cc.get(asn, 'Unknown')
        if cc != 'Unknown':
            all_countries[cc] += 1
    top10_countries = [c for c, _ in all_countries.most_common(10)]

    # Build heatmap matrix
    top10_comms = [c for c, _ in top_comms[:10]]
    heat = np.zeros((10, 10))
    for i, cid in enumerate(top10_comms):
        total = sum(comm_countries[cid].values())
        for j, cc in enumerate(top10_countries):
            heat[i, j] = comm_countries[cid].get(cc, 0) / total * 100

    im = ax3.imshow(heat, cmap='YlOrRd', aspect='auto')
    ax3.set_xticks(range(10))
    ax3.set_yticks(range(10))
    ax3.set_xticklabels(top10_countries, fontsize=9, color=TEXT_MUTED)
    ax3.set_yticklabels([f'C{c} ({comm_sizes[c]:,})' for c in top10_comms],
                         fontsize=8, color=TEXT_MUTED)
    for i in range(10):
        for j in range(10):
            if heat[i, j] > 0.5:
                ax3.text(j, i, f'{heat[i,j]:.0f}%', ha='center', va='center',
                         fontsize=7, color='white' if heat[i,j] > 20 else TEXT_MUTED)
    plt.colorbar(im, ax=ax3, shrink=0.8, label='% of community')

    # Panel 4: Inter-community edge density
    ax4 = fig.add_subplot(gs[1, 0])
    style_ax(ax4, 'Inter-Community Edge Density\n(Top 10 communities)')
    inter_edges = np.zeros((10, 10))
    for u, v in G.edges():
        cu = partition.get(u)
        cv = partition.get(v)
        if cu in top10_comms and cv in top10_comms:
            i = top10_comms.index(cu)
            j = top10_comms.index(cv)
            inter_edges[i, j] += 1
            inter_edges[j, i] += 1

    # Normalize by product of community sizes
    for i in range(10):
        for j in range(10):
            si = comm_sizes[top10_comms[i]]
            sj = comm_sizes[top10_comms[j]]
            if si > 0 and sj > 0:
                inter_edges[i, j] /= (si * sj / 1000)

    im4 = ax4.imshow(inter_edges, cmap='viridis', aspect='auto')
    ax4.set_xticks(range(10))
    ax4.set_yticks(range(10))
    ax4.set_xticklabels([f'C{c}' for c in top10_comms], fontsize=9, color=TEXT_MUTED)
    ax4.set_yticklabels([f'C{c}' for c in top10_comms], fontsize=9, color=TEXT_MUTED)
    plt.colorbar(im4, ax=ax4, shrink=0.8, label='Edge density (×1000)')

    # Panel 5: Community size CDF
    ax5 = fig.add_subplot(gs[1, 1])
    style_ax(ax5, 'Cumulative Community Size Distribution', 'Community Size', 'CDF')
    sorted_sizes = sorted(comm_sizes.values())
    cdf_y = np.arange(1, len(sorted_sizes) + 1) / len(sorted_sizes)
    ax5.plot(sorted_sizes, cdf_y, '-', color=COLORS['cyan'], linewidth=2)
    ax5.set_xscale('log')
    ax5.axhline(0.5, color=DARK_BORDER, linestyle='--')
    median_size = sorted_sizes[len(sorted_sizes) // 2]
    ax5.axvline(median_size, color=COLORS['yellow'], linestyle='--',
                label=f'Median={median_size}')
    ax5.legend(fontsize=10, facecolor=DARK_PANEL, edgecolor=DARK_BORDER, labelcolor=TEXT_MUTED)

    # Panel 6: Summary
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.set_facecolor(DARK_PANEL)
    ax6.axis('off')
    ax6.set_title('Community Detection Summary', fontsize=14, fontweight='bold',
                  color=TEXT_PRIMARY, pad=12)

    lines = [
        f'Modularity Q = {modularity:.4f}',
        f'Communities = {n_communities}',
        f'Largest = {max(sizes):,} ASes',
        f'Smallest = {min(sizes)} ASes',
        f'Median = {median_size} ASes',
        '',
        'Top-10 Community Dominant Countries:',
    ]
    for cid in top10_comms:
        cc_counter = comm_countries[cid]
        cc_counter_clean = Counter({k: v for k, v in cc_counter.items() if k != 'Unknown'})
        if cc_counter_clean:
            top3 = cc_counter_clean.most_common(3)
            cc_str = ', '.join(f'{c}:{n}' for c, n in top3)
            lines.append(f'  C{cid} ({comm_sizes[cid]:>6,}): {cc_str}')

    ax6.text(0.05, 0.95, '\n'.join(lines), transform=ax6.transAxes,
             fontsize=10, color=TEXT_MUTED, va='top', family='monospace',
             bbox=dict(boxstyle='round,pad=0.5', facecolor=DARK_BG, edgecolor=DARK_BORDER))

    fig.suptitle(
        f'Louvain Community Detection on AS Peering Graph\n'
        f'Q = {modularity:.4f} | {n_communities} Communities | IYP 2026-04-08',
        fontsize=16, fontweight='bold', color=TEXT_PRIMARY, y=0.96
    )

    save_fig(fig, 'step11_community_detection.png')

    # Save community assignments
    comm_path = os.path.join(DATA_DIR, 'step11_communities.csv')
    with open(comm_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['asn', 'community', 'country'])
        for asn, comm in partition.items():
            w.writerow([asn, comm, as_cc.get(asn, '')])
    print(f'Saved community assignments to {comm_path}')


if __name__ == '__main__':
    main()
