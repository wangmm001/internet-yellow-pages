"""Step 2: Select a renderable pool of ~5,000 ASes from the cached extracts.

Strategy:
  - Rank ASes by IPv4 address count desc; take top 3,000 ("economic mass").
  - Add any AS peered with ≥2 of those top 3K, up to a strict 5,000 cap
    ("structural support").
  - Drop edges where either endpoint is not in the pool.
  - Compute per-node region bucket, color, radius, and geo (real or centroid+jitter).

Emits:
  data/nodes.json  — compact keys {a,c,k,r,x,y,g,v,d}
  data/links.json  — compact keys {s,t}
  data/step02_metrics.json
"""
from __future__ import annotations

import os
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.as_globe.common import (  # noqa: E402
    CACHE_DIR, COUNTRY_CENTROIDS, DATA_DIR, REGION_COLOR, REGION_ORDER,
    jitter_latlon, radius_px, read_csv, region_of, write_json, write_step_metrics,
)


TOP_BY_IPV4 = 3000
POOL_CAP = 5000
MIN_ANCHORS_FOR_ADMIT = 2  # must peer with ≥N of the top-IPv4 core to qualify
# Cap how many edges get emitted (sorted by combined endpoint radius). 60K
# lets the force view reach the full 5K-AS pool (top-30K edges only cover ~2700
# distinct endpoints — the rest need longer-tail edges to show up at all).
MAX_EMIT_LINKS = 60000


def _load() -> tuple[dict[int, str], dict[int, dict], list[tuple[int, int]], dict[int, tuple[float, float]]]:
    as_country = {int(r['asn']): r['cc'] for r in read_csv(os.path.join(CACHE_DIR, 'as_country.csv')) if r.get('cc')}

    as_ipv4: dict[int, dict] = {}
    for r in read_csv(os.path.join(CACHE_DIR, 'as_ipv4.csv')):
        try:
            asn = int(r['asn'])
            v4 = int(r['ipv4_addresses'])
            pc = int(r['prefix_count'])
        except (ValueError, KeyError):
            continue
        as_ipv4[asn] = {'ipv4': v4, 'prefix_count': pc}

    edges: list[tuple[int, int]] = []
    for r in read_csv(os.path.join(CACHE_DIR, 'as_peers.csv')):
        try:
            s, t = int(r['src']), int(r['dst'])
        except (ValueError, KeyError):
            continue
        if s == t:
            continue
        if s > t:
            s, t = t, s
        edges.append((s, t))

    as_geo: dict[int, tuple[float, float]] = {}
    for r in read_csv(os.path.join(CACHE_DIR, 'as_geo.csv')):
        try:
            as_geo[int(r['asn'])] = (float(r['lat']), float(r['lon']))
        except (ValueError, KeyError):
            continue

    return as_country, as_ipv4, edges, as_geo


def _select_pool(as_ipv4: dict[int, dict], edges: list[tuple[int, int]]) -> set[int]:
    by_ipv4 = sorted(as_ipv4.items(), key=lambda kv: -kv[1]['ipv4'])
    core = {asn for asn, _ in by_ipv4[:TOP_BY_IPV4]}

    if len(core) >= POOL_CAP:
        return set(list(core)[:POOL_CAP])

    # Count how many core ASes each non-core AS peers with.
    anchor_hits: dict[int, int] = defaultdict(int)
    for s, t in edges:
        if s in core and t not in core:
            anchor_hits[t] += 1
        elif t in core and s not in core:
            anchor_hits[s] += 1

    candidates = sorted(
        (asn for asn, hits in anchor_hits.items() if hits >= MIN_ANCHORS_FOR_ADMIT),
        key=lambda asn: (-anchor_hits[asn], -as_ipv4.get(asn, {}).get('ipv4', 0)),
    )

    pool = set(core)
    for asn in candidates:
        if len(pool) >= POOL_CAP:
            break
        pool.add(asn)
    return pool


def _resolve_geo(asn: int, cc: str, as_geo: dict[int, tuple[float, float]]) -> tuple[float, float, bool]:
    if asn in as_geo:
        lat, lon = as_geo[asn]
        return lat, lon, True
    centroid = COUNTRY_CENTROIDS.get(cc.upper())
    if centroid is not None:
        lat, lon = jitter_latlon(asn, centroid[0], centroid[1])
        return lat, lon, False
    # Truly unknown country — scatter near (0,0) with asn-keyed jitter.
    lat, lon = jitter_latlon(asn, 0.0, 0.0, radius_deg=30.0)
    return lat, lon, False


