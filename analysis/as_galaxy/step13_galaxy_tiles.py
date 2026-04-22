"""Step 13: partition the global AS graph into a 4-level LOD pyramid.

Per-preset script. Reads the merged outputs of step10/11/12 and writes
per-tier node + edge CSVs that step14 (HEB bundling) and step15 (binary
export) consume.

Tier admission (cumulative — L3 contains every AS, L2 the top 30K of
those, etc.):

  L0  top      500  by score_<preset>           → 1 file
  L1  next   4 500                              → 1 file
  L2  next  25 000  bucketed into 64 octree cells (depth=2)
  L3  rest 70 000+  bucketed into 512 octree cells (depth=3)

Edge admission: an edge (s, d) lives at tier max(tier_in[s], tier_in[d]).
For L2/L3 edges, when both endpoints sit in the same octree cell the edge
is stored in that cell's tile. When endpoints sit in different cells (or
when one endpoint is L0/L1 and the L2/L3 endpoint's cell would orphan it)
the edge is "demoted" to L1.bin so it's always loaded — this matches the
design's "stored in the parent file (higher LOD)" guidance and prevents
edges from disappearing when only one of two adjacent tiles is loaded.

Edge weight = min(log10(v_src+1), log10(v_dst+1))   (per design §4.6).
Sprite radius = 0.005 + score**0.5 * 0.05            — square-root keeps
                                                      tier-1s ~3-4× the
                                                      smallest sprite, not
                                                      hundreds of times.

CLI:
  python -m analysis.as_galaxy.step13_galaxy_tiles --preset economy
  python -m analysis.as_galaxy.step13_galaxy_tiles --preset structure
  python -m analysis.as_galaxy.step13_galaxy_tiles --preset reach

Outputs land in:
  data_cache/as_galaxy/<preset>/
    tiers.json                 (counts, bbox, octree depths)
    nodes_l0.csv               (asn, x, y, z, radius, region, cc, name, score, v)
    nodes_l1.csv
    nodes_l2/tile_<id>.csv     (~64 files; only cells with >=1 node)
    nodes_l3/tile_<id>.csv     (~512 files; only cells with >=1 node)
    edges_l0.csv               (src, dst, weight)
    edges_l1.csv
    edges_l2/tile_<id>.csv
    edges_l3/tile_<id>.csv
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from collections import defaultdict

from analysis.as_galaxy.common import (
    CACHE_DIR,
    REGION_ORDER,
    PRESETS,
    preset_by_name,
    read_csv,
    region_of,
    write_csv,
    write_step_metrics,
)


# Tier sizes — match design §4.4. We accept fewer if the graph is small
# (e.g. the smoke test runs with N=200, in which case everything spills
# into L0 and the L1+ files end up empty but still well-formed).
TIER_SIZES = {0: 500, 1: 5_000, 2: 30_000}  # L3 absorbs everything else.

# Edge caps — the design's L0 ~2K / L1 ~20K *edge* budget assumed sparse
# tier interconnection but in reality the global top-500 ASes are nearly
# a clique (~70K edges among them) and the top-5000 mesh has 200-330K
# internal edges. Without a cap, L1.bin balloons to 35-40 MB and breaks
# the <500 ms cold-start goal in design §7.
#
# Strategy: sort each tier's candidate edges by weight (= min of log10 v
# at either endpoint, an "edge importance" proxy), keep the top N, and
# demote the overflow into L2 tiles by edge midpoint position. Demoted
# edges become visible only when the user zooms into that region.
EDGE_CAP_L0 = 2_000
EDGE_CAP_L1 = 18_000

# Octree depths.
L2_DEPTH = 2   # 4×4×4 = 64 cells
L3_DEPTH = 3   # 8×8×8 = 512 cells

# Sprite radius mapping.
RADIUS_BASE = 0.005
RADIUS_RANGE = 0.050


# ---------------------------------------------------------------------------
# Tier assignment
# ---------------------------------------------------------------------------

def assign_tiers(scored: list[dict], score_col: str) -> dict[int, int]:
    """{asn: tier_in} where tier_in ∈ {0,1,2,3}.

    Scaling is robust to small graphs (smoke test). Sizes shrink
    proportionally if `len(scored)` is smaller than the design targets.
    """
    n = len(scored)
    by_score = sorted(
        scored,
        key=lambda r: -float(r.get(score_col) or 0.0),
    )
    sizes = {
        0: min(TIER_SIZES[0], max(1, n // 200)),
        1: min(TIER_SIZES[1], max(1, n // 20)),
        2: min(TIER_SIZES[2], max(1, n // 3)),
    }
    # If the requested L0/L1 sizes overlap (tiny graphs), clamp left-to-right.
    sizes[1] = max(sizes[1], sizes[0] + 1)
    sizes[2] = max(sizes[2], sizes[1] + 1)
    out: dict[int, int] = {}
    for i, r in enumerate(by_score):
        try:
            asn = int(r['asn'])
        except (KeyError, ValueError):
            continue
        if i < sizes[0]:
            out[asn] = 0
        elif i < sizes[1]:
            out[asn] = 1
        elif i < sizes[2]:
            out[asn] = 2
        else:
            out[asn] = 3
    return out


# ---------------------------------------------------------------------------
# Octree assignment
# ---------------------------------------------------------------------------

def cell_id(x: float, y: float, z: float, depth: int,
            bbox: tuple[float, float, float, float, float, float]) -> int:
    """Pack (ix, iy, iz) into a `depth*3`-bit integer.

    Layout: low 2*depth+ bits store ix/iy/iz packed least-significant axis
    first. Not Morton-ordered — readability beats locality at our N.
    """
    x0, y0, z0, x1, y1, z1 = bbox
    D = 1 << depth
    ix = max(0, min(D - 1, int((x - x0) / (x1 - x0) * D))) if x1 > x0 else 0
    iy = max(0, min(D - 1, int((y - y0) / (y1 - y0) * D))) if y1 > y0 else 0
    iz = max(0, min(D - 1, int((z - z0) / (z1 - z0) * D))) if z1 > z0 else 0
    return (iz * D * D) + (iy * D) + ix


def cell_bbox(cid: int, depth: int,
              bbox: tuple[float, float, float, float, float, float]
              ) -> tuple[float, float, float, float, float, float]:
    """Inverse of cell_id — returns the cell's axis-aligned bbox."""
    x0, y0, z0, x1, y1, z1 = bbox
    D = 1 << depth
    ix = cid % D
    iy = (cid // D) % D
    iz = cid // (D * D)
    sx, sy, sz = (x1 - x0) / D, (y1 - y0) / D, (z1 - z0) / D
    return (
        x0 + ix * sx, y0 + iy * sy, z0 + iz * sz,
        x0 + (ix + 1) * sx, y0 + (iy + 1) * sy, z0 + (iz + 1) * sz,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--preset', required=True,
                    choices=[p['name'] for p in PRESETS])
    ap.add_argument('--cache-dir', default=CACHE_DIR,
                    help='Override CACHE_DIR (also overridable by IYP_AS_GALAXY_CACHE_DIR)')
    args = ap.parse_args(argv)

    t0 = time.time()
    preset = preset_by_name(args.preset)
    score_col = f'score_{preset["name"]}'
    cache_dir = args.cache_dir
    out_dir = os.path.join(cache_dir, preset['name'])
    os.makedirs(out_dir, exist_ok=True)
    print(f'Tiling preset={preset["name"]} → {out_dir}')

    # --- read inputs -----------------------------------------------------
    scored_path = os.path.join(cache_dir, 'nodes_scored.csv')
    layout_path = os.path.join(cache_dir, 'nodes_layout.csv')
    raw_path = os.path.join(cache_dir, 'nodes_raw.csv')
    edges_path = os.path.join(cache_dir, 'edges_raw.csv')
    for p in (scored_path, layout_path, raw_path, edges_path):
        if not os.path.exists(p):
            print(f'[FATAL] missing input {p} — run step10/11/12 first',
                  file=sys.stderr)
            return 1

    scored_rows = list(read_csv(scored_path))
    layout_rows = list(read_csv(layout_path))
    raw_rows = list(read_csv(raw_path))

    pos: dict[int, tuple[float, float, float]] = {}
    for r in layout_rows:
        try:
            pos[int(r['asn'])] = (float(r['x']), float(r['y']), float(r['z']))
        except (KeyError, ValueError):
            continue

    # nodes_raw → cc, name, ipv4 (for edge weight + display)
    raw_by_asn: dict[int, dict] = {}
    for r in raw_rows:
        try:
            raw_by_asn[int(r['asn'])] = r
        except (KeyError, ValueError):
            continue

    # nodes_scored → score_<preset>, plus other components for inspection.
    score_by_asn: dict[int, float] = {}
    for r in scored_rows:
        try:
            score_by_asn[int(r['asn'])] = float(r.get(score_col) or 0.0)
        except (KeyError, ValueError):
            continue

    # Pre-compute log10(v+1) once — it's used per-edge for the weight.
    log_v: dict[int, float] = {}
    for asn, r in raw_by_asn.items():
        try:
            log_v[asn] = math.log10(float(r.get('ipv4') or 0) + 1.0)
        except (ValueError, TypeError):
            log_v[asn] = 0.0

    # --- tier assignment -------------------------------------------------
    tier_in = assign_tiers(scored_rows, score_col)
    print(f'  tier counts:  '
          + '  '.join(f'L{t}={sum(1 for v in tier_in.values() if v == t):,}'
                      for t in (0, 1, 2, 3)))

    # --- octree assignment for L2 + L3 ----------------------------------
    bbox = (-1.0, -1.0, -1.0, 1.0, 1.0, 1.0)
    cell_l2: dict[int, int] = {}
    cell_l3: dict[int, int] = {}
    for asn, t in tier_in.items():
        if asn not in pos:
            continue
        x, y, z = pos[asn]
        if t == 2:
            cell_l2[asn] = cell_id(x, y, z, L2_DEPTH, bbox)
        elif t == 3:
            cell_l3[asn] = cell_id(x, y, z, L3_DEPTH, bbox)

    # --- partition nodes by tier+cell ------------------------------------
    nodes_l0, nodes_l1 = [], []
    nodes_l2_per_tile: dict[int, list[dict]] = defaultdict(list)
    nodes_l3_per_tile: dict[int, list[dict]] = defaultdict(list)

    for asn, t in tier_in.items():
        if asn not in pos:
            # Layout backend may have dropped a node — skip rather than emit
            # garbage coordinates. Step12's outer-shell scatter should have
            # caught these, but be defensive.
            continue
        x, y, z = pos[asn]
        score = score_by_asn.get(asn, 0.0)
        radius = RADIUS_BASE + (max(0.0, min(1.0, score)) ** 0.5) * RADIUS_RANGE
        raw = raw_by_asn.get(asn, {})
        cc = (raw.get('cc') or '').upper()
        # Truncate long names — the binary spec caps at 63 chars.
        name = (raw.get('name') or '')[:63]
        rec = {
            'asn': asn,
            'x': round(x, 5),
            'y': round(y, 5),
            'z': round(z, 5),
            'radius': round(radius, 5),
            'region': REGION_ORDER.index(region_of(cc)),
            'cc': cc,
            'name': name,
            'score': round(score, 6),
            'v': raw.get('ipv4') or 0,
        }
        if t == 0:
            nodes_l0.append(rec)
        elif t == 1:
            nodes_l1.append(rec)
        elif t == 2:
            nodes_l2_per_tile[cell_l2[asn]].append(rec)
        else:
            nodes_l3_per_tile[cell_l3[asn]].append(rec)

    # --- partition edges --------------------------------------------------
    # First pass: classify every edge into its candidate tier slot.
    # Second pass: cap L0/L1 by weight, demote overflow to L2 tiles by
    # midpoint position.
    cand_l0, cand_l1 = [], []
    edges_l2_per_tile: dict[int, list[dict]] = defaultdict(list)
    edges_l3_per_tile: dict[int, list[dict]] = defaultdict(list)
    edge_demote_l2_to_l1 = 0
    edge_demote_l3_to_l1 = 0
    edge_dropped_no_tier = 0

    for r in read_csv(edges_path):
        try:
            s, d = int(r['src']), int(r['dst'])
        except (KeyError, ValueError):
            continue
        ts, td = tier_in.get(s), tier_in.get(d)
        if ts is None or td is None:
            edge_dropped_no_tier += 1
            continue
        if s not in pos or d not in pos:
            edge_dropped_no_tier += 1
            continue
        et = max(ts, td)
        weight = min(log_v.get(s, 0.0), log_v.get(d, 0.0))
        rec = {'src': s, 'dst': d, 'weight': round(weight, 5)}
        if et == 0:
            cand_l0.append(rec)
        elif et == 1:
            cand_l1.append(rec)
        elif et == 2:
            cs = cell_l2.get(s)
            cd = cell_l2.get(d)
            cells = {c for c in (cs, cd) if c is not None}
            if len(cells) == 1:
                edges_l2_per_tile[next(iter(cells))].append(rec)
            else:
                # Cross-cell L2 edge: demote to L1 candidate pool (still
                # subject to L1 cap below).
                cand_l1.append(rec)
                edge_demote_l2_to_l1 += 1
        else:  # et == 3
            cs = cell_l3.get(s)
            cd = cell_l3.get(d)
            cells = {c for c in (cs, cd) if c is not None}
            if len(cells) == 1:
                edges_l3_per_tile[next(iter(cells))].append(rec)
            else:
                # Cross-cell L3 edges go straight to L2 by midpoint
                # rather than burdening L1 — they're long-haul but only
                # involve one or two L3 nodes.
                mx = (pos[s][0] + pos[d][0]) / 2
                my = (pos[s][1] + pos[d][1]) / 2
                mz = (pos[s][2] + pos[d][2]) / 2
                mid_cell = cell_id(mx, my, mz, L2_DEPTH, bbox)
                edges_l2_per_tile[mid_cell].append(rec)
                edge_demote_l3_to_l1 += 1

    # Cap L0 / L1 by weight; demoted overflow goes to L2 tiles by midpoint.
    cand_l0.sort(key=lambda r: -r['weight'])
    cand_l1.sort(key=lambda r: -r['weight'])
    edges_l0 = cand_l0[:EDGE_CAP_L0]
    edges_l1 = cand_l1[:EDGE_CAP_L1]
    overflow = cand_l0[EDGE_CAP_L0:] + cand_l1[EDGE_CAP_L1:]
    edge_demote_cap_to_l2 = 0
    for rec in overflow:
        s, d = rec['src'], rec['dst']
        if s not in pos or d not in pos:
            continue
        mx = (pos[s][0] + pos[d][0]) / 2
        my = (pos[s][1] + pos[d][1]) / 2
        mz = (pos[s][2] + pos[d][2]) / 2
        mid_cell = cell_id(mx, my, mz, L2_DEPTH, bbox)
        edges_l2_per_tile[mid_cell].append(rec)
        edge_demote_cap_to_l2 += 1

    print(f'  edge candidates: L0={len(cand_l0):,}  L1={len(cand_l1):,}  '
          f'(after cap → L0={len(edges_l0):,}  L1={len(edges_l1):,})')
    print(f'  demoted to L2 by cap overflow: {edge_demote_cap_to_l2:,}  '
          f'(L2 cross-cell rejoined L1 pool: {edge_demote_l2_to_l1:,};  '
          f'L3 cross-cell to L2: {edge_demote_l3_to_l1:,})')
    print(f'  edge counts after assignment: '
          f'L0={len(edges_l0):,}  L1={len(edges_l1):,}  '
          f'L2={sum(len(v) for v in edges_l2_per_tile.values()):,}  '
          f'L3={sum(len(v) for v in edges_l3_per_tile.values()):,}')
    print(f'  dropped (no tier/pos): {edge_dropped_no_tier:,}')

    # --- write outputs ---------------------------------------------------
    node_cols = ['asn', 'x', 'y', 'z', 'radius', 'region', 'cc', 'name',
                 'score', 'v']
    edge_cols = ['src', 'dst', 'weight']

    # Single-file tiers
    write_csv(os.path.join(out_dir, 'nodes_l0.csv'), nodes_l0, node_cols)
    write_csv(os.path.join(out_dir, 'nodes_l1.csv'), nodes_l1, node_cols)
    write_csv(os.path.join(out_dir, 'edges_l0.csv'), edges_l0, edge_cols)
    write_csv(os.path.join(out_dir, 'edges_l1.csv'), edges_l1, edge_cols)

    # Octree tiers — one file per non-empty cell
    def _write_tile_dir(subdir: str, per_tile: dict[int, list[dict]],
                        cols: list[str]) -> dict[int, str]:
        d = os.path.join(out_dir, subdir)
        os.makedirs(d, exist_ok=True)
        # Clean stale tile files from prior runs (depth changes etc.)
        for fn in os.listdir(d):
            if fn.startswith('tile_') and fn.endswith('.csv'):
                os.remove(os.path.join(d, fn))
        out: dict[int, str] = {}
        for cid, rows in per_tile.items():
            fn = f'tile_{cid:04d}.csv'
            write_csv(os.path.join(d, fn), rows, cols)
            out[cid] = fn
        return out

    n2_files = _write_tile_dir('nodes_l2', nodes_l2_per_tile, node_cols)
    n3_files = _write_tile_dir('nodes_l3', nodes_l3_per_tile, node_cols)
    e2_files = _write_tile_dir('edges_l2', edges_l2_per_tile, edge_cols)
    e3_files = _write_tile_dir('edges_l3', edges_l3_per_tile, edge_cols)

    # tiers.json — what step15 and the manifest will need.
    tiers_meta = {
        'preset': preset['name'],
        'preset_label_zh': preset['label_zh'],
        'preset_label_en': preset['label_en'],
        'weights': preset['weights'],
        'bbox': list(bbox),
        'octree': {'l2_depth': L2_DEPTH, 'l3_depth': L3_DEPTH},
        'tiers': {
            'L0': {'nodes': len(nodes_l0), 'edges': len(edges_l0),
                   'file': 'nodes_l0.csv'},
            'L1': {'nodes': len(nodes_l1), 'edges': len(edges_l1),
                   'file': 'nodes_l1.csv'},
            'L2': {'nodes': sum(len(v) for v in nodes_l2_per_tile.values()),
                   'edges': sum(len(v) for v in edges_l2_per_tile.values()),
                   'tile_count': len(nodes_l2_per_tile),
                   'tiles': sorted(nodes_l2_per_tile),
                   'cell_bboxes': {
                       str(c): list(cell_bbox(c, L2_DEPTH, bbox))
                       for c in nodes_l2_per_tile
                   }},
            'L3': {'nodes': sum(len(v) for v in nodes_l3_per_tile.values()),
                   'edges': sum(len(v) for v in edges_l3_per_tile.values()),
                   'tile_count': len(nodes_l3_per_tile),
                   'tiles': sorted(nodes_l3_per_tile),
                   'cell_bboxes': {
                       str(c): list(cell_bbox(c, L3_DEPTH, bbox))
                       for c in nodes_l3_per_tile
                   }},
        },
        'edge_caps': {'L0': EDGE_CAP_L0, 'L1': EDGE_CAP_L1},
        'demoted_edges': {
            'l2_cross_cell_to_l1_pool': edge_demote_l2_to_l1,
            'l3_cross_cell_to_l2_midpoint': edge_demote_l3_to_l1,
            'cap_overflow_to_l2_midpoint': edge_demote_cap_to_l2,
        },
        'dropped_edges_no_tier_or_pos': edge_dropped_no_tier,
    }
    with open(os.path.join(out_dir, 'tiers.json'), 'w', encoding='utf-8') as f:
        json.dump(tiers_meta, f, ensure_ascii=False, indent=2)
    print(f'  wrote {os.path.join(out_dir, "tiers.json")}')

    write_step_metrics(13, {
        'preset': preset['name'],
        'tier_counts': {f'L{t}': sum(1 for v in tier_in.values() if v == t)
                        for t in (0, 1, 2, 3)},
        'l2_tile_count': len(nodes_l2_per_tile),
        'l3_tile_count': len(nodes_l3_per_tile),
        'edges_l0': len(edges_l0),
        'edges_l1': len(edges_l1),
        'edges_l2_total': sum(len(v) for v in edges_l2_per_tile.values()),
        'edges_l3_total': sum(len(v) for v in edges_l3_per_tile.values()),
        'edges_l2_cross_cell_rejoined_l1': edge_demote_l2_to_l1,
        'edges_l3_cross_cell_to_l2_mid': edge_demote_l3_to_l1,
        'edges_cap_overflow_to_l2_mid': edge_demote_cap_to_l2,
        'edges_dropped': edge_dropped_no_tier,
        'elapsed_sec': round(time.time() - t0, 2),
    }, title_zh=f'Step 13 · LOD 切分 + 八叉树 ({preset["label_zh"]})',
       title_en=f'Step 13 · LOD pyramid + octree ({preset["label_en"]})')

    print(f'\nStep 13 ({preset["name"]}) complete in {time.time() - t0:.1f}s')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
