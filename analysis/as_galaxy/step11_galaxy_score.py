"""Step 11: compute importance scores per AS for the 3 presets.

Reads:
  data_cache/as_galaxy/nodes_raw.csv
  data_cache/as_galaxy/edges_raw.csv
  data_cache/as_galaxy/as_cone.csv   (optional, IHR Hegemony customer cone)

Writes:
  data_cache/as_galaxy/nodes_scored.csv

Columns in the output (all normalized to [0, 1] except ASN):
  asn
  v            log10(IPv4 + 1) normalized — economic scale
  prefix       log10(prefix_count + 1) normalized — announcement breadth
  kcore        k-core number normalized — structural depth
  eigen        eigenvector centrality normalized — global reach
  cone         IHR Hegemony customer-cone size normalized (0 if unavailable)
  score_economy
  score_structure
  score_reach

Dependencies: tries `igraph` first (fast C core, ~30s for k-core and
~2 min for eigenvector at 100K nodes), falls back to `networkx` (slower
but pure-Python, pip-installable).

If `as_cone.csv` is absent, the `reach` preset is re-normalized to drop
the cone component: {eigen: 0.7, kcore: 0.3}. The manifest records
`cone_available: false` so the frontend can dim the preset label.

Runtime: ~3–5 min total on 100K-node graph with igraph, ~20–30 min with
networkx fallback.
"""
from __future__ import annotations

import math
import os
import sys
import time

from analysis.as_galaxy.common import (
    CACHE_DIR,
    PRESETS,
    read_csv,
    write_csv,
    write_step_metrics,
)


# ---------------------------------------------------------------------------
# Graph-metric backends
# ---------------------------------------------------------------------------

def _load_graph_igraph(nodes: list[int], edges: list[tuple[int, int]]):
    """Build an undirected igraph.Graph with compact indices. Returns (g, idx_of)."""
    import igraph as ig  # noqa: WPS433 — deliberate optional import
    idx_of = {asn: i for i, asn in enumerate(nodes)}
    kept = []
    for s, t in edges:
        if s in idx_of and t in idx_of:
            kept.append((idx_of[s], idx_of[t]))
    g = ig.Graph(n=len(nodes), edges=kept, directed=False)
    # Dedupe parallel edges that might slip through from multi-source joins.
    g.simplify(multiple=True, loops=True)
    return g, idx_of


def _kcore_and_eigen_igraph(nodes, edges):
    g, _idx = _load_graph_igraph(nodes, edges)
    print(f'  [igraph] graph built: |V|={g.vcount():,}, |E|={g.ecount():,}')
    t0 = time.time()
    kc = g.coreness(mode='all')
    print(f'  [igraph] coreness: {time.time() - t0:.1f}s')
    t0 = time.time()
    # igraph rejects `directed=False` for undirected graphs (it's a directed-
    # only flag); the graph here is already undirected, so omit it.
    ev = g.eigenvector_centrality(scale=True)
    print(f'  [igraph] eigenvector_centrality: {time.time() - t0:.1f}s')
    return (
        {nodes[i]: kc[i] for i in range(len(nodes))},
        {nodes[i]: ev[i] for i in range(len(nodes))},
    )


def _kcore_and_eigen_networkx(nodes, edges):
    import networkx as nx  # noqa: WPS433
    g = nx.Graph()
    g.add_nodes_from(nodes)
    g.add_edges_from(edges)
    print(f'  [networkx] graph built: |V|={g.number_of_nodes():,}, '
          f'|E|={g.number_of_edges():,}')
    t0 = time.time()
    kc = nx.core_number(g)
    print(f'  [networkx] core_number: {time.time() - t0:.1f}s')
    t0 = time.time()
    # eigenvector_centrality_numpy is MUCH faster than the iterative version
    # at this scale, but it needs the full adjacency matrix in dense form —
    # 100K×100K is prohibitive. Fall back to the power iteration.
    try:
        ev = nx.eigenvector_centrality(g, max_iter=500, tol=1e-6)
    except nx.PowerIterationFailedConvergence as e:
        print(f'  [networkx] eigenvector convergence failed ({e}); '
              f'retrying with max_iter=2000')
        ev = nx.eigenvector_centrality(g, max_iter=2000, tol=1e-4)
    print(f'  [networkx] eigenvector_centrality: {time.time() - t0:.1f}s')
    return dict(kc), dict(ev)


