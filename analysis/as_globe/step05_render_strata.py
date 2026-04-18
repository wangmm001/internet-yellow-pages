"""Step 5: Render `html/as_strata.html` — AS Strata country-canopy view.

Design goal: fix two failures of step03 (geographic globe) and step04 (force
topology) within the same screen budget:

  1. Country share (占比) is perceptually encoded as angular sector area on a
     3D disk (region → country nested pie).
  2. 30,000 peering edges collapse into ~2K country-pair bundles rendered as
     3D ribbons whose thickness is log10(pair_count). No more edge fog;
     individual AS edges render on demand.
  3. AS sphere radius is un-capped log-scale so tier-1 backbones visibly
     tower over regionals.

Academic grounding (see plan):
  - Hierarchical Edge Bundles (Holten 2006) → bundle via country centroids.
  - Hive plots (Krzywinski 2012) → axis-aligned structural positioning within
    a country sub-sector (angle = degree-rank, radial = IPv4-rank).
  - Nested treemap (Balzer 2005, Bruls 2000) → region → country area partition.
"""
from __future__ import annotations

import json
import math
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.as_globe.common import (  # noqa: E402
    DATA_DIR, HTML_DIR, PAGE_CSS, REGION_COLOR, REGION_LABEL, REGION_ORDER,
    save_placeholder_html,
)


DISK_OUTER_R = 420.0       # world units
DISK_INNER_R = 40.0        # a small empty circle at centre to avoid singularity
MIN_COUNTRY_AS = 5         # below this → folded into a region-residual cell
MESA_MIN_ASES = 3          # only countries with ≥ this many ASes get a mesa
BUNDLE_MAX_RADIUS = 9.0    # ribbon tube radius at max peering
BUNDLE_MIN_RADIUS = 0.22
BUNDLE_MIN_OPACITY = 0.35  # even the thinnest visible ribbon reads clearly
BUNDLE_MAX_OPACITY = 0.95
MAX_INDIVIDUAL_EDGES = 120_000  # safety cap when rendering per-AS fan on click
THREE_VERSION = '0.160.0'  # pinned via importmap


# ─────────────────────────────────────────────────────────────
# Geometry helpers
# ─────────────────────────────────────────────────────────────

def _country_rank_within_region(nodes, region_key, by='as_count'):
    """Return {cc: metric_total} for a region, sorted descending by metric."""
    totals = defaultdict(lambda: {'as_count': 0, 'ipv4_total': 0.0})
    for n in nodes:
        if n['k'] != region_key:
            continue
        cc = n['c'] or '??'
        totals[cc]['as_count'] += 1
        totals[cc]['ipv4_total'] += n.get('v', 0) or 0
    if by == 'as_count':
        return sorted(totals.items(), key=lambda kv: -kv[1]['as_count'])
    return sorted(totals.items(), key=lambda kv: -kv[1]['ipv4_total'])


def _build_cells(nodes):
    """Compute nested pie-sector layout.

    Layout:
        - Regions get angular wedges proportional to their AS-count share.
        - Within each region, countries get sub-wedges proportional to
          their AS-count share of that region. Small countries (< MIN_COUNTRY_AS)
          fold into a single residual cell per region.
    Returns a list of cell dicts with fields consumed by the renderer.
    """
    total_as = len(nodes)
    region_counts = Counter(n['k'] for n in nodes)

    cells = []
    cell_id = 0
    theta = -math.pi / 2  # start at "north" (12 o'clock) so cn is at top

    for rk in REGION_ORDER:
        reg_total = region_counts.get(rk, 0)
        if reg_total == 0:
            continue
        reg_share = reg_total / total_as
        reg_span = reg_share * 2 * math.pi

        country_ranks = _country_rank_within_region(nodes, rk)
        residual_count = 0
        residual_ipv4 = 0.0
        named = []
        for cc, stats in country_ranks:
            if stats['as_count'] >= MIN_COUNTRY_AS:
                named.append((cc, stats))
            else:
                residual_count += stats['as_count']
                residual_ipv4 += stats['ipv4_total']

        named_total_as = sum(s['as_count'] for _, s in named) + residual_count
        if named_total_as == 0:
            continue

        ctheta = theta
        for cc, stats in named:
            sub_span = reg_span * stats['as_count'] / named_total_as
            cells.append({
                'id': cell_id,
                'cc': cc,
                'region': rk,
                'color': REGION_COLOR[rk],
                'theta_start': ctheta,
                'theta_span': sub_span,
                'as_count': stats['as_count'],
                'ipv4_total': stats['ipv4_total'],
                'is_residual': False,
            })
            cell_id += 1
            ctheta += sub_span

        if residual_count > 0:
            sub_span = reg_span * residual_count / named_total_as
            cells.append({
                'id': cell_id,
                'cc': f'__{rk}_rest__',
                'region': rk,
                'color': REGION_COLOR[rk],
                'theta_start': ctheta,
                'theta_span': sub_span,
                'as_count': residual_count,
                'ipv4_total': residual_ipv4,
                'is_residual': True,
            })
            cell_id += 1
            ctheta += sub_span

        theta += reg_span

    # mesa_height + mesa_radius get filled in by _enrich_cells_with_connectivity()
    # after bundle aggregation, because both encodings depend on the peering graph.
    # Placeholder values here so _layout_nodes() can still position AS spheres
    # above the mesa cap.
    for c in cells:
        c['mesa_height'] = 0.0
        c['mesa_radius'] = 0.0
        # centroid of the cell polygon at mid-angle, mid-radius.
        # NOTE on sign: the disk is a CircleGeometry (shape XY) tipped by
        # `mesh.rotation.x = -π/2`, so shape +Y → world -Z. To make centroids
        # sit *over* the rendered sector (not on the opposite side), we negate
        # sin for the z-axis. AS layout (`_layout_nodes`) applies the same flip.
        mid_theta = c['theta_start'] + c['theta_span'] / 2
        mid_r = (DISK_INNER_R + DISK_OUTER_R) / 2
        c['centroid_x'] = mid_r * math.cos(mid_theta)
        c['centroid_z'] = -mid_r * math.sin(mid_theta)
        c['mid_theta'] = mid_theta

    return cells


