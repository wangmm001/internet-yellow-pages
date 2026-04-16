"""CDN Detection & Anycast Analysis Dashboard from IYP data."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.patches as mpatches
import numpy as np

# ============================================================
# Pre-queried data from Neo4j
# ============================================================

# 1. IP distribution per hostname
ip_dist = {
    '1 IP': 11526311,
    '2 IPs': 3227281,
    '3-4 IPs': 2447639,
    '5-10 IPs': 2327020,
    '11-20 IPs': 375373,
    '21-50 IPs': 471618,
    '50+ IPs': 346128,
}

# 2. AS-level hosting market share (hostnames on their IPs)
as_hosting = [
    ('Oracle/Bluehost\nAS31898', 27404332, False, True),
    ('Network Solutions\nAS19871', 22458249, False, True),
    ('Google\nAS15169', 16701986, True, True),
    ('Cloudflare\nAS13335', 14960714, True, True),
    ('Unified Layer\nAS46606', 5428758, False, True),
    ('Microsoft\nAS8075', 4430224, True, True),
    ('Amazon AWS\nAS16509', 4261570, True, True),
    ('Squarespace\nAS53831', 2310854, True, False),
    ('Wix\nAS58182', 1802010, True, False),
    ('Google Cloud\nAS396982', 1697884, True, True),
    ('Automattic\nAS2635', 1419248, True, False),
    ('OVH\nAS16276', 1371326, False, True),
    ('PDR\nAS394695', 1327705, False, True),
    ('Cloudflare Spectrum\nAS209242', 1176798, True, True),
    ('Azion\nAS52580', 1083452, True, False),
]

# 3. Top anycast ASes by prefix count
anycast_as = [
    ('Incapsula/Imperva', 19551, 850),
    ('Cloudflare', 13335, 822),
    ('Amazon AWS', 16509, 736),
    ('Afilias', 12041, 451),
    ('Fastly', 54113, 380),
    ('Cloudflare Spectrum', 209242, 250),
    ('Google Cloud', 396982, 210),
    ('NetActuate', 63911, 182),
    ('Afilias Secondary', 207266, 164),
    ('Vercara', 12008, 163),
    ('Akamai', 21342, 155),
    ('ACE', 139341, 132),
    ('Fly.io', 40509, 121),
    ('WoodyNet', 42, 112),
    ('Meteverse', 54994, 82),
]

# 4. CDN provider profiles
cdn_profiles = {
    'Cloudflare': {
        'asn': 13335,
        'anycast_pfx': 822,
        'hosted': 14960714,
        'tags': ['CDN', 'DDoS', 'Anycast', 'Critical Infra'],
        'top_ip_hosts': 960759,  # single IP hosts this many
    },
    'Akamai': {
        'asn': 20940,
        'anycast_pfx': 155,  # AS21342
        'hosted': 0,  # via CNAME mostly
        'tags': ['CDN', 'Anycast', 'Streaming'],
        'top_ip_hosts': 0,
    },
    'Fastly': {
        'asn': 54113,
        'anycast_pfx': 380,
        'hosted': 828090,
        'tags': ['CDN', 'DDoS', 'Anycast'],
        'top_ip_hosts': 0,
    },
    'Amazon CF': {
        'asn': 16509,
        'anycast_pfx': 736,
        'hosted': 4261570,
        'tags': ['CDN', 'Cloud', 'Anycast'],
        'top_ip_hosts': 0,
    },
    'Google': {
        'asn': 15169,
        'anycast_pfx': 51,
        'hosted': 16701986,
        'tags': ['CDN', 'Anycast', 'Critical Infra'],
        'top_ip_hosts': 0,
    },
    'Imperva': {
        'asn': 19551,
        'anycast_pfx': 850,
        'hosted': 0,
        'tags': ['CDN', 'DDoS', 'Anycast'],
        'top_ip_hosts': 0,
    },
    'Microsoft': {
        'asn': 8075,
        'anycast_pfx': 76,
        'hosted': 4430224,
        'tags': ['Content', 'Anycast', 'Critical Infra'],
        'top_ip_hosts': 0,
    },
}

# 5. Key stats
total_hostnames = 21298259
anycast_hostnames = 6693310
anycast_pct = anycast_hostnames / total_hostnames * 100
total_anycast_pfx = 14245
anycast_as_count = 950
content_as_count = 1485

# ============================================================
# Create 2x2 dashboard
# ============================================================
fig = plt.figure(figsize=(30, 24))
fig.patch.set_facecolor('#0D1117')

# Grid: 2 rows, top row has 2 charts, bottom row has 3
gs = fig.add_gridspec(2, 6, hspace=0.35, wspace=0.4,
                      left=0.06, right=0.96, top=0.90, bottom=0.05)
ax1 = fig.add_subplot(gs[0, :3])
ax2 = fig.add_subplot(gs[0, 3:])
ax3 = fig.add_subplot(gs[1, :2])
ax4 = fig.add_subplot(gs[1, 2:4])
ax5 = fig.add_subplot(gs[1, 4:])

def style_ax(ax, title):
    ax.set_facecolor('#161B22')
    ax.set_title(title, fontsize=14, fontweight='bold', color='#E6EDF3', pad=12)
    ax.tick_params(colors='#8B949E', labelsize=9)
    for spine in ax.spines.values():
        spine.set_color('#30363D')

# ====== Chart 1: Hostname IP Distribution (CDN indicator) ======
style_ax(ax1, 'Hostname IP Distribution\n(Multi-IP = likely CDN/Anycast)')
labels1 = list(ip_dist.keys())
vals1 = list(ip_dist.values())
colors1 = ['#6C757D', '#5BC0DE', '#45B7D1', '#4ECDC4', '#2A9D8F', '#FF6B6B', '#E63946']
bars1 = ax1.bar(labels1, vals1, color=colors1, edgecolor='#30363D', width=0.7)
ax1.set_ylabel('Number of HostNames', color='#8B949E', fontsize=11)
ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x/1e6:.1f}M'))

# Annotations
for bar, val in zip(bars1, vals1):
    pct = val / total_hostnames * 100
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 100000,
             f'{val/1e6:.1f}M\n({pct:.1f}%)', ha='center', va='bottom',
             fontsize=9, color='#C9D1D9', fontweight='bold')

# Add CDN zone highlight
ax1.axvspan(2.5, 6.5, alpha=0.08, color='#FF6B6B')
ax1.text(4.5, max(vals1)*0.85, 'CDN / Anycast Zone\n(3+ IPs)',
         ha='center', fontsize=12, color='#FF6B6B', fontweight='bold',
         style='italic')
single_ip_pct = vals1[0] / total_hostnames * 100
multi_ip = sum(vals1[2:])
multi_ip_pct = multi_ip / total_hostnames * 100
ax1.text(0, max(vals1)*0.75, f'Single-IP:\n{single_ip_pct:.0f}%',
         ha='center', fontsize=11, color='#6C757D', fontweight='bold')

# ====== Chart 2: AS-level CDN Market Share ======
style_ax(ax2, 'Hosting Concentration by AS\n(HostNames resolving to AS IP space)')
names2 = [x[0] for x in reversed(as_hosting)]
vals2 = [x[1] for x in reversed(as_hosting)]
is_cdn = [x[2] for x in reversed(as_hosting)]
is_hosting = [x[3] for x in reversed(as_hosting)]

colors2 = []
for cdn, hosting in zip(is_cdn, is_hosting):
    if cdn and hosting:
        colors2.append('#FF6B6B')   # CDN + Cloud
    elif cdn:
        colors2.append('#4ECDC4')   # Pure CDN/Platform
    else:
        colors2.append('#45B7D1')   # Traditional Hosting

bars2 = ax2.barh(range(len(names2)), vals2, color=colors2, edgecolor='#30363D', height=0.7)
ax2.set_yticks(range(len(names2)))
ax2.set_yticklabels(names2, fontsize=8, color='#C9D1D9', family='monospace')
ax2.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x/1e6:.0f}M'))
ax2.set_xlabel('HostNames on AS IP space', color='#8B949E', fontsize=10)

for bar, val in zip(bars2, vals2):
    ax2.text(bar.get_width() + 200000, bar.get_y() + bar.get_height()/2,
             f'{val/1e6:.1f}M', va='center', fontsize=8, color='#C9D1D9')

legend2 = [
    mpatches.Patch(color='#FF6B6B', label='CDN + Cloud Provider'),
    mpatches.Patch(color='#4ECDC4', label='CDN / Platform'),
    mpatches.Patch(color='#45B7D1', label='Traditional Hosting'),
]
ax2.legend(handles=legend2, loc='lower right', fontsize=9,
           facecolor='#161B22', edgecolor='#30363D', labelcolor='#C9D1D9')

# ====== Chart 3: Anycast Prefix Distribution by AS ======
style_ax(ax3, 'Anycast Prefix Count by AS\n(BGP Anycast deployment scale)')
names3 = [f'{x[0]}\nAS{x[1]}' for x in reversed(anycast_as)]
vals3 = [x[2] for x in reversed(anycast_as)]

gradient = plt.cm.magma(np.linspace(0.25, 0.85, len(vals3)))
bars3 = ax3.barh(range(len(names3)), vals3, color=gradient, edgecolor='#30363D', height=0.7)
ax3.set_yticks(range(len(names3)))
ax3.set_yticklabels(names3, fontsize=7, color='#C9D1D9', family='monospace')
ax3.set_xlabel('Number of Anycast BGP Prefixes', color='#8B949E', fontsize=10)

for bar, val in zip(bars3, vals3):
    ax3.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2,
             str(val), va='center', fontsize=8, color='#C9D1D9')

# ====== Chart 4: Anycast vs Unicast pie ======
style_ax(ax4, 'Anycast vs Unicast HostNames\n(based on BGP prefix tagging)')
sizes4 = [anycast_hostnames, total_hostnames - anycast_hostnames]
labels4 = [f'Anycast\n{anycast_hostnames/1e6:.1f}M ({anycast_pct:.1f}%)',
           f'Unicast\n{(total_hostnames-anycast_hostnames)/1e6:.1f}M ({100-anycast_pct:.1f}%)']
colors4 = ['#FF6B6B', '#30363D']
explode4 = (0.05, 0)
wedges4, texts4 = ax4.pie(sizes4, labels=labels4, colors=colors4,
                           explode=explode4, startangle=90,
                           wedgeprops=dict(edgecolor='#0D1117', linewidth=2),
                           textprops=dict(color='#E6EDF3', fontsize=11, fontweight='bold'))

# Stats box
stats_text = (
    f'Total Anycast Prefixes: {total_anycast_pfx:,}\n'
    f'Anycast ASes: {anycast_as_count}\n'
    f'Content ASes: {content_as_count}\n'
    f'\nCloudflare single IP hosts\n'
    f'960,759 domains'
)
ax4.text(-0.1, -1.5, stats_text, fontsize=10, color='#8B949E',
         ha='center', va='top', family='monospace',
         bbox=dict(boxstyle='round,pad=0.5', facecolor='#0D1117', edgecolor='#30363D'))

# ====== Chart 5: CDN Provider Comparison Radar ======
style_ax(ax5, 'CDN Provider Fingerprints')

# Simplified comparison table
providers = ['Cloudflare', 'Amazon', 'Google', 'Fastly', 'Imperva', 'Microsoft', 'Akamai']
metrics = ['Anycast\nPrefixes', 'Hosted\nDomains (M)', 'Tags\nCount']
data = [
    [822, 15.0, 4],    # Cloudflare
    [736, 4.3, 4],     # Amazon
    [51, 16.7, 4],     # Google
    [380, 0.8, 4],     # Fastly
    [850, 0, 3],       # Imperva
    [76, 4.4, 3],      # Microsoft
    [155, 0, 3],       # Akamai
]

# Grouped bar chart instead
x5 = np.arange(len(providers))
width = 0.35

ax5_twin = ax5.twinx()

bars5a = ax5.bar(x5 - width/2, [d[0] for d in data], width,
                 color='#FF6B6B', alpha=0.85, edgecolor='#30363D', label='Anycast Prefixes')
bars5b = ax5_twin.bar(x5 + width/2, [d[1] for d in data], width,
                       color='#4ECDC4', alpha=0.85, edgecolor='#30363D', label='Hosted Domains (M)')

ax5.set_xticks(x5)
ax5.set_xticklabels(providers, fontsize=9, color='#C9D1D9', rotation=25, ha='right')
ax5.set_ylabel('Anycast Prefixes', color='#FF6B6B', fontsize=10)
ax5_twin.set_ylabel('Hosted Domains (Millions)', color='#4ECDC4', fontsize=10)
ax5.tick_params(axis='y', colors='#FF6B6B')
ax5_twin.tick_params(axis='y', colors='#4ECDC4')
ax5_twin.set_facecolor('#161B22')
for spine in ax5_twin.spines.values():
    spine.set_color('#30363D')

# Add value labels
for bar in bars5a:
    h = bar.get_height()
    if h > 0:
        ax5.text(bar.get_x() + bar.get_width()/2, h + 10,
                 str(int(h)), ha='center', fontsize=8, color='#FF6B6B', fontweight='bold')
for bar in bars5b:
    h = bar.get_height()
    if h > 0:
        ax5_twin.text(bar.get_x() + bar.get_width()/2, h + 0.3,
                      f'{h:.1f}M', ha='center', fontsize=8, color='#4ECDC4', fontweight='bold')

lines1, labels1 = ax5.get_legend_handles_labels()
lines2, labels2 = ax5_twin.get_legend_handles_labels()
ax5.legend(lines1 + lines2, labels1 + labels2, loc='upper right',
           fontsize=9, facecolor='#161B22', edgecolor='#30363D', labelcolor='#C9D1D9')

# ====== Super title ======
fig.suptitle(
    'CDN Detection & Anycast Deployment Analysis\n'
    f'21.3M HostNames | 14,245 Anycast Prefixes | 950 Anycast ASes | 1,485 Content ASes | IYP 2026-04-08',
    fontsize=20, fontweight='bold', color='#E6EDF3', y=0.97
)

plt.savefig('/home/wangmm/internet-yellow-pages/cdn_detection.png',
            dpi=180, bbox_inches='tight', facecolor='#0D1117', edgecolor='none')
print('Saved: cdn_detection.png')
