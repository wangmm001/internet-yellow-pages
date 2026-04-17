"""Step 8: k-core decomposition and core-periphery structure analysis."""
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

def load_as_metadata():
    meta = {}
    path = os.path.join(DATA_DIR, 'as_metadata.csv')
    if not os.path.exists(path):
        return meta
    with open(path) as f:
        for row in csv.DictReader(f):
            meta[int(row['asn'])] = {
                'countries': row.get('countries', '').split('|') if row.get('countries') else [],
                'tags': row.get('tags', '').split('|') if row.get('tags') else [],
            }
    return meta

def load_ixp_membership():
    as_ixp = Counter()
    with open(os.path.join(DATA_DIR, 'as_ixp_membership.csv')) as f:
        for row in csv.DictReader(f):
            as_ixp[int(row['asn'])] += 1
    return as_ixp

def main():
    print('Loading BGP graph...')
    G = load_bgp_graph()
    meta = load_as_metadata()
    ixp_counts = load_ixp_membership()

    # k-core decomposition
    print('Computing k-core decomposition...')
    core_numbers = nx.core_number(G)
    max_k = max(core_numbers.values())
    print(f'  Max coreness: {max_k}')

    # Distribution of coreness values
    core_dist = Counter(core_numbers.values())

    # Identify the innermost core
    inner_core = {n for n, k in core_numbers.items() if k == max_k}
    print(f'  Innermost core ({max_k}-core): {len(inner_core)} ASes')

    # Categorize ASes by type from tags
    def get_as_type(asn):
        if asn not in meta:
            return 'Unknown'
        tags = set(t.lower() for t in meta[asn]['tags'])
        if any(t in tags for t in ['tier-1', 'transit']):
            return 'Tier-1/Transit'
        elif any(t in tags for t in ['cdn', 'content']):
            return 'CDN/Content'
        elif any(t in tags for t in ['cloud']):
            return 'Cloud'
        elif any(t in tags for t in ['isp', 'access']):
            return 'ISP/Access'
        elif any(t in tags for t in ['education', 'research']):
            return 'Education/Research'
        else:
            return 'Other'

    # Core composition by AS type
    core_by_type = Counter()
    for asn in inner_core:
        core_by_type[get_as_type(asn)] += 1

    # k-shell vs IXP membership correlation
    k_vals = []
    ixp_vals = []
    for n in G.nodes():
        k_vals.append(core_numbers[n])
        ixp_vals.append(ixp_counts.get(n, 0))

    from scipy.stats import spearmanr
    rho, p_val = spearmanr(k_vals, ixp_vals)
    print(f'  k-core vs IXP membership: ρ={rho:.4f}, p={p_val:.2e}')

    # ── Visualization ──
    fig = plt.figure(figsize=(28, 18))
    fig.patch.set_facecolor(DARK_BG)
    gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.35,
                          left=0.06, right=0.96, top=0.90, bottom=0.06)

    # Panel 1: k-shell distribution
    ax1 = fig.add_subplot(gs[0, 0])
    style_ax(ax1, 'k-Shell Size Distribution', 'Coreness k', 'Number of ASes')
    k_values = sorted(core_dist.keys())
    counts = [core_dist[k] for k in k_values]
    ax1.bar(k_values, counts, color=COLORS['red'], alpha=0.8, edgecolor=DARK_BORDER)
    ax1.set_yscale('log')
    ax1.axvline(max_k, color=COLORS['yellow'], linestyle='--', linewidth=1.5,
                label=f'Max k={max_k}')
    ax1.legend(fontsize=10, facecolor=DARK_PANEL, edgecolor=DARK_BORDER, labelcolor=TEXT_MUTED)

    # Panel 2: Cumulative k-shell (CDF)
    ax2 = fig.add_subplot(gs[0, 1])
    style_ax(ax2, 'Cumulative k-Core Size\n(nodes with coreness ≥ k)', 'k', 'Fraction of ASes')
    total_nodes = sum(counts)
    cumsum = []
    running = total_nodes
    for k in k_values:
        cumsum.append(running / total_nodes)
        running -= core_dist[k]
    ax2.plot(k_values, cumsum, '-o', color=COLORS['cyan'], markersize=3, linewidth=2)
    ax2.set_yscale('log')
    ax2.axhline(len(inner_core)/total_nodes, color=COLORS['yellow'], linestyle='--',
                label=f'{max_k}-core: {len(inner_core)} ASes ({len(inner_core)/total_nodes*100:.2f}%)')
    ax2.legend(fontsize=9, facecolor=DARK_PANEL, edgecolor=DARK_BORDER, labelcolor=TEXT_MUTED)

    # Panel 3: Inner core composition by AS type
    ax3 = fig.add_subplot(gs[0, 2])
    style_ax(ax3, f'Inner Core ({max_k}-core) Composition\nby AS Type')
    types_sorted = sorted(core_by_type.items(), key=lambda x: x[1], reverse=True)
    type_labels = [t[0] for t in types_sorted]
    type_counts = [t[1] for t in types_sorted]
    type_colors = [COLORS['red'], COLORS['cyan'], COLORS['blue'],
                   COLORS['orange'], COLORS['purple'], COLORS['green']][:len(types_sorted)]
    wedges, texts, autotexts = ax3.pie(type_counts, labels=type_labels, colors=type_colors,
                                        autopct='%1.1f%%', startangle=90,
                                        wedgeprops=dict(edgecolor=DARK_BG, linewidth=2),
                                        textprops=dict(color=TEXT_PRIMARY, fontsize=9))
    for at in autotexts:
        at.set_fontsize(8)
        at.set_color(TEXT_PRIMARY)

    # Panel 4: Coreness vs IXP membership scatter
    ax4 = fig.add_subplot(gs[1, 0])
    style_ax(ax4, 'Coreness vs IXP Membership', 'k-Core Number', 'Number of IXPs')
    # Add jitter for visibility
    jitter_k = np.array(k_vals) + np.random.normal(0, 0.2, len(k_vals))
    jitter_ixp = np.array(ixp_vals) + np.random.normal(0, 0.15, len(ixp_vals))
    ax4.scatter(jitter_k, jitter_ixp, s=1, alpha=0.15, color=COLORS['blue'])
    # Bin averages
    bins = defaultdict(list)
    for k, ixp in zip(k_vals, ixp_vals):
        bins[k].append(ixp)
    bin_k = sorted(bins.keys())
    bin_avg = [np.mean(bins[k]) for k in bin_k]
    ax4.plot(bin_k, bin_avg, 'o-', color=COLORS['red'], linewidth=2, markersize=4, label=f'ρ={rho:.3f}')
    ax4.legend(fontsize=10, facecolor=DARK_PANEL, edgecolor=DARK_BORDER, labelcolor=TEXT_MUTED)

    # Panel 5: Coreness vs Degree scatter
    ax5 = fig.add_subplot(gs[1, 1])
    style_ax(ax5, 'Coreness vs Degree', 'Degree', 'k-Core Number')
    degs = [G.degree(n) for n in G.nodes()]
    cores = [core_numbers[n] for n in G.nodes()]
    ax5.scatter(degs, cores, s=1, alpha=0.15, color=COLORS['purple'])
    ax5.set_xscale('log')
    ax5.plot([1, max(degs)], [1, max(degs)], '--', color=DARK_BORDER, alpha=0.5)  # k <= degree

    # Panel 6: Top ASes in innermost core
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.set_facecolor(DARK_PANEL)
    ax6.axis('off')
    ax6.set_title(f'Top ASes in {max_k}-Core (by degree)', fontsize=14,
                  fontweight='bold', color=TEXT_PRIMARY, pad=12)

    inner_by_deg = sorted(inner_core, key=lambda n: G.degree(n), reverse=True)[:25]
    lines = [f'{"ASN":<10} {"Degree":>8} {"IXPs":>6} {"Type":<18}']
    lines.append('─' * 44)
    for asn in inner_by_deg:
        deg = G.degree(asn)
        ixps = ixp_counts.get(asn, 0)
        atype = get_as_type(asn)
        lines.append(f'AS{asn:<8} {deg:>8,} {ixps:>6} {atype:<18}')

    ax6.text(0.05, 0.95, '\n'.join(lines), transform=ax6.transAxes,
             fontsize=9, color=TEXT_MUTED, va='top', family='monospace',
             bbox=dict(boxstyle='round,pad=0.5', facecolor=DARK_BG, edgecolor=DARK_BORDER))

    fig.suptitle(
        f'k-Core Decomposition of AS-Level Internet Topology\n'
        f'Max Coreness = {max_k} | Inner Core = {len(inner_core)} ASes | '
        f'k-core vs IXP: ρ={rho:.3f} | IYP 2026-04-08',
        fontsize=16, fontweight='bold', color=TEXT_PRIMARY, y=0.96
    )

    save_fig(fig, 'step08_kcore.png')

    # Save coreness data
    core_path = os.path.join(DATA_DIR, 'step08_coreness.csv')
    with open(core_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['asn', 'coreness', 'degree', 'ixp_count'])
        for n in G.nodes():
            w.writerow([n, core_numbers[n], G.degree(n), ixp_counts.get(n, 0)])
    print(f'Saved coreness to {core_path}')


if __name__ == '__main__':
    main()