def _enrich_cells_with_connectivity(cells, bundles):
    """Fill cell.mesa_height + cell.mesa_radius from the aggregated bundle data.

    - `mesa_height` ∝ log10(total peering edges touching this country) — "连接密度"
    - `mesa_radius` ∝ sqrt(distinct partner-country count)            — "连接广度"

    Both are independent of sector angle (= AS count share), so the three
    channels (sector-area / height / thickness) now carry orthogonal meaning.
    """
    peering_total = defaultdict(int)
    partners = defaultdict(set)
    for b in bundles:
        a, t = b['a'], b['b']
        n = b['n']
        if a == t:  # intra-country: counts toward the country's density only
            peering_total[a] += n
        else:
            peering_total[a] += n
            peering_total[t] += n
            partners[a].add(t)
            partners[t].add(a)

    eligible = [c for c in cells if c['as_count'] >= MESA_MIN_ASES]
    max_log = max(
        (math.log10(peering_total.get(c['cc'], 0) + 1) for c in eligible),
        default=1.0,
    ) or 1.0
    max_partners = max(
        (len(partners.get(c['cc'], set())) for c in eligible),
        default=1,
    ) or 1
    sqrt_max_partners = math.sqrt(max_partners) or 1.0

    # Solid-pillar encoding: radius scales with √(partner_count) in world units.
    # Range 4..26 — chosen so small-sector countries (CN, TW) still hold a
    # visible pillar without the pillar bleeding beyond its sector.
    mesa_r_min = 4.0
    mesa_r_max = 26.0

    for c in cells:
        cc = c['cc']
        pt = peering_total.get(cc, 0)
        pcount = len(partners.get(cc, set()))
        c['peering_total'] = pt
        c['partner_count'] = pcount
        if c['as_count'] < MESA_MIN_ASES:
            c['mesa_height'] = 0.0
            c['mesa_radius'] = 0.0
            continue
        c['mesa_height'] = round((math.log10(pt + 1) / max_log) * 80.0, 2)
        norm = math.sqrt(pcount) / sqrt_max_partners
        c['mesa_radius'] = round(mesa_r_min + norm * (mesa_r_max - mesa_r_min), 2)


def _layout_nodes(nodes, cells):
    """Assign each AS a position inside its country cell.

    In-cell polar coords: angular = degree-rank (hubs at cell mid-angle),
    radial = IPv4-rank from inner to outer. Altitude z = f(log10(ipv4)).
    Returns a parallel list of enhanced nodes ready to serialize.
    """
    by_cc_cell = {c['cc']: c for c in cells}
    # ASes may fall into a residual cell — look up by region if cc cell missing
    by_region_residual = {c['region']: c for c in cells if c['is_residual']}

    # group nodes by cell
    buckets = defaultdict(list)
    for n in nodes:
        cc = n['c'] or '??'
        if cc in by_cc_cell:
            cell = by_cc_cell[cc]
        else:
            cell = by_region_residual.get(n['k'])
        if cell is None:
            continue
        buckets[cell['id']].append(n)

    out = []
    for cell_id, group in buckets.items():
        cell = next(c for c in cells if c['id'] == cell_id)
        n_group = len(group)

        # rank within cell
        by_degree = sorted(group, key=lambda n: -(n.get('d') or 0))
        by_ipv4 = sorted(group, key=lambda n: -(n.get('v') or 0))
        deg_rank = {id(n): i for i, n in enumerate(by_degree)}
        v4_rank = {id(n): i for i, n in enumerate(by_ipv4)}

        for n in group:
            dr = deg_rank[id(n)] / max(1, n_group - 1) if n_group > 1 else 0.5
            vr = v4_rank[id(n)] / max(1, n_group - 1) if n_group > 1 else 0.5

            # angular: hubs cluster at cell's mid-angle; fan out by degree-rank
            # low dr (hubs) → close to mid_theta; high dr (leaves) → near edges.
            # Alternate sign so the cell fills symmetrically.
            span_half = cell['theta_span'] / 2 * 0.88
            signed = ((deg_rank[id(n)] % 2) * 2 - 1) * (dr ** 0.6)
            theta = cell['mid_theta'] + signed * span_half

            # radial: big IPv4 → inward (closer to centre); small → outward
            radial = DISK_INNER_R + 6 + vr * (DISK_OUTER_R - DISK_INNER_R - 12)

            x = radial * math.cos(theta)
            z = -radial * math.sin(theta)   # match rotated disk (see _build_cells)
            # altitude: AS IPv4 scale — un-capped log
            y = cell['mesa_height'] + 4 + math.log10((n.get('v') or 0) + 1) * 6

            out.append({
                'a': n['a'],
                'c': n['c'],
                'k': n['k'],
                'v': n.get('v', 0),
                'd': n.get('d', 0),
                'cell': cell_id,
                'x': round(x, 2),
                'y': round(y, 2),
                'z': round(z, 2),
                'rad': round(0.6 + math.log10((n.get('v') or 0) + 1) * 0.95, 3),
            })
    return out


def _build_bundles(links, nodes_out, cells):
    """Aggregate raw edges into country-pair bundles.

    Each bundle: {cc_s, cc_t, count, samples}.
    Bundle radius logged; endpoints use cell centroids + mesa height.
    """
    asn_to_node = {n['a']: n for n in nodes_out}
    cell_by_id = {c['id']: c for c in cells}
    cell_by_cc = {c['cc']: c for c in cells}
    region_residual = {c['region']: c for c in cells if c['is_residual']}

    def resolve_cc(node):
        """Return the canonical cell 'cc' key for this node — may be __xx_rest__."""
        cc = node['c'] or '??'
        if cc in cell_by_cc:
            return cc
        residual = region_residual.get(node['k'])
        return residual['cc'] if residual else cc

    pairs = defaultdict(lambda: {'count': 0, 'samples': []})
    for link in links:
        s, t = link['s'], link['t']
        ns = asn_to_node.get(s)
        nt = asn_to_node.get(t)
        if not ns or not nt:
            continue
        cc_s = resolve_cc(ns)
        cc_t = resolve_cc(nt)
        if cc_s == cc_t:
            key = ('_intra', cc_s)
        else:
            key = tuple(sorted([cc_s, cc_t]))
        bucket = pairs[key]
        bucket['count'] += 1
        if len(bucket['samples']) < 16:
            bucket['samples'].append([s, t])

    # Radius scale: sqrt(count) — stretches the top end so the Top-5 ribbons
    # visually dominate instead of log-compressing everything into a haze.
    # Opacity also scales with count (quadratic in normalized sqrt) so the
    # long tail of count=1 sample edges fades to near-invisible context.
    max_count = max((b['count'] for b in pairs.values()), default=1)
    sqrt_max = math.sqrt(max_count) or 1.0

    bundles = []
    for key, data in pairs.items():
        norm = math.sqrt(data['count']) / sqrt_max      # 0..1
        radius = BUNDLE_MIN_RADIUS + norm * (BUNDLE_MAX_RADIUS - BUNDLE_MIN_RADIUS)
        # Linear (not squared) so every visible ribbon is at least BUNDLE_MIN_OPACITY.
        opacity = BUNDLE_MIN_OPACITY + norm * (BUNDLE_MAX_OPACITY - BUNDLE_MIN_OPACITY)
        if key[0] == '_intra':
            cc_s = cc_t = key[1]
        else:
            cc_s, cc_t = key
        bundles.append({
            'a': cc_s,
            'b': cc_t,
            'n': data['count'],
            'r': round(radius, 3),
            'o': round(opacity, 3),
            's': data['samples'],
        })

    # sort by count descending so front-loaded rendering takes thickest first
    bundles.sort(key=lambda x: -x['n'])
    return bundles


