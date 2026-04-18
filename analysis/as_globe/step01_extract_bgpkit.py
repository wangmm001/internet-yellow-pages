"""Step 1 (alternative): extract from BGPKit + NRO delegated-stats directly.

Used when a local IYP Neo4j is unavailable. Same output schema as
`step01_extract.py` (produces the 4 CSVs downstream steps expect), but pulls
directly from the upstream sources IYP itself aggregates:

 - BGPKit pfx2as-latest.json.bz2          → AS → IPv4 addresses originated
 - BGPKit as2rel-v4-latest.json.bz2       → AS ↔ AS peering
 - NRO nro-delegated-stats                → AS → country

No geo source here (CAIDA ASRank is used by IYP but is unreliable through some
networks); `as_geo.csv` is emitted empty and step02 falls back to country
centroids for every AS.

Semantically equivalent to the Neo4j extract for this visualization's purpose:
same numbers, same edges. Differences from the Neo4j path:
 - No deduplication against other IYP sources (BGPKit is the only source).
 - `as_geo` is empty (all nodes use country centroid + jitter).
"""
from __future__ import annotations

import bz2
import csv
import json
import os
import sys
import time
import urllib.request
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.as_globe.common import (  # noqa: E402
    CACHE_DIR, ipv4_addresses_for_prefix, write_csv, write_step_metrics,
)


PFX2AS_URL = 'https://data.bgpkit.com/pfx2as/pfx2as-latest.json.bz2'
AS2REL_V4_URL = 'https://data.bgpkit.com/as2rel/as2rel-v4-latest.json.bz2'
NRO_URL = 'https://ftp.ripe.net/pub/stats/ripencc/nro-stats/latest/nro-delegated-stats'

RAW_DIR = os.path.join(CACHE_DIR, 'raw')
os.makedirs(RAW_DIR, exist_ok=True)


def _download(url: str, dest: str) -> str:
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        print(f'  [cache] {dest} ({os.path.getsize(dest)//1024} KB) — skip download')
        return dest
    print(f'  [get ] {url}')
    t0 = time.time()
    tmp = dest + '.part'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'iyp-as-globe/0.1 (analysis pipeline; +https://iyp.iijlab.net)',
        'Accept': '*/*',
    })
    with urllib.request.urlopen(req, timeout=180) as r, open(tmp, 'wb') as f:
        read = 0
        chunk = 1 << 16
        while True:
            buf = r.read(chunk)
            if not buf:
                break
            f.write(buf)
            read += len(buf)
    os.rename(tmp, dest)
    dt = time.time() - t0
    print(f'  [ok  ] {dest} ({read//1024} KB in {dt:.1f}s)')
    return dest


def extract_as_country() -> list[dict]:
    """Parse NRO delegated stats and return one row per ASN with country code."""
    path = os.path.join(RAW_DIR, 'nro-delegated-stats')
    _download(NRO_URL, path)

    rows: list[dict] = []
    skipped = 0
    with open(path, encoding='utf-8', errors='replace') as f:
        for raw in f:
            line = raw.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            # Skip the version header and summary lines.
            parts = line.split('|')
            if len(parts) < 7:
                continue
            rir, cc, rtype, start, count, date, status = parts[:7]
            if rtype != 'asn':
                continue
            if status not in ('assigned', 'allocated'):
                skipped += 1
                continue
            if not cc or cc == 'ZZ':
                skipped += 1
                continue
            try:
                start_i = int(start)
                count_i = int(count)
            except ValueError:
                continue
            cc = cc.upper()
            for asn in range(start_i, start_i + count_i):
                rows.append({'asn': asn, 'cc': cc})

    # Dedupe: keep first cc seen for any given ASN.
    seen: dict[int, str] = {}
    for r in rows:
        seen.setdefault(r['asn'], r['cc'])
    print(f'  [nro] {len(seen):,} ASes with country ({skipped:,} skipped reserved/unassigned)')
    return [{'asn': asn, 'cc': cc} for asn, cc in sorted(seen.items())]


