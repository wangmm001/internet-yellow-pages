"""Step 7: Multi-dimensional centrality analysis of AS peering graph."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.complex_network.utils import *

import numpy as np
import csv
import networkx as nx
from scipy import stats

def load_bgp_graph():
    G = nx.Graph()
    path = os.path.join(DATA_DIR, 'bgp_peering.csv')
    with open(path) as f:
        for row in csv.DictReader(f):
            G.add_edge(int(row['src']), int(row['dst']))
    return G

def load_as_names():
    """Load AS metadata for labeling."""
    names = {}
    path = os.path.join(DATA_DIR, 'as_metadata.csv')
    if not os.path.exists(path):
        return names
    with open(path) as f:
        for row in csv.DictReader(f):
            tags = row.get('tags', '')
            names[int(row['asn'])] = tags
    return names

def main():
    print('Loading BGP graph...')
    G = load_bgp_graph()
    gcc_nodes = max(nx.connected_components(G), key=len)
    G_gcc = G.subgraph(gcc_nodes).copy()
    print(f'GCC: {G_gcc.number_of_nodes():,} nodes, {G_gcc.number_of_edges():,} edges')

    # Compute centralities
    print('Computing degree centrality...')
    deg_c = nx.degree_centrality(G_gcc)

    print('Computing betweenness centrality (approximate, k=3000)...')
    bet_c = nx.betweenness_centrality(G_gcc, k=3000, seed=42)

    print('Computing eigenvector centrality...')
    try:
        eig_c = nx.eigenvector_centrality(G_gcc, max_iter=500, tol=1e-6)
    except nx.PowerIterationFailedConvergence:
        print('  Eigenvector did not converge, using numpy fallback...')
        eig_c = nx.eigenvector_centrality_numpy(G_gcc)

    print('Computing PageRank...')
    pr_c = nx.pagerank(G_gcc, alpha=0.85)

    # Build ranking table
    nodes = list(G_gcc.nodes())
    metrics = {
        'degree': deg_c,
        'betweenness': bet_c,
        'eigenvector': eig_c,
        'pagerank': pr_c,
    }

    # Save full centrality data
    centrality_path = os.path.join(DATA_DIR, 'step07_centrality_full.csv')
    with open(centrality_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['asn', 'degree', 'betweenness', 'eigenvector', 'pagerank'])
        for n in nodes:
            w.writerow([n, deg_c[n], bet_c[n], eig_c.get(n, 0), pr_c[n]])
    print(f'Saved centrality to {centrality_path}')

    # Top-50 by each metric
    top_n = 50
    rankings = {}
    for metric_name, metric_dict in metrics.items():
        sorted_nodes = sorted(metric_dict, key=metric_dict.get, reverse=True)[:top_n]
        rankings[metric_name] = sorted_nodes

    # Spearman correlation between centrality metrics
    print('Computing Spearman correlations...')
    metric_names = list(metrics.keys())
    n_metrics = len(metric_names)
    corr_matrix = np.zeros((n_metrics, n_metrics))
    for i, m1 in enumerate(metric_names):
        for j, m2 in enumerate(metric_names):
            vals1 = [metrics[m1].get(n, 0) for n in nodes]
            vals2 = [metrics[m2].get(n, 0) for n in nodes]
            rho, _ = stats.spearmanr(vals1, vals2)
            corr_matrix[i, j] = rho

    # ── Visualization ──
    fig = plt.figure(figsize=(30, 20))
    fig.patch.set_facecolor(DARK_BG)
    gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.35,
                          left=0.06, right=0.96, top=0.90, bottom=0.05)

    # Panel 1: Degree vs Betweenness scatter
    ax1 = fig.add_subplot(gs[0, 0])
    style_ax(ax1, 'Degree vs Betweenness Centrality', 'Degree Centrality', 'Betweenness Centrality')
    x_vals = [deg_c[n] for n in nodes]
    y_vals = [bet_c[n] for n in nodes]
    ax1.scatter(x_vals, y_vals, s=2, alpha=0.3, color=COLORS['blue'])
    # Highlight top-10
    for metric_dict, color, label in [(deg_c, COLORS['red'], 'Top Degree'),
                                       (bet_c, COLORS['cyan'], 'Top Betweenness')]:
        top10 = sorted(metric_dict, key=metric_dict.get, reverse=True)[:10]
        for n in top10:
            ax1.scatter(deg_c[n], bet_c[n], s=60, color=color, zorder=5, edgecolors='white', linewidth=0.5)
            ax1.annotate(f'AS{n}', (deg_c[n], bet_c[n]), fontsize=6, color=TEXT_MUTED,
                        xytext=(5, 5), textcoords='offset points')
    ax1.set_xscale('log')
    ax1.set_yscale('log')

    # Panel 2: PageRank vs Eigenvector scatter
    ax2 = fig.add_subplot(gs[0, 1])
    style_ax(ax2, 'PageRank vs Eigenvector Centrality', 'PageRank', 'Eigenvector Centrality')
    x_vals2 = [pr_c[n] for n in nodes]
    y_vals2 = [eig_c.get(n, 0) for n in nodes]
    ax2.scatter(x_vals2, y_vals2, s=2, alpha=0.3, color=COLORS['purple'])
    top10_pr = sorted(pr_c, key=pr_c.get, reverse=True)[:10]
    for n in top10_pr:
        ax2.scatter(pr_c[n], eig_c.get(n, 0), s=60, color=COLORS['red'], zorder=5,
                    edgecolors='white', linewidth=0.5)
        ax2.annotate(f'AS{n}', (pr_c[n], eig_c.get(n, 0)), fontsize=6, color=TEXT_MUTED,
                    xytext=(5, 5), textcoords='offset points')
    ax2.set_xscale('log')

    # Panel 3: Correlation heatmap
    ax3 = fig.add_subplot(gs[0, 2])
    style_ax(ax3, 'Spearman Rank Correlation\nBetween Centrality Metrics')
    im = ax3.imshow(corr_matrix, cmap='RdYlBu_r', vmin=0.5, vmax=1.0)
    ax3.set_xticks(range(n_metrics))
    ax3.set_yticks(range(n_metrics))
    labels = ['Degree', 'Betweenness', 'Eigenvector', 'PageRank']
    ax3.set_xticklabels(labels, fontsize=10, color=TEXT_MUTED, rotation=30, ha='right')
    ax3.set_yticklabels(labels, fontsize=10, color=TEXT_MUTED)
    for i in range(n_metrics):
        for j in range(n_metrics):
            ax3.text(j, i, f'{corr_matrix[i,j]:.3f}', ha='center', va='center',
                     fontsize=11, fontweight='bold',
                     color='white' if corr_matrix[i,j] > 0.8 else TEXT_PRIMARY)
    plt.colorbar(im, ax=ax3, shrink=0.8)

    # Panel 4: Top-30 AS ranking comparison (heatmap of ranks)
    ax4 = fig.add_subplot(gs[1, :2])
    style_ax(ax4, 'Top-30 AS: Centrality Rank Comparison')

    # Collect union of top-30 across all metrics
    top_union = set()
    for m in metric_names:
        top_union.update(sorted(metrics[m], key=metrics[m].get, reverse=True)[:30])

    # Sort by average rank
    rank_data = {}
    for n in top_union:
        ranks = []
        for m in metric_names:
            sorted_all = sorted(metrics[m], key=metrics[m].get, reverse=True)
            ranks.append(sorted_all.index(n) + 1 if n in sorted_all[:200] else 200)
        rank_data[n] = ranks

    sorted_by_avg = sorted(rank_data.items(), key=lambda x: np.mean(x[1]))[:30]
    as_labels = [f'AS{n}' for n, _ in sorted_by_avg]
    rank_matrix = np.array([r for _, r in sorted_by_avg])

    im4 = ax4.imshow(rank_matrix, cmap='RdYlGn_r', aspect='auto', vmin=1, vmax=100)
    ax4.set_yticks(range(len(as_labels)))
    ax4.set_yticklabels(as_labels, fontsize=8, color=TEXT_MUTED, family='monospace')
    ax4.set_xticks(range(4))
    ax4.set_xticklabels(labels, fontsize=10, color=TEXT_MUTED)
    for i in range(len(sorted_by_avg)):
        for j in range(4):
            val = rank_matrix[i, j]
            ax4.text(j, i, f'{int(val)}', ha='center', va='center',
                     fontsize=7, color='white' if val < 50 else TEXT_MUTED)
    plt.colorbar(im4, ax=ax4, shrink=0.6, label='Rank (1=highest)')

    # Panel 5: "Bridge" ASes — high betweenness but low degree
    ax5 = fig.add_subplot(gs[1, 2])
    style_ax(ax5, 'Critical Bridge ASes\n(High Betweenness / Low Degree)', 'Degree Rank', 'Betweenness Rank')

    # Compute rank positions
    deg_rank = {n: i+1 for i, n in enumerate(sorted(deg_c, key=deg_c.get, reverse=True))}
    bet_rank = {n: i+1 for i, n in enumerate(sorted(bet_c, key=bet_c.get, reverse=True))}

    x_ranks = [deg_rank[n] for n in nodes[:5000]]  # subsample for plotting
    y_ranks = [bet_rank[n] for n in nodes[:5000]]
    ax5.scatter(x_ranks, y_ranks, s=2, alpha=0.2, color=COLORS['blue'])

    # Highlight bridges: betweenness rank << degree rank
    bridges = []
    for n in nodes:
        dr = deg_rank[n]
        br = bet_rank[n]
        if br < 100 and dr > 500:
            bridges.append((n, dr, br))
    bridges.sort(key=lambda x: x[2])
    for n, dr, br in bridges[:15]:
        ax5.scatter(dr, br, s=80, color=COLORS['orange'], zorder=5, edgecolors='white', linewidth=0.5)
        ax5.annotate(f'AS{n}', (dr, br), fontsize=7, color=COLORS['orange'],
                    xytext=(5, -10), textcoords='offset points')
    ax5.set_xlim(0, min(5000, max(x_ranks)))
    ax5.set_ylim(0, min(5000, max(y_ranks)))
    ax5.plot([0, 5000], [0, 5000], '--', color=DARK_BORDER, linewidth=1, alpha=0.5)
    ax5.text(0.95, 0.05, f'{len(bridges)} bridge ASes\n(bet_rank<100, deg_rank>500)',
             transform=ax5.transAxes, ha='right', va='bottom',
             fontsize=10, color=COLORS['orange'], fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.3', facecolor=DARK_BG, edgecolor=DARK_BORDER))

    fig.suptitle(
        'Multi-Dimensional Centrality Analysis of AS-Level Internet Topology\n'
        f'{G_gcc.number_of_nodes():,} ASes | 4 Centrality Metrics | IYP 2026-04-08',
        fontsize=16, fontweight='bold', color=TEXT_PRIMARY, y=0.96
    )

    save_fig(fig, 'step07_centrality_analysis.png')


if __name__ == '__main__':
    main()