# ─────────────────────────────────────────────────────────────
# HTML / JS emission
# ─────────────────────────────────────────────────────────────

def _banner_html() -> str:
    region_chips = []
    for k in REGION_ORDER:
        zh, en = REGION_LABEL[k]
        region_chips.append(
            f'<span class="chip" data-region="{k}">'
            f'<span class="dot" style="background:{REGION_COLOR[k]}"></span>'
            f'{zh} · {en}</span>'
        )
    legend_html = '<div class="legend">' + ''.join(region_chips) + '</div>'

    return (
        f'<div class="overlay bottom">'
        f'{legend_html}'
        f'<div class="slider-row">'
        f'<span>对等底线 Bundle floor</span>'
        f'<input type="range" id="floor-slider" min="0" max="3" step="0.01" value="3">'
        f'<span id="floor-label">≥1000</span>'
        f'</div>'
        f'<div class="spacer"></div>'
        f'<div class="stats-inline" id="stats-panel">'
        f'<span class="kv"><b id="n-countries">…</b> 国</span>'
        f'<span class="kv"><b id="n-nodes">…</b> AS</span>'
        f'<span class="kv"><b id="n-pairs">…</b> 对</span>'
        f'<span class="kv focus-chip" id="focus-kv" style="display:none">聚焦 <b id="focus-label"></b></span>'
        f'</div>'
        f'<button class="panel-toggle legend-fab" data-toggle="legend" type="button" aria-label="展开说明">图例 ＋</button>'
        f'</div>'
        f'<div class="overlay legend-flyout collapsed" id="legend-panel">'
        f'<div class="panel-body">'
        f'<h1>AS 都会 · Country Canopy</h1>'
        f'<h2>扇区 · 柱 · 球 · 环 · 丝带 五通道编码</h2>'
        f'<p><strong>扇区面积</strong> = AS 数占比；<strong>柱高</strong> = log10(总对等边) 连接密度；'
        f'<strong>柱粗</strong> = √(伙伴国数) 连接广度；<strong>球大小/高度</strong> = AS IPv4；'
        f'<strong>环</strong> = 国内 mesh；<strong>丝带</strong> = 国家对对等量。</p>'
        f'<p>Sector = AS count share · Pillar height = peering-edge density (log) · '
        f'Pillar radius = partner-country reach (√) · Sphere = per-AS IPv4 · '
        f'Ring = intra-country mesh · Ribbon = country-pair peering.</p>'
        f'<p class="hint">操作 · Controls: 拖拽旋转 · 滚轮缩放 · <kbd>T</kbd> 俯视 · <kbd>G</kbd> 地平 · <kbd>R</kbd> 还原 · 点击 AS 看其对等扇</p>'
        f'</div>'
        f'</div>'
        f'<div class="tooltip" id="tip"></div>'
    )


