"""Step 10 (Neo4j path): extract the FULL global AS graph from IYP.

Unlike as_globe/step01 which only pulls what's needed for a 5K pool, this
emits EVERYTHING — typically ~100K ASes and ~700K undirected peering edges
— in a shape step11/12 can consume directly.

Output CSVs in data_cache/as_galaxy/:
 - nodes_raw.csv  (asn, cc, name, ipv4, prefix_count)   ~100K rows
 - edges_raw.csv  (src, dst)  src < dst, deduped        ~700K rows

Neo4j (bolt://localhost:7687) must be reachable. If not, use the BGPKit
fallback: `python -m analysis.as_galaxy.step10_galaxy_extract_bgpkit`.

Typical runtime on a laptop with the IYP snapshot: ~2–4 minutes, ~500 MB
peak RAM in Python (mostly the ORIGINATE cursor — prefix aggregation
streams row-by-row).
"""
from __future__ import annotations

import os
import sys
import time
from collections import defaultdict

from analysis.as_galaxy.common import (
    CACHE_DIR,
    ipv4_addresses_for_prefix,
    write_csv,
    write_step_metrics,
)
from analysis.complex_network.utils import run_query


# ---------------------------------------------------------------------------
# Neo4j extractors — one query each, each returning a plain dict keyed by ASN
# ---------------------------------------------------------------------------

def extract_ipv4_and_prefixes() -> dict[int, tuple[int, int]]:
    """Return {asn: (ipv4_total, prefix_count)} for every AS that ORIGINATEs ≥1 prefix.

    Sums addresses across all BGP prefixes the AS announces — deliberately
    NOT deduping overlapping prefixes (a /20 plus a /24 inside it represent
    two observed announcements worth counting). Upshot: an upper-bound on
    advertised address space, good enough for ranking.
    """
    rows = run_query('''
        MATCH (a:AS)-[:ORIGINATE]->(pfx:BGPPrefix)
        RETURN a.asn AS asn, pfx.prefix AS prefix
    ''')
    by_asn: dict[int, list[int]] = defaultdict(lambda: [0, 0])  # [ipv4_total, prefix_count]
    skipped = 0
    for r in rows:
        asn = r.get('asn')
        prefix = r.get('prefix')
        if asn is None or not prefix:
            skipped += 1
            continue
        addrs = ipv4_addresses_for_prefix(prefix)
        if addrs > 0:
            entry = by_asn[int(asn)]
            entry[0] += addrs
            entry[1] += 1
    if skipped:
        print(f'  [ipv4] skipped {skipped:,} rows (null asn/prefix or IPv6)')
    return {asn: (entry[0], entry[1]) for asn, entry in by_asn.items()}


def extract_country() -> dict[int, str]:
    """Return {asn: cc}. Picks the first non-empty cc seen per AS."""
    rows = run_query('''
        MATCH (a:AS)-[:COUNTRY]->(c:Country)
        RETURN a.asn AS asn, c.country_code AS cc
    ''')
    out: dict[int, str] = {}
    for r in rows:
        asn = r.get('asn')
        cc = (r.get('cc') or '').upper()
        if asn is None or not cc:
            continue
        out.setdefault(int(asn), cc)
    return out


def extract_name() -> dict[int, str]:
    """One human-readable name per AS, picking the most curated source.

    Priority matches as_globe/step01_extract.py::extract_as_name — curated
    lists beat bare RIR handles (ripe, arin etc.) which are often cryptic.
    """
    rows = run_query('''
        MATCH (a:AS)-[r:NAME]->(n:Name)
        RETURN a.asn AS asn, n.name AS name, r.reference_name AS src
    ''')
    priority = [
        'bgp.tools',
        'emileaben.github.io',
        'asnames',
        'peeringdb.org',
        'apnic.net',
        'ripe.net',
        'arin.net',
        'afrinic.net',
        'lacnic.net',
        'caida.org',
    ]
    def rank(src: str) -> int:
        src = (src or '').lower()
        for i, needle in enumerate(priority):
            if needle in src:
                return i
        return len(priority)

    best: dict[int, tuple[int, str]] = {}
    for r in rows:
        asn = r.get('asn')
        name = (r.get('name') or '').strip()
        if asn is None or not name:
            continue
        rk = rank(r.get('src') or '')
        prev = best.get(int(asn))
        if prev is None or rk < prev[0]:
            best[int(asn)] = (rk, name)
    return {asn: name for asn, (_, name) in best.items()}


