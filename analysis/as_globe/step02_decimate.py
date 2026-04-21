"""Step 2: Select a renderable pool of ~5,000 ASes from the cached extracts.

Strategy:
  - Rank ASes by IPv4 address count desc; take top 3,000 ("economic mass").
  - Add any AS peered with ≥2 of those top 3K, up to a strict 5,000 cap
    ("structural support").
  - Drop edges where either endpoint is not in the pool.
  - Compute per-node region bucket, color, radius, and geo (real or centroid+jitter).

Emits:
  data/nodes.json  — compact keys {a,c,k,r,x,y,g,v,d,o}
                     (a=ASN, c=CC, k=region, r=radius_px, x=lat, y=lon,
                      g=has_real_geo, v=IPv4_count, d=pool_degree,
                      o=human-readable name)
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
# Cap how many edges get emitted. Selection is coverage-first: every pool AS
# contributes its fattest incident edge before the remaining budget is filled
# with the heaviest remaining edges. 60K keeps the force view readable while
# guaranteeing no isolated nodes (plain top-30K only covered ~2,700 ASes).
MAX_EMIT_LINKS = 60000


def _load() -> tuple[
    dict[int, str],
    dict[int, dict],
    list[tuple[int, int]],
    dict[int, tuple[float, float]],
    dict[int, str],
]:
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

    # as_name.csv is optional — an older cache without it still works (names
    # render as empty strings in the tooltip).
    as_name: dict[int, str] = {}
    name_path = os.path.join(CACHE_DIR, 'as_name.csv')
    if os.path.exists(name_path):
        for r in read_csv(name_path):
            try:
                asn = int(r['asn'])
            except (ValueError, KeyError):
                continue
            name = (r.get('name') or '').strip()
            if name:
                as_name[asn] = name

    return as_country, as_ipv4, edges, as_geo, as_name


def _select_pool(as_ipv4: dict[int, dict], edges: list[tuple[int, int]]) -> set[int]:
    by_ipv4 = sorted(as_ipv4.items(), key=lambda kv: -kv[1]['ipv4'])
    core = {asn for asn, _ in by_ipv4[:TOP_BY_IPV4]}

    neighbors: dict[int, set[int]] = defaultdict(set)
    for s, t in edges:
        neighbors[s].add(t)
        neighbors[t].add(s)

    if len(core) >= POOL_CAP:
        return set(list(core)[:POOL_CAP])

    anchor_hits: dict[int, int] = defaultdict(int)
    for s, t in edges:
        if s in core and t not in core:
            anchor_hits[t] += 1
        elif t in core and s not in core:
            anchor_hits[s] += 1

    # Rank all non-core candidates (hits ≥1) by (hits desc, IPv4 desc).
    # hits ≥ MIN_ANCHORS_FOR_ADMIT is used for the first fill; the "saver" pool
    # for replacing islands can draw from hits ≥ 1 — we only need a single
    # pool-neighbor, not two.
    candidates = sorted(
        (asn for asn, hits in anchor_hits.items() if asn not in core),
        key=lambda asn: (-anchor_hits[asn], -as_ipv4.get(asn, {}).get('ipv4', 0)),
    )
    primary = [a for a in candidates if anchor_hits[a] >= MIN_ANCHORS_FOR_ADMIT]
    fallback = [a for a in candidates if anchor_hits[a] < MIN_ANCHORS_FOR_ADMIT]

    pool = set(core)
    for asn in primary:
        if len(pool) >= POOL_CAP:
            break
        pool.add(asn)

    # Drop islands (no neighbor inside the pool) and refill from the waitlist —
    # only candidates that themselves have ≥1 neighbor in the *current* pool
    # qualify, so everyone we admit is guaranteed to get a visible edge.
    waitlist = [a for a in primary + fallback if a not in pool]
    wait_idx = 0
    for _ in range(10):  # converges in ≤ a couple iterations
        islands = {asn for asn in pool if not (neighbors.get(asn, set()) & pool)}
        if not islands:
            break
        pool -= islands
        added = 0
        while wait_idx < len(waitlist) and len(pool) < POOL_CAP:
            cand = waitlist[wait_idx]
            wait_idx += 1
            if cand in pool:
                continue
            if neighbors.get(cand, set()) & pool:
                pool.add(cand)
                added += 1
        if added == 0:
            break
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

    as_country, as_ipv4, edges, as_geo, as_name = _load()
    if not as_ipv4:
        print(f'[FATAL] no IPv4 data in {CACHE_DIR}; run step01 first.', file=sys.stderr)
        return 1

    print(f'Loaded: {len(as_country):,} AS-country, {len(as_ipv4):,} AS-IPv4, '
          f'{len(edges):,} edges, {len(as_geo):,} AS-geo, '
          f'{len(as_name):,} AS-name')

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
            'o': as_name.get(asn, ''),
        })
        region_hist[bucket] += 1

    # Rank edges by combined endpoint radius so "importance" (hub-hub) sorts first.
    node_radius: dict[int, float] = {n['a']: n['r'] for n in nodes_out}
    pool_edges_ranked = sorted(
        pool_edges,
        key=lambda e: -(node_radius.get(e[0], 0) + node_radius.get(e[1], 0)),
    )

    # Coverage-first: every AS gets at least one edge before the rest of the
    # budget is filled by importance. Walk edges in importance order and keep
    # any edge that is the first one to cover one of its endpoints.
    seen: set[int] = set()
    chosen_idx: set[int] = set()
    for i, (s, t) in enumerate(pool_edges_ranked):
        if s not in seen or t not in seen:
            chosen_idx.add(i)
            seen.add(s)
            seen.add(t)
            if len(seen) >= len(pool):
                break

    # Fill remaining budget with the heaviest edges we haven't picked yet.
    for i in range(len(pool_edges_ranked)):
        if len(chosen_idx) >= MAX_EMIT_LINKS:
            break
        if i in chosen_idx:
            continue
        chosen_idx.add(i)

    edges_emitted = [pool_edges_ranked[i] for i in sorted(chosen_idx)]
    links_out = [{'s': s, 't': t} for (s, t) in edges_emitted]

    covered = {s for s, _ in edges_emitted} | {t for _, t in edges_emitted}
    missing = len(pool) - len(covered & pool)

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
        'pool_as_uncovered': missing,
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
