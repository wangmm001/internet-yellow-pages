"""Step 15: serialize a preset's tier files to binary + update manifest.json.

Per-preset script. Reads step13's CSV tiles + step14's bundle CSVs and
emits the binary wire format defined in DESIGN_GALAXY.md §4.6.

Outputs (under analysis/as_galaxy/data/):
  manifest.json                 (top-level, lists all 3 presets — read-
                                modified-written so per-preset runs merge)
  <preset>/L0.bin
  <preset>/L1.bin
  <preset>/L2/tile_<id>.bin     one per non-empty L2 octree cell
  <preset>/L3/tile_<id>.bin     one per non-empty L3 octree cell

Wire format (all little-endian):

  HEADER (48 B — design's "32 B" line is a doc-arithmetic slip; the field
                  list adds up to 48):
    char[4] magic            'GALX'
    u8      version          0x01
    u8      tier             L0=0, L1=1, L2=2, L3=3
    u8      region_mask      OR of bits {0:cn,1:na,2:ea,3:eu,4:ot}
    u8      reserved         0
    u32     tile_id          packed octree address (0 for L0/L1)
    f32 × 6 bbox             min_xyz, max_xyz
    u32     node_count
    u32     edge_count
    u32     bundle_count

  NODE BLOCK (variable, padded to next 32 B; min 32, max 96 B for our
              63-char name cap):
    u32  asn
    f32  x, y, z
    f32  radius
    u8   region              0..4
    u8   tier_in             0..3
    char cc[2]               ASCII; '\\0\\0' if unknown
    u8   name_len            0..63
    char name[name_len]
    u8   pad[…]              up to next 32 B boundary

  EDGE BLOCK (12 B):
    u32 src_asn, u32 dst_asn, f32 weight

  BUNDLE BLOCK (108 B — design's "100 B" line miscounts; (4+4+4) +
                8·3·4 = 108):
    u32 src_asn, u32 dst_asn, f32 weight
    f32[8][3] pts            bezier samples in (x, y, z) order

CLI:
  python -m analysis.as_galaxy.step15_galaxy_export --preset economy
  python -m analysis.as_galaxy.step15_galaxy_export --rewrite-manifest
        re-derive manifest.json from whatever preset dirs exist (handy
        after deleting/replacing one preset)
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys
import time
from collections import defaultdict
from datetime import date

from analysis.as_galaxy.common import (
    CACHE_DIR,
    DATA_DIR,
    PRESETS,
    REGION_ORDER,
    preset_by_name,
    read_csv,
)


GALAXY_MAGIC = b'GALX'
GALAXY_VERSION = 0x01
SAMPLES_PER_CURVE = 8

# Per-block expected sizes (recalculated; not the "32 B"/"100 B" labels in
# the design doc, which are off-by-N).
HEADER_SIZE = 48
EDGE_BLOCK_SIZE = 12
BUNDLE_BLOCK_SIZE = 12 + SAMPLES_PER_CURVE * 3 * 4   # 108


# ---------------------------------------------------------------------------
# Encoders
# ---------------------------------------------------------------------------

def encode_header(tier: int, tile_id: int, region_mask: int,
                  bbox: tuple[float, float, float, float, float, float],
                  node_count: int, edge_count: int, bundle_count: int) -> bytes:
    return (
        GALAXY_MAGIC
        + struct.pack('<BBBB', GALAXY_VERSION, tier & 0xFF,
                      region_mask & 0xFF, 0)
        + struct.pack('<I', tile_id & 0xFFFFFFFF)
        + struct.pack('<6f', *bbox)
        + struct.pack('<III', node_count, edge_count, bundle_count)
    )


def encode_node(asn: int, x: float, y: float, z: float, radius: float,
                region: int, tier_in: int, cc: str, name: str) -> bytes:
    """Pack one node, padded to next 32-byte boundary."""
    cc_bytes = (cc or '').upper().encode('ascii', errors='replace')[:2]
    cc_bytes = cc_bytes + b'\0' * (2 - len(cc_bytes))
    name_bytes = (name or '').encode('utf-8', errors='replace')[:63]
    body = (
        struct.pack('<I', asn & 0xFFFFFFFF)
        + struct.pack('<4f', x, y, z, radius)
        + struct.pack('<BB', region & 0xFF, tier_in & 0xFF)
        + cc_bytes
        + struct.pack('<B', len(name_bytes))
        + name_bytes
    )
    pad = (-len(body)) % 32
    return body + b'\0' * pad


def encode_edge(src: int, dst: int, weight: float) -> bytes:
    return struct.pack('<IIf', src & 0xFFFFFFFF, dst & 0xFFFFFFFF, weight)


def encode_bundle(src: int, dst: int, weight: float,
                  pts: list[tuple[float, float, float]]) -> bytes:
    if len(pts) != SAMPLES_PER_CURVE:
        raise ValueError(
            f'bundle expects {SAMPLES_PER_CURVE} samples, got {len(pts)}')
    flat = [c for p in pts for c in p]
    return (
        struct.pack('<IIf', src & 0xFFFFFFFF, dst & 0xFFFFFFFF, weight)
        + struct.pack(f'<{SAMPLES_PER_CURVE * 3}f', *flat)
    )


# ---------------------------------------------------------------------------
# Tile assembly
# ---------------------------------------------------------------------------

def _bbox_of_nodes(nodes: list[dict],
                   fallback: tuple[float, float, float, float, float, float]
                   ) -> tuple[float, float, float, float, float, float]:
    if not nodes:
        return fallback
    xs = [float(n['x']) for n in nodes]
    ys = [float(n['y']) for n in nodes]
    zs = [float(n['z']) for n in nodes]
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def _region_mask(nodes: list[dict]) -> int:
    m = 0
    for n in nodes:
        try:
            m |= 1 << (int(n['region']) & 0xFF)
        except (KeyError, ValueError):
            pass
    return m & 0xFF


def _bundle_rows_to_records(bundle_rows: list[dict]) -> dict[tuple[int, int], dict]:
    """{(src,dst): {weight, pts:[(x,y,z), ...]}} — keyed on the unordered pair
    so straight-edge lookup matches regardless of which side is "src".
    """
    out: dict[tuple[int, int], dict] = {}
    for r in bundle_rows:
        try:
            s, d = int(r['src']), int(r['dst'])
        except (KeyError, ValueError):
            continue
        pts = []
        for i in range(SAMPLES_PER_CURVE):
            try:
                pts.append((float(r[f'x{i}']), float(r[f'y{i}']),
                            float(r[f'z{i}'])))
            except (KeyError, ValueError):
                pts = []
                break
        if len(pts) != SAMPLES_PER_CURVE:
            continue
        try:
            w = float(r.get('weight') or 0.0)
        except ValueError:
            w = 0.0
        key = (min(s, d), max(s, d))
        out[key] = {'src': s, 'dst': d, 'weight': w, 'pts': pts}
    return out


def write_tile(path: str, tier: int, tile_id: int,
               bbox: tuple[float, float, float, float, float, float],
               nodes: list[dict], edges: list[dict],
               bundles: dict[tuple[int, int], dict] | None) -> int:
    """Write one .bin file. Returns bytes written."""
    bundle_recs: list[dict] = []
    if bundles:
        for e in edges:
            try:
                s, d = int(e['src']), int(e['dst'])
            except (KeyError, ValueError):
                continue
            key = (min(s, d), max(s, d))
            b = bundles.get(key)
            if b is not None:
                bundle_recs.append(b)
    region_mask = _region_mask(nodes)
    parts: list[bytes] = [
        encode_header(tier, tile_id, region_mask, bbox,
                      len(nodes), len(edges), len(bundle_recs)),
    ]
    for n in nodes:
        parts.append(encode_node(
            int(n['asn']),
            float(n['x']), float(n['y']), float(n['z']),
            float(n['radius']),
            int(n['region']), int(n.get('tier_in') or tier),
            n.get('cc') or '', n.get('name') or '',
        ))
    for e in edges:
        try:
            parts.append(encode_edge(int(e['src']), int(e['dst']),
                                     float(e.get('weight') or 0.0)))
        except (KeyError, ValueError):
            continue
    for b in bundle_recs:
        parts.append(encode_bundle(b['src'], b['dst'], b['weight'], b['pts']))
    blob = b''.join(parts)
    with open(path, 'wb') as f:
        f.write(blob)
    return len(blob)


# ---------------------------------------------------------------------------
# Per-preset export
# ---------------------------------------------------------------------------

def _list_tile_files(d: str) -> list[tuple[int, str]]:
    """Return sorted [(tile_id, path), ...] for tile_*.csv inside d."""
    if not os.path.isdir(d):
        return []
    out = []
    for fn in os.listdir(d):
        if fn.startswith('tile_') and fn.endswith('.csv'):
            try:
                tid = int(fn[len('tile_'):-len('.csv')])
            except ValueError:
                continue
            out.append((tid, os.path.join(d, fn)))
    return sorted(out)


def _attach_tier_in(rows: list[dict], tier: int) -> list[dict]:
    for r in rows:
        r['tier_in'] = tier
    return rows


def export_preset(preset_name: str, cache_dir: str, data_dir: str) -> dict:
    """Export one preset; return its manifest fragment."""
    preset = preset_by_name(preset_name)
    src_dir = os.path.join(cache_dir, preset_name)
    dst_dir = os.path.join(data_dir, preset_name)
    if not os.path.isdir(src_dir):
        raise SystemExit(
            f'[FATAL] {src_dir} missing — run step13/14 --preset {preset_name} first')
    os.makedirs(dst_dir, exist_ok=True)

    # --- read tiers.json for bbox + octree depths ----------------------
    with open(os.path.join(src_dir, 'tiers.json'), encoding='utf-8') as f:
        tiers = json.load(f)
    bbox = tuple(tiers['bbox'])
    l2_depth = tiers['octree']['l2_depth']
    l3_depth = tiers['octree']['l3_depth']

    # --- bundles (per L0/L1) ------------------------------------------
    bundles_l0 = _bundle_rows_to_records(
        list(read_csv(os.path.join(src_dir, 'bundles_l0.csv'))))
    bundles_l1 = _bundle_rows_to_records(
        list(read_csv(os.path.join(src_dir, 'bundles_l1.csv'))))

    bytes_total = 0

    # --- L0 ----------------------------------------------------------
    nodes = _attach_tier_in(list(read_csv(os.path.join(src_dir, 'nodes_l0.csv'))), 0)
    edges = list(read_csv(os.path.join(src_dir, 'edges_l0.csv')))
    bytes_total += write_tile(os.path.join(dst_dir, 'L0.bin'), 0, 0,
                              _bbox_of_nodes(nodes, bbox),
                              nodes, edges, bundles_l0)
    l0_meta = {'file': 'L0.bin', 'nodes': len(nodes), 'edges': len(edges),
               'bundles': sum(1 for e in edges
                              if (min(int(e['src']), int(e['dst'])),
                                  max(int(e['src']), int(e['dst']))) in bundles_l0),
               'bytes': os.path.getsize(os.path.join(dst_dir, 'L0.bin'))}

    # --- L1 ----------------------------------------------------------
    nodes = _attach_tier_in(list(read_csv(os.path.join(src_dir, 'nodes_l1.csv'))), 1)
    edges = list(read_csv(os.path.join(src_dir, 'edges_l1.csv')))
    bytes_total += write_tile(os.path.join(dst_dir, 'L1.bin'), 1, 0,
                              _bbox_of_nodes(nodes, bbox),
                              nodes, edges, bundles_l1)
    l1_meta = {'file': 'L1.bin', 'nodes': len(nodes), 'edges': len(edges),
               'bundles': sum(1 for e in edges
                              if (min(int(e['src']), int(e['dst'])),
                                  max(int(e['src']), int(e['dst']))) in bundles_l1),
               'bytes': os.path.getsize(os.path.join(dst_dir, 'L1.bin'))}

    # --- L2 / L3 octree tiles ----------------------------------------
    def _export_octree(tier: int, depth: int, node_subdir: str,
                       edge_subdir: str) -> dict:
        out_subdir = f'L{tier}'
        out_dir = os.path.join(dst_dir, out_subdir)
        os.makedirs(out_dir, exist_ok=True)
        # Wipe stale files
        for fn in os.listdir(out_dir):
            if fn.startswith('tile_') and fn.endswith('.bin'):
                os.remove(os.path.join(out_dir, fn))

        node_files = dict(_list_tile_files(os.path.join(src_dir, node_subdir)))
        edge_files = dict(_list_tile_files(os.path.join(src_dir, edge_subdir)))
        all_tile_ids = sorted(set(node_files) | set(edge_files))
        tiles: dict[str, dict] = {}
        nonlocal bytes_total
        for tid in all_tile_ids:
            nrows = _attach_tier_in(
                list(read_csv(node_files[tid])) if tid in node_files else [],
                tier,
            )
            erows = list(read_csv(edge_files[tid])) if tid in edge_files else []
            cb = tuple(tiers['tiers'][f'L{tier}']['cell_bboxes'].get(
                str(tid), list(bbox)))
            fname = f'tile_{tid:04d}.bin'
            n = write_tile(os.path.join(out_dir, fname), tier, tid, cb,
                           nrows, erows, None)
            bytes_total += n
            tiles[str(tid)] = {'file': f'{out_subdir}/{fname}',
                               'nodes': len(nrows), 'edges': len(erows),
                               'bytes': n}
        return {'dir': out_subdir, 'tile_count': len(tiles),
                'depth': depth, 'tiles': tiles}

    l2_meta = _export_octree(2, l2_depth, 'nodes_l2', 'edges_l2')
    l3_meta = _export_octree(3, l3_depth, 'nodes_l3', 'edges_l3')

    fragment = {
        'label_zh': preset['label_zh'], 'label_en': preset['label_en'],
        'weights': preset['weights'],
        'dir': preset['name'],
        'bytes_total': bytes_total,
        'tiers': {'L0': l0_meta, 'L1': l1_meta, 'L2': l2_meta, 'L3': l3_meta},
    }
    return fragment


# ---------------------------------------------------------------------------
# Manifest read-modify-write
# ---------------------------------------------------------------------------

def _detect_cone_available(cache_dir: str) -> bool:
    return os.path.exists(os.path.join(cache_dir, 'as_cone.csv'))


def _scan_global_counts(cache_dir: str) -> tuple[int, int]:
    n_nodes = 0
    for r in read_csv(os.path.join(cache_dir, 'nodes_raw.csv')):
        try:
            int(r['asn'])
            n_nodes += 1
        except (KeyError, ValueError):
            continue
    n_edges = 0
    for r in read_csv(os.path.join(cache_dir, 'edges_raw.csv')):
        try:
            int(r['src'])
            int(r['dst'])
            n_edges += 1
        except (KeyError, ValueError):
            continue
    return n_nodes, n_edges


def write_manifest(data_dir: str, cache_dir: str,
                   merged_presets: dict[str, dict],
                   bbox: tuple[float, float, float, float, float, float],
                   l2_depth: int, l3_depth: int) -> str:
    n_nodes, n_edges = _scan_global_counts(cache_dir)
    payload = {
        'version': 1,
        'snapshot_date': date.today().isoformat(),
        'source': 'iyp + bgpkit + nro + asnames',
        'presets': merged_presets,
        'default': PRESETS[0]['name'],
        'octree': {'l2_depth': l2_depth, 'l3_depth': l3_depth,
                   'bbox': [list(bbox[:3]), list(bbox[3:])]},
        'total_nodes': n_nodes,
        'total_edges': n_edges,
        'cone_available': _detect_cone_available(cache_dir),
        'samples_per_curve': SAMPLES_PER_CURVE,
        'binary_format': {
            'magic': 'GALX',
            'header_bytes': HEADER_SIZE,
            'edge_bytes': EDGE_BLOCK_SIZE,
            'bundle_bytes': BUNDLE_BLOCK_SIZE,
            'note': ('node block is variable, padded to 32 B; design '
                     'comment "32 B / 100 B" labels miscount — fields sum '
                     f'to {HEADER_SIZE} (header) and {BUNDLE_BLOCK_SIZE} (bundle).'),
        },
    }
    path = os.path.join(data_dir, 'manifest.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def merge_into_manifest(data_dir: str, preset_name: str,
                        fragment: dict, cache_dir: str,
                        bbox: tuple[float, float, float, float, float, float],
                        l2_depth: int, l3_depth: int) -> str:
    """Read existing manifest, replace this preset's fragment, write back."""
    mpath = os.path.join(data_dir, 'manifest.json')
    if os.path.exists(mpath):
        with open(mpath, encoding='utf-8') as f:
            existing = json.load(f)
        merged = dict(existing.get('presets') or {})
    else:
        merged = {}
    merged[preset_name] = fragment
    return write_manifest(data_dir, cache_dir, merged, bbox, l2_depth, l3_depth)


