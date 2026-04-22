"""Step 10 (BGPKit fallback): extract the full global AS graph directly.

For environments where IYP Neo4j isn't available. Downloads the same
upstream sources IYP itself aggregates:

  pfx2as-latest.json.bz2        → AS → IPv4 address count + prefix count
  as2rel-v4-latest.json.bz2     → AS ↔ AS peering (undirected)
  nro-delegated-stats           → AS → country
  ripe/asnames/asn.txt          → AS → curated name

Shares the raw-download cache with as_globe/step01_extract_bgpkit.py via
data_cache/as_globe/raw/ (see common.RAW_DIR). If those files are already
present from a previous as_globe run, this step skips download entirely.

Same output CSVs as the Neo4j path:
 - nodes_raw.csv  (asn, cc, name, ipv4, prefix_count)
 - edges_raw.csv  (src, dst)

Typical cold-start: ~3–8 min (pfx2as is the slow one, ~40 MB over HTTPS).
Warm run: <30 sec (all downloads cached).
"""
from __future__ import annotations

import bz2
import json
import os
import sys
import time
import urllib.request
from collections import defaultdict

from analysis.as_galaxy.common import (
    CACHE_DIR,
    RAW_DIR,
    ipv4_addresses_for_prefix,
    write_csv,
    write_step_metrics,
)


PFX2AS_URL = 'https://data.bgpkit.com/pfx2as/pfx2as-latest.json.bz2'
AS2REL_V4_URL = 'https://data.bgpkit.com/as2rel/as2rel-v4-latest.json.bz2'
NRO_URL = 'https://ftp.ripe.net/pub/stats/ripencc/nro-stats/latest/nro-delegated-stats'
ASNAMES_URL = 'https://ftp.ripe.net/ripe/asnames/asn.txt'


# ---------------------------------------------------------------------------
# Shared HTTP download with a local file cache
# ---------------------------------------------------------------------------

def _download(url: str, dest: str) -> str:
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        print(f'  [cache] {dest} ({os.path.getsize(dest)//1024:,} KB) — skip')
        return dest
    print(f'  [get ] {url}')
    t0 = time.time()
    tmp = dest + '.part'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'iyp-as-galaxy/0.1 (analysis pipeline; +https://iyp.iijlab.net)',
        'Accept': '*/*',
    })
    with urllib.request.urlopen(req, timeout=240) as r, open(tmp, 'wb') as f:
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
    print(f'  [ok  ] {dest} ({read//1024:,} KB in {dt:.1f}s)')
    return dest


# ---------------------------------------------------------------------------
# Parsers — one per upstream source
# ---------------------------------------------------------------------------

def parse_nro_country() -> dict[int, str]:
    """NRO delegated stats → {asn: cc}. Only 'assigned'/'allocated' kept."""
    path = os.path.join(RAW_DIR, 'nro-delegated-stats')
    _download(NRO_URL, path)
    out: dict[int, str] = {}
    skipped = 0
    with open(path, encoding='utf-8', errors='replace') as f:
        for raw in f:
            line = raw.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            parts = line.split('|')
            if len(parts) < 7:
                continue
            _rir, cc, rtype, start, count, _date, status = parts[:7]
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
                out.setdefault(asn, cc)
    print(f'  [nro] {len(out):,} ASes with country ({skipped:,} skipped)')
    return out


def parse_pfx2as_ipv4() -> dict[int, tuple[int, int]]:
    """BGPKit pfx2as → {asn: (ipv4_total, prefix_count)}."""
    path = os.path.join(RAW_DIR, 'pfx2as-latest.json.bz2')
    _download(PFX2AS_URL, path)
    by_asn: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    skipped = 0
    # BGPKit's pfx2as is a newline-delimited JSON stream inside the bz2.
    with bz2.open(path, 'rt', encoding='utf-8') as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                skipped += 1
                continue
            prefix = rec.get('prefix')
            origins = rec.get('origins') or []
            if not prefix or not origins:
                skipped += 1
                continue
            # pfx2as encodes multi-origin prefixes — count each origin once.
            addrs = ipv4_addresses_for_prefix(prefix)
            if addrs <= 0:
                continue
            for origin in origins:
                try:
                    asn = int(origin)
                except (ValueError, TypeError):
                    continue
                entry = by_asn[asn]
                entry[0] += addrs
                entry[1] += 1
    if skipped:
        print(f'  [pfx2as] skipped {skipped:,} malformed rows')
    print(f'  [pfx2as] {len(by_asn):,} ASes originate ≥1 IPv4 prefix')
    return {asn: (entry[0], entry[1]) for asn, entry in by_asn.items()}