def _build_html(cells, nodes_out, bundles) -> str:
    max_intra = max((b['n'] for b in bundles if b['a'] == b['b']), default=1)
    data_json = json.dumps({
        'cells': cells,
        'nodes': nodes_out,
        'bundles': bundles,
        'regionColor': REGION_COLOR,
        'regionOrder': REGION_ORDER,
        'regionLabel': {k: {'zh': v[0], 'en': v[1]} for k, v in REGION_LABEL.items()},
        'diskOuterR': DISK_OUTER_R,
        'diskInnerR': DISK_INNER_R,
        'maxIntraCount': max_intra,
    }, ensure_ascii=False, separators=(',', ':'))

    three_base = f'https://unpkg.com/three@{THREE_VERSION}'

    extra_css = """
      .overlay { position: absolute; }
      .panel-toggle {
        background: rgba(255,255,255,0.08);
        border: 1px solid var(--border);
        border-radius: 6px;
        color: var(--fg); cursor: pointer;
        font-size: 12px; line-height: 1; padding: 6px 10px;
      }
      .panel-toggle:hover { background: rgba(255,255,255,0.16); }
      .legend-fab { white-space: nowrap; }
      .legend-flyout {
        right: 18px; bottom: 80px; max-width: 420px;
        transition: opacity 0.18s ease, transform 0.18s ease;
      }
      .legend-flyout.collapsed {
        opacity: 0; transform: translateY(8px); pointer-events: none;
      }
      .overlay .hint { color: var(--muted); font-size: 11px; margin-top: 6px; }
      .spacer { flex: 1 1 auto; }
      .stats-inline {
        display: flex; gap: 14px; align-items: center;
        color: var(--muted); font-size: 12px;
      }
      .stats-inline .kv b { color: var(--fg); font-weight: 600; }
      .stats-inline .focus-chip b { color: #5E5CE6; }
      .overlay kbd {
        display: inline-block; padding: 1px 5px; border-radius: 4px;
        background: rgba(255,255,255,0.08); border: 1px solid var(--border);
        color: var(--fg); font-family: ui-monospace, SFMono-Regular, monospace;
        font-size: 10px; margin: 0 2px;
      }
      .as-label {
        color: var(--fg); font-size: 10px;
        background: rgba(13,17,23,0.82);
        border: 1px solid var(--border); border-radius: 4px;
        padding: 1px 5px; pointer-events: none;
      }
      .cc-label {
        color: var(--fg); font-size: 11px;
        font-weight: 500;
        letter-spacing: 0.5px;
        padding: 0;
        pointer-events: none;
        text-shadow: 0 0 6px rgba(13,17,23,0.9), 0 0 12px rgba(13,17,23,0.7);
      }
      .cc-label.dim { opacity: 0.35; }
      #focus-panel {
        position: absolute; right: 18px; top: 170px; z-index: 10;
        background: rgba(22,27,34,0.90); border: 1px solid var(--border);
        border-radius: 10px; padding: 14px 16px; font-size: 12px;
        width: 280px; display: none;
        backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
      }
      #focus-panel h3 { margin: 0 0 8px 0; font-size: 14px; }
      #focus-panel ol { padding-left: 18px; margin: 6px 0; }
      #focus-panel li { color: var(--muted); margin: 2px 0; }
      #focus-panel .asn { color: #5E5CE6; font-weight: 600; }
      #focus-panel .close {
        float: right; cursor: pointer; color: var(--muted);
        font-size: 14px; line-height: 1;
      }
    """

    return f"""<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>AS 都会 · Country Canopy</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{PAGE_CSS}{extra_css}</style>
</head>
<body>
<div id="viz"></div>
<div id="labels"></div>
{_banner_html()}
<div id="focus-panel">
  <span class="close" onclick="this.parentNode.style.display='none'">×</span>
  <h3 id="focus-title">—</h3>
  <div id="focus-meta"></div>
  <ol id="focus-peers"></ol>
</div>

<div id="load-error" style="display:none;position:absolute;top:18px;left:50%;transform:translateX(-50%);z-index:30;background:#ff453a;color:#fff;padding:10px 16px;border-radius:8px;font-size:13px"></div>
<script>
  window.addEventListener('error', function(e) {{
    var el = document.getElementById('load-error');
    if (el) {{ el.textContent = '加载失败 · ' + (e.message || 'unknown'); el.style.display = 'block'; }}
    console.error('[as_strata]', e);
  }});
  window.addEventListener('unhandledrejection', function(e) {{
    var el = document.getElementById('load-error');
    if (el) {{ el.textContent = 'ESM 导入失败 · ' + (e.reason || 'unknown'); el.style.display = 'block'; }}
    console.error('[as_strata]', e);
  }});
</script>

<script type="importmap">
{{
  "imports": {{
    "three": "{three_base}/build/three.module.js",
    "three/addons/": "{three_base}/examples/jsm/"
  }}
}}
</script>

<script type="module">
import * as THREE from 'three';
import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';
import {{ CSS2DRenderer, CSS2DObject }} from 'three/addons/renderers/CSS2DRenderer.js';

const DATA = {data_json};
const MAX_INTRA_COUNT = DATA.maxIntraCount || 1;

// ---------- Scene / camera / renderer setup -----------------
const el = document.getElementById('viz');
const labelHost = document.getElementById('labels');
labelHost.style.position = 'absolute';
labelHost.style.inset = '0';
labelHost.style.pointerEvents = 'none';

const scene = new THREE.Scene();
scene.background = new THREE.Color('#05070C');
scene.fog = new THREE.Fog('#05070C', 900, 2300);

const camera = new THREE.PerspectiveCamera(
  45, el.clientWidth / el.clientHeight, 0.1, 3500
);
camera.position.set(0, 380, 720);
camera.lookAt(0, 0, 0);

const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: false }});
renderer.setSize(el.clientWidth, el.clientHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
el.appendChild(renderer.domElement);

const labelRenderer = new CSS2DRenderer();
labelRenderer.setSize(el.clientWidth, el.clientHeight);
labelRenderer.domElement.style.position = 'absolute';
labelRenderer.domElement.style.inset = '0';
labelRenderer.domElement.style.pointerEvents = 'none';
el.appendChild(labelRenderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.minDistance = 120;
controls.maxDistance = 2000;
controls.maxPolarAngle = Math.PI / 2 - 0.03; // keep camera above disk

scene.add(new THREE.AmbientLight(0xffffff, 0.75));
const dir1 = new THREE.DirectionalLight(0xffffff, 0.55);
dir1.position.set(260, 480, 320);
scene.add(dir1);
const dir2 = new THREE.DirectionalLight(0x88a0ff, 0.25);
dir2.position.set(-260, 280, -220);
scene.add(dir2);

// ---------- Colour helpers ----------
function hexToColor(hex) {{ return new THREE.Color(hex); }}

// ---------- Disk sectors (pie slices) ----------
const regionGroups = {{}};
for (const rk of DATA.regionOrder) regionGroups[rk] = new THREE.Group();
Object.values(regionGroups).forEach(g => scene.add(g));

const cellById = new Map();
DATA.cells.forEach(cell => {{
  cellById.set(cell.id, cell);
  const geom = new THREE.CircleGeometry(
    DATA.diskOuterR, 36, cell.theta_start, cell.theta_span
  );
  const mat = new THREE.MeshStandardMaterial({{
    color: hexToColor(cell.color),
    transparent: true,
    opacity: cell.is_residual ? 0.22 : 0.42,
    side: THREE.DoubleSide,
    metalness: 0.15,
    roughness: 0.55,
  }});
  const mesh = new THREE.Mesh(geom, mat);
  mesh.rotation.x = -Math.PI / 2;  // lay flat on XZ plane
  mesh.userData = {{ kind: 'cell', cell }};
  regionGroups[cell.region].add(mesh);
  cell._mesh = mesh;

  // Cut out a centre hole by overlaying a small dark disk
  // (simpler than computing ring geometry with theta span).
  // Done once at scene-build via a single centre disk below.

  // Sector border: thin ring segment at outer edge
  const borderGeom = new THREE.RingGeometry(
    DATA.diskOuterR - 0.6, DATA.diskOuterR + 0.6, 2, 1,
    cell.theta_start, cell.theta_span
  );
  const borderMat = new THREE.MeshBasicMaterial({{
    color: hexToColor(cell.color),
    transparent: true, opacity: 0.8,
    side: THREE.DoubleSide,
  }});
  const borderMesh = new THREE.Mesh(borderGeom, borderMat);
  borderMesh.rotation.x = -Math.PI / 2;
  borderMesh.position.y = 0.05;
  regionGroups[cell.region].add(borderMesh);
}});

// Central dark cap (covers the spike where slices meet)
{{
  const capGeom = new THREE.CircleGeometry(DATA.diskInnerR, 48);
  const capMat = new THREE.MeshBasicMaterial({{ color: 0x05070C }});
  const cap = new THREE.Mesh(capGeom, capMat);
  cap.rotation.x = -Math.PI / 2;
  cap.position.y = 0.1;
  scene.add(cap);
}}

// ---------- Mesas: solid pillars sitting on the mid-radius of each sector ----------
// radius = √(partner_count) · height = log10(total_peering).
// Opaque + emissive rim so the pillar reads as a solid colour-stop even at distance.
const mesaCaps = {{}};
const mesaMeshes = [];                 // raycast targets for country-click
const meshesByCC = new Map();          // cc → [pillar mesh, ring mesh, ...]
DATA.cells.forEach(cell => {{
  const midTheta = cell.mid_theta;
  // Pillar sits on the sector's mid-radius. Using Python-computed centroid
  // (already sign-flipped with -sin to match the rotated disk).
  const capX = cell.centroid_x;
  const capZ = cell.centroid_z;

  if (!cell.mesa_height || cell.mesa_height < 2) {{
    mesaCaps[cell.id] = new THREE.Vector3(capX, 1.0, capZ);
    return;
  }}

  const mesaR = cell.mesa_radius;
  const geom = new THREE.CylinderGeometry(
    mesaR * 0.78, mesaR, cell.mesa_height, 28, 1, false
  );
  const color = hexToColor(cell.color);
  const mat = new THREE.MeshStandardMaterial({{
    color: color,
    transparent: false,
    opacity: 1.0,
    metalness: 0.10,
    roughness: 0.55,
    emissive: color,
    emissiveIntensity: 0.12,
  }});
  const mesh = new THREE.Mesh(geom, mat);
  mesh.position.set(capX, cell.mesa_height / 2, capZ);
  mesh.userData = {{ kind: 'mesa', cell, baseOpacity: 1.0, baseEmissive: 0.12 }};
  regionGroups[cell.region].add(mesh);
  mesaMeshes.push(mesh);
  if (!meshesByCC.has(cell.cc)) meshesByCC.set(cell.cc, []);
  meshesByCC.get(cell.cc).push(mesh);

  mesaCaps[cell.id] = new THREE.Vector3(capX, cell.mesa_height, capZ);
}});

// ---------- Country labels ----------
DATA.cells.forEach(cell => {{
  if (cell.is_residual || cell.as_count < 10) return;
  const div = document.createElement('div');
  div.className = 'cc-label';
  div.textContent = cell.cc;
  div.style.color = cell.color;
  const obj = new CSS2DObject(div);
  const top = mesaCaps[cell.id];
  obj.position.set(top.x, top.y + 8, top.z);
  regionGroups[cell.region].add(obj);
  cell._label = div;
}});

// ---------- AS spheres via InstancedMesh (one per region) ----------
const nodesByRegion = {{}};
for (const rk of DATA.regionOrder) nodesByRegion[rk] = [];
DATA.nodes.forEach(n => nodesByRegion[n.k].push(n));

const nodeIndexInRegion = new Map();    // asn -> record
const nodePositions = new Map();        // asn → THREE.Vector3
const instancedMeshes = {{}};

const sphereGeom = new THREE.SphereGeometry(1, 12, 10);
const dummy = new THREE.Object3D();
for (const rk of DATA.regionOrder) {{
  const group = nodesByRegion[rk];
  if (group.length === 0) continue;
  const mat = new THREE.MeshStandardMaterial({{
    color: hexToColor(DATA.regionColor[rk]),
    metalness: 0.15, roughness: 0.35,
    transparent: true, opacity: 0.95,
    emissive: hexToColor(DATA.regionColor[rk]),
    emissiveIntensity: 0.18,
  }});
  const mesh = new THREE.InstancedMesh(sphereGeom, mat, group.length);
  mesh.userData = {{ kind: 'as-group', region: rk }};
  group.forEach((n, idx) => {{
    dummy.position.set(n.x, n.y, n.z);
    dummy.scale.setScalar(n.rad * 2.4);  // world-unit radius
    dummy.updateMatrix();
    mesh.setMatrixAt(idx, dummy.matrix);
    nodeIndexInRegion.set(n.a, {{ region: rk, index: idx, node: n }});
    nodePositions.set(n.a, new THREE.Vector3(n.x, n.y, n.z));
  }});
  mesh.instanceMatrix.needsUpdate = true;
  regionGroups[rk].add(mesh);
  instancedMeshes[rk] = mesh;
}}

// ---------- Bundled ribbons ----------
function _buildBundleCurve(capA, capB) {{
  const mid = capA.clone().add(capB).multiplyScalar(0.5);
  const dist = capA.distanceTo(capB);
  // Apex altitude: at least 40, scales with distance (0..1400 range)
  const apexY = Math.max(capA.y, capB.y) + 40 + Math.min(300, dist * 0.42);
  const apex = new THREE.Vector3(mid.x, apexY, mid.z);
  const ctrl1 = apex.clone().lerp(capA, 0.4);
  const ctrl2 = apex.clone().lerp(capB, 0.4);
  ctrl1.y = apexY * 0.82;
  ctrl2.y = apexY * 0.82;
  return new THREE.CubicBezierCurve3(capA, ctrl1, ctrl2, capB);
}}

const cellByCC = new Map();
DATA.cells.forEach(c => cellByCC.set(c.cc, c));

const ribbonsGroup = new THREE.Group();
scene.add(ribbonsGroup);

DATA.bundles.forEach(b => {{
  const cellA = cellByCC.get(b.a);
  const cellB = cellByCC.get(b.b);
  if (!cellA || !cellB) return;
  const capA = mesaCaps[cellA.id];
  const capB = mesaCaps[cellB.id];
  if (b.a === b.b) {{
    // intra-country bundle: a horizontal torus ring just above the mesa cap.
    // Colour: brightened region hue (setHSL(h, s, 0.58)) so it has visible
    // identity (CN pink · NA sky · EU mint · EA apricot · OT silver) and
    // CONTRASTS with the deeper pillar hue beneath it.
    //
    // Material: OPAQUE MeshStandardMaterial with emissive glow. Using opaque
    // geometry + depthWrite eliminates the view-dependent alpha blending
    // that was causing rings to look "white / transparent-white" under
    // T (top-down) and G (ground) camera views.
    const intraNormSqrt = Math.sqrt(b.n) / Math.sqrt(MAX_INTRA_COUNT);
    const ringR = 4 + intraNormSqrt * 24;
    const tubeR = 0.4 + intraNormSqrt * 5.6;
    const geom = new THREE.TorusGeometry(ringR, tubeR, 10, 40);
    // Hard-coded contrast hues per region: the ring sits on top of its pillar
    // and must read as distinctly brighter AND distinctly different in hue-mix
    // from the pillar's saturated colour. Values chosen by eye on #0D1117 bg.
    const RING_HEX = {{
      cn: 0xFFC2BD,   // pillar red #FF453A   → light coral
      na: 0xBFE0FF,   // pillar blue #0A84FF  → powder blue
      ea: 0xFFDA9A,   // pillar orange #FF9F0A → pale amber
      eu: 0xB7F2C4,   // pillar green #30D158 → soft mint
      ot: 0xE5E5EA,   // pillar grey #8E8E93  → silver
    }};
    const ringColor = new THREE.Color(RING_HEX[cellA.region] || 0xFFFFFF);
    const mat = new THREE.MeshStandardMaterial({{
      color: ringColor,
      emissive: ringColor,
      emissiveIntensity: 0.45,
      metalness: 0.05,
      roughness: 0.35,
    }});
    const mesh = new THREE.Mesh(geom, mat);
    mesh.position.set(capA.x, capA.y + 4 + tubeR, capA.z);
    mesh.rotation.x = Math.PI / 2;   // lie flat on horizontal plane
    mesh.userData = {{
      kind: 'bundle', a: b.a, b: b.b, count: b.n, intra: true,
      baseOpacity: 1.0,
    }};
    ribbonsGroup.add(mesh);
    if (!meshesByCC.has(b.a)) meshesByCC.set(b.a, []);
    meshesByCC.get(b.a).push(mesh);
    return;
  }}

  const curve = _buildBundleCurve(capA, capB);
  const segs = 32;
  const geom = new THREE.TubeGeometry(curve, segs, b.r, 8, false);
  // Vertex-colored gradient from cellA.color -> cellB.color
  const colors = [];
  const pos = geom.attributes.position;
  const colA = hexToColor(cellA.color);
  const colB = hexToColor(cellB.color);
  const tmp = new THREE.Color();
  for (let i = 0; i < pos.count; i++) {{
    const u = Math.floor(i / 9) / segs;
    tmp.copy(colA).lerp(colB, u);
    colors.push(tmp.r, tmp.g, tmp.b);
  }}
  geom.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
  const mat = new THREE.MeshBasicMaterial({{
    vertexColors: true, transparent: true,
    opacity: b.o, depthWrite: false,
  }});
  const mesh = new THREE.Mesh(geom, mat);
  mesh.userData = {{ kind: 'bundle', a: b.a, b: b.b, count: b.n, baseOpacity: b.o }};
  ribbonsGroup.add(mesh);
}});

// ---------- Frayed per-AS edges (for on-click focus) ----------
const linksByAsn = new Map();  // asn → [{{ other, other_cc }}, ...]
DATA.bundles.forEach(b => {{
  b.s.forEach(pair => {{
    const [s, t] = pair;
    if (!linksByAsn.has(s)) linksByAsn.set(s, []);
    if (!linksByAsn.has(t)) linksByAsn.set(t, []);
    linksByAsn.get(s).push({{ other: t, cc: b.b === DATA.nodes.find(n=>n.a===s)?.c ? b.a : b.b }});
    linksByAsn.get(t).push({{ other: s, cc: b.a === DATA.nodes.find(n=>n.a===t)?.c ? b.b : b.a }});
  }});
}});

const focusLines = new THREE.Group();
scene.add(focusLines);

// Track currently-focused country (for the click-pillar filter).
// null = no country focus; otherwise the ISO-2 cc.
let focusedCC = null;

// All 5 region buckets are active by default; the chip handler mutates this.
const activeRegion = new Set(DATA.regionOrder);

// Three orthogonal channels keep distinct responsibilities:
//
//   chip   (activeRegion)  → toggles ONLY the AS-sphere layer of a region.
//                            The structural scaffold (sectors, pillars, rings,
//                            ribbons) stays untouched — chips are a lens over
//                            the "who are the AS balls" layer, nothing more.
//
//   focus  (focusedCC)     → isolates one country: brightens its incident
//                            ribbons + pillar, dims all other pillars +
//                            dims ALL AS spheres (across all regions).
//
//   slider (bundle floor)  → hides ribbons whose peering-edge count is below
//                            the threshold.
//
// Ribbon visibility composes only focus + slider (chips no longer affect it).
function refreshRibbonVisibility() {{
  const thr = Math.round(Math.pow(10, parseFloat(
    document.getElementById('floor-slider').value
  )));
  ribbonsGroup.children.forEach(m => {{
    const passesFloor = m.userData.count >= thr;
    const passesFocus = focusedCC === null
      || m.userData.a === focusedCC
      || m.userData.b === focusedCC;
    m.visible = passesFloor && passesFocus;
  }});
}}

// Chip visibility only touches the per-region InstancedMesh of AS spheres.
// Everything else in the region group — the sector circle, the pillar, the
// intra ring — remains visible and is not affected by the chip state.
function applyRegionVisibility() {{
  for (const rk of DATA.regionOrder) {{
    const mesh = instancedMeshes[rk];
    if (mesh) mesh.visible = activeRegion.has(rk);
  }}
}}

// Reset MATERIAL state only (does not touch visibility).
function resetAllStylesToBase() {{
  ribbonsGroup.children.forEach(m => {{
    if (m.userData.intra) {{
      m.material.emissiveIntensity = 0.45;
    }} else {{
      m.material.opacity = m.userData.baseOpacity || 0.12;
    }}
  }});
  mesaMeshes.forEach(m => {{
    m.material.emissiveIntensity = m.userData.baseEmissive || 0.12;
    m.material.transparent = false;
    m.material.opacity = 1.0;
  }});
  Object.values(instancedMeshes).forEach(mesh => {{
    mesh.material.transparent = true;
    mesh.material.opacity = 0.95;
  }});
}}

function clearCountryFocus() {{
  focusedCC = null;
  resetAllStylesToBase();
  document.getElementById('focus-kv').style.display = 'none';
  refreshRibbonVisibility();
}}

function focusCountry(cc) {{
  // Toggle off if clicking the same country again.
  if (focusedCC === cc) {{
    clearCountryFocus();
    return;
  }}
  // Clean slate first — wipes any residual state from the previous focus.
  clearFocusLines();
  resetAllStylesToBase();
  focusedCC = cc;

  // Highlight ribbons that touch this country (others keep base styles but
  // will be hidden by refreshRibbonVisibility).
  ribbonsGroup.children.forEach(m => {{
    const touches = (m.userData.a === cc || m.userData.b === cc);
    if (!touches) return;
    if (m.userData.intra) {{
      m.material.emissiveIntensity = 0.75;
    }} else {{
      m.material.opacity = Math.max(0.75, m.userData.baseOpacity || 0.6);
    }}
  }});

  // Non-focus pillars → dim + translucent; focus pillar stays at base.
  mesaMeshes.forEach(m => {{
    if (m.userData.cell.cc === cc) return;
    m.material.emissiveIntensity = 0.02;
    m.material.transparent = true;
    m.material.opacity = 0.25;
  }});

  // All AS spheres → dim so ribbons dominate visually.
  Object.values(instancedMeshes).forEach(mesh => {{
    mesh.material.transparent = true;
    mesh.material.opacity = 0.15;
  }});

  // Update focus chip.
  const cell = DATA.cells.find(c => c.cc === cc);
  const label = cell ? (DATA.regionLabel[cell.region]?.zh || '') : '';
  document.getElementById('focus-kv').style.display = '';
  document.getElementById('focus-label').textContent =
    cc + (label ? ' · ' + label : '');

  refreshRibbonVisibility();
}}

function clearFocusLines() {{
  while (focusLines.children.length) {{
    const ch = focusLines.children.pop();
    ch.geometry.dispose();
    ch.material.dispose();
  }}
}}

function showFocusLinesForAS(asn) {{
  clearFocusLines();
  const rec = nodeIndexInRegion.get(asn);
  if (!rec) return;
  const startPos = nodePositions.get(asn);
  const peers = linksByAsn.get(asn) || [];
  const seen = new Set();
  peers.forEach(p => {{
    if (seen.has(p.other)) return;
    seen.add(p.other);
    const endPos = nodePositions.get(p.other);
    if (!endPos) return;
    const curve = _buildBundleCurve(startPos, endPos);
    const pts = curve.getPoints(24);
    const geom = new THREE.BufferGeometry().setFromPoints(pts);
    const mat = new THREE.LineBasicMaterial({{
      color: hexToColor(DATA.regionColor[rec.region]),
      transparent: true, opacity: 0.85,
    }});
    focusLines.add(new THREE.Line(geom, mat));
  }});
}}

// ---------- Legend flyout collapse toggle ----------
document.querySelectorAll('.panel-toggle[data-toggle="legend"]').forEach(btn => {{
  btn.addEventListener('click', () => {{
    const panel = document.getElementById('legend-panel');
    const collapsed = panel.classList.toggle('collapsed');
    btn.textContent = collapsed ? '图例 ＋' : '图例 －';
    btn.setAttribute('aria-label', collapsed ? '展开说明' : '折叠说明');
  }});
}});

// ---------- Controls: region chips, bundle slider ----------
// Chips toggle `activeRegion`; the single source of truth is applyRegionVisibility().
// This composes cleanly with focusCountry() — pillar focus never overrides chip state.
document.querySelectorAll('.chip[data-region]').forEach(chip => {{
  chip.addEventListener('click', () => {{
    const rk = chip.getAttribute('data-region');
    if (activeRegion.has(rk)) {{
      activeRegion.delete(rk);
      chip.classList.add('off');
    }} else {{
      activeRegion.add(rk);
      chip.classList.remove('off');
    }}
    applyRegionVisibility();
  }});
}});

// Bundle floor slider — hides bundles with count < 10^slider.
// Visibility delegated to refreshRibbonVisibility() so the slider + country
// focus filter compose cleanly.
const slider = document.getElementById('floor-slider');
const floorLabel = document.getElementById('floor-label');
function applyFloor() {{
  const threshold = Math.round(Math.pow(10, parseFloat(slider.value)));
  floorLabel.textContent = '≥' + threshold;
  refreshRibbonVisibility();
}}
slider.addEventListener('input', applyFloor);
applyFloor();
applyRegionVisibility();   // initial pass (all on; harmless but explicit)

// ---------- Stats panel ----------
document.getElementById('n-countries').textContent = DATA.cells.filter(c => !c.is_residual).length.toLocaleString();
document.getElementById('n-nodes').textContent = DATA.nodes.length.toLocaleString();
document.getElementById('n-pairs').textContent = DATA.bundles.length.toLocaleString();

// ---------- Raycaster & interaction ----------
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
const tip = document.getElementById('tip');
const focusPanel = document.getElementById('focus-panel');
const focusTitle = document.getElementById('focus-title');
const focusMeta = document.getElementById('focus-meta');
const focusPeers = document.getElementById('focus-peers');
const focusLabel = document.getElementById('focus-label');
const focusKV = document.getElementById('focus-kv');

function onPointerMove(ev) {{
  const rect = renderer.domElement.getBoundingClientRect();
  mouse.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;

  raycaster.setFromCamera(mouse, camera);

  // 1. Prefer AS sphere hits (closer to camera, smaller target)
  const asHits = raycaster.intersectObjects(Object.values(instancedMeshes), false);
  if (asHits.length > 0) {{
    const h = asHits[0];
    const rk = h.object.userData.region;
    const node = nodesByRegion[rk][h.instanceId];
    el.style.cursor = 'pointer';
    tip.style.display = 'block';
    tip.style.left = (ev.clientX + 14) + 'px';
    tip.style.top = (ev.clientY + 14) + 'px';
    const label = DATA.regionLabel[rk];
    tip.innerHTML = `
      <div><span class="asn">AS${{node.a}}</span>
           <span class="kv" style="margin-left:6px">${{node.c || '??'}} · ${{label.zh}}</span></div>
      <div class="kv">IPv4: ${{(node.v || 0).toLocaleString()}}</div>
      <div class="kv">对等度 Degree: ${{node.d || 0}}</div>
      <div class="kv" style="margin-top:4px;opacity:0.75">${{label.en}}</div>
    `;
    return;
  }}

  // 2. Otherwise try a pillar hit (fallback — big target, country-level info)
  const mesaHits = raycaster.intersectObjects(mesaMeshes, false);
  if (mesaHits.length > 0) {{
    const cell = mesaHits[0].object.userData.cell;
    const label = DATA.regionLabel[cell.region];
    el.style.cursor = 'pointer';
    tip.style.display = 'block';
    tip.style.left = (ev.clientX + 14) + 'px';
    tip.style.top = (ev.clientY + 14) + 'px';
    tip.innerHTML = `
      <div><span class="asn">${{cell.cc}}</span>
           <span class="kv" style="margin-left:6px">${{label.zh}} · ${{label.en}}</span></div>
      <div class="kv">AS 数: ${{cell.as_count}}</div>
      <div class="kv">对等边 Peering edges: ${{(cell.peering_total||0).toLocaleString()}}</div>
      <div class="kv">伙伴国 Partner countries: ${{cell.partner_count || 0}}</div>
      <div class="kv" style="margin-top:4px;opacity:0.7">点击只看本国连线</div>
    `;
    return;
  }}

  el.style.cursor = 'grab';
  tip.style.display = 'none';
}}

function onClick(ev) {{
  const rect = renderer.domElement.getBoundingClientRect();
  mouse.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(mouse, camera);

  // AS sphere takes priority over pillar (smaller + closer target).
  const asHits = raycaster.intersectObjects(Object.values(instancedMeshes), false);
  if (asHits.length === 0) {{
    const mesaHits = raycaster.intersectObjects(mesaMeshes, false);
    if (mesaHits.length > 0) {{
      const cell = mesaHits[0].object.userData.cell;
      focusCountry(cell.cc);
      // Camera fly-to: hover roughly over the country pillar.
      const capX = cell.centroid_x;
      const capZ = cell.centroid_z;
      const h = cell.mesa_height || 40;
      animateCamera(
        new THREE.Vector3(capX * 1.3, h + 260, capZ * 1.3),
        new THREE.Vector3(capX, h / 2, capZ),
        900,
      );
    }}
    return;
  }}

  const h = asHits[0];
  const rk = h.object.userData.region;
  const node = nodesByRegion[rk][h.instanceId];
  // Clear any country focus — AS-level focus supersedes it.
  if (focusedCC !== null) clearCountryFocus();
  showFocusLinesForAS(node.a);
  // Dim everything so the frayed edges pop. Intra rings are opaque
  // MeshStandardMaterial: dim via emissiveIntensity. Inter ribbons are
  // transparent MeshBasicMaterial: dim via opacity.
  ribbonsGroup.children.forEach(m => {{
    if (m.userData.intra) {{
      m.material.emissiveIntensity = 0.08;
    }} else {{
      m.material.opacity = (m.userData.baseOpacity || 0.12) * 0.2;
    }}
    m.material.needsUpdate = true;
  }});
  // Open focus panel
  const peers = (linksByAsn.get(node.a) || []).slice(0, 10);
  focusTitle.textContent = 'AS' + node.a + ' · ' + (node.c || '??');
  focusMeta.innerHTML = `
    <div class="kv">IPv4: ${{(node.v||0).toLocaleString()}}</div>
    <div class="kv">对等度 Peering Degree: ${{node.d||0}}</div>
    <div class="kv">地区 Region: ${{DATA.regionLabel[rk].zh}} · ${{DATA.regionLabel[rk].en}}</div>
  `;
  focusPeers.innerHTML = peers.length === 0
    ? '<li>(no sample peers in bundles)</li>'
    : peers.map(p => `<li>AS${{p.other}}${{p.cc ? ' · ' + p.cc : ''}}</li>`).join('');
  focusPanel.style.display = 'block';
  focusKV.style.display = '';
  focusLabel.textContent = 'AS' + node.a;
  // Camera fly-to
  const pos = nodePositions.get(node.a);
  const target = pos.clone();
  const desiredDist = 140;
  const dir = camera.position.clone().sub(target).normalize();
  const newPos = target.clone().add(dir.multiplyScalar(desiredDist));
  animateCamera(newPos, target, 900);
}}

function animateCamera(toPos, toTarget, durMs) {{
  const fromPos = camera.position.clone();
  const fromTarget = controls.target.clone();
  const t0 = performance.now();
  function step(now) {{
    const t = Math.min(1, (now - t0) / durMs);
    const easeT = t < 0.5 ? 2*t*t : 1 - Math.pow(-2*t+2, 2)/2;
    camera.position.lerpVectors(fromPos, toPos, easeT);
    controls.target.lerpVectors(fromTarget, toTarget, easeT);
    if (t < 1) requestAnimationFrame(step);
  }}
  requestAnimationFrame(step);
}}

renderer.domElement.addEventListener('pointermove', onPointerMove);
renderer.domElement.addEventListener('click', onClick);

// Keyboard shortcuts
window.addEventListener('keydown', e => {{
  const tag = (e.target && e.target.tagName) || '';
  if (tag === 'INPUT' || tag === 'TEXTAREA') return;
  if (e.key === 't' || e.key === 'T') {{
    animateCamera(new THREE.Vector3(0, 900, 0.01), new THREE.Vector3(0, 0, 0), 800);
  }} else if (e.key === 'g' || e.key === 'G') {{
    animateCamera(new THREE.Vector3(0, 40, 620), new THREE.Vector3(0, 30, 0), 800);
  }} else if (e.key === 'r' || e.key === 'R') {{
    animateCamera(new THREE.Vector3(0, 380, 720), new THREE.Vector3(0, 0, 0), 800);
    clearFocusLines();
    clearCountryFocus();
    focusPanel.style.display = 'none';
  }} else if (e.key === 'Escape') {{
    clearFocusLines();
    clearCountryFocus();
    focusPanel.style.display = 'none';
  }}
}});

// ---------- Resize ----------
window.addEventListener('resize', () => {{
  const w = el.clientWidth, h = el.clientHeight;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
  labelRenderer.setSize(w, h);
}});

// ---------- Animation loop ----------
function animate() {{
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
  labelRenderer.render(scene, camera);
}}
animate();
</script>
</body>
</html>
"""


