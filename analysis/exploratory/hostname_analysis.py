"""HostName analysis dashboard - 4 charts from IYP data."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

# ============================================================
# Data (pre-queried from Neo4j)
# ============================================================

# 1. Top CNAME targets (website platform market share)
cname_data = [
    ('Wix', 429020 + 52895),
    ('Shopify', 309880),
    ('Blogspot/Google', 174279 + 64712 + 44143),
    ('Webflow', 97649 + 14932),
    ('Squarespace', 88332 + 79786),
    ('WordPress.com', 78914),
    ('Fastly CDN', 71061 + 40099),
    ('Tistory (Kakao)', 64966),
    ('Vercel', 54560),
    ('Tienda Nube', 34385 + 21069),
    ('Multiscreensite', 41115),
    ('Shoptet', 27980),
    ('Webnode', 27420),
    ('Fandom', 24360),
    ('WP Engine', 22033),
]

# 2. Top shared IPs (hosting concentration)
ip_data = [
    ('188.114.97.0\n(Cloudflare)', 960759),
    ('188.114.96.0\n(Cloudflare)', 960757),
    ('2a06:98c1:3121::\n(Cloudflare v6)', 949207),
    ('2a06:98c1:3120::\n(Cloudflare v6)', 949203),
    ('::1\n(Localhost)', 828633),
    ('23.227.38.65\n(Shopify)', 619584),
    ('34.160.37.117\n(Google Cloud)', 528093),
    ('103.7.9.22\n(Unknown)', 450253),
    ('216.92.3.51\n(Hosting)', 422604),
    ('66.81.203.137\n(Hosting)', 411966),
]

# 3. Top domains by subdomain count (infrastructure footprint)
domain_data = [
    ('blogspot.com', 87074),
    ('cloudflare.net', 51537),
    ('edgekey.net', 40332),
    ('wordpress.com', 39460),
    ('googlevideo.com', 34745),
    ('myshopify.com', 34265),
    ('tistory.com', 32488),
    ('azurewebsites.net', 25893),
    ('sharepoint.com', 25339 + 23655),
    ('softonic.com', 24425),
    ('skysound7.com', 22638),
    ('uptodown.com', 18313),
    ('impervadns.net', 18209),
    ('mitiendanube.com', 17187),
    ('fbcdn.net', 15534),
]

# 4. HostName relationship breakdown
rel_data = [
    ('RESOLVES_TO\n(-> IP)', 147352606),
    ('RANK\n(-> Ranking)', 26386961),
    ('PART_OF\n(-> DomainName)', 23922535),
    ('ALIAS_OF\n(-> HostName)', 9104815),
    ('MANAGED_BY\n(<- DomainName)', 49987836),
    ('MANAGED_BY\n(<- Prefix)', 3498679),
    ('PART_OF\n(<- URL)', 33578),
    ('TARGET\n(<- AtlasMeas.)', 20411),
]

# ============================================================
# Plot
# ============================================================
fig, axes = plt.subplots(2, 2, figsize=(28, 22))
fig.patch.set_facecolor('#0D1117')

colors_warm = plt.cm.YlOrRd(np.linspace(0.3, 0.85, 15))[::-1]
colors_cool = plt.cm.YlGnBu(np.linspace(0.3, 0.85, 15))[::-1]
colors_teal = plt.cm.viridis(np.linspace(0.3, 0.85, 15))[::-1]

def style_ax(ax, title):
    ax.set_facecolor('#161B22')
    ax.set_title(title, fontsize=15, fontweight='bold', color='#E6EDF3', pad=15)
    ax.tick_params(colors='#8B949E', labelsize=10)
    for spine in ax.spines.values():
        spine.set_color('#30363D')

# ------ Chart 1: CNAME Platform Market Share ------
ax1 = axes[0, 0]
style_ax(ax1, 'Website Platform Market Share\n(by CNAME alias count)')
names, vals = zip(*sorted(cname_data, key=lambda x: x[1]))
y_pos = np.arange(len(names))
bars = ax1.barh(y_pos, vals, color=colors_warm[:len(names)], edgecolor='#30363D', height=0.7)
ax1.set_yticks(y_pos)
ax1.set_yticklabels(names, fontsize=10, color='#C9D1D9')
ax1.set_xlabel('Number of CNAME aliases pointing to platform', color='#8B949E', fontsize=11)
ax1.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x/1000:.0f}K'))
for bar, val in zip(bars, vals):
    ax1.text(bar.get_width() + 5000, bar.get_y() + bar.get_height()/2,
             f'{val:,}', va='center', fontsize=8, color='#C9D1D9')

# ------ Chart 2: IP Hosting Concentration ------
ax2 = axes[0, 1]
style_ax(ax2, 'IP Address Hosting Concentration\n(domains per single IP)')
names2, vals2 = zip(*ip_data)
y_pos2 = np.arange(len(names2))
bars2 = ax2.barh(y_pos2, vals2, color=colors_cool[:len(names2)], edgecolor='#30363D', height=0.7)
ax2.set_yticks(y_pos2)
ax2.set_yticklabels(names2, fontsize=8, color='#C9D1D9', family='monospace')
ax2.set_xlabel('Number of HostNames resolving to this IP', color='#8B949E', fontsize=11)
ax2.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x/1000:.0f}K'))
for bar, val in zip(bars2, vals2):
    ax2.text(bar.get_width() + 10000, bar.get_y() + bar.get_height()/2,
             f'{val:,}', va='center', fontsize=8, color='#C9D1D9')

# ------ Chart 3: Domain Infrastructure Footprint ------
ax3 = axes[1, 0]
style_ax(ax3, 'DNS Infrastructure Footprint\n(subdomains per parent domain)')
names3, vals3 = zip(*sorted(domain_data, key=lambda x: x[1]))
y_pos3 = np.arange(len(names3))
bars3 = ax3.barh(y_pos3, vals3, color=colors_teal[:len(names3)], edgecolor='#30363D', height=0.7)
ax3.set_yticks(y_pos3)
ax3.set_yticklabels(names3, fontsize=10, color='#C9D1D9', family='monospace')
ax3.set_xlabel('Number of HostNames under this domain', color='#8B949E', fontsize=11)
ax3.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x/1000:.0f}K'))
for bar, val in zip(bars3, vals3):
    ax3.text(bar.get_width() + 500, bar.get_y() + bar.get_height()/2,
             f'{val:,}', va='center', fontsize=8, color='#C9D1D9')

# ------ Chart 4: Relationship Type Breakdown ------
ax4 = axes[1, 1]
style_ax(ax4, 'HostName Relationship Types\n(21.3M nodes, 260M+ edges)')
rel_names = [r[0] for r in rel_data]
rel_vals = [r[1] for r in rel_data]
colors4 = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#F7DC6F', '#BB8FCE']
wedges, texts, autotexts = ax4.pie(
    rel_vals, labels=None, autopct='%1.1f%%',
    colors=colors4, startangle=90,
    pctdistance=0.8, wedgeprops=dict(edgecolor='#0D1117', linewidth=2)
)
for t in autotexts:
    t.set_fontsize(9)
    t.set_color('#0D1117')
    t.set_fontweight('bold')

legend_labels = [f'{n}  ({v/1e6:.1f}M)' for n, v in zip(rel_names, rel_vals)]
ax4.legend(wedges, legend_labels, loc='center left', bbox_to_anchor=(-0.35, 0.5),
           fontsize=10, facecolor='#161B22', edgecolor='#30363D',
           labelcolor='#C9D1D9', framealpha=0.95)

# Super title
fig.suptitle('IYP HostName Analysis Dashboard — 21.3 Million DNS Hostnames\nData: IYP 2026-04-08 | 147M DNS resolutions, 9.1M CNAME aliases, 26.4M rankings',
             fontsize=20, fontweight='bold', color='#E6EDF3', y=0.98)

plt.tight_layout(rect=[0, 0, 1, 0.94])
plt.savefig('/home/wangmm/internet-yellow-pages/hostname_analysis.png',
            dpi=180, bbox_inches='tight', facecolor='#0D1117', edgecolor='none')
print('Saved: hostname_analysis.png')
