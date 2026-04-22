# 全局 AS 星图 · Galaxy View

Technical design for a **new** page that visualises the full global AS graph
(~80–110 K nodes, ~500K–1M peering edges) without breaking the existing
`as_force.html` / `as_globe.html` / `as_strata.html` views.

Author: design doc for review — **not yet implemented**.

---

## 0. Scope

- **New page only**. Zero changes to `step01`–`step05`, zero changes to
  `as_force.html`, `as_globe.html`, `as_strata.html`, and the IYP
  `as_globe/data/` directory. Everything in this doc lives under a new
  `analysis/as_galaxy/` module and a new `html/as_galaxy.html` artifact.
- **Offline-first**: all layout, scoring, tiling, and bundling happen in
  Python at build time. The browser does no physics.
- **Static hosting**: output is a set of binary files + one HTML, served
  as plain static assets. No server-side rendering, no runtime Neo4j
  dependency, no backend API.
- **Desktop-only**. Mobile is a non-goal; viewports <720 px get a banner
  redirecting to `as_force.html` (which works at 5 K).

## 1. Goals & non-goals

### Goals

| G1 | Render ~100 K ASes at 60 fps on a 2019-era laptop. |
| G2 | Deliver first visual within 500 ms (L0 skeleton only). |
| G3 | LOD so zoom-in reveals progressively more long-tail ASes; zoom-out falls back to skeleton. |
| G4 | Edge rendering that shows real connectivity (not just a ball of noise) at every LOD. |
| G5 | Feature parity with `as_force.html` finder: search, provider chips, pulsing Saturn halo, tooltip. |
| G6 | All data reproducible by re-running the Python pipeline. |

### Non-goals

- Runtime physics / force simulation. Layout is frozen at build time.
- Streaming updates / live data. Snapshot == build-time snapshot.
- Directed graph semantics. Peering is undirected; customer-cone arrows are future work.
- Browsers without WebGL2. Target is evergreen Chromium/Firefox/Safari 16+.

## 2. Scale assumptions

Cross-checked against CAIDA AS-Rank, IHR, and IYP's own PEERS_WITH count:

| Metric | Value | Source |
|---|---|---|
| Announcing ASes | **~100 K** | CAIDA AS-Rank 2025-Q1 |
| Stable peering edges (undirected) | **~700 K** | BGPKit as2rel-v4 snapshot 2026-04 |
| Top decile by customer cone | ~10 K | IHR Hegemony |
| Tier-1 / core (k-core ≥ 200) | ~300 | our own `step08_k_core` |
| Leaf ASes (k-core = 1, single provider) | ~45 K | measured |

Storage bound per AS in the wire format:
- ASN (u32) + pos3 (3× f32) + radius (f32) + region (u8) + tier (u8) + padding = **32 bytes**.
  → 100 K AS × 32 B = **3.2 MB node data**.
- Edge: src_idx (u32) + dst_idx (u32) + weight (f32) = **12 B**.
  → 700 K × 12 B = **8.4 MB edge data**.

Gross total raw: **~11.6 MB**. After splitting into LOD tiers and compressing
cross-tile edges, the initial payload can drop to **<100 KB** (see §7).

## 3. Architecture overview

```
┌──────────────────────────────────────────────────────────────┐
│  BUILD TIME (Python, run on server with Neo4j + big RAM)     │
│                                                              │
│  step10_galaxy_extract ─┐                                    │
│   pulls (:AS)-[:PEERS_WITH]-(:AS) + :NAME + :COUNTRY         │
│                         │                                    │
│  step11_galaxy_score ───┤ importance rank (k-core + IPv4 +   │
│                         │   eigenvector + cone size)         │
│                         │                                    │
│  step12_galaxy_layout ──┤ force-atlas / sfdp → (x,y,z) ∈ R³  │
│                         │                                    │
│  step13_galaxy_tiles ───┤ LOD pyramid + octree tiling        │
│                         │                                    │
│  step14_galaxy_bundle ──┤ edge bundling (HEB over Louvain)   │
│                         │                                    │
│  step15_galaxy_export ──┘ binary tile files + manifest.json  │
│                                                              │
│  → analysis/as_galaxy/data/                                  │
│     ├── manifest.json                                        │
│     ├── L0.bin          (500 nodes, 2 K edges, ~30 KB)       │
│     ├── L1.bin          (5 K nodes, 20 K edges, ~500 KB)     │
│     ├── L2/tile_<oct>.bin  ~64 files, ~150 KB each           │
│     ├── L3/tile_<oct>.bin  ~512 files, ~80 KB each           │
│     └── bundles.bin     pre-bundled curves for L1+L2         │
└──────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  RUNTIME (Browser, no server)                                │
│                                                              │
│  as_galaxy.html                                              │
│   ├─ Three.js scene (OrbitControls, no d3-force)             │
│   ├─ InstancedBufferGeometry × 1 for ALL nodes (sprite)      │
│   ├─ LineSegments × 1 for current LOD edges                  │
│   ├─ LODController — chooses tier from camera distance       │
│   ├─ TileStream    — fetch()s tiles, merges into GPU buffers │
│   ├─ FinderPanel   — search + provider chips + halo layer    │
│   └─ StatsPanel    — N loaded / N total, tier, frame time    │
└──────────────────────────────────────────────────────────────┘
```