def main() -> int:
    nodes_path = os.path.join(DATA_DIR, 'nodes.json')
    links_path = os.path.join(DATA_DIR, 'links.json')
    out_html = os.path.join(HTML_DIR, 'as_strata.html')

    if not os.path.exists(nodes_path) or not os.path.exists(links_path):
        save_placeholder_html(
            out_html,
            'AS 都会 · Country Canopy',
            'AS Strata · awaiting data',
            cause='缺少 data/nodes.json 或 data/links.json — 请先运行 step01 + step02。',
        )
        print(f'[placeholder] wrote {out_html}')
        return 0

    with open(nodes_path, encoding='utf-8') as f:
        nodes = json.load(f)
    with open(links_path, encoding='utf-8') as f:
        links = json.load(f)

    cells = _build_cells(nodes)
    # Aggregate bundles first — we need peering totals to set mesa height + radius.
    bundles = _build_bundles(links, nodes, cells)
    # Now that cells carry peering_total + partner_count + mesa_*, lay out nodes
    # so AS altitudes sit above the correct mesa cap.
    _enrich_cells_with_connectivity(cells, bundles)
    nodes_out = _layout_nodes(nodes, cells)

    # Emit support data JSON for debugging / rebuilding
    strata_cells_path = os.path.join(DATA_DIR, 'strata_cells.json')
    strata_bundles_path = os.path.join(DATA_DIR, 'strata_bundles.json')
    with open(strata_cells_path, 'w', encoding='utf-8') as f:
        json.dump(cells, f, ensure_ascii=False, separators=(',', ':'))
    with open(strata_bundles_path, 'w', encoding='utf-8') as f:
        json.dump(bundles, f, ensure_ascii=False, separators=(',', ':'))

    metrics = {
        'cells': len(cells),
        'named_countries': sum(1 for c in cells if not c['is_residual']),
        'residual_cells': sum(1 for c in cells if c['is_residual']),
        'nodes_placed': len(nodes_out),
        'bundles': len(bundles),
        'intra_bundles': sum(1 for b in bundles if b['a'] == b['b']),
        'inter_bundles': sum(1 for b in bundles if b['a'] != b['b']),
        'top5_inter_bundles': [
            {'a': b['a'], 'b': b['b'], 'count': b['n']}
            for b in bundles if b['a'] != b['b']
        ][:5],
    }
    metrics_path = os.path.join(DATA_DIR, 'step05_metrics.json')
    with open(metrics_path, 'w', encoding='utf-8') as f:
        json.dump({
            'step': 5,
            'title_zh': 'Step 05 · 分层占比图渲染',
            'title_en': 'Step 05 · Render AS Strata (country canopy)',
            'metrics': metrics,
        }, f, ensure_ascii=False, indent=2)

    html = _build_html(cells, nodes_out, bundles)
    with open(out_html, 'w', encoding='utf-8') as f:
        f.write(html)

    size_kb = os.path.getsize(out_html) // 1024
    print(f'Wrote {out_html} ({size_kb} KB)')
    print(f'  {metrics["named_countries"]} named countries + '
          f'{metrics["residual_cells"]} residual cells')
    print(f'  {metrics["nodes_placed"]:,} AS spheres '
          f'across {metrics["bundles"]:,} bundles '
          f'({metrics["intra_bundles"]:,} intra + {metrics["inter_bundles"]:,} inter)')
    if metrics['top5_inter_bundles']:
        print('  Top inter-country bundles:')
        for b in metrics['top5_inter_bundles']:
            print(f'    {b["a"]} ↔ {b["b"]}  {b["count"]:,} edges')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