def extract_as_ipv4() -> list[dict]:
    """Sum IPv4 address space per ASN from BGPKit pfx2as."""
    path = os.path.join(RAW_DIR, 'pfx2as-latest.json.bz2')
    _download(PFX2AS_URL, path)

    print('  [pfx2as] decoding...')
    t0 = time.time()
    with bz2.open(path, 'rt', encoding='utf-8') as f:
        records = json.load(f)
    print(f'  [pfx2as] {len(records):,} records in {time.time() - t0:.1f}s')

    by_asn_sum: dict[int, int] = defaultdict(int)
    by_asn_cnt: dict[int, int] = defaultdict(int)
    skipped = 0
    for r in records:
        asn = r.get('asn')
        prefix = r.get('prefix')
        if asn is None or not prefix:
            skipped += 1
            continue
        addrs = ipv4_addresses_for_prefix(prefix)
        if addrs == 0:
            skipped += 1   # IPv6 or malformed
            continue
        by_asn_sum[int(asn)] += addrs
        by_asn_cnt[int(asn)] += 1

    out = [
        {'asn': asn, 'ipv4_addresses': by_asn_sum[asn], 'prefix_count': by_asn_cnt[asn]}
        for asn in by_asn_sum
    ]
    out.sort(key=lambda r: -r['ipv4_addresses'])
    print(f'  [pfx2as] {len(out):,} ASes with IPv4 announcements ({skipped:,} rows skipped)')
    return out


def extract_as_peers() -> list[dict]:
    """Undirected, deduped PEERS_WITH edges from BGPKit as2rel-v4."""
    path = os.path.join(RAW_DIR, 'as2rel-v4-latest.json.bz2')
    _download(AS2REL_V4_URL, path)

    print('  [as2rel] decoding...')
    t0 = time.time()
    with bz2.open(path, 'rt', encoding='utf-8') as f:
        records = json.load(f)
    print(f'  [as2rel] {len(records):,} records in {time.time() - t0:.1f}s')

    edges: set[tuple[int, int]] = set()
    for r in records:
        a, b = r.get('asn1'), r.get('asn2')
        if a is None or b is None or a == b:
            continue
        a, b = int(a), int(b)
        if a > b:
            a, b = b, a
        edges.add((a, b))

    out = [{'src': a, 'dst': b} for (a, b) in sorted(edges)]
    print(f'  [as2rel] {len(out):,} unique undirected edges')
    return out


def main() -> int:
    t0 = time.time()
    print(f'Extracting into {CACHE_DIR} ...')

    print('[1/3] AS → country (NRO delegated stats)')
    as_country = extract_as_country()
    write_csv(os.path.join(CACHE_DIR, 'as_country.csv'), as_country, ['asn', 'cc'])

    print('[2/3] AS → IPv4 address count (BGPKit pfx2as)')
    as_ipv4 = extract_as_ipv4()
    write_csv(os.path.join(CACHE_DIR, 'as_ipv4.csv'), as_ipv4,
              ['asn', 'ipv4_addresses', 'prefix_count'])

    print('[3/3] AS ↔ AS peering (BGPKit as2rel-v4)')
    as_peers = extract_as_peers()
    write_csv(os.path.join(CACHE_DIR, 'as_peers.csv'), as_peers, ['src', 'dst'])

    # Empty geo file — step02 treats missing rows as "use country centroid".
    write_csv(os.path.join(CACHE_DIR, 'as_geo.csv'), [], ['asn', 'lat', 'lon'])
    print('  [as_geo] empty (CAIDA ASRank skipped; step02 falls back to centroid+jitter)')

    write_step_metrics(1, {
        'source': 'bgpkit + nro (direct)',
        'as_with_country': len(as_country),
        'as_with_ipv4': len(as_ipv4),
        'peering_edges': len(as_peers),
        'as_with_geo': 0,
        'cache_dir': CACHE_DIR,
        'elapsed_sec': round(time.time() - t0, 2),
    }, title_zh='Step 01 · 从 BGPKit + NRO 直接抽取底表',
       title_en='Step 01 · Direct extract from BGPKit + NRO (no Neo4j)')

    print(f'\nStep 1 (bgpkit) complete in {time.time() - t0:.1f}s → {CACHE_DIR}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