def rewrite_manifest_from_disk(data_dir: str, cache_dir: str) -> str:
    """Inspect data_dir/<preset>/ subdirs, rebuild manifest from what's there."""
    merged: dict[str, dict] = {}
    bbox = (-1.0, -1.0, -1.0, 1.0, 1.0, 1.0)
    l2_depth, l3_depth = 2, 3
    for p in PRESETS:
        pdir = os.path.join(data_dir, p['name'])
        if not os.path.isdir(pdir):
            continue
        # Try to recover counts from on-disk .bin files.
        l0_path = os.path.join(pdir, 'L0.bin')
        l1_path = os.path.join(pdir, 'L1.bin')
        if not (os.path.exists(l0_path) and os.path.exists(l1_path)):
            continue

        def _stat(path: str) -> dict:
            return {'file': os.path.basename(path),
                    'bytes': os.path.getsize(path)}

        def _scan_octree(subdir: str) -> dict:
            d = os.path.join(pdir, subdir)
            if not os.path.isdir(d):
                return {'dir': subdir, 'tile_count': 0, 'tiles': {}}
            tiles = {}
            for fn in sorted(os.listdir(d)):
                if not (fn.startswith('tile_') and fn.endswith('.bin')):
                    continue
                try:
                    tid = int(fn[len('tile_'):-len('.bin')])
                except ValueError:
                    continue
                tiles[str(tid)] = {'file': f'{subdir}/{fn}',
                                   'bytes': os.path.getsize(os.path.join(d, fn))}
            return {'dir': subdir, 'tile_count': len(tiles), 'tiles': tiles}

        merged[p['name']] = {
            'label_zh': p['label_zh'], 'label_en': p['label_en'],
            'weights': p['weights'], 'dir': p['name'],
            'tiers': {
                'L0': _stat(l0_path),
                'L1': _stat(l1_path),
                'L2': _scan_octree('L2'),
                'L3': _scan_octree('L3'),
            },
        }
    return write_manifest(data_dir, cache_dir, merged, bbox, l2_depth, l3_depth)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--preset',
                   choices=[p['name'] for p in PRESETS],
                   help='Export this preset (writes .bin files + merges into manifest)')
    g.add_argument('--rewrite-manifest', action='store_true',
                   help='Just regenerate manifest.json from existing on-disk binaries')
    ap.add_argument('--cache-dir', default=CACHE_DIR)
    ap.add_argument('--data-dir', default=DATA_DIR)
    args = ap.parse_args(argv)

    t0 = time.time()
    if args.rewrite_manifest:
        path = rewrite_manifest_from_disk(args.data_dir, args.cache_dir)
        print(f'rewrote manifest from disk → {path}  '
              f'({time.time() - t0:.2f}s)')
        return 0

    src_dir = os.path.join(args.cache_dir, args.preset)
    if not os.path.isdir(src_dir):
        print(f'[FATAL] {src_dir} missing — run step13/14 first', file=sys.stderr)
        return 1
    with open(os.path.join(src_dir, 'tiers.json'), encoding='utf-8') as f:
        tiers = json.load(f)
    bbox = tuple(tiers['bbox'])
    l2_depth = tiers['octree']['l2_depth']
    l3_depth = tiers['octree']['l3_depth']

    fragment = export_preset(args.preset, args.cache_dir, args.data_dir)
    mpath = merge_into_manifest(args.data_dir, args.preset, fragment,
                                args.cache_dir, bbox, l2_depth, l3_depth)
    bytes_total = fragment['bytes_total']
    print(f'\nStep 15 ({args.preset}) wrote {bytes_total/1024:.1f} KB across '
          f'{1 + 1 + fragment["tiers"]["L2"]["tile_count"] + fragment["tiers"]["L3"]["tile_count"]} '
          f'.bin files; manifest → {mpath}  ({time.time() - t0:.2f}s)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