def main() -> int:
    t0 = time.time()

    as_country, as_ipv4, edges, as_geo = _load()
    if not as_ipv4:
        print(f'[FATAL] no IPv4 data in {CACHE_DIR}; run step01 first.', file=sys.stderr)
        return 1

    print(f'Loaded: {len(as_country):,} AS-country, {len(as_ipv4):,} AS-IPv4, '
          f'{len(edges):,} edges, {len(as_geo):,} AS-geo')

    pool = _select_pool(as_ipv4, edges)
    print(f'Pool selected: {len(pool):,} ASes '
          f'(top-{TOP_BY_IPV4} by IPv4 + neighbor closure to ≤{POOL_CAP})')

    # Edge subset — strictly within the pool.
    pool_edges = [(s, t) for (s, t) in edges if s in pool and t in pool]
    # Dedupe in case input had duplicates across sources.
    pool_edges = sorted(set(pool_edges))
    print(f'Pool edges: {len(pool_edges):,}')

    # Degree within the pool, for tooltip + size blending.
    degree: dict[int, int] = defaultdict(int)
    for s, t in pool_edges:
        degree[s] += 1
        degree[t] += 1

    # Build nodes.
    nodes_out = []
    region_hist: dict[str, int] = defaultdict(int)
    real_geo_n = 0
    for asn in sorted(pool):
        cc = as_country.get(asn, '') or ''
        bucket = region_of(cc)
        ipv4 = as_ipv4.get(asn, {}).get('ipv4', 0)
        lat, lon, has_geo = _resolve_geo(asn, cc, as_geo)
        if has_geo:
            real_geo_n += 1
        nodes_out.append({
            'a': asn,
            'c': cc,
            'k': bucket,
            'r': round(radius_px(ipv4), 3),
            'x': round(lat, 4),
            'y': round(lon, 4),
            'g': 1 if has_geo else 0,
            'v': ipv4,
            'd': degree.get(asn, 0),
        })
        region_hist[bucket] += 1

    # Rank edges by combined endpoint radius so the top-N preserves importance.
    node_radius: dict[int, float] = {n['a']: n['r'] for n in nodes_out}
    pool_edges_ranked = sorted(
        pool_edges,
        key=lambda e: -(node_radius.get(e[0], 0) + node_radius.get(e[1], 0)),
    )
    edges_emitted = pool_edges_ranked[:MAX_EMIT_LINKS]
    links_out = [{'s': s, 't': t} for (s, t) in edges_emitted]

    nodes_path = os.path.join(DATA_DIR, 'nodes.json')
    links_path = os.path.join(DATA_DIR, 'links.json')
    write_json(nodes_path, nodes_out)
    write_json(links_path, links_out)
    print(f'Wrote {nodes_path} ({os.path.getsize(nodes_path)//1024} KB)')
    print(f'Wrote {links_path} ({os.path.getsize(links_path)//1024} KB)')

    meta = {
        'pool_size': len(pool),
        'edges_in_pool': len(pool_edges),
        'edges_emitted': len(edges_emitted),
        'max_emit_links': MAX_EMIT_LINKS,
        'as_with_real_geo': real_geo_n,
        'real_geo_pct': round(100.0 * real_geo_n / max(1, len(pool)), 2),
        'region_histogram': {k: region_hist.get(k, 0) for k in REGION_ORDER},
        'region_color': REGION_COLOR,
        'top10_by_ipv4': [
            {'asn': n['a'], 'cc': n['c'], 'ipv4': n['v'], 'degree': n['d']}
            for n in sorted(nodes_out, key=lambda n: -n['v'])[:10]
        ],
        'elapsed_sec': round(time.time() - t0, 2),
    }
    write_step_metrics(2, meta,
                       title_zh='Step 02 · 降采样到 5,000 个头部 AS',
                       title_en='Step 02 · Decimate to ~5K head ASes')

    print('\nRegion histogram:')
    for k in REGION_ORDER:
        print(f'  {k}: {region_hist.get(k, 0):>5}  ({REGION_COLOR[k]})')
    print(f'\nStep 2 complete in {time.time() - t0:.1f}s')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
