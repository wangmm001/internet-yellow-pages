"""Smoke test for P1 (step11 + step12).

Skips step10 (needs Neo4j or a ~50 MB download). Instead, generates a
synthetic power-law-ish graph of ~200 ASes, writes it to a temp
CACHE_DIR as if step10 had produced it, then runs step11 and step12
as subprocesses (so env-override of IYP_AS_GALAXY_CACHE_DIR sticks)
and verifies their outputs look sensible.

Usage:
  python -m analysis.as_galaxy.smoke_test

Exits 0 on success, non-zero on any problem. Safe to include in CI.
Does not touch the real CACHE_DIR or DATA_DIR.
"""
from __future__ import annotations

import os
import random
import subprocess
import sys
import tempfile

from analysis.as_galaxy.common import read_csv, write_csv


SYNTHETIC_N = 200
SYNTHETIC_M = 3   # Barabási–Albert edges per new node


# ---------------------------------------------------------------------------
# Synthetic graph generator — Barabási-Albert preferential attachment so the
# degree distribution is power-law-ish, like the real AS graph
# ---------------------------------------------------------------------------

def _synthetic_graph(n: int, m: int, seed: int = 42):
    """Return (nodes, edges) where nodes is a list of (asn, cc, name, v, pc).

    ASNs start at 1000 to stay out of the reserved space. A handful of
    well-known ASNs (174, 3356, 15169, 13335) are injected so the smoke
    test output includes recognisable names when visually inspected.
    """
    rng = random.Random(seed)
    # Barabási-Albert
    adj: dict[int, set[int]] = {}
    nodes_list: list[int] = []
    # seed with a complete graph on m nodes
    for i in range(m):
        adj[i] = set()
    for i in range(m):
        for j in range(i + 1, m):
            adj[i].add(j)
            adj[j].add(i)
    nodes_list = list(range(m))

    def pick_attachment_target():
        # Weighted by current degree (preferential attachment).
        weights = [len(adj[v]) or 1 for v in nodes_list]
        total = sum(weights)
        r = rng.uniform(0, total)
        acc = 0
        for v, w in zip(nodes_list, weights):
            acc += w
            if acc >= r:
                return v
        return nodes_list[-1]

    for i in range(m, n):
        adj[i] = set()
        for _ in range(m):
            tgt = pick_attachment_target()
            if tgt != i and tgt not in adj[i]:
                adj[i].add(tgt)
                adj[tgt].add(i)
        nodes_list.append(i)

    # Assign ASNs with a few well-known ones sprinkled in for sanity
    sentinel_asns = [174, 3356, 15169, 13335, 16509, 2914]
    sentinel_names = {
        174:   'COGENT-174 - Cogent Communications, LLC',
        3356:  'LEVEL3 - Level 3 Parent, LLC',
        15169: 'GOOGLE - Google LLC',
        13335: 'CLOUDFLARENET - Cloudflare, Inc.',
        16509: 'AMAZON-02 - Amazon.com, Inc.',
        2914:  'NTT-DATA-2914 - NTT America, Inc.',
    }
    # top-degree nodes get the sentinel ASNs (so scores surface them)
    by_deg = sorted(nodes_list, key=lambda v: -len(adj[v]))
    idx_to_asn: dict[int, int] = {}
    for i, v in enumerate(by_deg):
        if i < len(sentinel_asns):
            idx_to_asn[v] = sentinel_asns[i]
        else:
            idx_to_asn[v] = 100000 + v  # synthetic high ASNs, no collision

    ccs = ['US', 'CN', 'JP', 'DE', 'GB', 'FR', 'NL', 'IN', 'BR']
    nodes_rows = []
    for v in nodes_list:
        asn = idx_to_asn[v]
        nodes_rows.append({
            'asn': asn,
            'cc': rng.choice(ccs),
            'name': sentinel_names.get(asn, f'synthetic-as-{asn}'),
            # v (IPv4) is heavy-tailed: big with probability ∝ degree
            'ipv4': int(len(adj[v]) ** 2 * rng.uniform(100, 10000)),
            'prefix_count': max(1, len(adj[v]) // 2),
        })
    edges_set: set[tuple[int, int]] = set()
    for v, ns in adj.items():
        for u in ns:
            a, b = idx_to_asn[v], idx_to_asn[u]
            if a > b:
                a, b = b, a
            edges_set.add((a, b))
    edges_rows = [{'src': s, 'dst': d} for s, d in sorted(edges_set)]
    return nodes_rows, edges_rows


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def _run_step(step_mod: str, cache_dir: str, data_dir: str) -> None:
    """Run a step as a subprocess with dirs overridden to the temp sandbox."""
    env = dict(os.environ)
    env['IYP_AS_GALAXY_CACHE_DIR'] = cache_dir
    env['IYP_AS_GALAXY_DATA_DIR'] = data_dir
    cmd = [sys.executable, '-m', step_mod]
    print(f'\n$ {" ".join(cmd)}  (cache={cache_dir}, data={data_dir})')
    res = subprocess.run(cmd, env=env, check=False)
    if res.returncode != 0:
        raise SystemExit(f'{step_mod} exited {res.returncode}')


def main() -> int:
    print(f'=== as_galaxy P1 smoke test — N={SYNTHETIC_N}, m={SYNTHETIC_M} ===')
    with tempfile.TemporaryDirectory(prefix='as_galaxy_smoke_') as tmp:
        cache_dir = os.path.join(tmp, 'cache')
        data_dir  = os.path.join(tmp, 'data')
        os.makedirs(cache_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)
        print(f'Temp cache: {cache_dir}\nTemp data:  {data_dir}')

        # --- 1. Generate synthetic CSVs that look like step10 output ------
        nodes, edges = _synthetic_graph(SYNTHETIC_N, SYNTHETIC_M)
        write_csv(os.path.join(cache_dir, 'nodes_raw.csv'), nodes,
                  ['asn', 'cc', 'name', 'ipv4', 'prefix_count'])
        write_csv(os.path.join(cache_dir, 'edges_raw.csv'), edges, ['src', 'dst'])
        print(f'Wrote synthetic nodes_raw.csv ({len(nodes)}) + '
              f'edges_raw.csv ({len(edges)})')

        # --- 2. Run step11 (scoring) --------------------------------------
        _run_step('analysis.as_galaxy.step11_galaxy_score', cache_dir, data_dir)
        scored_path = os.path.join(cache_dir, 'nodes_scored.csv')
        assert os.path.exists(scored_path), 'step11 did not emit nodes_scored.csv'
        scored = list(read_csv(scored_path))
        assert len(scored) == len(nodes), (
            f'nodes_scored.csv row count {len(scored)} != expected {len(nodes)}'
        )
        # Spot-check required columns
        required_cols = {
            'asn', 'v', 'prefix', 'kcore', 'eigen', 'cone',
            'score_economy', 'score_structure', 'score_reach',
        }
        got_cols = set(scored[0].keys()) if scored else set()
        assert required_cols <= got_cols, (
            f'nodes_scored.csv missing columns: {required_cols - got_cols}'
        )
        # All scores should be in [0, ~1] (re-normalized preset weights sum to 1)
        for r in scored:
            for k in ('score_economy', 'score_structure', 'score_reach'):
                val = float(r[k])
                assert -0.01 <= val <= 1.01, f'{k} out of range for AS{r["asn"]}: {val}'

        # --- 3. Run step12 (layout) ---------------------------------------
        _run_step('analysis.as_galaxy.step12_galaxy_layout', cache_dir, data_dir)
        layout_path = os.path.join(cache_dir, 'nodes_layout.csv')
        assert os.path.exists(layout_path), 'step12 did not emit nodes_layout.csv'
        laid_out = list(read_csv(layout_path))
        assert len(laid_out) == len(nodes), (
            f'nodes_layout.csv row count {len(laid_out)} != expected {len(nodes)}'
        )
        xs = [float(r['x']) for r in laid_out]
        ys = [float(r['y']) for r in laid_out]
        zs = [float(r['z']) for r in laid_out]
        # Normalized to unit cube
        for vs, axis in ((xs, 'x'), (ys, 'y'), (zs, 'z')):
            assert min(vs) >= -1.2 and max(vs) <= 1.2, (
                f'{axis} range [{min(vs):.3f}, {max(vs):.3f}] escapes expected bounds'
            )
        # And they shouldn't all be zero (layout actually did something)
        spread = (max(xs) - min(xs)) + (max(ys) - min(ys)) + (max(zs) - min(zs))
        assert spread > 0.1, f'layout too flat (spread={spread:.4f})'

        print('\n=== ALL CHECKS PASSED ===')
        print(f'  {len(nodes)} nodes · {len(edges)} edges')
        print(f'  score_economy top:   '
              + ', '.join(f'AS{r["asn"]}={float(r["score_economy"]):.3f}'
                          for r in sorted(scored,
                                          key=lambda r: -float(r['score_economy']))[:3]))
        print(f'  score_structure top: '
              + ', '.join(f'AS{r["asn"]}={float(r["score_structure"]):.3f}'
                          for r in sorted(scored,
                                          key=lambda r: -float(r['score_structure']))[:3]))
        print(f'  score_reach top:     '
              + ', '.join(f'AS{r["asn"]}={float(r["score_reach"]):.3f}'
                          for r in sorted(scored,
                                          key=lambda r: -float(r['score_reach']))[:3]))
        print(f'  layout bbox x=[{min(xs):.2f},{max(xs):.2f}] '
              f'y=[{min(ys):.2f},{max(ys):.2f}] '
              f'z=[{min(zs):.2f},{max(zs):.2f}]')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
