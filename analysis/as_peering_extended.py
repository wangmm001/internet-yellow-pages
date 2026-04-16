"""Generate extended AS interconnection graph with hub-spoke structure."""
import subprocess
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
import numpy as np

# Top 6 transit providers as hubs
hubs = {
    6939: 'Hurricane Electric',
    174: 'Cogent',
    3356: 'Level 3 / Lumen',
    1299: 'Arelion',
    6461: 'Zayo',
    9002: 'RETN',
}

hub_asns = ','.join(str(a) for a in hubs.keys())

# Query: for each hub, get their top peers (excluding other hubs) with peering count
query = f"""
MATCH (hub:AS)-[:PEERS_WITH]-(peer:AS)
WHERE hub.asn IN [{hub_asns}] AND NOT peer.asn IN [{hub_asns}]
WITH hub.asn AS hub_asn, peer.asn AS peer_asn, count(*) AS weight
ORDER BY hub_asn, weight DESC
WITH hub_asn, collect({{peer: peer_asn, w: weight}})[..15] AS top_peers
UNWIND top_peers AS tp
RETURN hub_asn, tp.peer AS peer_asn, tp.w AS weight
"""

result = subprocess.run(
    ['sg', 'docker', '-c',
     f'docker exec iyp cypher-shell -u neo4j -p password --format plain "{query}"'],
    capture_output=True, text=True
)

# Parse
peer_set = set()
edges = []
for line in result.stdout.strip().split('\n'):
    line = line.strip()
    if not line or 'hub_asn' in line:
        continue
    parts = line.split(',')
    if len(parts) == 3:
        try:
            h, p, w = int(parts[0].strip()), int(parts[1].strip()), int(parts[2].strip())
            edges.append((h, p, w))
            peer_set.add(p)
        except ValueError:
            continue

print(f'Hub-peer edges: {len(edges)}, unique peers: {len(peer_set)}')

# Get peer names
peer_list = ','.join(str(a) for a in peer_set)
name_query = f"""
MATCH (a:AS)-[:NAME]->(n:Name)
WHERE a.asn IN [{peer_list}]
WITH a.asn AS asn, collect(DISTINCT n.name) AS names
RETURN asn, names[0] AS name
"""
name_result = subprocess.run(
    ['sg', 'docker', '-c',
     f'docker exec iyp cypher-shell -u neo4j -p password --format plain "{name_query}"'],
    capture_output=True, text=True
)

peer_names = {}
for line in name_result.stdout.strip().split('\n'):
    line = line.strip()
    if not line or 'asn' in line:
        continue
    parts = line.split(',', 1)
    if len(parts) == 2:
        try:
            asn = int(parts[0].strip().strip('"'))
            name = parts[1].strip().strip('"')
            # Shorten name
            name = name.split(' - ')[0].split(',')[0].strip()
            if len(name) > 20:
                name = name[:18] + '..'
            peer_names[asn] = name
        except ValueError:
            continue

# Also query hub-to-hub edges
hub_query = f"""
MATCH (a1:AS)-[:PEERS_WITH]->(a2:AS)
WHERE a1.asn IN [{hub_asns}] AND a2.asn IN [{hub_asns}]
RETURN DISTINCT a1.asn AS src, a2.asn AS dst
"""
hub_result = subprocess.run(
    ['sg', 'docker', '-c',
     f'docker exec iyp cypher-shell -u neo4j -p password --format plain "{hub_query}"'],
    capture_output=True, text=True
)

hub_edges = set()
for line in hub_result.stdout.strip().split('\n'):
    line = line.strip()
    if not line or 'src' in line:
        continue
    parts = line.split(',')
    if len(parts) == 2:
        try:
            s, d = int(parts[0].strip()), int(parts[1].strip())
            hub_edges.add(tuple(sorted([s, d])))
        except ValueError:
            continue

# Build graph
G = nx.Graph()

# Add hub nodes
for asn, name in hubs.items():
    G.add_node(asn, label=f'AS{asn}\n{name}', node_type='hub')

# Add peer nodes
for asn in peer_set:
    name = peer_names.get(asn, str(asn))
    G.add_node(asn, label=f'AS{asn}\n{name}', node_type='peer')

# Add hub-hub edges
for s, d in hub_edges:
    if s in hubs and d in hubs:
        G.add_edge(s, d, weight=10, edge_type='hub-hub')

# Add hub-peer edges
for h, p, w in edges:
    G.add_edge(h, p, weight=w, edge_type='hub-peer')

# Count connections per peer to hubs
peer_hub_count = {}
for asn in peer_set:
    connected_hubs = [h for h in hubs if G.has_edge(asn, h)]
    peer_hub_count[asn] = len(connected_hubs)

# Layout: place hubs in a circle, peers around their primary hub
np.random.seed(42)
pos = {}
hub_list = list(hubs.keys())
n_hubs = len(hub_list)

# Hubs in inner circle
for i, asn in enumerate(hub_list):
    angle = 2 * np.pi * i / n_hubs - np.pi / 2
    pos[asn] = (2.0 * np.cos(angle), 2.0 * np.sin(angle))

# Assign each peer to its primary hub (highest weight edge)
peer_primary = {}
for asn in peer_set:
    best_hub = None
    best_w = 0
    for h, p, w in edges:
        if p == asn and w > best_w:
            best_w = w
            best_hub = h
    if best_hub:
        peer_primary[asn] = best_hub

