"""Step 12: compute a 3D force-directed layout of the full AS graph.

Reads:
  data_cache/as_galaxy/nodes_raw.csv
  data_cache/as_galaxy/edges_raw.csv
  data_cache/as_galaxy/nodes_scored.csv  (optional — only used to seed
      the top ASes at deterministic positions so layout reruns stay
      roughly consistent)

Writes:
  data_cache/as_galaxy/nodes_layout.csv  (asn, x, y, z) — unit cube [-1,1]^3

The layout is SHARED across all three presets. Presets differ only in
which subset of ASes is admitted to each LOD tier and how sprites are
sized — the positions are preset-independent.

Backend priority:
  1. graph-tool    sfdp_layout(3D)     ~5–15 min on 100K nodes  (optional, C++)
  2. igraph        layout_drl("drl_3d") ~20–40 min              (fallback)
  3. networkx      spring_layout(dim=3)  ~2–4 hours             (last resort)

Install `graph-tool` for speed:
  conda install -c conda-forge graph-tool

If only networkx is available, leave this running overnight — it's a
one-time cost per snapshot.
"""
from __future__ import annotations

import math
import os
import sys
import time

from analysis.as_galaxy.common import (
    CACHE_DIR,
    read_csv,
    write_csv,
    write_step_metrics,
)


# ---------------------------------------------------------------------------
# Backend 1: graph-tool SFDP (fastest by a wide margin)
# ---------------------------------------------------------------------------

def _layout_graph_tool(nodes, edges):
    import graph_tool.all as gt  # noqa: WPS433 — optional
    print('  [graph-tool] building graph')
    g = gt.Graph(directed=False)
    g.add_vertex(len(nodes))
    idx_of = {asn: i for i, asn in enumerate(nodes)}
    kept = [(idx_of[s], idx_of[t]) for s, t in edges if s in idx_of and t in idx_of]
    g.add_edge_list(kept)
    print(f'  [graph-tool] |V|={g.num_vertices():,} |E|={g.num_edges():,}')
    t0 = time.time()
    pos = gt.sfdp_layout(g, max_iter=0, epsilon=1e-4, dim=3)
    print(f'  [graph-tool] sfdp_layout: {time.time() - t0:.1f}s')
    out: dict[int, tuple[float, float, float]] = {}
    arr = pos.get_2d_array(range(3))  # shape (3, N)
    for i, asn in enumerate(nodes):
        out[asn] = (float(arr[0][i]), float(arr[1][i]), float(arr[2][i]))
    return out


# ---------------------------------------------------------------------------
# Backend 2: igraph DRL 3D
# ---------------------------------------------------------------------------

def _layout_igraph(nodes, edges):
    import igraph as ig  # noqa: WPS433
    print('  [igraph] building graph')
    idx_of = {asn: i for i, asn in enumerate(nodes)}
    kept = [(idx_of[s], idx_of[t]) for s, t in edges if s in idx_of and t in idx_of]
    g = ig.Graph(n=len(nodes), edges=kept, directed=False)
    g.simplify(multiple=True, loops=True)
    print(f'  [igraph] |V|={g.vcount():,} |E|={g.ecount():,}')
    t0 = time.time()
    coords = g.layout('drl_3d')  # distributed recursive layout, 3D
    print(f'  [igraph] layout_drl_3d: {time.time() - t0:.1f}s')
    out: dict[int, tuple[float, float, float]] = {}
    for i, asn in enumerate(nodes):
        x, y, z = coords[i]
        out[asn] = (float(x), float(y), float(z))
    return out


# ---------------------------------------------------------------------------
# Backend 3: networkx spring (slow, pure Python, always available)
# ---------------------------------------------------------------------------

def _layout_networkx(nodes, edges):
    import networkx as nx  # noqa: WPS433
    print('  [networkx] building graph')
    g = nx.Graph()
    g.add_nodes_from(nodes)
    g.add_edges_from(edges)
    print(f'  [networkx] |V|={g.number_of_nodes():,} |E|={g.number_of_edges():,}')
    t0 = time.time()
    # iterations=50 is the default. Increase if the result looks hairy.
    pos = nx.spring_layout(g, dim=3, k=None, iterations=50, seed=42)
    print(f'  [networkx] spring_layout: {time.time() - t0:.1f}s')
    return {asn: (float(p[0]), float(p[1]), float(p[2])) for asn, p in pos.items()}