def kcore_and_eigen(nodes, edges):
    """Try igraph first, fall back to networkx. Both return (kcore_dict, eigen_dict)."""
    try:
        return _kcore_and_eigen_igraph(nodes, edges)
    except ImportError:
        print('  [warn] igraph not available; falling back to networkx (slower)')
        return _kcore_and_eigen_networkx(nodes, edges)


# ---------------------------------------------------------------------------
# IHR Hegemony customer-cone — optional input
# ---------------------------------------------------------------------------

def load_cone() -> dict[int, float]:
    """Load {asn: cone_size} from as_cone.csv if present. Empty dict otherwise.

    Expected CSV shape: `asn,cone_size`. Any other columns are ignored.
    """
    path = os.path.join(CACHE_DIR, 'as_cone.csv')
    if not os.path.exists(path):
        return {}
    out: dict[int, float] = {}
    for r in read_csv(path):
        try:
            asn = int(r['asn'])
            val = float(r.get('cone_size') or r.get('cone') or 0)
        except (ValueError, KeyError, TypeError):
            continue
        if val > 0:
            out[asn] = val
    return out


# ---------------------------------------------------------------------------
# Normalization + scoring
# ---------------------------------------------------------------------------

def _normalize(vals: dict[int, float]) -> dict[int, float]:
    """Linear scale to [0, 1]. Returns {k: 0.0} if all values equal."""
    if not vals:
        return {}
    lo = min(vals.values())
    hi = max(vals.values())
    if hi <= lo:
        return {k: 0.0 for k in vals}
    scale = 1.0 / (hi - lo)
    return {k: (v - lo) * scale for k, v in vals.items()}


def _log_normalize(vals: dict[int, float]) -> dict[int, float]:
    """log10(x+1) then linear [0,1]. For heavy-tailed inputs (v, prefix, cone)."""
    logs = {k: math.log10(v + 1.0) for k, v in vals.items()}
    return _normalize(logs)


