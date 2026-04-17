"""Step 18: Cross-layer cascade amplification factor analysis."""
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

def load_dependency():
    """Load AS dependency: which ASes depend on each AS."""
    dependents = defaultdict(set)  # key = upstream AS, value = set of dependent ASes
    with open(os.path.join(DATA_DIR, 'as_dependency.csv')) as f:
        for row in csv.DictReader(f):
            src = int(row['src'])  # dependent AS
            dst = int(row['dst'])  # upstream AS
            hege = float(row['hege']) if row['hege'] else 0
            if hege > 0.1:  # significant dependency
                dependents[dst].add(src)
    return dependents

def load_dns_hosting():
    """Load how many hostnames each AS hosts."""
    hosting = {}
    path = os.path.join(DATA_DIR, 'dns_as_hosting.csv')
    if not os.path.exists(path):
        return hosting
    with open(path) as f:
        for row in csv.DictReader(f):
            hosting[int(row['asn'])] = int(row['hostname_count'])
    return hosting

def load_prefix_counts():
    counts = {}
    with open(os.path.join(DATA_DIR, 'as_prefix_count.csv')) as f:
        for row in csv.DictReader(f):
            counts[int(row['asn'])] = int(row['prefix_count'])
    return counts

def load_ns_to_as():
    """Load AuthNS to AS mapping."""
    ns_as = {}
    path = os.path.join(DATA_DIR, 'ns_to_as.csv')
    if not os.path.exists(path):
        return ns_as
    with open(path) as f:
        for row in csv.DictReader(f):
            asns = set()
            if row['hosting_asns']:
                for a in row['hosting_asns'].split('|'):
                    try:
                        asns.add(int(a))
                    except ValueError:
                        pass
            ns_as[row['ns_name']] = asns
    return ns_as

def load_dns_authority():
    """Load top DNS authority providers."""
    auth = {}
    path = os.path.join(DATA_DIR, 'dns_authority_top500.csv')
    if not os.path.exists(path):
        return auth
    with open(path) as f:
        for row in csv.DictReader(f):
            auth[row['ns_name']] = int(row['domain_count'])
    return auth

def simulate_as_failure(G, failed_as, dependents, dns_hosting, prefix_counts):
    """Simulate removing a single AS and measure cross-layer impact."""
    # Phase 1: BGP impact
    directly_affected = {failed_as}
    # Add dependents
    cascade_affected = directly_affected | dependents.get(failed_as, set())

    # Phase 2: Check BGP connectivity loss
    G_residual = G.copy()
    G_residual.remove_nodes_from([n for n in cascade_affected if n in G_residual])
    if G_residual.number_of_nodes() == 0:
        bgp_disconnected = set(G.nodes())
    else:
        gcc = max(nx.connected_components(G_residual), key=len)
        bgp_disconnected = set(G.nodes()) - gcc

    all_affected = cascade_affected | bgp_disconnected

    # Phase 3: DNS/Content impact
    total_hostnames_lost = sum(dns_hosting.get(asn, 0) for asn in all_affected)
    total_prefixes_lost = sum(prefix_counts.get(asn, 0) for asn in all_affected)

    return {
        'direct_deps': len(dependents.get(failed_as, set())),
        'cascade_affected': len(cascade_affected),
        'bgp_disconnected': len(bgp_disconnected),
        'total_affected_as': len(all_affected),
        'hostnames_lost': total_hostnames_lost,
        'prefixes_lost': total_prefixes_lost,
    }