def compute_layout(nodes, edges):
    """Try backends in order of speed; return {asn: (x, y, z)}."""
    for name, fn in (
        ('graph-tool', _layout_graph_tool),
        ('igraph',     _layout_igraph),
        ('networkx',   _layout_networkx),
    ):
        try:
            print(f'Trying layout backend: {name}')
            return name, fn(nodes, edges)
        except ImportError as e:
            print(f'  [skip] {name} unavailable ({e.name})')
            continue
    print('[FATAL] no layout backend available; install one of: '
          'graph-tool, python-igraph, networkx', file=sys.stderr)
    raise SystemExit(2)


# ---------------------------------------------------------------------------
# Post-processing: normalize to unit cube
# ---------------------------------------------------------------------------

def normalize_to_unit_cube(positions: dict[int, tuple[float, float, float]]) -> None:
    """In-place: centre at origin, scale longest axis to [-1, 1]."""
    if not positions:
        return
    xs = [p[0] for p in positions.values()]
    ys = [p[1] for p in positions.values()]
    zs = [p[2] for p in positions.values()]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    cz = (min(zs) + max(zs)) / 2
    spans = [max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)]
    scale = 2.0 / max(spans) if max(spans) > 0 else 1.0
    for asn, (x, y, z) in positions.items():
        positions[asn] = (
            (x - cx) * scale,
            (y - cy) * scale,
            (z - cz) * scale,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    t0 = time.time()
    print(f'Computing 3D layout over full graph in {CACHE_DIR}')

    nodes_path = os.path.join(CACHE_DIR, 'nodes_raw.csv')
    edges_path = os.path.join(CACHE_DIR, 'edges_raw.csv')
    if not os.path.exists(nodes_path) or not os.path.exists(edges_path):
        print(f'[FATAL] run step10 first — missing {nodes_path} / {edges_path}',
              file=sys.stderr)
        return 1

    nodes: list[int] = []
    for r in read_csv(nodes_path):
        try:
            nodes.append(int(r['asn']))
        except (ValueError, KeyError):
            continue

    edges: list[tuple[int, int]] = []
    for r in read_csv(edges_path):
        try:
            s, t = int(r['src']), int(r['dst'])
        except (ValueError, KeyError):
            continue
        if s != t:
            edges.append((s, t))

    print(f'  {len(nodes):,} nodes, {len(edges):,} edges')

    backend_name, positions = compute_layout(nodes, edges)

    # Any node that the layout backend silently dropped (because igraph
    # reindexing on extremely disconnected components can skip vertices)
    # gets jittered into the outer shell so it's not all stacked at origin.
    missing = [a for a in nodes if a not in positions]
    if missing:
        print(f'  [warn] {len(missing):,} nodes missing from backend output; '
              f'scattering on outer shell')
        import random
        rng = random.Random(42)
        for asn in missing:
            # Uniform-on-sphere with radius 1.1 (just outside unit cube).
            theta = rng.uniform(0, 2 * math.pi)
            phi = math.acos(1 - 2 * rng.random())
            r = 1.1
            positions[asn] = (
                r * math.sin(phi) * math.cos(theta),
                r * math.sin(phi) * math.sin(theta),
                r * math.cos(phi),
            )

    print('Normalizing to unit cube [-1, 1]^3')
    normalize_to_unit_cube(positions)

    rows = [
        {'asn': asn, 'x': round(x, 5), 'y': round(y, 5), 'z': round(z, 5)}
        for asn, (x, y, z) in sorted(positions.items())
    ]
    out_path = os.path.join(CACHE_DIR, 'nodes_layout.csv')
    write_csv(out_path, rows, ['asn', 'x', 'y', 'z'])
    print(f'  wrote {out_path} ({os.path.getsize(out_path)//1024:,} KB)')

    # Sanity: spread stats
    xs = [r['x'] for r in rows]
    ys = [r['y'] for r in rows]
    zs = [r['z'] for r in rows]
    print(f'  bbox: x=[{min(xs):.3f}, {max(xs):.3f}]  '
          f'y=[{min(ys):.3f}, {max(ys):.3f}]  '
          f'z=[{min(zs):.3f}, {max(zs):.3f}]')

    write_step_metrics(12, {
        'backend': backend_name,
        'nodes_laid_out': len(positions),
        'nodes_missing_from_backend': len(missing),
        'edges_used': len(edges),
        'elapsed_sec': round(time.time() - t0, 2),
    }, title_zh='Step 12 · 全图 3D 力导布局',
       title_en='Step 12 · 3D force-directed layout of the full AS graph')

    print(f'\nStep 12 complete in {time.time() - t0:.1f}s (backend: {backend_name})')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