# Place peers around their primary hub
hub_peer_groups = {}
for asn, hub in peer_primary.items():
    hub_peer_groups.setdefault(hub, []).append(asn)

for hub, peers in hub_peer_groups.items():
    hx, hy = pos[hub]
    hub_idx = hub_list.index(hub)
    base_angle = 2 * np.pi * hub_idx / n_hubs - np.pi / 2
    n_peers = len(peers)
    for i, asn in enumerate(peers):
        spread = np.pi * 0.8
        a = base_angle - spread / 2 + spread * (i + 0.5) / n_peers
        r = 4.0 + np.random.uniform(-0.5, 0.5)
        pos[asn] = (r * np.cos(a), r * np.sin(a))

# Draw
fig, ax = plt.subplots(figsize=(24, 20))
fig.patch.set_facecolor('#0D1117')
ax.set_facecolor('#0D1117')

# Separate edge types
hub_hub_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('edge_type') == 'hub-hub']
hub_peer_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('edge_type') == 'hub-peer']

# Draw hub-peer edges first (background)
# Color by which hub
hub_colors_map = {
    6939: '#FF6B6B',
    174: '#4ECDC4',
    3356: '#45B7D1',
    1299: '#96CEB4',
    6461: '#FFEAA7',
    9002: '#DDA0DD',
}

for u, v in hub_peer_edges:
    hub = u if u in hubs else v
    color = hub_colors_map.get(hub, '#30363D')
    nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], ax=ax,
                           edge_color=color, width=0.5, alpha=0.2)

# Draw hub-hub edges (prominent)
nx.draw_networkx_edges(G, pos, edgelist=hub_hub_edges, ax=ax,
                       edge_color='#F0F6FC', width=2.0, alpha=0.6,
                       style='solid')

# Draw peer nodes
peer_nodes = [n for n in G.nodes() if G.nodes[n].get('node_type') == 'peer']
peer_colors = []
for n in peer_nodes:
    nhubs = peer_hub_count.get(n, 0)
    if nhubs >= 5:
        peer_colors.append('#FFD700')  # Gold - multi-homed
    elif nhubs >= 3:
        peer_colors.append('#87CEEB')  # Light blue
    else:
        peer_colors.append('#6C757D')  # Gray

nx.draw_networkx_nodes(G, pos, nodelist=peer_nodes, ax=ax,
                       node_color=peer_colors, node_size=350,
                       edgecolors='#30363D', linewidths=0.8, alpha=0.85)

# Draw hub nodes (large)
hub_node_list = list(hubs.keys())
hub_node_colors = [hub_colors_map[h] for h in hub_node_list]
nx.draw_networkx_nodes(G, pos, nodelist=hub_node_list, ax=ax,
                       node_color=hub_node_colors, node_size=3000,
                       edgecolors='#F0F6FC', linewidths=2.5, alpha=0.95)

# Hub labels
hub_labels = {asn: f'AS{asn}\n{name}' for asn, name in hubs.items()}
nx.draw_networkx_labels(G, pos, hub_labels, ax=ax,
                        font_size=9, font_color='#0D1117',
                        font_weight='bold', font_family='monospace')

# Peer labels (only multi-homed ones)
peer_labels = {}
for n in peer_nodes:
    if peer_hub_count.get(n, 0) >= 4:
        name = peer_names.get(n, str(n))
        peer_labels[n] = f'AS{n}\n{name}'

nx.draw_networkx_labels(G, pos, peer_labels, ax=ax,
                        font_size=6, font_color='#E6EDF3',
                        font_family='monospace')

# Legend
legend_items = [
    mpatches.Patch(color='#FF6B6B', label=f'AS6939 Hurricane Electric ({G.degree(6939)} peers)'),
    mpatches.Patch(color='#4ECDC4', label=f'AS174 Cogent ({G.degree(174)} peers)'),
    mpatches.Patch(color='#45B7D1', label=f'AS3356 Level 3 / Lumen ({G.degree(3356)} peers)'),
    mpatches.Patch(color='#96CEB4', label=f'AS1299 Arelion ({G.degree(1299)} peers)'),
    mpatches.Patch(color='#FFEAA7', label=f'AS6461 Zayo ({G.degree(6461)} peers)'),
    mpatches.Patch(color='#DDA0DD', label=f'AS9002 RETN ({G.degree(9002)} peers)'),
    plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#FFD700',
               markersize=10, label='Multi-homed (5+ hubs)', linestyle='None'),
    plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#87CEEB',
               markersize=10, label='Multi-homed (3-4 hubs)', linestyle='None'),
    plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#6C757D',
               markersize=10, label='Single/Dual-homed', linestyle='None'),
]
legend = ax.legend(handles=legend_items, loc='upper left',
                   fontsize=11, facecolor='#161B22',
                   edgecolor='#30363D', labelcolor='#C9D1D9',
                   framealpha=0.95)

# Title
title = 'AS Interconnection Map — Top 6 Transit Providers & Their Top Peers'
subtitle = f'{len(G.nodes())} ASes, {len(G.edges())} peering links | IYP 2026-04-08 | ~1.89M total AS peering relationships'
ax.set_title(f'{title}\n{subtitle}',
             fontsize=18, fontweight='bold',
             color='#E6EDF3', pad=25)

ax.axis('off')
plt.tight_layout()
plt.savefig('/home/wangmm/internet-yellow-pages/as_interconnection_map.png',
            dpi=200, bbox_inches='tight',
            facecolor='#0D1117', edgecolor='none')
print('Saved: as_interconnection_map.png')