def main():
    print('Loading data...')
    G = load_bgp_graph()
    N = G.number_of_nodes()
    dependents = load_dependency()
    dns_hosting = load_dns_hosting()
    prefix_counts = load_prefix_counts()
    dns_authority = load_dns_authority()
    ns_to_as = load_ns_to_as()

    total_hostnames = sum(dns_hosting.values()) if dns_hosting else 1
    total_prefixes = sum(prefix_counts.values()) if prefix_counts else 1

    # Select top ASes to test (by degree + by dependency + by hosting)
    degree_top = sorted(G.nodes(), key=lambda n: G.degree(n), reverse=True)[:30]
    dep_top = sorted(dependents.keys(), key=lambda k: len(dependents[k]), reverse=True)[:30]
    hosting_top = sorted(dns_hosting.keys(), key=dns_hosting.get, reverse=True)[:30] if dns_hosting else []
    test_ases = list(set(degree_top) | set(dep_top) | set(hosting_top))
    print(f'Testing {len(test_ases)} critical ASes...')

    # Run simulations
    results = []
    for i, asn in enumerate(test_ases):
        if i % 20 == 0:
            print(f'  Simulating AS{asn} ({i+1}/{len(test_ases)})...')
        impact = simulate_as_failure(G, asn, dependents, dns_hosting, prefix_counts)
        impact['asn'] = asn
        impact['degree'] = G.degree(asn) if asn in G else 0
        impact['hosting'] = dns_hosting.get(asn, 0)

        # Amplification factors
        if impact['prefixes_lost'] > 0:
            impact['amp_prefix_to_host'] = impact['hostnames_lost'] / impact['prefixes_lost']
        else:
            impact['amp_prefix_to_host'] = 0

        impact['host_pct'] = impact['hostnames_lost'] / total_hostnames * 100
        impact['as_pct'] = impact['total_affected_as'] / N * 100
        impact['pfx_pct'] = impact['prefixes_lost'] / total_prefixes * 100

        results.append(impact)

    # Sort by total impact
    results.sort(key=lambda x: x['hostnames_lost'], reverse=True)

    # ── Visualization ──
    fig = plt.figure(figsize=(30, 20))
    fig.patch.set_facecolor(DARK_BG)
    gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.35,
                          left=0.06, right=0.96, top=0.90, bottom=0.06)

    # Panel 1: Cascade impact — top 20 ASes
    ax1 = fig.add_subplot(gs[0, :2])
    style_ax(ax1, 'Cross-Layer Cascade Impact: Top-20 ASes\n(single AS failure → multi-layer damage)',
             '', 'Impact')
    top20 = results[:20]
    asn_labels = [f'AS{r["asn"]}' for r in top20]
    x = np.arange(len(top20))
    w = 0.2
    ax1.bar(x - w*1.5, [r['total_affected_as'] for r in top20], w,
            color=COLORS['red'], label='Affected ASes', edgecolor=DARK_BORDER)
    ax1.bar(x - w*0.5, [r['prefixes_lost'] for r in top20], w,
            color=COLORS['cyan'], label='Prefixes Lost', edgecolor=DARK_BORDER)
    ax1.bar(x + w*0.5, [r['hostnames_lost'] / 1000 for r in top20], w,
            color=COLORS['green'], label='HostNames Lost (K)', edgecolor=DARK_BORDER)
    ax1.bar(x + w*1.5, [r['direct_deps'] for r in top20], w,
            color=COLORS['orange'], label='Direct Dependents', edgecolor=DARK_BORDER)
    ax1.set_xticks(x)
    ax1.set_xticklabels(asn_labels, fontsize=8, color=TEXT_MUTED, rotation=45, ha='right')
    ax1.set_yscale('log')
    ax1.legend(fontsize=9, facecolor=DARK_PANEL, edgecolor=DARK_BORDER, labelcolor=TEXT_MUTED,
               loc='upper right')

    # Panel 2: Amplification factor scatter
    ax2 = fig.add_subplot(gs[0, 2])
    style_ax(ax2, 'Amplification Factor\n(HostNames Lost / Prefixes Lost)',
             'BGP Impact (% prefixes)', 'DNS Impact (% hostnames)')
    pfx_pcts = [r['pfx_pct'] for r in results if r['pfx_pct'] > 0]
    host_pcts = [r['host_pct'] for r in results if r['pfx_pct'] > 0]
    amps = [r['amp_prefix_to_host'] for r in results if r['pfx_pct'] > 0]
    scatter = ax2.scatter(pfx_pcts, host_pcts, c=np.log10(np.array(amps) + 1),
                          s=30, cmap='hot', alpha=0.7, edgecolors=DARK_BORDER, linewidth=0.3)
    ax2.plot([0, max(pfx_pcts)*1.1], [0, max(pfx_pcts)*1.1], '--', color=DARK_BORDER, alpha=0.5)
    # Label top amplifiers
    for r in results[:10]:
        if r['pfx_pct'] > 0:
            ax2.annotate(f'AS{r["asn"]}', (r['pfx_pct'], r['host_pct']),
                        fontsize=7, color=TEXT_MUTED, xytext=(5, 5), textcoords='offset points')
    plt.colorbar(scatter, ax=ax2, label='log10(Amplification)')
    ax2.text(0.02, 0.98, 'Above diagonal:\nDNS impact > BGP impact\n(amplification)',
             transform=ax2.transAxes, ha='left', va='top', fontsize=8, color=COLORS['red'],
             bbox=dict(boxstyle='round,pad=0.3', facecolor=DARK_BG, edgecolor=DARK_BORDER))

    # Panel 3: Impact type breakdown for top-10
    ax3 = fig.add_subplot(gs[1, 0])
    style_ax(ax3, 'Impact Decomposition: Top-10 ASes',
             'AS', 'Fraction of total impact')
    top10 = results[:10]
    labels10 = [f'AS{r["asn"]}' for r in top10]
    x10 = np.arange(len(top10))
    bottom = np.zeros(len(top10))
    for label, key, color in [
        ('Direct deps', 'direct_deps', COLORS['red']),
        ('Cascade deps', 'cascade_affected', COLORS['orange']),
        ('BGP disconnected', 'bgp_disconnected', COLORS['cyan']),
    ]:
        vals = np.array([r[key] for r in top10], dtype=float)
        total_each = np.array([r['total_affected_as'] for r in top10], dtype=float)
        fracs = np.divide(vals, total_each, where=total_each > 0, out=np.zeros_like(vals))
        ax3.bar(x10, fracs, bottom=bottom, color=color, label=label, edgecolor=DARK_BORDER)
        bottom += fracs
    ax3.set_xticks(x10)
    ax3.set_xticklabels(labels10, fontsize=8, color=TEXT_MUTED, rotation=45, ha='right')
    ax3.legend(fontsize=9, facecolor=DARK_PANEL, edgecolor=DARK_BORDER, labelcolor=TEXT_MUTED)
    ax3.set_ylim(0, 1.1)

    # Panel 4: AS degree vs cascade impact scatter
    ax4 = fig.add_subplot(gs[1, 1])
    style_ax(ax4, 'Degree vs Total Cascade Impact', 'AS Degree', 'Total Affected ASes')
    degs = [r['degree'] for r in results]
    impacts = [r['total_affected_as'] for r in results]
    ax4.scatter(degs, impacts, s=20, alpha=0.6, color=COLORS['purple'], edgecolors=DARK_BORDER, linewidth=0.3)
    for r in results[:5]:
        ax4.annotate(f'AS{r["asn"]}', (r['degree'], r['total_affected_as']),
                    fontsize=7, color=TEXT_MUTED, xytext=(5, 5), textcoords='offset points')
    ax4.set_xscale('log')
    ax4.set_yscale('log')

    # Panel 5: Summary
    ax5 = fig.add_subplot(gs[1, 2])
    ax5.set_facecolor(DARK_PANEL)
    ax5.axis('off')
    ax5.set_title('Cross-Layer Cascade Summary', fontsize=14, fontweight='bold',
                  color=TEXT_PRIMARY, pad=12)

    lines = ['TOP-10 MOST IMPACTFUL AS FAILURES:', '─' * 50]
    for r in results[:10]:
        lines.append(
            f'AS{r["asn"]:<8} deg={r["degree"]:>6,} deps={r["direct_deps"]:>4} '
            f'hosts={r["hostnames_lost"]:>10,} pfx={r["prefixes_lost"]:>5,}'
        )
    lines.extend(['', 'AMPLIFICATION STATISTICS:', '─' * 50])
    amps_valid = [r['amp_prefix_to_host'] for r in results if r['amp_prefix_to_host'] > 0]
    if amps_valid:
        lines.append(f'Mean amplification: {np.mean(amps_valid):.1f}')
        lines.append(f'Max amplification:  {max(amps_valid):.1f}')
        lines.append(f'Median:             {np.median(amps_valid):.1f}')
    lines.extend(['', 'INTERPRETATION:', '─' * 50,
                  'CDN/hosting ASes show high',
                  'amplification: small BGP impact',
                  '→ large DNS/content impact.',
                  'Transit ASes show wide cascade',
                  'but lower amplification per prefix.'])

    ax5.text(0.05, 0.95, '\n'.join(lines), transform=ax5.transAxes,
             fontsize=8, color=TEXT_MUTED, va='top', family='monospace',
             bbox=dict(boxstyle='round,pad=0.5', facecolor=DARK_BG, edgecolor=DARK_BORDER))

    fig.suptitle(
        'Cross-Layer Cascade Analysis: BGP → DNS → Content\n'
        f'{len(test_ases)} Critical ASes Tested | Amplification Factor Quantification | IYP 2026-04-08',
        fontsize=16, fontweight='bold', color=TEXT_PRIMARY, y=0.96
    )

    save_fig(fig, 'step18_cross_layer_cascade.png')

    # Save results
    res_path = os.path.join(DATA_DIR, 'step18_cascade_results.csv')
    with open(res_path, 'w', newline='') as f:
        keys = ['asn', 'degree', 'direct_deps', 'cascade_affected', 'bgp_disconnected',
                'total_affected_as', 'hostnames_lost', 'prefixes_lost',
                'amp_prefix_to_host', 'host_pct', 'as_pct', 'pfx_pct']
        w = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
        w.writeheader()
        w.writerows(results)
    print(f'Saved cascade results to {res_path}')


if __name__ == '__main__':
    main()