## 4. Data pipeline (Python)

New module **`analysis/as_galaxy/`**, parallel to `as_globe/`. Shares nothing
at runtime; may import `as_globe/common.py` for colour palette and region
bucketing.

### 4.1 step10_galaxy_extract.py

```python
# Pulls the full AS graph from IYP Neo4j (falls back to BGPKit + NRO if
# Neo4j is unavailable, same pattern as as_globe/step01_extract_bgpkit.py).
#
# Output (data_cache/as_galaxy/):
#   nodes_raw.csv  (asn, cc, name, ipv4)            ~100 K rows
#   edges_raw.csv  (src, dst)  src < dst, deduped   ~700 K rows
```

Rough Neo4j load: ~2 min over bolt, ~400 MB RAM peak.
BGPKit fallback: ~8 min (pfx2as + as2rel + asnames + nro).

### 4.2 step11_galaxy_score.py

Computes **three** importance scores per AS — one per preset — used to
(a) rank-order nodes for LOD admission and (b) set sprite size. Components
are computed once and normalised to [0,1]; presets differ only in how
they're weighted:

| Component | Source | Meaning |
|---|---|---|
| `v` | `log10(IPv4 advertised + 1)` | economic scale |
| `prefix` | `log10(prefix_count + 1)` | announcement breadth |
| `kcore` | `igraph.coreness()` | structural depth in peering fabric |
| `eigen` | `igraph.eigenvector_centrality()` (tol 1e-6) | global reach in peering graph |
| `cone` | IHR Hegemony customer cone size (if available) | transit reach |

**Preset weights:**

| Preset | zh / en label | v | prefix | kcore | eigen | cone | Visual emphasis |
|---|---|---|---|---|---|---|---|
| `economy`   | 经济 / Economy     | **0.60** | 0.20 | 0.10 | 0.10 | 0.00 | Hyperscale clouds + large ISPs (Amazon, Lumen, Google) dominate |
| `structure` | 结构 / Structure   | 0.15 | 0.05 | **0.50** | **0.30** | 0.00 | IXP-dense and richly-peered ASes rise — European transit hubs jump |
| `reach`     | 到达度 / Reach     | 0.10 | 0.00 | 0.20 | **0.30** | **0.40** | Tier-1 transit (Cogent, Telia, NTT) and global CDN anchors dominate |

If `cone` data isn't available (no IHR integration on server), `reach`
gracefully falls back to `{eigen: 0.7, kcore: 0.3}`. Recorded in manifest.

Output: `nodes_scored.csv` with columns
`(asn, v, prefix, kcore, eigen, cone, score_economy, score_structure, score_reach)`.
Downstream steps (step13, step14, step15) run **once per preset** using one
of the three score columns; same `nodes_layout.csv` feeds all three.

### 4.3 step12_galaxy_layout.py

3D spring-embedder over the full graph, run **once, offline**. Layout is
**shared across all three presets** — presets differ in which nodes are
admitted to L0/L1/L2/L3 and how sprites are sized, but every AS sits at
the same coordinates regardless of preset. This keeps the doubled bake
cost of multi-preset tiling manageable: only step13–15 re-run per preset,
not step12.

- Library: `graph-tool` if installed (SFDP in C++, ~15 min for 100K nodes);
  fallback to `networkx.spring_layout` with `scipy.sparse` matrices
  (~2 hours, acceptable for offline).
- Output dimensions: unit cube `[-1, 1]³` (normalised after convergence).
- Seed tier-1 / top-100 AS with fixed angular positions (golden-ratio sphere)
  to bias the cluster centres toward a visually interpretable arrangement
  (cn/na/ea/eu roughly separate hemispheres).
