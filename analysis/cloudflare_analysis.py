"""Cloudflare Full-Chain Analysis - All Dimensions Dashboard."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
import numpy as np

fig = plt.figure(figsize=(36, 48))
fig.patch.set_facecolor('#0D1117')

gs = fig.add_gridspec(6, 3, hspace=0.35, wspace=0.3,
                      left=0.05, right=0.97, top=0.95, bottom=0.02)

def style_ax(ax, title):
    ax.set_facecolor('#161B22')
    ax.set_title(title, fontsize=13, fontweight='bold', color='#E6EDF3', pad=12)
    ax.tick_params(colors='#8B949E', labelsize=8)
    for spine in ax.spines.values():
        spine.set_color('#30363D')

# ============ Row 0: Identity Card (spanning full width) ============
ax_card = fig.add_subplot(gs[0, :])
ax_card.set_facecolor('#161B22')
ax_card.axis('off')

card_text = """
\u2588\u2588  CLOUDFLARE, INC.  (AS13335)  \u2588\u2588

\u250c\u2500 Identity \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510   \u250c\u2500 Network Scale \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510   \u250c\u2500 DNS/Hosting \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510
\u2502  Names: CLOUDFLARENET, CF, Cloudflare        \u2502   \u2502  BGP Prefixes: 11,251 (4,978 v4 / 6,273 v6) \u2502   \u2502  Hosted HostNames:   3,686,326              \u2502
\u2502  Organization: Cloudflare, Inc.               \u2502   \u2502  Anycast Prefixes: 822                      \u2502   \u2502  Managed Domains:    2,084,776 (via CF DNS)  \u2502
\u2502  Country: US                                   \u2502   \u2502  RPKI ROA: 4,703 authorizations              \u2502   \u2502  CNAME aliases:      120,407 pointing to CF  \u2502
\u2502  Website: cloudflare.com                       \u2502   \u2502  Peers: 1,731 ASes                           \u2502   \u2502  Managed Prefixes:   6,977 (rDNS via CF NS)  \u2502
\u2502  PeeringDB: NET-4224                           \u2502   \u2502  IXP Members: 350 (in 76 countries)           \u2502   \u2502  IP Addresses:       221,211                 \u2502
\u2502  Sibling ASes: 6 (AS209242, AS14789, ...)      \u2502   \u2502  Facilities: 222 (in 56 countries)            \u2502   \u2502  Top IP: 188.114.97.0 \u2192 1.92M domains       \u2502
\u2502  Tags: CDN, DDoS, Anycast, Critical Infra,     \u2502   \u2502  Dependent ASes: 961                         \u2502   \u2502  Atlas Probes: 31 in CF network              \u2502
\u2502        ISP, VPN Host, RPKI Validating           \u2502   \u2502  Dependent Prefixes: 11,568                  \u2502   \u2502  Atlas Measurements: 742 targeting CF         \u2502
\u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518   \u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518   \u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518
"""
ax_card.text(0.5, 0.5, card_text, fontsize=10, color='#E6EDF3',
            ha='center', va='center', family='monospace',
            bbox=dict(boxstyle='round,pad=1', facecolor='#0D1117', edgecolor='#FF6B6B', linewidth=2))

# ============ Row 1, Col 0: BGP Prefix IPv4 vs IPv6 ============
ax1 = fig.add_subplot(gs[1, 0])
style_ax(ax1, 'Step 4: BGP Prefix Distribution\n(IPv4 vs IPv6)')
sizes = [4978, 6273]
labels = [f'IPv4\n{4978}', f'IPv6\n{6273}']
colors = ['#FF6B6B', '#45B7D1']
wedges, texts = ax1.pie(sizes, labels=labels, colors=colors, startangle=90,
                        wedgeprops=dict(edgecolor='#0D1117', linewidth=2),
                        textprops=dict(color='#E6EDF3', fontsize=11, fontweight='bold'))
ax1.text(0, -1.4, f'Total: 11,251 prefixes\n822 Anycast ({822/11251*100:.1f}%)\n4,703 RPKI ROA',
        ha='center', fontsize=10, color='#8B949E', family='monospace')

# ============ Row 1, Col 1: Tier-1 Peering ============
ax2 = fig.add_subplot(gs[1, 1])
style_ax(ax2, 'Step 7: Tier-1 Peering Status\n(13/13 major backbones)')
tier1 = [
    ('AS174 Cogent', 1), ('AS701 Verizon', 1), ('AS1299 Arelion', 1),
    ('AS2914 NTT', 1), ('AS3257 GTT', 1), ('AS3356 Level3', 1),
    ('AS3491 PCCW', 1), ('AS6453 Tata', 1), ('AS6461 Zayo', 1),
    ('AS6762 Sparkle', 1), ('AS6939 HE', 1), ('AS7018 AT&T', 1),
    ('AS9002 RETN', 1),
]
names_t1 = [t[0] for t in tier1]
vals_t1 = [t[1] for t in tier1]
colors_t1 = ['#2A9D8F'] * len(tier1)
ax2.barh(range(len(names_t1)), vals_t1, color=colors_t1, edgecolor='#30363D', height=0.7)
ax2.set_yticks(range(len(names_t1)))
ax2.set_yticklabels(names_t1, fontsize=8, color='#C9D1D9', family='monospace')
ax2.set_xlim(0, 1.5)
ax2.set_xticks([0, 1])
ax2.set_xticklabels(['No', 'Yes'], color='#8B949E')
for i in range(len(tier1)):
    ax2.text(1.05, i, '\u2714', fontsize=14, color='#2A9D8F', va='center', fontweight='bold')
ax2.text(0.75, -1.5, 'Cloudflare peers with ALL\n13 major Tier-1 networks',
        ha='center', fontsize=10, color='#2A9D8F', fontweight='bold')

# ============ Row 1, Col 2: Sibling ASes ============
ax3 = fig.add_subplot(gs[1, 2])
style_ax(ax3, 'Step 3: Cloudflare AS Family\n(SIBLING_OF relationships)')
siblings = [
    ('AS13335\nCLOUDFLARENET\n(Primary)', 11251, '#FF6B6B'),
    ('AS209242\nSpectrum\n(L4 Proxy)', 680, '#4ECDC4'),
    ('AS14789\nCLOUDFLARENET\n(Secondary)', 534, '#45B7D1'),
    ('AS132892\nCLOUDFLARE\n(APAC)', 105, '#FFEAA7'),
    ('AS395747\nSFO05', 85, '#DDA0DD'),
    ('AS394536\nSFO', 2, '#8B949E'),
    ('AS400095\nArea1 Security', 2, '#96CEB4'),
]
names_s = [s[0] for s in siblings]
vals_s = [s[1] for s in siblings]
colors_s = [s[2] for s in siblings]
bars = ax3.barh(range(len(names_s)), vals_s, color=colors_s, edgecolor='#30363D', height=0.7)
ax3.set_yticks(range(len(names_s)))
ax3.set_yticklabels(names_s, fontsize=7, color='#C9D1D9', family='monospace')
ax3.set_xlabel('BGP Prefixes originated', color='#8B949E', fontsize=9)
ax3.set_xscale('log')
for bar, val in zip(bars, vals_s):
    ax3.text(bar.get_width() * 1.3, bar.get_y() + bar.get_height()/2,
            str(val), va='center', fontsize=9, color='#C9D1D9')

# ============ Row 2, Col 0: Global Facility Presence ============
ax4 = fig.add_subplot(gs[2, 0])
style_ax(ax4, 'Step 9: Global Facility Presence\n(222 facilities in 56 countries)')
fac_data = [
    ('US', 85), ('BR', 11), ('CA', 8), ('IN', 8), ('AU', 8),
    ('DE', 7), ('GB', 7), ('FR', 6), ('NZ', 4), ('NL', 4),
    ('JP', 4), ('ES', 4), ('TR', 3), ('RU', 3), ('ZA', 3),
    ('SG', 3), ('IT', 3), ('Other (39)', 56),
]
names_f = [f[0] for f in reversed(fac_data)]
vals_f = [f[1] for f in reversed(fac_data)]
colors_f = plt.cm.YlOrRd(np.linspace(0.2, 0.85, len(vals_f)))
bars4 = ax4.barh(range(len(names_f)), vals_f, color=colors_f, edgecolor='#30363D', height=0.7)
ax4.set_yticks(range(len(names_f)))
ax4.set_yticklabels(names_f, fontsize=9, color='#C9D1D9', fontweight='bold')
ax4.set_xlabel('Number of facilities', color='#8B949E', fontsize=9)
for bar, val in zip(bars4, vals_f):
    ax4.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
            str(val), va='center', fontsize=8, color='#C9D1D9')

# ============ Row 2, Col 1: Prefix Geographic Distribution ============
ax5 = fig.add_subplot(gs[2, 1])
style_ax(ax5, 'Step 19: Prefix Geographic Distribution\n(BGP prefixes by registered country)')
geo_data = [
    ('US', 2756), ('ZZ', 619), ('BR', 189), ('IN', 145), ('DE', 139),
    ('SG', 108), ('GB', 107), ('FR', 97), ('JP', 97), ('CA', 86),
    ('NL', 58), ('AU', 57), ('HK', 48), ('IT', 38), ('AR', 34),
]
names_g = [g[0] for g in reversed(geo_data)]
vals_g = [g[1] for g in reversed(geo_data)]
colors_g = plt.cm.viridis(np.linspace(0.2, 0.85, len(vals_g)))
bars5 = ax5.barh(range(len(names_g)), vals_g, color=colors_g, edgecolor='#30363D', height=0.7)
ax5.set_yticks(range(len(names_g)))
ax5.set_yticklabels(names_g, fontsize=9, color='#C9D1D9', fontweight='bold')
ax5.set_xlabel('BGP Prefixes registered', color='#8B949E', fontsize=9)
for bar, val in zip(bars5, vals_g):
    ax5.text(bar.get_width() + 10, bar.get_y() + bar.get_height()/2,
            str(val), va='center', fontsize=8, color='#C9D1D9')

# ============ Row 2, Col 2: IXP Presence by Region ============
ax6 = fig.add_subplot(gs[2, 2])
style_ax(ax6, 'Step 8: IXP Membership by Region\n(350 IXPs in 76 countries)')
# Group IXPs by region
region_ixps = {
    'North America': 80, 'Europe': 165, 'Asia-Pacific': 60,
    'Latin America': 25, 'Africa': 10, 'Middle East': 5, 'Oceania': 5,
}
r_names = list(region_ixps.keys())
r_vals = list(region_ixps.values())
r_colors = ['#FF6B6B', '#45B7D1', '#4ECDC4', '#FFEAA7', '#DDA0DD', '#96CEB4', '#F7DC6F']
wedges6, texts6, autotexts6 = ax6.pie(r_vals, labels=r_names, autopct='%1.0f%%',
    colors=r_colors, startangle=90, pctdistance=0.75,
    wedgeprops=dict(edgecolor='#0D1117', linewidth=2),
    textprops=dict(color='#E6EDF3', fontsize=9))
for t in autotexts6:
    t.set_fontsize(8)
    t.set_color('#0D1117')
    t.set_fontweight('bold')

# ============ Row 3, Col 0: DNS Dominance ============
ax7 = fig.add_subplot(gs[3, 0])
style_ax(ax7, 'Steps 13-16: DNS & Hosting Dominance\n(Cloudflare share of global IYP)')
metrics = ['Managed\nDomains', 'Hosted\nHostNames', 'CNAME\nAliases', 'Managed\nPrefixes']
cf_vals = [2084776, 3686326, 120407, 6977]
total_vals = [11184278, 21298259, 9104815, 1553954]
pcts = [c/t*100 for c, t in zip(cf_vals, total_vals)]

x = np.arange(len(metrics))
width = 0.35
bars_total = ax7.bar(x - width/2, total_vals, width, color='#30363D',
                     edgecolor='#30363D', label='Global Total')
bars_cf = ax7.bar(x + width/2, cf_vals, width, color='#FF6B6B',
                  edgecolor='#30363D', label='Cloudflare')
ax7.set_xticks(x)
ax7.set_xticklabels(metrics, fontsize=9, color='#C9D1D9')
ax7.set_yscale('log')
ax7.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K'))
ax7.legend(facecolor='#161B22', edgecolor='#30363D', labelcolor='#C9D1D9', fontsize=9)
for bar, pct in zip(bars_cf, pcts):
    ax7.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 1.5,
            f'{pct:.1f}%', ha='center', fontsize=10, color='#FF6B6B', fontweight='bold')

# ============ Row 3, Col 1: IP Concentration Risk ============
ax8 = fig.add_subplot(gs[3, 1])
style_ax(ax8, 'Step 22: IP Concentration Risk\n(Domains per single Cloudflare IP)')
ip_data = [
    ('188.114.97.0\n(v4)', 1921518),
    ('188.114.96.0\n(v4)', 1921514),
    ('2a06:98c1:3121::\n(v6)', 1898414),
    ('2a06:98c1:3120::\n(v6)', 1898406),
    ('23.227.38.65\n(Shopify/CF)', 1239168),
    ('2620:127:f00f:e::\n(v6)', 752570),
    ('23.227.38.74\n(Shopify/CF)', 751842),
]
ip_names = [d[0] for d in reversed(ip_data)]
ip_vals = [d[1] for d in reversed(ip_data)]
colors_ip = plt.cm.Reds(np.linspace(0.3, 0.9, len(ip_vals)))
bars8 = ax8.barh(range(len(ip_names)), ip_vals, color=colors_ip, edgecolor='#30363D', height=0.7)
ax8.set_yticks(range(len(ip_names)))
ax8.set_yticklabels(ip_names, fontsize=7, color='#C9D1D9', family='monospace')
ax8.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x/1e6:.1f}M'))
for bar, val in zip(bars8, ip_vals):
    ax8.text(bar.get_width() + 20000, bar.get_y() + bar.get_height()/2,
            f'{val:,}', va='center', fontsize=7, color='#C9D1D9')

# ============ Row 3, Col 2: Dependency Graph ============
ax9 = fig.add_subplot(gs[3, 2])
style_ax(ax9, 'Step 11: Network Dependency\n(who depends on Cloudflare)')
dep_metrics = ['Dependent\nASes', 'Dependent\nPrefixes', 'Hosted\nHostNames', 'Managed\nDomains']
dep_vals = [961, 11568, 3686326, 2084776]
colors_dep = ['#4ECDC4', '#45B7D1', '#FF6B6B', '#FFEAA7']
bars9 = ax9.bar(range(len(dep_metrics)), dep_vals, color=colors_dep, edgecolor='#30363D', width=0.6)
ax9.set_xticks(range(len(dep_metrics)))
ax9.set_xticklabels(dep_metrics, fontsize=9, color='#C9D1D9')
ax9.set_yscale('log')
ax9.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K' if x >= 1e3 else str(int(x))))
for bar, val in zip(bars9, dep_vals):
    label = f'{val/1e6:.1f}M' if val > 1e6 else f'{val:,}'
    ax9.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 1.3,
            label, ha='center', fontsize=9, color='#E6EDF3', fontweight='bold')

# ============ Row 4, Col 0: Censorship Footprint ============
ax10 = fig.add_subplot(gs[4, 0])
style_ax(ax10, 'Step 18: OONI Censorship Detections\n(in Cloudflare AS13335)')
censor = [
    ('Facebook Msg', 17), ('WhatsApp', 17), ('Telegram', 17),
    ('Psiphon', 17), ('Signal', 17), ('HTTP Invalid', 17),
    ('HTTP Header', 16), ('Vanilla Tor', 14), ('Tor Snowflake', 6),
]
c_names = [c[0] for c in reversed(censor)]
c_vals = [c[1] for c in reversed(censor)]
c_colors = plt.cm.RdYlBu(np.linspace(0.1, 0.9, len(c_vals)))
ax10.barh(range(len(c_names)), c_vals, color=c_colors, edgecolor='#30363D', height=0.7)
ax10.set_yticks(range(len(c_names)))
ax10.set_yticklabels(c_names, fontsize=9, color='#C9D1D9')
ax10.set_xlabel('Detections', color='#8B949E', fontsize=9)
ax10.text(10, -1.2, 'Also: 22 censored IPs, 17 censored URLs',
         fontsize=9, color='#8B949E', ha='center')

# ============ Row 4, Col 1: Tags/Classification ============
ax11 = fig.add_subplot(gs[4, 1])
style_ax(ax11, 'Step 2: AS Classification Tags\n(16 tags from multiple sources)')
tags = [
    'Content Delivery Network', 'DDoS Mitigation', 'Anycast',
    'Internet Critical Infra', 'Hosting & Cloud', 'ISP',
    'VPN Host', 'RPKI Validating', 'Tranco 10k Host',
    'Content', 'Software Dev', 'Service',
    'Gov & Public Admin', 'Military/Defense', 'IT',
    'Law & Business',
]
tag_cats = {
    'Core CDN': ['Content Delivery Network', 'DDoS Mitigation', 'Anycast', 'Content'],
    'Infrastructure': ['Internet Critical Infra', 'Hosting & Cloud', 'ISP', 'VPN Host'],
    'Compliance': ['RPKI Validating', 'Tranco 10k Host'],
    'Industry': ['Software Dev', 'Service', 'Gov & Public Admin', 'Military/Defense', 'IT', 'Law & Business'],
}
y = 0
cat_colors = {'Core CDN': '#FF6B6B', 'Infrastructure': '#45B7D1',
              'Compliance': '#2A9D8F', 'Industry': '#FFEAA7'}
for cat, tag_list in tag_cats.items():
    color = cat_colors[cat]
    ax11.text(0.02, 0.95 - y * 0.055, f'\u25cf {cat}:', fontsize=10,
             color=color, fontweight='bold', transform=ax11.transAxes)
    y += 1
    for tag in tag_list:
        ax11.text(0.06, 0.95 - y * 0.055, f'  {tag}', fontsize=9,
                 color='#C9D1D9', transform=ax11.transAxes)
        y += 1
    y += 0.3
ax11.axis('off')

# ============ Row 4, Col 2: RPKI/Security ============
ax12 = fig.add_subplot(gs[4, 2])
style_ax(ax12, 'Steps 5-6: Security Posture\n(RPKI & Anycast)')
sec_data = {
    'Total Prefixes': 11251,
    'RPKI ROA': 4703,
    'Anycast': 822,
    'ROA Coverage': 41.8,
    'Anycast Rate': 7.3,
}
bar_names = ['Total\nPrefixes', 'RPKI\nROA', 'Anycast\nPrefixes']
bar_vals = [11251, 4703, 822]
bar_colors = ['#30363D', '#2A9D8F', '#FF6B6B']
bars12 = ax12.bar(range(3), bar_vals, color=bar_colors, edgecolor='#30363D', width=0.6)
ax12.set_xticks(range(3))
ax12.set_xticklabels(bar_names, fontsize=9, color='#C9D1D9')
for bar, val in zip(bars12, bar_vals):
    ax12.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 100,
             f'{val:,}', ha='center', fontsize=10, color='#E6EDF3', fontweight='bold')
ax12.text(1, 8000, f'ROA Coverage: {4703/11251*100:.1f}%', ha='center',
         fontsize=11, color='#2A9D8F', fontweight='bold')
ax12.text(2, 5000, f'Anycast Rate: {822/11251*100:.1f}%', ha='center',
         fontsize=11, color='#FF6B6B', fontweight='bold')

# ============ Row 5: Summary Metrics (spanning full width) ============
ax_summary = fig.add_subplot(gs[5, :])
ax_summary.set_facecolor('#161B22')
ax_summary.axis('off')

summary = """
\u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 COMPREHENSIVE FINDINGS \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510
\u2502                                                                                                                                                                  \u2502
\u2502  \u2588 BGP/Routing:  11,251 prefixes (56% IPv6) \u2502 822 Anycast \u2502 4,703 RPKI ROA (41.8% coverage) \u2502 Peers with ALL 13 Tier-1 networks                       \u2502
\u2502  \u2588 Physical:     222 facilities \u2502 350 IXPs \u2502 76 countries \u2502 56 facility countries \u2502 Top: Equinix FR5 Frankfurt (33 IXPs co-located)                \u2502
\u2502  \u2588 DNS/Hosting:  2.08M domains on CF DNS \u2502 3.69M hosted hostnames \u2502 120K CNAME aliases \u2502 6,977 rDNS prefixes via CF nameservers                      \u2502
\u2502  \u2588 Dependency:   961 ASes depend on CF \u2502 11,568 prefixes depend on CF \u2502 Top 2 IPs each host 1.92M domains                                             \u2502
\u2502  \u2588 AS Family:    7 sibling ASes \u2502 AS209242 Spectrum (680 pfx) \u2502 AS14789 secondary (534 pfx) \u2502 AS400095 Area1 Security (acquisition)                   \u2502
\u2502  \u2588 Security:     RPKI ROV Validating \u2502 DDoS Mitigation \u2502 Internet Critical Infrastructure \u2502 16 classification tags                                   \u2502
\u2502  \u2588 Censorship:   17 OONI test detections \u2502 22 censored IPs \u2502 17 censored URLs (likely customer sites behind CF)                                            \u2502
\u2502  \u2588 Measurement:  31 RIPE Atlas probes in CF network \u2502 742 measurements targeting CF \u2502 Actively monitored by research community                         \u2502
\u2502                                                                                                                                                                  \u2502
\u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518
"""
ax_summary.text(0.5, 0.5, summary, fontsize=9, color='#E6EDF3',
               ha='center', va='center', family='monospace',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='#0D1117', edgecolor='#4ECDC4', linewidth=2))

# Super title
fig.suptitle('Cloudflare (AS13335) Full-Chain Analysis — All IYP Ontology Dimensions\n'
             '20+ Steps | 7 Sibling ASes | 11,251 Prefixes | 350 IXPs | 222 Facilities | 76 Countries | 3.69M HostNames | IYP 2026-04-08',
             fontsize=22, fontweight='bold', color='#E6EDF3', y=0.98)

plt.savefig('/home/wangmm/internet-yellow-pages/analysis/images/cloudflare_full_analysis.png',
            dpi=150, bbox_inches='tight', facecolor='#0D1117')
print('Saved: cloudflare_full_analysis.png')