def parse_as2rel_edges() -> list[tuple[int, int]]:
    """BGPKit as2rel → sorted, deduped undirected edges (src < dst)."""
    path = os.path.join(RAW_DIR, 'as2rel-v4-latest.json.bz2')
    _download(AS2REL_V4_URL, path)
    out: set[tuple[int, int]] = set()
    skipped = 0
    with bz2.open(path, 'rt', encoding='utf-8') as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                skipped += 1
                continue
            a, b = rec.get('asn1'), rec.get('asn2')
            if a is None or b is None:
                skipped += 1
                continue
            try:
                a, b = int(a), int(b)
            except (ValueError, TypeError):
                skipped += 1
                continue
            if a == b:
                continue
            if a > b:
                a, b = b, a
            out.add((a, b))
    if skipped:
        print(f'  [as2rel] skipped {skipped:,} malformed rows')
    print(f'  [as2rel] {len(out):,} unique undirected edges')
    return sorted(out)


def parse_asnames() -> dict[int, str]:
    """RIPE asnames (emileaben) → {asn: name}. Lines are `AS_NUMBER NAME, CC`."""
    path = os.path.join(RAW_DIR, 'asn.txt')
    try:
        _download(ASNAMES_URL, path)
    except Exception as e:
        print(f'  [asnames] download failed: {e} — proceeding with empty name map')
        return {}
    out: dict[int, str] = {}
    with open(path, encoding='utf-8', errors='replace') as f:
        for raw in f:
            line = raw.rstrip('\n').strip()
            if not line or line.startswith('#'):
                continue
            head, _, tail = line.partition(' ')
            try:
                asn = int(head.lstrip('AS'))
            except ValueError:
                continue
            name = tail.strip()
            # Strip a trailing ", CC" (two-letter code) if present.
            if len(name) >= 4 and name[-4:-2] == ', ' and name[-2:].isalpha():
                name = name[:-4].rstrip()
            if name:
                out.setdefault(asn, name)
    print(f'  [asnames] {len(out):,} ASes with a name')
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    t0 = time.time()
    print(f'Extracting full global AS graph (BGPKit path) to {CACHE_DIR}')
    print(f'  raw-download cache: {RAW_DIR}')

    print('[1/4] AS → country (NRO delegated stats)')
    cc_map = parse_nro_country()

    print('[2/4] AS → IPv4 + prefix count (BGPKit pfx2as)')
    ipv4 = parse_pfx2as_ipv4()

    print('[3/4] AS ↔ AS peering (BGPKit as2rel-v4)')
    edges = parse_as2rel_edges()

    print('[4/4] AS → name (RIPE asnames)')
    name_map = parse_asnames()

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
        'source': 'bgpkit + nro + asnames (direct)',
        'as_with_ipv4': len(ipv4),
        'as_with_country': len(cc_map),
        'as_with_name': len(name_map),
        'peering_edges': len(edges),
        'total_nodes': len(all_asns),
        'cache_dir': CACHE_DIR,
        'raw_dir': RAW_DIR,
        'elapsed_sec': round(time.time() - t0, 2),
    }, title_zh='Step 10 · 从 BGPKit + NRO + asnames 抽取全球 AS 图',
       title_en='Step 10 · Extract full global AS graph from BGPKit + NRO + asnames')

    print(f'\nStep 10 (bgpkit) complete in {time.time() - t0:.1f}s → {CACHE_DIR}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
