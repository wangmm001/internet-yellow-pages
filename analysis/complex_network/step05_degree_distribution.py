"""Step 5: Degree distribution analysis and power-law fitting across all layers."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.complex_network.utils import *

import numpy as np
import csv
import networkx as nx
import powerlaw
from collections import Counter

def load_bgp_graph():
    """Load AS peering graph from CSV."""
    G = nx.Graph()
    path = os.path.join(DATA_DIR, 'bgp_peering.csv')
    with open(path) as f:
        for row in csv.DictReader(f):
            G.add_edge(int(row['src']), int(row['dst']))
    print(f'BGP peering graph: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges')
    return G

def load_dependency_graph():
    """Load AS dependency graph from CSV."""
    G = nx.DiGraph()
    path = os.path.join(DATA_DIR, 'as_dependency.csv')
    with open(path) as f:
        for row in csv.DictReader(f):
            hege = float(row['hege']) if row['hege'] else 0
            G.add_edge(int(row['src']), int(row['dst']), weight=hege)
    print(f'AS dependency graph: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges')
    return G

def load_ixp_membership():
    """Load IXP membership as bipartite, project to AS co-membership."""
    from collections import defaultdict
    ixp_members = defaultdict(set)
    path = os.path.join(DATA_DIR, 'as_ixp_membership.csv')
    with open(path) as f:
        for row in csv.DictReader(f):
            ixp_members[row['ixp_name']].add(int(row['asn']))

    # AS degree = number of IXPs it belongs to
    as_ixp_count = Counter()
    for ixp, members in ixp_members.items():
        for asn in members:
            as_ixp_count[asn] += 1

    print(f'IXP membership: {len(as_ixp_count):,} ASes across {len(ixp_members):,} IXPs')
    return as_ixp_count

def load_dns_hosting():
    """Load AS-level DNS hosting degrees."""
    degrees = {}
    path = os.path.join(DATA_DIR, 'dns_as_hosting.csv')
    with open(path) as f:
        for row in csv.DictReader(f):
            degrees[int(row['asn'])] = int(row['hostname_count'])
    print(f'DNS hosting: {len(degrees):,} ASes')
    return degrees

def fit_and_plot(ax, degrees, label, color):
    """Fit power-law and plot CCDF."""
    deg_array = np.array(degrees)
    deg_array = deg_array[deg_array > 0]

    # CCDF
    sorted_d = np.sort(deg_array)[::-1]
    ccdf_y = np.arange(1, len(sorted_d) + 1) / len(sorted_d)

    ax.loglog(sorted_d, ccdf_y, '.', color=color, alpha=0.4, markersize=2)

    # Power-law fit
    try:
        fit = powerlaw.Fit(deg_array, discrete=True, verbose=False)
        alpha = fit.power_law.alpha
        xmin = fit.power_law.xmin

        # Compare with lognormal
        R_ln, p_ln = fit.distribution_compare('power_law', 'lognormal')
        # Compare with exponential
        R_exp, p_exp = fit.distribution_compare('power_law', 'exponential')

        # Plot fitted line
        x_fit = np.logspace(np.log10(xmin), np.log10(max(deg_array)), 100)
        # Normalized power-law CCDF: P(X>=x) = (x/xmin)^(1-alpha)
        y_fit = (x_fit / xmin) ** (1 - alpha)
        # Scale to match data at xmin
        n_above = np.sum(deg_array >= xmin)
        y_fit = y_fit * (n_above / len(deg_array))
        ax.loglog(x_fit, y_fit, '-', color=color, linewidth=2, alpha=0.9)

        info = (f'{label}\n'
                f'  α={alpha:.2f}, x_min={xmin:.0f}\n'
                f'  vs lognorm: R={R_ln:.2f}, p={p_ln:.3f}\n'
                f'  vs exp: R={R_exp:.2f}, p={p_exp:.3f}')
        return info, alpha, xmin, R_ln, p_ln, R_exp, p_exp
    except Exception as e:
        return f'{label}: fit failed ({e})', 0, 0, 0, 0, 0, 0


def main():
    # Load data
    G_bgp = load_bgp_graph()
    G_dep = load_dependency_graph()
    ixp_degrees = load_ixp_membership()

    # Check if DNS hosting data exists
    dns_path = os.path.join(DATA_DIR, 'dns_as_hosting.csv')
    dns_degrees = load_dns_hosting() if os.path.exists(dns_path) else None

    # Compute degree sequences
    bgp_degrees = [d for _, d in G_bgp.degree()]
    dep_in_degrees = [d for _, d in G_dep.in_degree()]
    dep_out_degrees = [d for _, d in G_dep.out_degree()]
    ixp_deg_vals = list(ixp_degrees.values())

    # ── Create 6-panel figure ──
    fig = plt.figure(figsize=(30, 18))
    fig.patch.set_facecolor(DARK_BG)
    gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.3,
                          left=0.05, right=0.97, top=0.90, bottom=0.05)

    results = []

    # Panel 1: BGP Peering Degree CCDF
    ax1 = fig.add_subplot(gs[0, 0])
    style_ax(ax1, 'BGP Peering Degree (CCDF)', 'Degree k', 'P(K ≥ k)')
    info, *params = fit_and_plot(ax1, bgp_degrees, 'BGP Peering', COLORS['red'])
    ax1.text(0.02, 0.02, info, transform=ax1.transAxes, fontsize=8,
             color=TEXT_MUTED, va='bottom', family='monospace',
             bbox=dict(boxstyle='round,pad=0.3', facecolor=DARK_BG, edgecolor=DARK_BORDER))
    results.append(('BGP Peering', *params))

    # Panel 2: Dependency In-degree CCDF
    ax2 = fig.add_subplot(gs[0, 1])
    style_ax(ax2, 'AS Dependency In-Degree (CCDF)\n(how many depend on this AS)', 'In-Degree k', 'P(K ≥ k)')
    dep_in_nonzero = [d for d in dep_in_degrees if d > 0]
    info, *params = fit_and_plot(ax2, dep_in_nonzero, 'Dependency In-Degree', COLORS['cyan'])
    ax2.text(0.02, 0.02, info, transform=ax2.transAxes, fontsize=8,
             color=TEXT_MUTED, va='bottom', family='monospace',
             bbox=dict(boxstyle='round,pad=0.3', facecolor=DARK_BG, edgecolor=DARK_BORDER))
    results.append(('Dependency In-Degree', *params))

    # Panel 3: IXP Membership Degree CCDF
    ax3 = fig.add_subplot(gs[0, 2])
    style_ax(ax3, 'IXP Membership Degree (CCDF)\n(IXPs per AS)', 'IXP Count k', 'P(K ≥ k)')
    info, *params = fit_and_plot(ax3, ixp_deg_vals, 'IXP Membership', COLORS['orange'])
    ax3.text(0.02, 0.02, info, transform=ax3.transAxes, fontsize=8,
             color=TEXT_MUTED, va='bottom', family='monospace',
             bbox=dict(boxstyle='round,pad=0.3', facecolor=DARK_BG, edgecolor=DARK_BORDER))
    results.append(('IXP Membership', *params))

    # Panel 4: DNS Hosting Degree CCDF
    ax4 = fig.add_subplot(gs[1, 0])
    style_ax(ax4, 'DNS Hosting Degree (CCDF)\n(HostNames per AS)', 'HostName Count k', 'P(K ≥ k)')
    if dns_degrees:
        dns_vals = list(dns_degrees.values())
        info, *params = fit_and_plot(ax4, dns_vals, 'DNS Hosting', COLORS['green'])
        ax4.text(0.02, 0.02, info, transform=ax4.transAxes, fontsize=8,
                 color=TEXT_MUTED, va='bottom', family='monospace',
                 bbox=dict(boxstyle='round,pad=0.3', facecolor=DARK_BG, edgecolor=DARK_BORDER))
        results.append(('DNS Hosting', *params))
    else:
        ax4.text(0.5, 0.5, 'DNS data not yet extracted\n(run step02 first)',
                 transform=ax4.transAxes, ha='center', va='center',
                 color=TEXT_SECONDARY, fontsize=12)

    # Panel 5: Degree histogram comparison (linear scale, top-100)
    ax5 = fig.add_subplot(gs[1, 1])
    style_ax(ax5, 'Degree Distribution Comparison\n(PDF, log-binned)', 'Degree k', 'P(k)')
    for deg_data, label, color in [
        (bgp_degrees, 'BGP Peering', COLORS['red']),
        (dep_in_nonzero, 'Dependency', COLORS['cyan']),
        (ixp_deg_vals, 'IXP Member', COLORS['orange']),
    ]:
        # Log-binned histogram
        arr = np.array(deg_data)
        arr = arr[arr > 0]
        bins = np.logspace(0, np.log10(max(arr) + 1), 50)
        hist, edges = np.histogram(arr, bins=bins, density=True)
        centers = (edges[:-1] + edges[1:]) / 2
        mask = hist > 0
        ax5.loglog(centers[mask], hist[mask], 'o-', color=color, label=label,
                   markersize=4, alpha=0.8, linewidth=1.5)
    ax5.legend(fontsize=9, facecolor=DARK_PANEL, edgecolor=DARK_BORDER, labelcolor=TEXT_MUTED)

    # Panel 6: Summary statistics table
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.set_facecolor(DARK_PANEL)
    ax6.axis('off')
    ax6.set_title('Summary Statistics', fontsize=14, fontweight='bold', color=TEXT_PRIMARY, pad=12)

    stats_lines = [
        f'{"Layer":<22} {"Nodes":>8} {"Edges":>10} {"<k>":>6} {"k_max":>8} {"C":>6}',
        '─' * 62,
        f'{"BGP Peering":<22} {G_bgp.number_of_nodes():>8,} {G_bgp.number_of_edges():>10,} '
        f'{2*G_bgp.number_of_edges()/G_bgp.number_of_nodes():>6.1f} {max(bgp_degrees):>8,} '
        f'{nx.transitivity(G_bgp):>6.4f}',
        f'{"AS Dependency (dir)":<22} {G_dep.number_of_nodes():>8,} {G_dep.number_of_edges():>10,} '
        f'{G_dep.number_of_edges()/G_dep.number_of_nodes():>6.1f} {max(dep_in_degrees):>8,} {"N/A":>6}',
        f'{"IXP Membership":<22} {len(ixp_degrees):>8,} {"N/A":>10} '
        f'{np.mean(ixp_deg_vals):>6.1f} {max(ixp_deg_vals):>8,} {"N/A":>6}',
    ]
    if dns_degrees:
        dns_vals = list(dns_degrees.values())
        stats_lines.append(
            f'{"DNS Hosting":<22} {len(dns_degrees):>8,} {"N/A":>10} '
            f'{np.mean(dns_vals):>6.0f} {max(dns_vals):>8,} {"N/A":>6}'
        )

    stats_text = '\n'.join(stats_lines)
    ax6.text(0.05, 0.85, stats_text, transform=ax6.transAxes,
             fontsize=10, color=TEXT_MUTED, va='top', family='monospace',
             bbox=dict(boxstyle='round,pad=0.5', facecolor=DARK_BG, edgecolor=DARK_BORDER))

    # Print fitting results
    print('\n── Power-law Fitting Results ──')
    for name, alpha, xmin, R_ln, p_ln, R_exp, p_exp in results:
        print(f'{name}: α={alpha:.3f}, xmin={xmin:.0f}, '
              f'vs_lognorm(R={R_ln:.3f},p={p_ln:.4f}), '
              f'vs_exp(R={R_exp:.3f},p={p_exp:.4f})')

    # Super title
    fig.suptitle(
        'Internet Infrastructure Degree Distributions\n'
        'Power-Law Fitting (Clauset-Shalizi-Newman Method) | IYP 2026-04-08',
        fontsize=18, fontweight='bold', color=TEXT_PRIMARY, y=0.97
    )

    save_fig(fig, 'step05_degree_distribution.png')

    # Save results to CSV
    results_path = os.path.join(DATA_DIR, 'step05_powerlaw_fits.csv')
    with open(results_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['layer', 'alpha', 'xmin', 'R_vs_lognorm', 'p_vs_lognorm', 'R_vs_exp', 'p_vs_exp'])
        for row in results:
            w.writerow(row)
    print(f'Saved fit results to {results_path}')


if __name__ == '__main__':
    main()