- Persist: `nodes_layout.csv (asn, x, y, z)`.

**Why not use d3-force runtime**: at 100 K nodes d3-force needs 30+ s of
simulation per page load, which is incompatible with our <500 ms first-paint
goal. Static layout is computed once, cached in the tile files.

### 4.4 step13_galaxy_tiles.py

**Runs once per preset.** Partitions nodes into LOD tiers by that preset's
score percentile, then octree-partitions L2 and L3 by position:

```
L0: top 500 by preset.score          →  1 file (always loaded)
L1: top 5 000                        →  1 file (load on first interaction)
L2: top 30 000                       →  64 octree cells (streamed)
L3: all 100 000                      →  512 octree cells (streamed)
```

Edges are assigned to the **highest LOD both endpoints are present in**.
Edges crossing octree tiles are stored in the "parent" file (higher LOD)
to avoid duplicate renders.

Switching presets is effectively switching which ~30 K ASes are "zoomed
in to you first" — a tier-1 like AS174 Cogent is in L0 under every
preset, but a strongly-peered but small-IPv4 AS like AS1103 SURFnet
appears in L1 under `structure`, in L2 under `economy`.

### 4.5 step14_galaxy_bundle.py

**Runs once per preset.** Hierarchical Edge Bundling (HEB) using Louvain
communities as the hierarchy:

1. Run `igraph.community_multilevel()` → ~1 K communities (Louvain output
   is preset-independent — same edges go in, same communities come out —
   but we re-key edges by each preset's L0/L1 node membership).
2. Build a community centroid tree (3 levels: community → super-community → root).
3. For each edge in L0+L1 (of the current preset): route through parent
   community centroids using a Bezier-weighted path with 8 control points.
4. Serialise curves as `(edge_src, edge_dst, pts[8][3])`.

L2 and L3 edges stay as straight lines — bundling cost is O(E · nodes_in_path)
and becomes prohibitive past ~50 K edges. At zoomed-in L2/L3 ranges, straight
lines are visually acceptable because they're short.

### 4.6 step15_galaxy_export.py

Emits the binary tile files. **Format spec** (little-endian throughout):

```
┌─ HEADER (32 B) ─────────────────────────────────────────┐
│ u32  magic       0x47414C58 "GALX"                       │
│ u8   version     0x01                                    │
│ u8   tier        L0=0, L1=1, L2=2, L3=3                  │
│ u8   region_mask bits [0..4] = cn,na,ea,eu,ot            │
│ u8   reserved                                            │
│ u32  tile_id     packed octree address (0 for L0/L1)     │
│ f32  bbox_min_x  \                                       │
│ f32  bbox_min_y   |  axis-aligned bounding box in the    │
│ f32  bbox_min_z   |  same unit-cube space as layout      │
│ f32  bbox_max_x   |                                       │
│ f32  bbox_max_y   |                                       │
│ f32  bbox_max_z  /                                       │
│ u32  node_count                                          │
│ u32  edge_count                                          │
│ u32  bundle_count  (curves, only set in L0/L1)           │
└──────────────────────────────────────────────────────────┘

┌─ NODE BLOCK (32 B × node_count) ────────────────────────┐
│ u32  asn                                                 │
│ f32  x                                                   │
│ f32  y                                                   │
│ f32  z                                                   │
│ f32  radius       sprite size, pre-computed from score   │
│ u8   region       0..4 (cn/na/ea/eu/ot)                  │
│ u8   tier_in      0..3 — L of first appearance           │
│ u8   cc[2]        ISO 3166-1 alpha-2                     │
│ u8   name_len                                            │
│ char name[name_len]   ← variable length, max 63          │
│ (padded to 32-byte boundary)                             │
└──────────────────────────────────────────────────────────┘

┌─ EDGE BLOCK (12 B × edge_count) ────────────────────────┐
│ u32  src_asn                                             │
│ u32  dst_asn                                             │
│ f32  weight      ≈ min(log10(v_src), log10(v_dst))      │
└──────────────────────────────────────────────────────────┘

┌─ BUNDLE BLOCK (100 B × bundle_count, optional) ─────────┐
│ u32  src_asn                                             │
│ u32  dst_asn                                             │
│ f32  weight                                              │
│ f32  pts[8][3]   24 × 4 = 96 B, bezier control points   │
└──────────────────────────────────────────────────────────┘
```

**Alignment**: 32-byte node block chosen so we can `DataView` it straight
into a packed Float32Array for the GPU instance buffer without reshuffling.

**Variable name lengths**: handled by reading `name_len` then skipping to
the next 32-B boundary. Names are truncated at 63 chars by the exporter.

### 4.7 manifest.json

```json
{
  "version": 1,
  "snapshot_date": "2026-04-22",
  "source": "iyp + bgpkit + asnames",
  "presets": {
    "economy": {
      "label_zh": "经济", "label_en": "Economy",
      "weights": {"v":0.6, "prefix":0.2, "kcore":0.1, "eigen":0.1, "cone":0.0},
      "dir": "economy",
      "tiers": {
        "L0": {"file": "L0.bin", "nodes": 500, "edges": 2000, "bundles": 2000},
        "L1": {"file": "L1.bin", "nodes": 5000, "edges": 20000, "bundles": 20000},
        "L2": {"dir":  "L2", "tiles": 64},
        "L3": {"dir":  "L3", "tiles": 512}
      }
    },
    "structure": {
      "label_zh": "结构", "label_en": "Structure",
      "weights": {"v":0.15, "prefix":0.05, "kcore":0.5, "eigen":0.3, "cone":0.0},
      "dir": "structure",
      "tiers": { /* same shape */ }
    },
    "reach": {
      "label_zh": "到达度", "label_en": "Reach",
      "weights": {"v":0.1, "prefix":0.0, "kcore":0.2, "eigen":0.3, "cone":0.4},
      "dir": "reach",
      "tiers": { /* same shape */ }
    }
  },
  "default": "economy",
  "octree": {"depth": 3, "bbox": [[-1,-1,-1],[1,1,1]]},
  "total_nodes": 98437,
  "total_edges": 683210,
  "cone_available": true
}
```

Browser fetches `manifest.json` first, derives tile URLs from
`presets[<current>].dir`, never hardcodes paths. Switching presets is
a matter of re-pointing the tile loader at a different directory; the
scene graph itself clears and reloads from L0.

## 5. Frontend (Three.js, ~1200 LOC total)

**No 3d-force-graph**. We stop using it here — it's great for up to ~5K
with runtime physics, and fighting against it at 100 K is harder than
rolling the scene ourselves.

### 5.1 Scene layout

```
scene
├── nodeMesh: THREE.InstancedMesh
│     geometry = PlaneBufferGeometry(1, 1)
│     material = ShaderMaterial (sprite shader, see 5.2)
│     instanceMatrix    Float32Array[N × 16]  (position + scale)
│     instanceColor     Float32Array[N × 3]   (per-region palette)
│     instanceASN       Uint32Array[N]        (for picking, via custom attr)
│
├── edgeLines: THREE.LineSegments   (straight edges, L2/L3)
│     positions  Float32Array[2E × 3]
│     colors     Float32Array[2E × 3]
│
├── edgeCurves: THREE.LineSegments  (bundled curves, L0/L1)
│     positions  Float32Array[8E × 3]  8 samples per bezier
│     (indexed so consecutive segments share endpoints)
│
└── haloLayer: DOM overlay (same as current force view)
```

### 5.2 Node shader (sprite)

Pure GLSL shader producing a soft circular sprite with region-tinted centre
and a brighter ring for hover/focus state. ~40 lines of GLSL. Key tricks:
- Billboard via `modelViewMatrix * vec4(position, 1)` with `-z` facing.
- `gl_FragColor.a = smoothstep(0.5, 0.3, length(uv - 0.5))` — soft disk.
- Uniform `uHighlight[16]` — up to 16 focused nodes' indices; compared in
  fragment shader to add a yellow rim (saves a separate halo pass for the
  common case).
- Alpha-to-coverage on, depth-test on, additive blending off (regular alpha).

### 5.3 LOD controller

```
camera_altitude = |camera.position - scene_origin|

L0  if camera_altitude > 2.5   (zoomed way out, tier-1 skeleton only)
L1  if camera_altitude > 1.0
L2  if camera_altitude > 0.3
L3  otherwise                 (zoomed in close)
```

Hysteresis: require altitude to cross threshold by 10% before tier change,
prevents flicker when user is parking at a boundary.

### 5.4 Tile streaming

- On LOD change, compute the set of octree cells whose bbox intersects
  (frustum ∪ camera-sphere-of-radius-2r).
- Diff against currently-loaded set → `toLoad` / `toEvict`.
- `toLoad`: `fetch(tile_url)` as `ArrayBuffer`, parse with `DataView`,
  upload to GPU buffers by **appending** to existing instance arrays
  (no reallocation unless we overflow the pre-allocated 200K slot cap).
- `toEvict`: memory pressure only — browsers typically don't, but we
  evict LRU tiles past ~150 MB GPU buffer usage.
- All async. UI thread never blocked past 8 ms for a tile load.

### 5.5 Picking

Not raycasting (too slow for 100K instances). Instead:
- Render a separate **hit-test pass** once per second into an offscreen
  R32UI render target where each fragment is the `instanceASN`. Read the
  pixel under cursor on hover.
- Or, cheap alternative: CPU-side BVH over loaded-tile bboxes, refined by
  per-tile KD-tree, lookup on `mousemove` (throttled to 10 Hz). Benchmark
  both; ship the one that holds 60 fps with a fast-moving cursor.

## 6. Finder parity + preset switcher

Reuse the exact UX from `as_force.html`:
- Top-centre panel with search input + two groups of chips.
- Saturn halo layer with multi-halo + baked-radius diameter.
- Global Enter/Esc keybindings.
- Provider ASN lists (`PROVIDER_GROUPS`).

The only diff: halos compute size from the **baked radius** in the node
block, not from `nodeVal^(1/3)`, because there's no `.nodeVal` accessor
in the raw Three.js path.

**New: preset segmented control.** A three-way selector sits in the
stats panel (top-right):

```
视角  · View:  [ 经济 |  结构  | 到达度 ]
              Economy  Structure  Reach
```

- Clicking a preset chip:
  1. Tears down current scene (instance buffers cleared, edge lines emptied).
  2. Switches `TileStream` base URL to the preset's tile dir.
  3. Re-fetches L0 from the new preset — typically <30 KB, <250 ms.
  4. Restores camera position (presets share layout, so "where you were
     looking" stays meaningful).
  5. Re-applies the active search/focus set via ASN lookup in the new
     node pool. ASes not admitted at the current LOD in the new preset
     fall back to their focus row in the stats panel without a halo.

Persistent selection: remembered via `localStorage['as_galaxy.preset']`
so the user's last choice loads on next visit.

Optional extension (not in v1): "custom" preset that takes weight
sliders — not worth the build-time cost unless users ask.

## 7. Initial load budget

| Phase | Time | Network | Displayed |
|---|---|---|---|
| 0 ms | — | 0 B | blank canvas + overlay skeleton |
| 80 ms | `manifest.json` fetched | ~2 KB | overlay chips populated (no nodes yet) |
| 250 ms | `L0.bin` fetched + parsed + uploaded | ~30 KB | **500 tier-1 nodes visible** |
| 500 ms | layout stabilised, first paint complete | — | full tier-1 skeleton + 2K bundled edges |
| 1.5 s (opt.) | `L1.bin` prefetched on idle | ~500 KB | 5K nodes, 20K edges — pre-load for zoom |
| 3 s+ | L2/L3 tiles stream as user zooms | variable | |

**Total cold-start transfer** to "page feels alive": **~35 KB**, way below
the current 1.9 MB as_force.html. Good for slow connections.

## 8. Performance budgets

| Item | Budget | Current force (5K) | Galaxy target |
|---|---|---|---|
| First paint | 500 ms | ~800 ms | 250 ms |
| Interactive (can zoom) | 1.5 s | ~1.2 s | 500 ms |
| Steady-state FPS | 60 | 60 | 60 @ L0/L1, 45+ @ L3 |
| Heap at steady state | <250 MB | ~80 MB | ~200 MB (all L2+L3 loaded) |
| Zoom-in new-tile latency | 100 ms | n/a | 50–100 ms |

Measurement plan: Chrome DevTools Performance + `performance.mark` at key
transitions; sampled each CI build against a headless Puppeteer script.

## 9. Navigation integration

Add one new entry to `analysis/web/site/globe/` (the existing site frame):

```
globe/
├── index.html
├── strata/      (current)
├── globe/       (current)
├── force/       (current)
└── galaxy/      (NEW)  ← iframe wrapper for html/as_galaxy.html
```

TOC in `analysis/web/site_build.py` (or wherever `toc-link` entries live)
gets one new row:

```html
<a class="toc-link" href="../../globe/galaxy/index.html">
  <span class="n">▸</span>
  <span>全景星图 · Galaxy</span>
</a>
```

No changes to existing TOC entries; strictly additive.

## 10. Phased implementation

| Phase | Artefacts | Python LOC | JS LOC | Estimated time |
|---|---|---|---|---|
| **P0** | This design doc | — | — | done on approval |
| **P1** | `step10` + `step11` + `step12` + smoke test | ~500 | 0 | 1–2 sessions |
| **P2** | `step13` + `step14` + `step15` + binary spec validator; each step driven by a `--preset {economy,structure,reach}` flag and run 3× | ~450 | 0 | 1 session |
| **P3** | `as_galaxy.html` bootstrap, InstancedMesh + sprite shader, load L0 statically | 0 | ~500 | 1 session |
| **P4** | LOD controller + tile streaming + octree culling | 0 | ~400 | 1 session |
| **P5** | Edge rendering (straight + bundled) | 0 | ~300 | 0.5 session |
| **P6** | Finder + halo + stats panel parity + preset switcher | 0 | ~450 | 0.5 session |
| **P7** | Navigation entry + TOC + iframe wrapper | 0 | ~50 | 0.25 session |

Total: **~900 LOC Python**, **~1 650 LOC JS**, ~5–7 working sessions.

## 11. Risks & mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `graph-tool` not installable on target server | medium | delays layout by ~10× | fall back to `networkx.spring_layout` with `scipy.sparse`, run overnight |
| 100 K-node layout converges to a hairball | medium | UX unusable | seed top-100 at fixed golden-spiral positions; run t-SNE on eigenvector centrality as a re-projection sanity check |
| HEB on 22 K edges takes too long | low | build-time cost | bundle only L0+L1 (~22 K); L2/L3 stay straight |
| Tile fetch storm at fast zoom | medium | FPS drop | rate-limit to 4 concurrent fetches; prioritise frustum centre |
| GPU instance buffer overflow | low | visual artefact | pre-allocate 200 K node slots; compact-on-evict |
| Picking slow at 100 K instances | high | hover feels sluggish | CPU BVH + 10 Hz throttle (no raycasting). Benchmark first. |
| Neo4j server cycle / BGPKit format drift | low | broken pipeline | both paths covered; ship a checked-in synthetic 10 K-node fixture for CI |
| Manifest schema evolution | low | future format break | `version` field + migration notes in manifest |

## 12. Open questions

Resolved in review (2026-04-22):
- ✅ **Importance metric**: 3 presets — Economy / Structure / Reach
  (see §4.2 for weights). User picks at runtime via a segmented control.
- ✅ **Mobile**: non-goal. Desktop-only. A single breakpoint-driven
  banner on `<720px` viewports redirects to `as_force.html` for the 5K
  experience.

Still open:
- **Colour hierarchy**: today we colour by region bucket (cn/na/ea/eu/ot).
  At 100 K nodes, showing k-core depth via luminance might read better
  than 5 flat region colours. Worth a v2 experiment — decide after P5
  when we can A/B it.

---

## Appendix A: file layout after implementation

```
analysis/
├── as_globe/                         (unchanged)
│   ├── step01–step05_*.py
│   ├── common.py
│   ├── data/
│   └── html/
│       ├── as_force.html
│       ├── as_globe.html
│       └── as_strata.html
│
└── as_galaxy/                        (NEW — this design)
    ├── DESIGN_GALAXY.md              ← this file
    ├── common.py                     small; imports as_globe/common for palette
    ├── step10_galaxy_extract.py
    ├── step11_galaxy_score.py
    ├── step12_galaxy_layout.py
    ├── step13_galaxy_tiles.py
    ├── step14_galaxy_bundle.py
    ├── step15_galaxy_export.py
    ├── data/
    │   ├── manifest.json                ← lists all 3 presets + tiers
    │   ├── economy/
    │   │   ├── L0.bin
    │   │   ├── L1.bin
    │   │   ├── L2/tile_*.bin
    │   │   ├── L3/tile_*.bin
    │   │   └── bundles.bin
    │   ├── structure/
    │   │   └── ...   (same shape)
    │   └── reach/
    │       └── ...   (same shape)
    └── html/
        └── as_galaxy.html
```

## Appendix B: browser support matrix

Desktop-only by design (§0). Mobile viewports see a breakpoint banner,
not the scene.

| Browser | Min version | Notes |
|---|---|---|
| Chrome / Edge | 90 | WebGL2 + BigInt64Array |
| Firefox | 85 | — |
| Safari | 16 | WebGL2 needs macOS 12+ |
| Mobile Safari / Chrome Android | — | **not supported** (banner only) |
