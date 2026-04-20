"""P13: Facility-level routing graph as bipartite DC↔AS pyvis network.

The full AS-Facility graph has ~60K edges — unreadable as-is. We keep
the "hub-hub" core: top-30 DCs (by AS count) × ASes that are present in
≥3 of those top-30 DCs. This is the set of operators that maintain a
multi-facility global footprint.

Outputs:
  analysis/new_angles/html/dc_routing_pyvis.html (+ countries mirror)
"""
import csv
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.china.common import (  # noqa: E402
    COLORS, country_color,
)

REPO = Path(__file__).resolve().parent.parent.parent
CACHE = REPO / 'data_cache' / 'new_angles'
OUT = REPO / 'analysis' / 'new_angles' / 'html'
LATEST = '2026-04-08'
TOP_N_DC = 30
MIN_FAC_PER_AS = 3


def _read(path):
    return list(csv.DictReader(open(path, encoding='utf-8')))


def build():
    from pyvis.network import Network

    facs = _read(CACHE / LATEST / 'facilities.csv')
    members = _read(CACHE / LATEST / 'facility_members.csv')
    pdb_nets = _read(CACHE / LATEST / 'peeringdb_nets.csv')

    # Top-N DCs by # AS members
    fac_as_count = Counter()
    fac_to_as = defaultdict(set)
    for r in members:
        fac = r['facility']
        asn = int(r['asn'])
        fac_as_count[fac] += 1
        fac_to_as[fac].add(asn)
    top_dcs = [f for f, _ in fac_as_count.most_common(TOP_N_DC)]
    top_dc_set = set(top_dcs)

    # For each AS, count how many top-DCs they're in
    as_fac_count = Counter()
    for r in members:
        if r['facility'] in top_dc_set:
            as_fac_count[int(r['asn'])] += 1
    # Keep AS present in >= MIN_FAC_PER_AS of top DCs
    core_ases = {a for a, n in as_fac_count.items() if n >= MIN_FAC_PER_AS}
    print(f'Top-{TOP_N_DC} DCs retain {len(core_ases):,} core-AS '
          f'(present in ≥{MIN_FAC_PER_AS} top DCs)', flush=True)

    # Lookup facility metadata
    fac_meta = {r['name']: r for r in facs}
    # Lookup AS info_type for color coding
    as_type = {int(r['asn']): r['info_type'] for r in pdb_nets}
    TYPE_COLOR = {
        'Content': COLORS['green'],
        'Cable/DSL/ISP': COLORS['orange'],
        'NSP': COLORS['blue'],
        'Enterprise': COLORS['purple'],
        'Educational/Research': COLORS['pink'],
        'Non-Profit': COLORS['cyan'],
        'Network Services': COLORS['teal'],
        'Route Server': COLORS['yellow'],
        'Route Collector': COLORS['amber'],
        '': COLORS['text2'] if 'text2' in COLORS else '#888',
    }

    # Build pyvis net
    net = Network(height='900px', width='100%', bgcolor='#0d0d17',
                  font_color='#f5f5f7', notebook=False,
                  cdn_resources='in_line')
    net.barnes_hut(gravity=-8000, central_gravity=0.15,
                   spring_length=200)

    # Add DC nodes
    for fac in top_dcs:
        m = fac_meta.get(fac, {})
        cc = m.get('cc', '??')
        n_as = fac_as_count[fac]
        n_ix = int(m.get('ix_count') or 0)
        size = 15 + (n_as ** 0.5)
        net.add_node(
            f'DC:{fac}',
            label=fac[:30],
            title=(f'{fac}<br>Operator: {m.get("operator","?")}<br>'
                   f'City: {m.get("city","?")}, {cc}<br>'
                   f'{n_as} AS presence · {n_ix} IXPs colocated'),
            color=country_color(cc),
            shape='box',
            size=size,
            group='dc',
        )
    # Add AS nodes
    for asn in core_ases:
        t = as_type.get(asn, '')
        net.add_node(
            f'AS:{asn}',
            label=f'AS{asn}',
            title=f'AS{asn} · {t or "unknown"} · '
                  f'present in {as_fac_count[asn]} top-DCs',
            color=TYPE_COLOR.get(t, TYPE_COLOR['']),
            shape='dot', size=8 + as_fac_count[asn] * 0.5,
            group='as',
        )
    # Edges
    for r in members:
        fac = r['facility']
        asn = int(r['asn'])
        if fac in top_dc_set and asn in core_ases:
            net.add_edge(f'AS:{asn}', f'DC:{fac}', width=0.5,
                         color='rgba(120,140,200,0.18)')

    print(f'Nodes: {len(net.nodes):,}, edges: {len(net.edges):,}',
          flush=True)

    # Save
    out_path = OUT / 'dc_routing_pyvis.html'
    net.save_graph(str(out_path))
    # Inject a header/summary block
    html = out_path.read_text(encoding='utf-8')
    type_legend = ' · '.join(
        f'<span style="color:{c}">■</span> {t or "—"}'
        for t, c in TYPE_COLOR.items() if t)
    header = f"""
<div style="background:#1a1a2e;border-left:4px solid {COLORS['cyan']};
            padding:16px 22px;color:#f5f5f7;font-family:-apple-system,
            'SF Pro Display',sans-serif">
<h1 style="margin:0 0 6px">Top-{TOP_N_DC} DC × Multi-DC AS · Facility-Level Routing Graph</h1>
<h2 style="margin:0 0 8px;font-size:14px;font-weight:400;color:#b0b0b8">
Bipartite: DCs (box, country-colored) ↔ ASes (dot, info_type-colored);
edge = AS present in DC.</h2>
<p style="margin:6px 0 0;font-size:13px;color:#b0b0b8">
<b>{len(top_dcs)}</b> top DCs ·
<b>{len(core_ases):,}</b> core ASes (in ≥{MIN_FAC_PER_AS} top DCs) ·
<b>{len(net.edges):,}</b> presence edges. AS color: {type_legend}</p>
</div>
"""
    html = html.replace('<body>', '<body>' + header)
    out_path.write_text(html, encoding='utf-8')

    mirror = REPO / 'analysis' / 'countries' / 'html' / 'dc_routing_pyvis.html'
    mirror.write_text(html, encoding='utf-8')
    print(f'wrote {out_path} ({out_path.stat().st_size // 1024} KB)')


if __name__ == '__main__':
    build()
