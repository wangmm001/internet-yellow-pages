"""Step 1: Extract raw AS/peering/geo tables from IYP Neo4j.

Writes four CSVs to data_cache/as_globe/:
 - as_country.csv   (asn, cc)
 - as_ipv4.csv      (asn, ipv4_addresses, prefix_count)
 - as_peers.csv     (src, dst)  — undirected, deduped, src<dst
 - as_geo.csv       (asn, lat, lon)  — from CAIDA LOCATED_IN (partial coverage)

Neo4j (bolt://localhost:7687) must be reachable. On failure the step exits
non-zero; downstream steps degrade by reading whatever CSVs are already on disk.
"""
from __future__ import annotations

import os
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.as_globe.common import (  # noqa: E402
    CACHE_DIR, ipv4_addresses_for_prefix, write_csv, write_step_metrics,
)
from analysis.complex_network.utils import run_query  # noqa: E402


def _parse_wgs84_point(pos) -> tuple[float, float] | None:
    """Neo4j driver returns a neo4j.spatial.WGS84Point; tolerate tuples / strings too."""
    if pos is None:
        return None
    lon = lat = None
    if hasattr(pos, 'longitude') and hasattr(pos, 'latitude'):
        lon, lat = pos.longitude, pos.latitude
    elif isinstance(pos, (list, tuple)) and len(pos) >= 2:
        lon, lat = pos[0], pos[1]
    elif isinstance(pos, str):
        s = pos.strip('{}() ')
        parts = [p.strip() for p in s.split(',') if p.strip()]
        nums: list[float] = []
        for p in parts:
            _, _, rhs = p.partition(':')
            try:
                nums.append(float(rhs if rhs else p))
            except ValueError:
                pass
        if len(nums) >= 2:
            lon, lat = nums[0], nums[1]
    try:
        lon_f = float(lon)
        lat_f = float(lat)
    except (TypeError, ValueError):
        return None
    if not (-180.0 <= lon_f <= 180.0 and -90.0 <= lat_f <= 90.0):
        return None
    return lat_f, lon_f


def extract_as_country() -> list[dict]:
    rows = run_query('''
        MATCH (a:AS)-[:COUNTRY]->(c:Country)
        RETURN a.asn AS asn, c.country_code AS cc
    ''')
    # An AS can be linked to multiple countries across sources — keep one per AS.
    # Prefer the first non-empty cc encountered (Neo4j row order is arbitrary but stable per run).
    seen: dict[int, str] = {}
    for r in rows:
        asn = r.get('asn')
        cc = (r.get('cc') or '').upper()
        if asn is None or not cc:
            continue
        seen.setdefault(int(asn), cc)
    return [{'asn': asn, 'cc': cc} for asn, cc in sorted(seen.items())]


def extract_as_ipv4() -> list[dict]:
    """Sum IPv4 addresses across all BGP prefixes each AS originates.

    Deliberately does *not* collapse overlapping prefixes — IYP stores
    announcements as-observed, and a /20 plus a more-specific /24 inside it
    represent real announcements worth counting. Upshot: numbers are an upper
    bound on advertised address space, not a strict reachable set.
    """
    rows = run_query('''
        MATCH (a:AS)-[:ORIGINATE]->(pfx:BGPPrefix)
        RETURN a.asn AS asn, pfx.prefix AS prefix
    ''')
    by_asn: dict[int, list[int]] = defaultdict(list)
    skipped = 0
    for r in rows:
        asn = r.get('asn')
        prefix = r.get('prefix')
        if asn is None or not prefix:
            skipped += 1
            continue
        addrs = ipv4_addresses_for_prefix(prefix)
        if addrs > 0:
            by_asn[int(asn)].append(addrs)
    out = []
    for asn, addrs_list in by_asn.items():
        out.append({
            'asn': asn,
            'ipv4_addresses': sum(addrs_list),
            'prefix_count': len(addrs_list),
        })
    out.sort(key=lambda r: -r['ipv4_addresses'])
    if skipped:
        print(f'  [as_ipv4] skipped {skipped} rows (null asn/prefix or IPv6)')
    return out


def extract_as_peers() -> list[dict]:
    rows = run_query('''
        MATCH (a:AS)-[:PEERS_WITH]-(b:AS) WHERE a.asn < b.asn
        RETURN DISTINCT a.asn AS src, b.asn AS dst
    ''')
    return [{'src': int(r['src']), 'dst': int(r['dst'])} for r in rows
            if r.get('src') is not None and r.get('dst') is not None]


def extract_as_geo() -> list[dict]:
    rows = run_query('''
        MATCH (a:AS)-[:LOCATED_IN]->(p:Point)
        RETURN a.asn AS asn, p.position AS pos
    ''')
    out = []
    bad = 0
    for r in rows:
        asn = r.get('asn')
        parsed = _parse_wgs84_point(r.get('pos'))
        if asn is None or parsed is None:
            bad += 1
            continue
        lat, lon = parsed
        out.append({'asn': int(asn), 'lat': round(lat, 4), 'lon': round(lon, 4)})
    if bad:
        print(f'  [as_geo] skipped {bad} rows (unparseable position)')
    # dedupe by asn — keep first
    seen: dict[int, dict] = {}
    for row in out:
        seen.setdefault(row['asn'], row)
    return list(seen.values())


def main() -> int:
    t0 = time.time()

    print('Extracting AS→country...')
    as_country = extract_as_country()
    write_csv(os.path.join(CACHE_DIR, 'as_country.csv'), as_country, ['asn', 'cc'])
    print(f'  {len(as_country):,} ASes → as_country.csv')

    print('Extracting AS→IPv4 address count...')
    as_ipv4 = extract_as_ipv4()
    write_csv(os.path.join(CACHE_DIR, 'as_ipv4.csv'), as_ipv4,
              ['asn', 'ipv4_addresses', 'prefix_count'])
    print(f'  {len(as_ipv4):,} ASes → as_ipv4.csv')

    print('Extracting AS↔AS peering...')
    as_peers = extract_as_peers()
    write_csv(os.path.join(CACHE_DIR, 'as_peers.csv'), as_peers, ['src', 'dst'])
    print(f'  {len(as_peers):,} edges → as_peers.csv')

    print('Extracting AS geolocation (CAIDA)...')
    as_geo = extract_as_geo()
    write_csv(os.path.join(CACHE_DIR, 'as_geo.csv'), as_geo, ['asn', 'lat', 'lon'])
    print(f'  {len(as_geo):,} ASes with real lat/lon → as_geo.csv')

    write_step_metrics(1, {
        'as_with_country': len(as_country),
        'as_with_ipv4': len(as_ipv4),
        'peering_edges': len(as_peers),
        'as_with_geo': len(as_geo),
        'cache_dir': CACHE_DIR,
        'elapsed_sec': round(time.time() - t0, 2),
    }, title_zh='Step 01 · 从 Neo4j 抽取底表',
       title_en='Step 01 · Extract base tables from Neo4j')

    print(f'\nStep 1 complete in {time.time() - t0:.1f}s → {CACHE_DIR}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
