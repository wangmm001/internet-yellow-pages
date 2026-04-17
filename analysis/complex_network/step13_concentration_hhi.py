"""Step 13: Multi-dimensional concentration analysis (HHI, Gini, Lorenz curves)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.complex_network.utils import *

import numpy as np
import csv
from collections import Counter

def gini_coefficient(values):
    """Compute Gini coefficient from a list of values."""
    arr = np.sort(np.array(values, dtype=float))
    n = len(arr)
    if n == 0 or arr.sum() == 0:
        return 0
    index = np.arange(1, n + 1)
    return (2 * np.sum(index * arr) - (n + 1) * arr.sum()) / (n * arr.sum())

def hhi_index(shares):
    """Compute Herfindahl-Hirschman Index from market shares (fractions)."""
    return sum(s**2 for s in shares)

def lorenz_curve(values):
    """Compute Lorenz curve coordinates."""
    arr = np.sort(np.array(values, dtype=float))
    cum = np.cumsum(arr) / arr.sum()
    x = np.arange(1, len(arr) + 1) / len(arr)
    return np.concatenate([[0], x]), np.concatenate([[0], cum])

def main():
    # ── Load data ──

    # 1. DNS Authority: AuthNS dominance
    dns_auth = {}
    path = os.path.join(DATA_DIR, 'dns_authority_top500.csv')
    if os.path.exists(path):
        with open(path) as f:
            for row in csv.DictReader(f):
                dns_auth[row['ns_name']] = int(row['domain_count'])

    # 2. BGP: AS prefix count
    as_pfx = {}
    with open(os.path.join(DATA_DIR, 'as_prefix_count.csv')) as f:
        for row in csv.DictReader(f):
            as_pfx[int(row['asn'])] = int(row['prefix_count'])

    # 3. DNS Hosting: HostNames per AS
    dns_hosting = {}
    path = os.path.join(DATA_DIR, 'dns_as_hosting.csv')
    if os.path.exists(path):
        with open(path) as f:
            for row in csv.DictReader(f):
                dns_hosting[int(row['asn'])] = int(row['hostname_count'])

    # 4. IXP: Members per IXP
    ixp_members = {}
    with open(os.path.join(DATA_DIR, 'ixp_stats.csv')) as f:
        for row in csv.DictReader(f):
            ixp_members[row['ixp_name']] = int(row['member_count'])

    # 5. Organization: ASes per org
    org_as = {}
    with open(os.path.join(DATA_DIR, 'org_power_top500.csv')) as f:
        for row in csv.DictReader(f):
            org_as[row['org_name']] = int(row['as_count'])

    # ── Compute metrics ──
    datasets = {}

    if dns_auth:
        dns_vals = sorted(dns_auth.values(), reverse=True)
        total_dns = sum(dns_vals)
        dns_shares = [v / total_dns for v in dns_vals]
        datasets['DNS Authority'] = {
            'values': dns_vals,
            'shares': dns_shares,
            'hhi': hhi_index(dns_shares[:100]),
            'gini': gini_coefficient(dns_vals),
            'top1': dns_shares[0],
            'top5': sum(dns_shares[:5]),
            'top10': sum(dns_shares[:10]),
            'color': COLORS['red'],
        }

    pfx_vals = sorted(as_pfx.values(), reverse=True)
    total_pfx = sum(pfx_vals)
    pfx_shares = [v / total_pfx for v in pfx_vals]
    datasets['BGP Prefixes'] = {
        'values': pfx_vals,
        'shares': pfx_shares,
        'hhi': hhi_index(pfx_shares[:100]),
        'gini': gini_coefficient(pfx_vals),
        'top1': pfx_shares[0],
        'top5': sum(pfx_shares[:5]),
        'top10': sum(pfx_shares[:10]),
        'color': COLORS['cyan'],
    }

    if dns_hosting:
        host_vals = sorted(dns_hosting.values(), reverse=True)
        total_host = sum(host_vals)
        host_shares = [v / total_host for v in host_vals]
        datasets['DNS Hosting'] = {
            'values': host_vals,
            'shares': host_shares,
            'hhi': hhi_index(host_shares[:100]),
            'gini': gini_coefficient(host_vals),
            'top1': host_shares[0],
            'top5': sum(host_shares[:5]),
            'top10': sum(host_shares[:10]),
            'color': COLORS['green'],
        }

    ixp_vals = sorted(ixp_members.values(), reverse=True)
    total_ixp = sum(ixp_vals)
    ixp_shares = [v / total_ixp for v in ixp_vals]
    datasets['IXP Membership'] = {
        'values': ixp_vals,
        'shares': ixp_shares,
        'hhi': hhi_index(ixp_shares[:100]),
        'gini': gini_coefficient(ixp_vals),
        'top1': ixp_shares[0],
        'top5': sum(ixp_shares[:5]),
        'top10': sum(ixp_shares[:10]),
        'color': COLORS['orange'],
    }

    org_vals = sorted(org_as.values(), reverse=True)
    total_org = sum(org_vals)
    org_shares = [v / total_org for v in org_vals]
    datasets['Organization Control'] = {
        'values': org_vals,
        'shares': org_shares,
        'hhi': hhi_index(org_shares[:100]),
        'gini': gini_coefficient(org_vals),
        'top1': org_shares[0],
        'top5': sum(org_shares[:5]),
        'top10': sum(org_shares[:10]),
        'color': COLORS['purple'],
    }

    # ── Visualization ──
    fig = plt.figure(figsize=(30, 18))
    fig.patch.set_facecolor(DARK_BG)
    gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.35,
                          left=0.06, right=0.96, top=0.90, bottom=0.06)

    # Panel 1: Lorenz curves (all dimensions)
    ax1 = fig.add_subplot(gs[0, 0])
    style_ax(ax1, 'Lorenz Curves\n(closer to diagonal = more equal)', 'Cumulative % of entities', 'Cumulative % of resources')
    ax1.plot([0, 1], [0, 1], '--', color=DARK_BORDER, linewidth=1, label='Perfect equality')
    for name, d in datasets.items():
        lx, ly = lorenz_curve(d['values'])
        ax1.plot(lx, ly, '-', color=d['color'], linewidth=2, label=f'{name} (Gini={d["gini"]:.3f})')
    ax1.legend(fontsize=8, facecolor=DARK_PANEL, edgecolor=DARK_BORDER, labelcolor=TEXT_MUTED)
    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)

    # Panel 2: HHI comparison bar chart
    ax2 = fig.add_subplot(gs[0, 1])
    style_ax(ax2, 'Herfindahl-Hirschman Index (HHI)\n(Top-100 entities)', 'Dimension', 'HHI')
    names = list(datasets.keys())
    hhis = [datasets[n]['hhi'] for n in names]
    colors = [datasets[n]['color'] for n in names]
    bars = ax2.bar(range(len(names)), hhis, color=colors, edgecolor=DARK_BORDER)
    ax2.set_xticks(range(len(names)))
    ax2.set_xticklabels(names, fontsize=9, color=TEXT_MUTED, rotation=20, ha='right')
    for bar, val in zip(bars, hhis):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.002,
                 f'{val:.4f}', ha='center', fontsize=9, color=TEXT_MUTED, fontweight='bold')
    # HHI thresholds
    ax2.axhline(0.25, color=COLORS['red'], linestyle='--', alpha=0.5, linewidth=1)
    ax2.axhline(0.15, color=COLORS['yellow'], linestyle='--', alpha=0.5, linewidth=1)
    ax2.text(0.98, 0.95, 'HHI > 0.25: Highly concentrated\nHHI 0.15-0.25: Moderately concentrated',
             transform=ax2.transAxes, ha='right', va='top', fontsize=8, color=TEXT_SECONDARY,
             bbox=dict(boxstyle='round,pad=0.3', facecolor=DARK_BG, edgecolor=DARK_BORDER))

    # Panel 3: Top-N concentration ratio
    ax3 = fig.add_subplot(gs[0, 2])
    style_ax(ax3, 'Concentration Ratios\n(CR1, CR5, CR10)', 'Dimension', 'Market Share (%)')
    x_pos = np.arange(len(names))
    w = 0.25
    for i, (label, key) in enumerate([('Top-1', 'top1'), ('Top-5', 'top5'), ('Top-10', 'top10')]):
        vals = [datasets[n][key] * 100 for n in names]
        bars = ax3.bar(x_pos + i * w - w, vals, w, label=label,
                       color=[COLORS['red'], COLORS['yellow'], COLORS['green']][i],
                       alpha=0.8, edgecolor=DARK_BORDER)
        for bar, val in zip(bars, vals):
            if val > 1:
                ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                         f'{val:.1f}%', ha='center', fontsize=6, color=TEXT_MUTED)
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(names, fontsize=8, color=TEXT_MUTED, rotation=20, ha='right')
    ax3.legend(fontsize=9, facecolor=DARK_PANEL, edgecolor=DARK_BORDER, labelcolor=TEXT_MUTED)

    # Panel 4: Rank-size plot (all dimensions)
    ax4 = fig.add_subplot(gs[1, 0])
    style_ax(ax4, 'Rank-Size Plot (Zipf)\n(all dimensions)', 'Rank', 'Size')
    for name, d in datasets.items():
        ax4.loglog(range(1, len(d['values']) + 1), d['values'],
                   '-', color=d['color'], linewidth=1.5, label=name, alpha=0.8)
    ax4.legend(fontsize=8, facecolor=DARK_PANEL, edgecolor=DARK_BORDER, labelcolor=TEXT_MUTED)

    # Panel 5: Gini coefficient comparison
    ax5 = fig.add_subplot(gs[1, 1])
    style_ax(ax5, 'Gini Coefficient Comparison\n(0=equal, 1=monopoly)', 'Dimension', 'Gini')
    ginis = [datasets[n]['gini'] for n in names]
    bars = ax5.barh(range(len(names)), ginis, color=colors, edgecolor=DARK_BORDER, height=0.6)
    ax5.set_yticks(range(len(names)))
    ax5.set_yticklabels(names, fontsize=10, color=TEXT_MUTED)
    for bar, val in zip(bars, ginis):
        ax5.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2,
                 f'{val:.3f}', va='center', fontsize=10, color=TEXT_PRIMARY, fontweight='bold')
    ax5.set_xlim(0, 1.1)
    ax5.axvline(0.5, color=COLORS['yellow'], linestyle='--', alpha=0.5)

    # Panel 6: Summary table
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.set_facecolor(DARK_PANEL)
    ax6.axis('off')
    ax6.set_title('Concentration Summary', fontsize=14, fontweight='bold',
                  color=TEXT_PRIMARY, pad=12)

    lines = [f'{"Dimension":<22} {"Gini":>6} {"HHI":>8} {"CR1%":>6} {"CR5%":>6} {"CR10%":>7}']
    lines.append('─' * 58)
    for name in names:
        d = datasets[name]
        lines.append(f'{name:<22} {d["gini"]:>6.3f} {d["hhi"]:>8.4f} '
                     f'{d["top1"]*100:>5.1f}% {d["top5"]*100:>5.1f}% {d["top10"]*100:>6.1f}%')

    lines.append('')
    lines.append('Interpretation:')
    most_concentrated = max(datasets.items(), key=lambda x: x[1]['gini'])
    least_concentrated = min(datasets.items(), key=lambda x: x[1]['gini'])
    lines.append(f'  Most concentrated: {most_concentrated[0]}')
    lines.append(f'    (Gini={most_concentrated[1]["gini"]:.3f})')
    lines.append(f'  Least concentrated: {least_concentrated[0]}')
    lines.append(f'    (Gini={least_concentrated[1]["gini"]:.3f})')

    ax6.text(0.05, 0.95, '\n'.join(lines), transform=ax6.transAxes,
             fontsize=9, color=TEXT_MUTED, va='top', family='monospace',
             bbox=dict(boxstyle='round,pad=0.5', facecolor=DARK_BG, edgecolor=DARK_BORDER))

    fig.suptitle(
        'Internet Infrastructure Concentration Analysis\n'
        '5 Dimensions: DNS Authority, BGP Prefixes, DNS Hosting, IXP Membership, Organization Control | IYP 2026-04-08',
        fontsize=16, fontweight='bold', color=TEXT_PRIMARY, y=0.96
    )

    save_fig(fig, 'step13_concentration_hhi.png')


if __name__ == '__main__':
    main()