def _preset_score(
    preset_weights: dict[str, float],
    v: dict[int, float],
    prefix: dict[int, float],
    kcore: dict[int, float],
    eigen: dict[int, float],
    cone: dict[int, float],
    asns: list[int],
) -> dict[int, float]:
    """Weighted sum per AS, with automatic re-normalization if cone is absent."""
    w = dict(preset_weights)
    if not cone and w.get('cone', 0) > 0:
        # Drop cone from this preset and re-normalize remaining weights to sum=1.
        cone_weight = w.pop('cone', 0)
        remaining = sum(w.values())
        if remaining > 0:
            scale = 1.0 / remaining
            for k in list(w):
                w[k] *= scale
        w['cone'] = 0.0
    out: dict[int, float] = {}
    for asn in asns:
        s = (
            w.get('v', 0)      * v.get(asn, 0.0)
            + w.get('prefix', 0) * prefix.get(asn, 0.0)
            + w.get('kcore', 0)  * kcore.get(asn, 0.0)
            + w.get('eigen', 0)  * eigen.get(asn, 0.0)
            + w.get('cone', 0)   * cone.get(asn, 0.0)
        )
        out[asn] = s
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    t0 = time.time()
    print(f'Scoring ASes in {CACHE_DIR}')

    nodes_path = os.path.join(CACHE_DIR, 'nodes_raw.csv')
    edges_path = os.path.join(CACHE_DIR, 'edges_raw.csv')
    if not os.path.exists(nodes_path) or not os.path.exists(edges_path):
        print(f'[FATAL] run step10 first — missing {nodes_path} / {edges_path}',
              file=sys.stderr)
        return 1

    # --- load raw ---------------------------------------------------------
    v_raw: dict[int, float] = {}
    prefix_raw: dict[int, float] = {}
    all_asns: set[int] = set()
    for r in read_csv(nodes_path):
        try:
            asn = int(r['asn'])
        except (ValueError, KeyError):
            continue
        all_asns.add(asn)
        try:
            v_raw[asn] = float(r.get('ipv4') or 0)
        except ValueError:
            pass
        try:
            prefix_raw[asn] = float(r.get('prefix_count') or 0)
        except ValueError:
            pass

    edges: list[tuple[int, int]] = []
    for r in read_csv(edges_path):
        try:
            s, t = int(r['src']), int(r['dst'])
        except (ValueError, KeyError):
            continue
        if s == t:
            continue
        if s > t:
            s, t = t, s
        edges.append((s, t))
        all_asns.add(s)
        all_asns.add(t)

    nodes = sorted(all_asns)
    print(f'  {len(nodes):,} ASes, {len(edges):,} edges loaded')

    # --- compute graph metrics -------------------------------------------
    print('Computing k-core and eigenvector centrality ...')
    kcore_raw, eigen_raw = kcore_and_eigen(nodes, edges)

    # --- cone (optional) --------------------------------------------------
    cone_raw = load_cone()
    cone_available = bool(cone_raw)
    if cone_available:
        print(f'  [cone] IHR Hegemony cone loaded: {len(cone_raw):,} ASes')
    else:
        print('  [cone] as_cone.csv not found — reach preset will re-normalize')

    # --- normalize -------------------------------------------------------
    v_n = _log_normalize(v_raw)
    prefix_n = _log_normalize(prefix_raw)
    kcore_n = _normalize(kcore_raw)
    eigen_n = _normalize(eigen_raw)
    cone_n = _log_normalize(cone_raw) if cone_available else {}

    # --- per-preset score ------------------------------------------------
    scores: dict[str, dict[int, float]] = {}
    for p in PRESETS:
        scores[p['name']] = _preset_score(
            p['weights'], v_n, prefix_n, kcore_n, eigen_n, cone_n, nodes,
        )

    # --- write nodes_scored.csv ------------------------------------------
    fieldnames = [
        'asn', 'v', 'prefix', 'kcore', 'eigen', 'cone',
        'score_economy', 'score_structure', 'score_reach',
    ]
    rows = []
    for asn in nodes:
        rows.append({
            'asn': asn,
            'v': round(v_n.get(asn, 0.0), 6),
            'prefix': round(prefix_n.get(asn, 0.0), 6),
            'kcore': round(kcore_n.get(asn, 0.0), 6),
            'eigen': round(eigen_n.get(asn, 0.0), 6),
            'cone': round(cone_n.get(asn, 0.0), 6),
            'score_economy': round(scores['economy'].get(asn, 0.0), 6),
            'score_structure': round(scores['structure'].get(asn, 0.0), 6),
            'score_reach': round(scores['reach'].get(asn, 0.0), 6),
        })
    out_path = os.path.join(CACHE_DIR, 'nodes_scored.csv')
    write_csv(out_path, rows, fieldnames)
    print(f'  wrote {out_path} ({os.path.getsize(out_path)//1024:,} KB)')

    # --- print top-10 per preset as a sanity check -----------------------
    # Try to look up names from nodes_raw for readability.
    name_by_asn: dict[int, str] = {}
    for r in read_csv(nodes_path):
        try:
            name_by_asn[int(r['asn'])] = r.get('name') or ''
        except (ValueError, KeyError):
            continue
    for p in PRESETS:
        key = f'score_{p["name"]}'
        top = sorted(scores[p['name']].items(), key=lambda kv: -kv[1])[:10]
        print(f'\n  Top 10 by {p["label_zh"]} ({p["name"]}):')
        for asn, s in top:
            print(f'    {s:.4f}  AS{asn:<7} {name_by_asn.get(asn, "")[:55]}')

    write_step_metrics(11, {
        'nodes': len(nodes),
        'edges': len(edges),
        'cone_available': cone_available,
        'cone_nodes': len(cone_raw),
        'presets': [p['name'] for p in PRESETS],
        'elapsed_sec': round(time.time() - t0, 2),
    }, title_zh='Step 11 · 计算 AS 三维重要度评分',
       title_en='Step 11 · Score ASes across the 3 presets')

    print(f'\nStep 11 complete in {time.time() - t0:.1f}s')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
