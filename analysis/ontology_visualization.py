"""IYP Ontology Map & Complex Network Visualizations."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
import matplotlib.patheffects as pe
import networkx as nx
import numpy as np
from matplotlib.patches import FancyArrowPatch

# ============================================================
# Figure 1: IYP Ontology Schema Map
# ============================================================

def draw_ontology_map():
    """Draw the complete IYP ontology schema as a graph."""
    fig, ax = plt.subplots(figsize=(28, 22))
    fig.patch.set_facecolor('#0D1117')
    ax.set_facecolor('#0D1117')

    G = nx.DiGraph()

    # Node definitions with categories
    # Category: dns, network, org, measurement, meta
    node_info = {
        'HostName':      {'cat': 'dns',    'count': '21.3M', 'size': 2800},
        'DomainName':    {'cat': 'dns',    'count': '11.2M', 'size': 2400},
        'IP':            {'cat': 'network','count': '8.0M',  'size': 2200},
        'Prefix':        {'cat': 'network','count': '6.3M',  'size': 2000},
        'BGPPrefix':     {'cat': 'network','count': '1.6M',  'size': 1600},
        'AS':            {'cat': 'network','count': '130K',  'size': 1800},
        'IXP':           {'cat': 'network','count': '1.3K',  'size': 1000},
        'Organization':  {'cat': 'org',    'count': '105K',  'size': 1400},
        'Facility':      {'cat': 'org',    'count': '5.9K',  'size': 900},
        'Country':       {'cat': 'meta',   'count': '254',   'size': 1200},
        'Name':          {'cat': 'meta',   'count': '323K',  'size': 800},
        'Tag':           {'cat': 'meta',   'count': '198',   'size': 800},
        'Ranking':       {'cat': 'meta',   'count': '967',   'size': 900},
        'Point':         {'cat': 'meta',   'count': '101K',  'size': 700},
        'OpaqueID':      {'cat': 'org',    'count': '128K',  'size': 800},
        'URL':           {'cat': 'dns',    'count': '67K',   'size': 700},
        'AtlasProbe':    {'cat': 'meas',   'count': '49K',   'size': 800},
        'AtlasMeasure.': {'cat': 'meas',   'count': '39K',   'size': 800},
        'BGPCollector':  {'cat': 'meas',   'count': '80',    'size': 600},
        'Estimate':      {'cat': 'meta',   'count': '1',     'size': 500},
    }

    cat_colors = {
        'dns':     '#45B7D1',
        'network': '#FF6B6B',
        'org':     '#4ECDC4',
        'meta':    '#8B949E',
        'meas':    '#FFEAA7',
    }

    for name, info in node_info.items():
        G.add_node(name, **info)

    # Key edges (top relationships by count, simplified)
    edges = [
        ('HostName', 'IP', 'RESOLVES_TO', 147.4),
        ('DomainName', 'HostName', 'MANAGED_BY', 50.0),
        ('IP', 'Prefix', 'PART_OF', 34.9),
        ('HostName', 'Ranking', 'RANK', 26.4),
        ('HostName', 'DomainName', 'PART_OF', 23.9),
        ('Prefix', 'Prefix', 'PART_OF', 21.5),
        ('AtlasProbe', 'AtlasMeasure.', 'PART_OF', 20.1),
        ('DomainName', 'DomainName', 'PARENT', 11.0),
        ('AS', 'AS', 'SIBLING_OF', 10.5),
        ('HostName', 'HostName', 'ALIAS_OF', 9.1),
        ('IP', 'BGPPrefix', 'PART_OF', 8.0),
        ('BGPPrefix', 'Prefix', 'PART_OF', 6.9),
        ('BGPPrefix', 'AS', 'DEPENDS_ON', 5.9),
        ('Prefix', 'Country', 'COUNTRY', 5.2),
        ('Prefix', 'HostName', 'MANAGED_BY', 3.5),
        ('AS', 'BGPPrefix', 'ORIGINATE', 2.9),
        ('BGPPrefix', 'Tag', 'CATEGORIZED', 2.7),
        ('AS', 'AS', 'PEERS_WITH', 1.9),
        ('BGPPrefix', 'Country', 'COUNTRY', 1.3),
        ('DomainName', 'Ranking', 'RANK', 1.3),
        ('Prefix', 'Point', 'LOCATED_IN', 1.0),
        ('AS', 'Prefix', 'ROA', 0.8),
        ('AS', 'AS', 'DEPENDS_ON', 0.7),
        ('AS', 'Country', 'COUNTRY', 0.4),
        ('AS', 'Tag', 'CATEGORIZED', 0.4),
        ('AS', 'Name', 'NAME', 0.4),
        ('AS', 'Organization', 'MANAGED_BY', 0.1),
        ('AS', 'IXP', 'MEMBER_OF', 0.1),
        ('Organization', 'Name', 'NAME', 0.1),
        ('Organization', 'Country', 'COUNTRY', 0.1),
        ('Facility', 'Organization', 'MANAGED_BY', 0.01),
        ('IXP', 'Facility', 'LOCATED_IN', 0.01),
        ('IXP', 'Country', 'COUNTRY', 0.01),
        ('IXP', 'Organization', 'MANAGED_BY', 0.01),
        ('AS', 'OpaqueID', 'ASSIGNED', 0.1),
        ('Prefix', 'OpaqueID', 'ASSIGNED', 0.3),
        ('URL', 'HostName', 'PART_OF', 0.03),
        ('URL', 'Tag', 'CATEGORIZED', 0.03),
        ('AS', 'URL', 'WEBSITE', 0.05),
        ('AtlasProbe', 'AS', 'LOCATED_IN', 0.05),
        ('AtlasProbe', 'Country', 'COUNTRY', 0.04),
        ('AS', 'BGPCollector', 'PEERS_WITH', 0.003),
        ('Country', 'Estimate', 'POPULATION', 0.0002),
        ('AS', 'IP', 'CENSORED', 0.05),
        ('AS', 'Tag', 'CENSORED', 0.02),
    ]

    for src, dst, rel, weight in edges:
        G.add_edge(src, dst, label=rel, weight=weight)

    # Manual layout for clarity
    pos = {
        # DNS layer (top)
        'URL':           (-5, 8),
        'HostName':      (0, 9),
        'DomainName':    (5, 8),
        'Ranking':       (10, 9),
        # Network layer (middle)
        'IP':            (-3, 5),
        'Prefix':        (3, 5),
        'BGPPrefix':     (0, 3),
        'AS':            (-5, 1),
        'IXP':           (5, 1),
        'BGPCollector':  (-9, 3),
        # Org layer (right)
        'Organization':  (9, 3),
        'Facility':      (10, 0),
        'OpaqueID':      (6, -2),
        # Meta layer (bottom)
        'Country':       (0, -2),
        'Name':          (-8, -1),
        'Tag':           (3, -1),
        'Point':         (7, -3),
        'Estimate':      (-2, -4),
        # Measurement layer
        'AtlasProbe':    (-8, 5),
        'AtlasMeasure.': (-10, 7),
    }

    # Draw edges with varying thickness
    for src, dst, data in G.edges(data=True):
        w = data['weight']
        if w > 10:
            width, alpha = 3.0, 0.5
        elif w > 1:
            width, alpha = 1.5, 0.35
        else:
            width, alpha = 0.6, 0.2

        # Self-loops need special handling
        if src == dst:
            x, y = pos[src]
            circle = plt.Circle((x, y + 0.8), 0.6, fill=False,
                               edgecolor='#58A6FF', linewidth=width, alpha=alpha,
                               linestyle='--')
            ax.add_patch(circle)
            ax.annotate(data['label'], (x, y + 1.5),
                       fontsize=5, color='#58A6FF', alpha=0.7,
                       ha='center', fontweight='bold')
        else:
            x1, y1 = pos[src]
            x2, y2 = pos[dst]
            ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                       arrowprops=dict(arrowstyle='->', color='#58A6FF',
                                      lw=width, alpha=alpha,
                                      connectionstyle='arc3,rad=0.1'))
            # Edge label
            mx, my = (x1+x2)/2, (y1+y2)/2
            # Offset label slightly
            dx, dy = x2-x1, y2-y1
            length = max(np.sqrt(dx*dx + dy*dy), 0.01)
            ox, oy = -dy/length*0.3, dx/length*0.3
            if w > 0.5:
                ax.text(mx+ox, my+oy, f'{data["label"]}\n{w:.1f}M',
                       fontsize=5, color='#58A6FF', alpha=0.6,
                       ha='center', va='center',
                       fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.1', facecolor='#0D1117',
                                edgecolor='none', alpha=0.8))

    # Draw nodes
    for name, info in node_info.items():
        x, y = pos[name]
        color = cat_colors[info['cat']]
        size = info['size']
        circle = plt.Circle((x, y), size/1000, color=color, alpha=0.9,
                            ec='#F0F6FC', linewidth=1.5)
        ax.add_patch(circle)
        ax.text(x, y + 0.1, name, fontsize=8, ha='center', va='center',
               color='#0D1117', fontweight='bold',
               path_effects=[pe.withStroke(linewidth=0, foreground='white')])
        ax.text(x, y - 0.25, info['count'], fontsize=6, ha='center', va='center',
               color='#0D1117', fontstyle='italic')

    # Layer labels
    layers = [
        ('DNS Layer', -6, 9.5, '#45B7D1'),
        ('Network Layer', -6, 3.5, '#FF6B6B'),
        ('Organization Layer', 11, 2, '#4ECDC4'),
        ('Metadata', -2, -3.5, '#8B949E'),
        ('Measurement', -11, 6, '#FFEAA7'),
    ]
    for label, x, y, color in layers:
        ax.text(x, y, label, fontsize=13, color=color, fontweight='bold',
               alpha=0.6, fontstyle='italic')

    # Legend
    legend_items = [
        mpatches.Patch(color='#45B7D1', label='DNS (HostName, DomainName, URL)'),
        mpatches.Patch(color='#FF6B6B', label='Network (AS, IP, Prefix, BGPPrefix, IXP)'),
        mpatches.Patch(color='#4ECDC4', label='Organization (Organization, Facility, OpaqueID)'),
        mpatches.Patch(color='#8B949E', label='Metadata (Country, Tag, Name, Ranking, Point)'),
        mpatches.Patch(color='#FFEAA7', label='Measurement (AtlasProbe, AtlasMeasurement)'),
    ]
    ax.legend(handles=legend_items, loc='lower left', fontsize=11,
             facecolor='#161B22', edgecolor='#30363D', labelcolor='#C9D1D9',
             framealpha=0.95)

    ax.set_xlim(-12, 13)
    ax.set_ylim(-5, 11)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('IYP Ontology Schema Map\n33 Node Types, 26 Relationship Types | 49.4M Nodes, 408M Edges',
                fontsize=20, fontweight='bold', color='#E6EDF3', pad=20)

    plt.tight_layout()
    plt.savefig('/home/wangmm/internet-yellow-pages/analysis/images/ontology_map.png',
                dpi=180, bbox_inches='tight', facecolor='#0D1117')
    print('Saved: ontology_map.png')
    plt.close()


# ============================================================
# Figure 2: Multi-layer Domain Resolution Chain
# ============================================================
def draw_domain_resolution_chain():
    """Visualize the full resolution chain: Domain -> HostName -> IP -> Prefix -> AS -> Org -> Country"""
    fig, ax = plt.subplots(figsize=(26, 18))
    fig.patch.set_facecolor('#0D1117')
    ax.set_facecolor('#0D1117')

    # Layers (bottom to top)
    layers = {
        'Country':  {'y': 0, 'color': '#2A9D8F', 'items': [
            ('US', 'United States'), ('JP', 'Japan'), ('DE', 'Germany'), ('SG', 'Singapore'),
        ]},
        'Organization': {'y': 2, 'color': '#4ECDC4', 'items': [
            ('Google LLC', None), ('Cloudflare Inc.', None), ('Amazon.com', None), ('IIJ', None),
        ]},
        'AS': {'y': 4, 'color': '#FF6B6B', 'items': [
            ('AS15169\nGoogle', None), ('AS13335\nCloudflare', None),
            ('AS16509\nAmazon', None), ('AS2497\nIIJ', None),
        ]},
        'BGPPrefix': {'y': 6, 'color': '#E63946', 'items': [
            ('142.251.0.0/15', None), ('188.114.96.0/20', None),
            ('13.32.0.0/15', None), ('210.130.0.0/16', None),
        ]},
        'IP': {'y': 8, 'color': '#457B9D', 'items': [
            ('142.251.154.119', None), ('188.114.97.0', None),
            ('13.32.100.42', None), ('210.130.137.80', None),
        ]},
        'HostName': {'y': 10, 'color': '#45B7D1', 'items': [
            ('www.google.com', None), ('www.cloudflare.com', None),
            ('aws.amazon.com', None), ('www.iij.ad.jp', None),
        ]},
        'DomainName': {'y': 12, 'color': '#96CEB4', 'items': [
            ('google.com', None), ('cloudflare.com', None),
            ('amazon.com', None), ('iij.ad.jp', None),
        ]},
    }

    # Draw layer bands
    for layer_name, info in layers.items():
        y = info['y']
        band = plt.Rectangle((-1, y - 0.7), 22, 1.4,
                             facecolor=info['color'], alpha=0.06,
                             edgecolor=info['color'], linewidth=0.5, linestyle='--')
        ax.add_patch(band)
        ax.text(-0.5, y, layer_name, fontsize=12, fontweight='bold',
               color=info['color'], ha='right', va='center', alpha=0.8)

    # Draw nodes at each layer
    node_positions = {}
    for layer_name, info in layers.items():
        y = info['y']
        items = info['items']
        n = len(items)
        for i, (label, _) in enumerate(items):
            x = 3 + i * 5
            node_positions[(layer_name, i)] = (x, y)
            circle = plt.Circle((x, y), 0.45, color=info['color'],
                               alpha=0.85, ec='#F0F6FC', linewidth=1.5)
            ax.add_patch(circle)
            ax.text(x, y, label, fontsize=6, ha='center', va='center',
                   color='#0D1117', fontweight='bold', family='monospace')

    # Draw connections (each column is one "trace")
    layer_order = ['DomainName', 'HostName', 'IP', 'BGPPrefix', 'AS', 'Organization', 'Country']
    rel_labels = ['MANAGED_BY/PART_OF', 'RESOLVES_TO', 'PART_OF', 'ORIGINATE', 'MANAGED_BY', 'COUNTRY']
    trace_colors = ['#45B7D1', '#4ECDC4', '#FF6B6B', '#FFEAA7']

    for col in range(4):
        color = trace_colors[col]
        for li in range(len(layer_order) - 1):
            src_layer = layer_order[li]
            dst_layer = layer_order[li + 1]
            x1, y1 = node_positions[(src_layer, col)]
            x2, y2 = node_positions[(dst_layer, col)]
            ax.annotate('', xy=(x2, y2 + 0.5), xytext=(x1, y1 - 0.5),
                       arrowprops=dict(arrowstyle='->', color=color,
                                      lw=2, alpha=0.5,
                                      connectionstyle='arc3,rad=0'))
            # Relationship label (only for first column)
            if col == 0:
                mx = x1 - 1.5
                my = (y1 + y2) / 2
                ax.text(mx, my, rel_labels[li], fontsize=7,
                       color='#8B949E', ha='right', va='center',
                       fontstyle='italic', rotation=0)

    # Title
    ax.set_xlim(-4, 22)
    ax.set_ylim(-1.5, 14)
    ax.axis('off')
    ax.set_title('IYP Ontology: Domain Resolution Chain\nDomainName → HostName → IP → BGPPrefix → AS → Organization → Country',
                fontsize=18, fontweight='bold', color='#E6EDF3', pad=20)

    # Stats annotation
    stats = (
        'Ontology Traversal Statistics:\n'
        '  DomainName → HostName:  49.9M MANAGED_BY edges\n'
        '  HostName → IP:         147.4M RESOLVES_TO edges\n'
        '  IP → BGPPrefix:          8.0M PART_OF edges\n'
        '  AS → BGPPrefix:          2.9M ORIGINATE edges\n'
        '  AS → Organization:     133K MANAGED_BY edges\n'
        '  Organization → Country: 112K COUNTRY edges'
    )
    ax.text(20, 1, stats, fontsize=9, color='#8B949E', ha='right', va='bottom',
           family='monospace',
           bbox=dict(boxstyle='round,pad=0.5', facecolor='#161B22',
                    edgecolor='#30363D', alpha=0.95))

    plt.tight_layout()
    plt.savefig('/home/wangmm/internet-yellow-pages/analysis/images/domain_resolution_chain.png',
                dpi=180, bbox_inches='tight', facecolor='#0D1117')
    print('Saved: domain_resolution_chain.png')
    plt.close()


# ============================================================
# Figure 3: Country-AS-IXP Infrastructure Map
# ============================================================
def draw_country_ixp_network():
    """Visualize the physical infrastructure layer: Country ← IXP → Facility ← AS → Organization"""
    fig, ax = plt.subplots(figsize=(24, 18))
    fig.patch.set_facecolor('#0D1117')
    ax.set_facecolor('#0D1117')

    G = nx.Graph()

    # IXP data per country
    ixp_data = [
        ('US', 212), ('ID', 77), ('DE', 58), ('BR', 53), ('RU', 43),
        ('IN', 40), ('AU', 36), ('NL', 36), ('GB', 30), ('CA', 28),
        ('JP', 26), ('UA', 25), ('FR', 25), ('SE', 24), ('IT', 21),
        ('CN', 21), ('HK', 18), ('PL', 17), ('ES', 16), ('CH', 15),
    ]

    # AS member counts for top IXPs (approximate from data)
    top_ixps = [
        ('DE-CIX\nFrankfurt', 'DE', 950),
        ('LINX\nLON1', 'GB', 880),
        ('AMS-IX', 'NL', 850),
        ('Equinix\nAshburn', 'US', 700),
        ('IX.br\nSao Paulo', 'BR', 600),
        ('JPNAP\nTokyo', 'JP', 400),
        ('MSK-IX', 'RU', 500),
        ('SGIX', 'SG', 300),
        ('HKIX', 'HK', 350),
        ('SIX\nSeattle', 'US', 400),
        ('Equinix\nSingapore', 'SG', 280),
        ('Netnod\nStockholm', 'SE', 250),
    ]

    # Layout: countries in outer ring, IXPs in middle
    n_countries = len(ixp_data)
    country_pos = {}
    for i, (cc, _) in enumerate(ixp_data):
        angle = 2 * np.pi * i / n_countries - np.pi / 2
        country_pos[cc] = (7 * np.cos(angle), 7 * np.sin(angle))
        G.add_node(cc, node_type='country', size=_ * 15 + 200)

    # Add IXP nodes near their country
    ixp_pos = {}
    for i, (name, cc, members) in enumerate(top_ixps):
        cx, cy = country_pos.get(cc, (0, 0))
        angle = 2 * np.pi * i / len(top_ixps) - np.pi / 2
        ixp_pos[name] = (3.5 * np.cos(angle), 3.5 * np.sin(angle))
        G.add_node(name, node_type='ixp', size=members)
        G.add_edge(cc, name, weight=members)

    # Cross-country IXP links (some IXPs connect ASes from multiple countries)
    cross_links = [
        ('DE-CIX\nFrankfurt', 'NL'), ('DE-CIX\nFrankfurt', 'GB'), ('DE-CIX\nFrankfurt', 'FR'),
        ('LINX\nLON1', 'DE'), ('LINX\nLON1', 'NL'), ('LINX\nLON1', 'FR'),
        ('AMS-IX', 'DE'), ('AMS-IX', 'GB'),
        ('Equinix\nAshburn', 'CA'), ('Equinix\nAshburn', 'BR'),
        ('IX.br\nSao Paulo', 'US'),
        ('SGIX', 'JP'), ('SGIX', 'AU'),
        ('HKIX', 'JP'), ('HKIX', 'CN'),
        ('Equinix\nSingapore', 'HK'), ('Equinix\nSingapore', 'JP'),
        ('MSK-IX', 'UA'),
    ]
    for ixp, cc in cross_links:
        if cc in country_pos and ixp in ixp_pos:
            G.add_edge(ixp, cc, weight=50)

    pos = {**country_pos, **ixp_pos}

    # Draw cross-country edges (thin, dotted)
    for ixp, cc in cross_links:
        if ixp in ixp_pos and cc in country_pos:
            x1, y1 = ixp_pos[ixp]
            x2, y2 = country_pos[cc]
            ax.plot([x1, x2], [y1, y2], color='#FFEAA7', linewidth=0.8,
                   alpha=0.25, linestyle='--', zorder=1)

    # Draw country-IXP edges (solid)
    for name, cc, members in top_ixps:
        if name in ixp_pos and cc in country_pos:
            x1, y1 = ixp_pos[name]
            x2, y2 = country_pos[cc]
            width = np.log10(members) * 0.8
            ax.plot([x1, x2], [y1, y2], color='#58A6FF', linewidth=width,
                   alpha=0.4, zorder=1)

    # Draw country nodes
    for cc, count in ixp_data:
        x, y = country_pos[cc]
        size = count * 2 + 100
        circle = plt.Circle((x, y), 0.45, color='#2A9D8F', alpha=0.85,
                            ec='#F0F6FC', linewidth=1.5, zorder=3)
        ax.add_patch(circle)
        ax.text(x, y + 0.08, cc, fontsize=10, ha='center', va='center',
               color='#0D1117', fontweight='bold', zorder=4)
        ax.text(x, y - 0.18, f'{count} IXPs', fontsize=6, ha='center', va='center',
               color='#0D1117', zorder=4)

    # Draw IXP nodes
    for name, cc, members in top_ixps:
        x, y = ixp_pos[name]
        radius = 0.25 + np.log10(members) * 0.12
        circle = plt.Circle((x, y), radius, color='#FF6B6B', alpha=0.85,
                            ec='#F0F6FC', linewidth=1.2, zorder=3)
        ax.add_patch(circle)
        ax.text(x, y + 0.05, name, fontsize=6, ha='center', va='center',
               color='#F0F6FC', fontweight='bold', zorder=4, family='monospace')
        ax.text(x, y - 0.25, f'{members} ASes', fontsize=5, ha='center',
               color='#FFEAA7', zorder=4)

    # Center stats
    center_text = (
        'IYP Physical Infrastructure\n'
        '━━━━━━━━━━━━━━━━━━━\n'
        f'1,302 IXPs\n'
        f'5,858 Facilities\n'
        f'125,284 AS memberships\n'
        f'254 Countries'
    )
    ax.text(0, 0, center_text, fontsize=11, ha='center', va='center',
           color='#E6EDF3', fontweight='bold', family='monospace',
           bbox=dict(boxstyle='round,pad=0.8', facecolor='#161B22',
                    edgecolor='#30363D', alpha=0.95), zorder=5)

    # Legend
    legend_items = [
        mpatches.Patch(color='#2A9D8F', label='Country (sized by IXP count)'),
        mpatches.Patch(color='#FF6B6B', label='Internet Exchange Point'),
        plt.Line2D([0], [0], color='#58A6FF', linewidth=2, label='Primary Country link'),
        plt.Line2D([0], [0], color='#FFEAA7', linewidth=1, linestyle='--',
                   label='Cross-border peering'),
    ]
    ax.legend(handles=legend_items, loc='upper left', fontsize=11,
             facecolor='#161B22', edgecolor='#30363D', labelcolor='#C9D1D9')

    ax.set_xlim(-9.5, 9.5)
    ax.set_ylim(-9.5, 9.5)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('IYP Ontology: Global IXP Infrastructure Map\nCountry ← IXP → AS membership | Cross-border peering paths',
                fontsize=18, fontweight='bold', color='#E6EDF3', pad=20)

    plt.tight_layout()
    plt.savefig('/home/wangmm/internet-yellow-pages/analysis/images/country_ixp_network.png',
                dpi=180, bbox_inches='tight', facecolor='#0D1117')
    print('Saved: country_ixp_network.png')
    plt.close()


# ============================================================
# Figure 4: AS Dependency + Censorship Composite
# ============================================================
def draw_as_dependency_censorship():
    """China AS dependency tree + global censorship landscape."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(28, 14))
    fig.patch.set_facecolor('#0D1117')

    # --- Left: China AS Dependency ---
    ax1.set_facecolor('#161B22')
    ax1.set_title('China AS Dependency Hierarchy\n(DEPENDS_ON relationship from CN-registered ASes)',
                 fontsize=14, fontweight='bold', color='#E6EDF3', pad=15)

    dep_data = [
        (6939, 'Hurricane Electric', 5041, 'US'),
        (23911, 'CNGI-BJIX', 4216, 'CN'),
        (38255, 'CERNET/FITI', 4179, 'CN'),
        (3356, 'Level 3 / Lumen', 607, 'US'),
        (1299, 'Arelion', 522, 'SE'),
        (174, 'Cogent', 501, 'US'),
        (4134, 'ChinaNet Backbone', 474, 'CN'),
        (6762, 'Telecom Italia Sparkle', 405, 'IT'),
        (6453, 'Tata Communications', 234, 'US'),
        (2914, 'NTT', 220, 'JP'),
        (4837, 'China Unicom 169', 147, 'CN'),
        (3491, 'PCCW Global', 114, 'HK'),
        (3257, 'GTT', 113, 'DE'),
        (20473, 'Vultr', 112, 'US'),
        (23764, 'CTGNet', 110, 'CN'),
    ]

    names_d = [f'AS{d[0]} {d[1]}' for d in reversed(dep_data)]
    vals_d = [d[2] for d in reversed(dep_data)]
    countries = [d[3] for d in reversed(dep_data)]

    country_colors = {'CN': '#E63946', 'US': '#457B9D', 'SE': '#96CEB4',
                      'IT': '#FFEAA7', 'JP': '#DDA0DD', 'HK': '#FF6B6B', 'DE': '#4ECDC4'}
    bar_colors = [country_colors.get(c, '#6C757D') for c in countries]

    bars = ax1.barh(range(len(names_d)), vals_d, color=bar_colors, edgecolor='#30363D', height=0.7)
    ax1.set_yticks(range(len(names_d)))
    ax1.set_yticklabels(names_d, fontsize=9, color='#C9D1D9', family='monospace')
    ax1.set_xlabel('Number of CN ASes depending on this AS', color='#8B949E', fontsize=11)
    ax1.tick_params(colors='#8B949E')
    for spine in ax1.spines.values():
        spine.set_color('#30363D')

    for bar, val in zip(bars, vals_d):
        ax1.text(bar.get_width() + 30, bar.get_y() + bar.get_height()/2,
                f'{val:,}', va='center', fontsize=9, color='#C9D1D9')

    # Country legend for left chart
    for cc, color in [('CN', '#E63946'), ('US', '#457B9D'), ('SE', '#96CEB4'),
                      ('JP', '#DDA0DD'), ('HK', '#FF6B6B'), ('DE', '#4ECDC4'), ('IT', '#FFEAA7')]:
        pass
    dep_legend = [mpatches.Patch(color=c, label=cc) for cc, c in
                  [('CN', '#E63946'), ('US', '#457B9D'), ('Others', '#96CEB4')]]
    ax1.legend(handles=dep_legend, loc='lower right', fontsize=10,
              facecolor='#161B22', edgecolor='#30363D', labelcolor='#C9D1D9')

    # --- Right: Censorship Landscape ---
    ax2.set_facecolor('#161B22')
    ax2.set_title('OONI Censorship Detection by Country\n(ASes flagged with CENSORED relationship)',
                 fontsize=14, fontweight='bold', color='#E6EDF3', pad=15)

    censor_data = [
        ('RU', 534), ('US', 254), ('BR', 161), ('GB', 107), ('DE', 76),
        ('UA', 63), ('NL', 50), ('IN', 50), ('CA', 38), ('AU', 37),
        ('FR', 36), ('ES', 35), ('HK', 33), ('IT', 29), ('ID', 27),
        ('KZ', 27), ('BD', 27), ('AT', 27), ('PL', 25), ('TR', 25),
    ]

    censor_tests = [
        ('Facebook Messenger', 2171),
        ('HTTP Invalid Request', 2164),
        ('Signal', 2097),
        ('HTTP Header Manip.', 2070),
        ('WhatsApp', 2032),
        ('Telegram', 2004),
        ('Psiphon', 1932),
        ('Vanilla Tor', 949),
        ('Tor Snowflake', 357),
        ('RiseupVPN', 17),
    ]

    # Stacked-style: countries as bars, colored by magnitude
    names_c = [d[0] for d in reversed(censor_data)]
    vals_c = [d[1] for d in reversed(censor_data)]

    # Color gradient based on value
    max_v = max(vals_c)
    bar_colors_c = [plt.cm.YlOrRd(0.3 + 0.6 * v / max_v) for v in vals_c]

    bars2 = ax2.barh(range(len(names_c)), vals_c, color=bar_colors_c,
                     edgecolor='#30363D', height=0.7)
    ax2.set_yticks(range(len(names_c)))
    ax2.set_yticklabels(names_c, fontsize=11, color='#C9D1D9', fontweight='bold')
    ax2.set_xlabel('Number of ASes with censorship detections', color='#8B949E', fontsize=11)
    ax2.tick_params(colors='#8B949E')
    for spine in ax2.spines.values():
        spine.set_color('#30363D')

    for bar, val in zip(bars2, vals_c):
        ax2.text(bar.get_width() + 3, bar.get_y() + bar.get_height()/2,
                str(val), va='center', fontsize=9, color='#C9D1D9')

    # Inset: test type breakdown
    ax_inset = ax2.inset_axes([0.45, 0.02, 0.53, 0.45])
    ax_inset.set_facecolor('#0D1117')
    test_names = [t[0] for t in reversed(censor_tests)]
    test_vals = [t[1] for t in reversed(censor_tests)]
    test_colors = plt.cm.RdYlBu(np.linspace(0.1, 0.9, len(test_vals)))
    ax_inset.barh(range(len(test_names)), test_vals, color=test_colors,
                  edgecolor='#30363D', height=0.7)
    ax_inset.set_yticks(range(len(test_names)))
    ax_inset.set_yticklabels(test_names, fontsize=7, color='#C9D1D9')
    ax_inset.set_title('OONI Tests (ASes flagged)', fontsize=9,
                       color='#E6EDF3', fontweight='bold')
    ax_inset.tick_params(colors='#8B949E', labelsize=7)
    for spine in ax_inset.spines.values():
        spine.set_color('#30363D')

    fig.suptitle('IYP Ontology: Geopolitical Network Analysis\nAS Dependencies & Internet Censorship Landscape | IYP 2026-04-08',
                fontsize=18, fontweight='bold', color='#E6EDF3', y=1.02)

    plt.tight_layout()
    plt.savefig('/home/wangmm/internet-yellow-pages/analysis/images/as_dependency_censorship.png',
                dpi=180, bbox_inches='tight', facecolor='#0D1117')
    print('Saved: as_dependency_censorship.png')
    plt.close()


# ============================================================
# Run all
# ============================================================
if __name__ == '__main__':
    draw_ontology_map()
    draw_domain_resolution_chain()
    draw_country_ixp_network()
    draw_as_dependency_censorship()
    print('All 4 figures generated.')
