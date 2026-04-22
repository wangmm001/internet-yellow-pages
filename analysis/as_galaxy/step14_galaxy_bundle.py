"""Step 14: hierarchical edge bundling for L0 + L1 edges, per preset.

Bundles only the always-loaded tiers (L0 + L1, ~22K edges total in the
real graph). L2/L3 edges stay straight — bundling cost is O(E · path_len)
and at our scale is best spent where the user spends most time (the
zoomed-out skeleton).

Pipeline:
  1. Build / load the Louvain community partition of the FULL global
     peering graph. This is preset-independent — same edges in, same
     communities out — so it's cached at
     data_cache/as_galaxy/communities.csv after the first run.
  2. Compute each community's centroid in the layout space.
  3. For each L0+L1 edge (s, d), build a Bezier control polyline:
        same community         →  [src, cent(c_s), dst]            (deg 2)
        different communities  →  [src, cent(c_s), cent(c_d), dst] (deg 3)
  4. De Casteljau-evaluate the curve at 8 evenly-spaced parameters
     in [0, 1] → 8 (x, y, z) samples per edge.
  5. Write bundles_l0.csv + bundles_l1.csv per preset (step15 binary-ifies).

CLI:
  python -m analysis.as_galaxy.step14_galaxy_bundle --preset economy
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from collections import defaultdict

from analysis.as_galaxy.common import (
    CACHE_DIR,
    PRESETS,
    preset_by_name,
    read_csv,
    write_csv,
    write_step_metrics,
)


# Number of samples to emit per bundled curve. The wire format reserves
# 8 × (x, y, z) so this is a contract — don't change without bumping the
# format version in step15.
SAMPLES_PER_CURVE = 8


# ---------------------------------------------------------------------------
# Louvain communities — cached once across presets
# ---------------------------------------------------------------------------

def compute_communities_igraph(nodes: list[int], edges: list[tuple[int, int]]
                               ) -> dict[int, int]:
    import igraph as ig  # noqa: WPS433
    idx_of = {asn: i for i, asn in enumerate(nodes)}
    kept = [(idx_of[s], idx_of[t]) for s, t in edges if s in idx_of and t in idx_of]
    g = ig.Graph(n=len(nodes), edges=kept, directed=False)
    g.simplify(multiple=True, loops=True)
    print(f'  [igraph] community_multilevel on |V|={g.vcount():,} '
          f'|E|={g.ecount():,}')
    t0 = time.time()
    membership = g.community_multilevel().membership
    print(f'  [igraph] {max(membership) + 1:,} communities in '
          f'{time.time() - t0:.1f}s')
    return {nodes[i]: membership[i] for i in range(len(nodes))}


def compute_communities_networkx(nodes, edges) -> dict[int, int]:
    import networkx as nx  # noqa: WPS433
    g = nx.Graph()
    g.add_nodes_from(nodes)
    g.add_edges_from(edges)
    print(f'  [networkx] louvain_communities on |V|={g.number_of_nodes():,} '
          f'|E|={g.number_of_edges():,}')
    t0 = time.time()
    coms = nx.community.louvain_communities(g, seed=42)
    print(f'  [networkx] {len(coms):,} communities in '
          f'{time.time() - t0:.1f}s')
    out: dict[int, int] = {}
    for cid, members in enumerate(coms):
        for asn in members:
            out[asn] = cid
    return out


def load_or_compute_communities(cache_dir: str) -> dict[int, int]:
    """Load communities.csv if present, else compute and persist it."""
    cpath = os.path.join(cache_dir, 'communities.csv')
    if os.path.exists(cpath):
        out: dict[int, int] = {}
        for r in read_csv(cpath):
            try:
                out[int(r['asn'])] = int(r['community'])
            except (KeyError, ValueError):
                continue
        print(f'  [cache] loaded {len(out):,} community assignments from {cpath}')
        return out

    nodes_path = os.path.join(cache_dir, 'nodes_raw.csv')
    edges_path = os.path.join(cache_dir, 'edges_raw.csv')
    nodes = []
    for r in read_csv(nodes_path):
        try:
            nodes.append(int(r['asn']))
        except (KeyError, ValueError):
            continue
    edges = []
    for r in read_csv(edges_path):
        try:
            s, d = int(r['src']), int(r['dst'])
        except (KeyError, ValueError):
            continue
        if s != d:
            edges.append((s, d))

    try:
        com = compute_communities_igraph(nodes, edges)
    except ImportError:
        print('  [warn] igraph unavailable; falling back to networkx Louvain')
        com = compute_communities_networkx(nodes, edges)

    write_csv(cpath,
              [{'asn': a, 'community': c} for a, c in sorted(com.items())],
              ['asn', 'community'])
    print(f'  [cache] wrote {cpath} ({os.path.getsize(cpath)//1024:,} KB)')
    return com


# ---------------------------------------------------------------------------
# Centroids + Bezier
# ---------------------------------------------------------------------------

def compute_centroids(community: dict[int, int],
                      pos: dict[int, tuple[float, float, float]]
                      ) -> dict[int, tuple[float, float, float]]:
    """Mean (x, y, z) per community, ignoring members that lack a position."""
    sums: dict[int, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
    for asn, cid in community.items():
        if asn not in pos:
            continue
        x, y, z = pos[asn]
        s = sums[cid]
        s[0] += x
        s[1] += y
        s[2] += z
        s[3] += 1
    return {
        cid: (s[0] / s[3], s[1] / s[3], s[2] / s[3])
        for cid, s in sums.items() if s[3] > 0
    }


def de_casteljau(points: list[tuple[float, float, float]], t: float
                 ) -> tuple[float, float, float]:
    """Evaluate a Bezier curve through `points` at parameter t ∈ [0,1].

    Pure De Casteljau, no NumPy — fine at our N (~22K edges × 8 samples).
    """
    pts = [list(p) for p in points]
    while len(pts) > 1:
        nxt = []
        omt = 1.0 - t
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            nxt.append([
                omt * a[0] + t * b[0],
                omt * a[1] + t * b[1],
                omt * a[2] + t * b[2],
            ])
        pts = nxt
    return (pts[0][0], pts[0][1], pts[0][2])


def sample_curve(control: list[tuple[float, float, float]], n: int
                 ) -> list[tuple[float, float, float]]:
    """Return n samples evenly in t = 0, 1/(n-1), ..., 1."""
    if n < 2:
        return [control[0]]
    step = 1.0 / (n - 1)
    return [de_casteljau(control, i * step) for i in range(n)]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _load_node_pos(path: str) -> dict[int, tuple[float, float, float]]:
    out: dict[int, tuple[float, float, float]] = {}
    for r in read_csv(path):
        try:
            out[int(r['asn'])] = (float(r['x']), float(r['y']), float(r['z']))
        except (KeyError, ValueError):
            continue
    return out


def _load_edges(path: str) -> list[tuple[int, int, float]]:
    out: list[tuple[int, int, float]] = []
    for r in read_csv(path):
        try:
            s, d = int(r['src']), int(r['dst'])
            w = float(r.get('weight') or 0.0)
        except (KeyError, ValueError):
            continue
        out.append((s, d, w))
    return out


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
    cache_dir = args.cache_dir
    out_dir = os.path.join(cache_dir, preset['name'])
    if not os.path.isdir(out_dir):
        print(f'[FATAL] {out_dir} missing — run step13 --preset {preset["name"]} first',
              file=sys.stderr)
        return 1
    print(f'Bundling preset={preset["name"]} → {out_dir}')

    # 1. Communities (cached, preset-independent)
    print('[1/4] Louvain communities (cached across presets)')
    community = load_or_compute_communities(cache_dir)

    # 2. Layout positions (full graph)
    layout_path = os.path.join(cache_dir, 'nodes_layout.csv')
    pos = _load_node_pos(layout_path)
    print(f'[2/4] {len(pos):,} positions loaded from {layout_path}')

    centroids = compute_centroids(community, pos)
    print(f'      {len(centroids):,} community centroids computed')

    # 3. Edges to bundle: L0 + L1 of this preset
    edges_l0 = _load_edges(os.path.join(out_dir, 'edges_l0.csv'))
    edges_l1 = _load_edges(os.path.join(out_dir, 'edges_l1.csv'))
    print(f'[3/4] edges to bundle: L0={len(edges_l0):,}  L1={len(edges_l1):,}')

    same_community = 0
    cross_community = 0
    skipped = 0

    def _bundle(edges: list[tuple[int, int, float]]) -> list[dict]:
        nonlocal same_community, cross_community, skipped
        out_rows: list[dict] = []
        for s, d, w in edges:
            if s not in pos or d not in pos:
                skipped += 1
                continue
            sp = pos[s]
            dp = pos[d]
            cs = community.get(s)
            cd = community.get(d)
            if cs is None or cd is None or cs not in centroids or cd not in centroids:
                # Communityless endpoint: degenerate to a straight line that
                # the wire format can still consume.
                control = [sp, dp]
                skipped += 1
            elif cs == cd:
                control = [sp, centroids[cs], dp]
                same_community += 1
            else:
                control = [sp, centroids[cs], centroids[cd], dp]
                cross_community += 1
            samples = sample_curve(control, SAMPLES_PER_CURVE)
            row = {'src': s, 'dst': d, 'weight': round(w, 5)}
            for i, (x, y, z) in enumerate(samples):
                row[f'x{i}'] = round(x, 5)
                row[f'y{i}'] = round(y, 5)
                row[f'z{i}'] = round(z, 5)
            out_rows.append(row)
        return out_rows

    rows_l0 = _bundle(edges_l0)
    rows_l1 = _bundle(edges_l1)

    # 4. Write per-tier bundle CSVs
    print('[4/4] writing bundles_l*.csv')
    pt_cols = []
    for i in range(SAMPLES_PER_CURVE):
        pt_cols += [f'x{i}', f'y{i}', f'z{i}']
    bundle_cols = ['src', 'dst', 'weight'] + pt_cols
    p0 = write_csv(os.path.join(out_dir, 'bundles_l0.csv'), rows_l0, bundle_cols)
    p1 = write_csv(os.path.join(out_dir, 'bundles_l1.csv'), rows_l1, bundle_cols)
    print(f'  {p0} ({os.path.getsize(p0)//1024:,} KB, {len(rows_l0):,} rows)')
    print(f'  {p1} ({os.path.getsize(p1)//1024:,} KB, {len(rows_l1):,} rows)')

    print(f'  same-community edges: {same_community:,}  '
          f'cross-community: {cross_community:,}  skipped: {skipped:,}')

    write_step_metrics(14, {
        'preset': preset['name'],
        'communities': len(set(community.values())),
        'edges_bundled_l0': len(rows_l0),
        'edges_bundled_l1': len(rows_l1),
        'same_community_edges': same_community,
        'cross_community_edges': cross_community,
        'skipped_edges': skipped,
        'samples_per_curve': SAMPLES_PER_CURVE,
        'elapsed_sec': round(time.time() - t0, 2),
    }, title_zh=f'Step 14 · 边层级捆扎 ({preset["label_zh"]})',
       title_en=f'Step 14 · Hierarchical edge bundling ({preset["label_en"]})')

    print(f'\nStep 14 ({preset["name"]}) complete in {time.time() - t0:.1f}s')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
