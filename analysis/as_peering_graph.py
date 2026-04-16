"""Generate AS interconnection graph from IYP Neo4j database."""
import json
import subprocess
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
from collections import defaultdict

# Top 20 ASes by peering degree and their names
as_names = {
    6939: 'Hurricane Electric',
    174: 'Cogent',
    3356: 'Level 3 / Lumen',
    24482: 'SG.GS',
    49544: 'i3D.net',
    35280: 'F5 Networks',
    39120: 'Convergenze',
    36236: 'NetActuate',
    1299: 'Arelion (Telia)',
    32590: 'Valve Corp',
    199524: 'G-Core Labs',
    51185: 'MainStreaming',
    14537: 'Continent 8',
    6057: 'ANTEL (Uruguay)',
    14840: 'BR.Digital',
    25091: 'IP-Max',
    6461: 'Zayo',
    6424: 'EDGOO',
    137409: 'GSL Networks',
    9002: 'RETN',
}

# Query peering edges between top ASes
asns = list(as_names.keys())
asn_list = ','.join(str(a) for a in asns)

query = f"""
MATCH (a1:AS)-[:PEERS_WITH]->(a2:AS)
WHERE a1.asn IN [{asn_list}] AND a2.asn IN [{asn_list}]
RETURN DISTINCT a1.asn AS src, a2.asn AS dst
"""

result = subprocess.run(
    ['sg', 'docker', '-c',
     f'docker exec iyp cypher-shell -u neo4j -p password --format plain "{query}"'],
    capture_output=True, text=True, shell=False
)

# Parse edges
edges = set()
for line in result.stdout.strip().split('\n'):
    line = line.strip()
    if not line or 'src' in line:
        continue
    parts = line.split(',')
    if len(parts) == 2:
        try:
            src, dst = int(parts[0].strip()), int(parts[1].strip())
            if src in as_names and dst in as_names:
                edge = tuple(sorted([src, dst]))
                edges.add(edge)
        except ValueError:
            continue

print(f'Unique edges: {len(edges)}')

# Build graph
G = nx.Graph()
for asn in asns:
    G.add_node(asn)
for src, dst in edges:
    G.add_edge(src, dst)

# Classify ASes by type for coloring
tier1_transit = {6939, 174, 3356, 1299, 6461, 9002, 3257}  # Major transit providers
cdn_gaming = {32590, 199524, 35280, 51185, 49544, 14537, 36236, 137409}  # CDN/Gaming/Hosting
regional_isp = {24482, 39120, 6057, 14840, 25091, 6424}  # Regional/ISP

color_map = {}
for asn in asns:
    if asn in tier1_transit:
        color_map[asn] = '#E63946'  # Red - Tier 1/Transit
    elif asn in cdn_gaming:
        color_map[asn] = '#457B9D'  # Blue - CDN/Gaming/Hosting
    else:
        color_map[asn] = '#2A9D8F'  # Teal - Regional/ISP

node_colors = [color_map[n] for n in G.nodes()]

# Node size proportional to degree
degrees = dict(G.degree())
max_deg = max(degrees.values())
min_deg = min(degrees.values())
node_sizes = []
for n in G.nodes():
    normalized = (degrees[n] - min_deg) / (max_deg - min_deg + 1)
    node_sizes.append(800 + normalized * 2200)

# Layout
pos = nx.spring_layout(G, k=2.5, iterations=100, seed=42)

# Draw
fig, ax = plt.subplots(1, 1, figsize=(20, 16))
fig.patch.set_facecolor('#0D1117')
ax.set_facecolor('#0D1117')

# Draw edges
nx.draw_networkx_edges(G, pos, ax=ax,
                       edge_color='#30363D',
                       width=0.6, alpha=0.5)

# Draw nodes
nx.draw_networkx_nodes(G, pos, ax=ax,
                       node_color=node_colors,
                       node_size=node_sizes,
                       edgecolors='#C9D1D9',
                       linewidths=1.2,
                       alpha=0.92)

# Labels
labels = {}
for asn in G.nodes():
    name = as_names.get(asn, '')
    short = name.split('(')[0].strip() if '(' in name else name
    if len(short) > 16:
        short = short[:15] + '..'
    labels[asn] = f'AS{asn}\n{short}'

nx.draw_networkx_labels(G, pos, labels, ax=ax,
                        font_size=7,
                        font_color='#E6EDF3',
                        font_weight='bold',
                        font_family='monospace')

# Legend
legend_items = [
    mpatches.Patch(color='#E63946', label='Tier-1 / Transit Provider'),
    mpatches.Patch(color='#457B9D', label='CDN / Gaming / Hosting'),
    mpatches.Patch(color='#2A9D8F', label='Regional / ISP'),
]
legend = ax.legend(handles=legend_items, loc='upper left',
                   fontsize=11, facecolor='#161B22',
                   edgecolor='#30363D', labelcolor='#C9D1D9',
                   framealpha=0.9)

# Title and stats
title = f'AS Peering Interconnection Graph — Top 20 ASes by Degree'
subtitle = f'{len(G.nodes())} nodes, {len(G.edges())} unique edges | IYP 2026-04-08'
ax.set_title(f'{title}\n{subtitle}',
             fontsize=16, fontweight='bold',
             color='#E6EDF3', pad=20)

ax.axis('off')
plt.tight_layout()
plt.savefig('/home/wangmm/internet-yellow-pages/as_peering_top20.png',
            dpi=200, bbox_inches='tight',
            facecolor='#0D1117', edgecolor='none')
print('Saved: as_peering_top20.png')