def extract_edges() -> list[tuple[int, int]]:
    """Return sorted, deduped undirected edges (src < dst)."""
    rows = run_query('''
        MATCH (a:AS)-[:PEERS_WITH]-(b:AS) WHERE a.asn < b.asn
        RETURN DISTINCT a.asn AS src, b.asn AS dst
    ''')
    out: set[tuple[int, int]] = set()
    for r in rows:
        s, d = r.get('src'), r.get('dst')
        if s is None or d is None:
            continue
        s, d = int(s), int(d)
        if s == d:
            continue
        if s > d:
            s, d = d, s
        out.add((s, d))
    return sorted(out)


# ---------------------------------------------------------------------------
# Main — orchestrate the four queries and join results into two CSVs
# ---------------------------------------------------------------------------

def main() -> int:
    t0 = time.time()
    print(f'Extracting full global AS graph to {CACHE_DIR} ...')

    print('[1/4] AS → IPv4 + prefix count (ORIGINATE)')
    ipv4 = extract_ipv4_and_prefixes()
    print(f'  {len(ipv4):,} ASes with ≥1 originated prefix')

    print('[2/4] AS → country')
    cc_map = extract_country()
    print(f'  {len(cc_map):,} ASes with a country')

    print('[3/4] AS → name (curated > RIR)')
    name_map = extract_name()
    print(f'  {len(name_map):,} ASes with a name')

    print('[4/4] AS ↔ AS peering edges')
    edges = extract_edges()
    print(f'  {len(edges):,} unique undirected edges')

    # Union of every source we saw — some ASes may only appear as a peering
    # endpoint (no originated prefix, no curated name). Keep them all.
    all_asns: set[int] = set(ipv4)
    all_asns.update(cc_map)
    all_asns.update(name_map)
    for s, d in edges:
        all_asns.add(s)
        all_asns.add(d)
    print(f'  → union node set: {len(all_asns):,} ASes')

    rows = []
    for asn in sorted(all_asns):
        v, pc = ipv4.get(asn, (0, 0))
        rows.append({
            'asn': asn,
            'cc': cc_map.get(asn, ''),
            'name': name_map.get(asn, ''),
            'ipv4': v,
            'prefix_count': pc,
        })
    nodes_path = os.path.join(CACHE_DIR, 'nodes_raw.csv')
    write_csv(nodes_path, rows, ['asn', 'cc', 'name', 'ipv4', 'prefix_count'])
    print(f'  wrote {nodes_path} ({os.path.getsize(nodes_path)//1024:,} KB)')

    edges_path = os.path.join(CACHE_DIR, 'edges_raw.csv')
    write_csv(edges_path,
              [{'src': s, 'dst': d} for s, d in edges],
              ['src', 'dst'])
    print(f'  wrote {edges_path} ({os.path.getsize(edges_path)//1024:,} KB)')

    write_step_metrics(10, {
        'source': 'iyp neo4j',
        'as_with_ipv4': len(ipv4),
        'as_with_country': len(cc_map),
        'as_with_name': len(name_map),
        'peering_edges': len(edges),
        'total_nodes': len(all_asns),
        'cache_dir': CACHE_DIR,
        'elapsed_sec': round(time.time() - t0, 2),
    }, title_zh='Step 10 · 从 Neo4j 抽取全球 AS 图',
       title_en='Step 10 · Extract full global AS graph from Neo4j')

    print(f'\nStep 10 complete in {time.time() - t0:.1f}s → {CACHE_DIR}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
