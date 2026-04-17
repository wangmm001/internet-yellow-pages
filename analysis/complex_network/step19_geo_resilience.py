"""Step 19: Geographic resilience — country-level failure simulation."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.complex_network.utils import *

import numpy as np
import csv
import networkx as nx
from collections import defaultdict, Counter

def load_bgp_graph():
    G = nx.Graph()
    with open(os.path.join(DATA_DIR, 'bgp_peering.csv')) as f:
        for row in csv.DictReader(f):
            G.add_edge(int(row['src']), int(row['dst']))
    return G

def load_as_country():
    """Return dict of asn -> set of countries."""
    as_cc = defaultdict(set)
    with open(os.path.join(DATA_DIR, 'as_country.csv')) as f:
        for row in csv.DictReader(f):
            as_cc[int(row['asn'])].add(row['country'])
    return as_cc

def load_dns_hosting():
    hosting = {}
    path = os.path.join(DATA_DIR, 'dns_as_hosting.csv')
    if not os.path.exists(path):
        return hosting
    with open(path) as f:
        for row in csv.DictReader(f):
            hosting[int(row['asn'])] = int(row['hostname_count'])
    return hosting

def simulate_country_isolation(G, country_ases, country_code, dns_hosting):
    """Remove all ASes of a country and measure global impact."""
    ases_to_remove = country_ases.get(country_code, set())
    if not ases_to_remove:
        return None

    N = G.number_of_nodes()
    total_hosts = sum(dns_hosting.values()) if dns_hosting else 1

    G_residual = G.copy()
    existing = [n for n in ases_to_remove if n in G_residual]
    G_residual.remove_nodes_from(existing)

    if G_residual.number_of_nodes() == 0:
        return {
            'country': country_code,
            'ases_removed': len(existing),
            'ases_removed_pct': len(existing) / N * 100,
            'gcc_remaining_pct': 0,
            'components': 0,
            'hostnames_lost': sum(dns_hosting.get(a, 0) for a in ases_to_remove),
            'hostnames_lost_pct': 0,
            'third_countries_affected': 0,
        }

    gcc = max(nx.connected_components(G_residual), key=len)
    gcc_pct = len(gcc) / N * 100

    # How many ASes get disconnected from GCC?
    disconnected = set(G_residual.nodes()) - gcc
    # Which third countries are affected?
    affected_countries = set()
    for asn in disconnected:
        if asn not in ases_to_remove:  # third-party damage
            for cc in as_country_map.get(asn, set()):
                if cc != country_code:
                    affected_countries.add(cc)

    hostnames_lost = sum(dns_hosting.get(a, 0) for a in ases_to_remove)
    # Add hostnames from disconnected third-party ASes
    hostnames_lost += sum(dns_hosting.get(a, 0) for a in disconnected if a not in ases_to_remove)

    return {
        'country': country_code,
        'ases_removed': len(existing),
        'ases_removed_pct': len(existing) / N * 100,
        'gcc_remaining_pct': gcc_pct,
        'components': nx.number_connected_components(G_residual),
        'hostnames_lost': hostnames_lost,
        'hostnames_lost_pct': hostnames_lost / total_hosts * 100 if total_hosts > 0 else 0,
        'third_countries_affected': len(affected_countries),
    }

# Global for closure
as_country_map = {}

def main():
    global as_country_map
    print('Loading data...')
    G = load_bgp_graph()
    as_cc = load_as_country()
    as_country_map = as_cc
    dns_hosting = load_dns_hosting()

    # Build country -> set of ASes
    country_ases = defaultdict(set)
    for asn, countries in as_cc.items():
        for cc in countries:
            country_ases[cc].add(asn)

    # Count ASes per country
    country_as_count = {cc: len(ases) for cc, ases in country_ases.items()}
    top_countries = sorted(country_as_count, key=country_as_count.get, reverse=True)[:30]

    print(f'Top-10 countries by AS count: {[(cc, country_as_count[cc]) for cc in top_countries[:10]]}')

    # Simulate isolation for top-30 countries
    print('Simulating country-level isolation...')
    results = []
    for cc in top_countries:
        r = simulate_country_isolation(G, country_ases, cc, dns_hosting)
        if r:
            results.append(r)
            print(f'  {cc}: removed {r["ases_removed"]:,} ASes, '
                  f'GCC={r["gcc_remaining_pct"]:.1f}%, '
                  f'hosts_lost={r["hostnames_lost"]:,}')

    results.sort(key=lambda x: x['gcc_remaining_pct'])

    # ── Visualization ──
    fig = plt.figure(figsize=(30, 18))
    fig.patch.set_facecolor(DARK_BG)
    gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.35,
                          left=0.06, right=0.96, top=0.90, bottom=0.06)

    # Panel 1: GCC impact per country
    ax1 = fig.add_subplot(gs[0, :2])
    style_ax(ax1, 'Global Connectivity Impact of Country-Level Isolation',
             '', 'Remaining GCC (%)')
    cc_labels = [r['country'] for r in results[:25]]
    gcc_vals = [r['gcc_remaining_pct'] for r in results[:25]]
    as_pcts = [r['ases_removed_pct'] for r in results[:25]]

    x = np.arange(len(cc_labels))
    bars1 = ax1.bar(x - 0.2, gcc_vals, 0.4, color=COLORS['cyan'],
                    edgecolor=DARK_BORDER, label='GCC remaining (%)')
    bars2 = ax1.bar(x + 0.2, [100 - p for p in as_pcts], 0.4, color=COLORS['red'],
                    alpha=0.5, edgecolor=DARK_BORDER, label='ASes remaining (%)')
    ax1.set_xticks(x)
    ax1.set_xticklabels(cc_labels, fontsize=9, color=TEXT_MUTED, rotation=45, ha='right')
    ax1.axhline(100, color=DARK_BORDER, linestyle='--', linewidth=0.5)
    ax1.legend(fontsize=10, facecolor=DARK_PANEL, edgecolor=DARK_BORDER, labelcolor=TEXT_MUTED)

    # Panel 2: ASes removed vs GCC scatter
    ax2 = fig.add_subplot(gs[0, 2])
    style_ax(ax2, 'Country Size vs Global Impact',
             'ASes Removed (%)', 'GCC Reduction (%)')
    gcc_reductions = [100 - r['gcc_remaining_pct'] for r in results]
    as_removed_pcts = [r['ases_removed_pct'] for r in results]
    ax2.scatter(as_removed_pcts, gcc_reductions, s=40, color=COLORS['purple'],
                edgecolors=DARK_BORDER, linewidth=0.5, alpha=0.8)
    for r in results:
        if r['ases_removed_pct'] > 3 or (100 - r['gcc_remaining_pct']) > 2:
            ax2.annotate(r['country'], (r['ases_removed_pct'], 100 - r['gcc_remaining_pct']),
                        fontsize=8, color=TEXT_MUTED, xytext=(4, 4), textcoords='offset points')
    ax2.plot([0, max(as_removed_pcts)*1.1], [0, max(as_removed_pcts)*1.1],
             '--', color=DARK_BORDER, alpha=0.5)
    ax2.text(0.02, 0.98, 'Above diagonal: Disproportionate impact\n(country more important than its size)',
             transform=ax2.transAxes, ha='left', va='top', fontsize=8, color=COLORS['red'],
             bbox=dict(boxstyle='round,pad=0.3', facecolor=DARK_BG, edgecolor=DARK_BORDER))

    # Panel 3: Hostname loss per country
    ax3 = fig.add_subplot(gs[1, 0])
    style_ax(ax3, 'HostName Loss by Country Isolation', '', 'HostNames Lost')
    sorted_by_host = sorted(results, key=lambda x: x['hostnames_lost'], reverse=True)[:15]
    cc_h = [r['country'] for r in sorted_by_host]
    h_vals = [r['hostnames_lost'] for r in sorted_by_host]
    bars = ax3.barh(range(len(cc_h)), h_vals, color=COLORS['green'],
                    edgecolor=DARK_BORDER, height=0.6)
    ax3.set_yticks(range(len(cc_h)))
    ax3.set_yticklabels(cc_h, fontsize=10, color=TEXT_MUTED)
    ax3.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K'))
    for bar, val in zip(bars, h_vals):
        label = f'{val/1e6:.1f}M' if val >= 1e6 else f'{val/1e3:.0f}K'
        ax3.text(bar.get_width() * 1.02, bar.get_y() + bar.get_height()/2,
                 label, va='center', fontsize=9, color=TEXT_PRIMARY)

    # Panel 4: Third-country collateral damage
    ax4 = fig.add_subplot(gs[1, 1])
    style_ax(ax4, 'Third-Country Collateral Damage\n(countries losing connectivity)',
             '', '# Countries Affected')
    sorted_by_3rd = sorted(results, key=lambda x: x['third_countries_affected'], reverse=True)[:15]
    cc_3rd = [r['country'] for r in sorted_by_3rd]
    third_vals = [r['third_countries_affected'] for r in sorted_by_3rd]
    bars4 = ax4.barh(range(len(cc_3rd)), third_vals, color=COLORS['orange'],
                     edgecolor=DARK_BORDER, height=0.6)
    ax4.set_yticks(range(len(cc_3rd)))
    ax4.set_yticklabels(cc_3rd, fontsize=10, color=TEXT_MUTED)
    for bar, val in zip(bars4, third_vals):
        ax4.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                 str(val), va='center', fontsize=9, color=TEXT_PRIMARY)

    # Panel 5: Summary
    ax5 = fig.add_subplot(gs[1, 2])
    ax5.set_facecolor(DARK_PANEL)
    ax5.axis('off')
    ax5.set_title('Geographic Resilience Summary', fontsize=14, fontweight='bold',
                  color=TEXT_PRIMARY, pad=12)

    # Categorize
    critical = [r for r in results if r['gcc_remaining_pct'] < 95]
    moderate = [r for r in results if 95 <= r['gcc_remaining_pct'] < 99]

    lines = ['CRITICAL COUNTRIES (GCC < 95%):', '─' * 45]
    for r in critical[:10]:
        lines.append(f'  {r["country"]}: GCC={r["gcc_remaining_pct"]:.1f}%, '
                     f'{r["ases_removed"]:,} ASes')
    if not critical:
        lines.append('  (none — network is geographically resilient)')

    lines.extend(['', 'MODERATE IMPACT (95% < GCC < 99%):', '─' * 45])
    for r in moderate[:10]:
        lines.append(f'  {r["country"]}: GCC={r["gcc_remaining_pct"]:.1f}%')
    if not moderate:
        lines.append('  (none)')

    lines.extend(['', 'KEY FINDING:', '─' * 45])
    if results:
        us = next((r for r in results if r['country'] == 'US'), None)
        if us:
            lines.append(f'  US isolation: GCC={us["gcc_remaining_pct"]:.1f}%')
            lines.append(f'    {us["ases_removed"]:,} ASes, {us["hostnames_lost"]:,} hosts')
        most_impact = min(results, key=lambda x: x['gcc_remaining_pct'])
        lines.append(f'  Most impactful: {most_impact["country"]}')
        lines.append(f'    GCC→{most_impact["gcc_remaining_pct"]:.1f}%')

    ax5.text(0.05, 0.95, '\n'.join(lines), transform=ax5.transAxes,
             fontsize=9, color=TEXT_MUTED, va='top', family='monospace',
             bbox=dict(boxstyle='round,pad=0.5', facecolor=DARK_BG, edgecolor=DARK_BORDER))

    fig.suptitle(
        'Geographic Resilience: Country-Level Internet Isolation Simulation\n'
        f'Top-30 Countries by AS Count | Impact on Global GCC & DNS | IYP 2026-04-08',
        fontsize=16, fontweight='bold', color=TEXT_PRIMARY, y=0.96
    )

    save_fig(fig, 'step19_geo_resilience.png')

    # Save results
    res_path = os.path.join(DATA_DIR, 'step19_geo_resilience.csv')
    with open(res_path, 'w', newline='') as f:
        keys = ['country', 'ases_removed', 'ases_removed_pct', 'gcc_remaining_pct',
                'components', 'hostnames_lost', 'hostnames_lost_pct', 'third_countries_affected']
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(results)
    print(f'Saved geo resilience results to {res_path}')


if __name__ == '__main__':
    main()
