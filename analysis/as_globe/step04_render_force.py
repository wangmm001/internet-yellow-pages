"""Step 4: Render `html/as_force.html` — force-directed topology view.

Uses 3d-force-graph (Three.js + d3-force, WebGL). Same data as the globe view,
but no geographic constraint — the physics layout reveals peering clusters.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.as_globe.common import (  # noqa: E402
    DATA_DIR, HTML_DIR, PAGE_CSS, REGION_COLOR, REGION_LABEL, REGION_ORDER,
    save_placeholder_html,
)


FORCE_GRAPH_VERSION = '1.77'   # pinned; ships its own bundled Three.js.

DEFAULT_EDGE_DENSITY_PCT = 35
MAX_EDGES_HARD_CAP = 30000


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
        f'<button class="info-fab" id="info-toggle" type="button" aria-label="展开说明">说明 ＋</button>'
        f'<div class="overlay info-panel collapsed" id="info-panel">'
        f'<h1>全球 AS 互联立体图 · 拓扑力图</h1>'
        f'<h2>Top 5,000 ASes · force-directed 3D layout · clusters reveal peering communities</h2>'
        f'<p>不受地理约束，力导布局会把频繁互联的 AS 拉到一起。左右拖动旋转，滚轮缩放。</p>'
        f'<p>Drag to rotate, scroll to zoom. Similar-color clusters mean regional peering densities.</p>'
        f'</div>'
        f'<div class="overlay top-right" id="stats-panel">'
        f'<div class="kv">节点 Nodes: <span id="n-count">…</span></div>'
        f'<div class="kv">对等边 Edges: <span id="a-count">…</span></div>'
        f'<div class="kv" id="focus-kv" style="display:none">聚焦 Focus: <span id="focus-asn"></span></div>'
        f'</div>'
        f'<div class="overlay bottom">'
        f'{legend_html}'
        f'<div class="slider-row">'
        f'<span>对等边密度 Edge density</span>'
        f'<input type="range" id="edge-slider" min="0" max="100" step="5" value="{DEFAULT_EDGE_DENSITY_PCT}">'
        f'<span id="edge-pct">{DEFAULT_EDGE_DENSITY_PCT}%</span>'
        f'</div>'
        f'</div>'
        f'<div class="overlay finder" style="top:18px;left:50%;transform:translateX(-50%);'
        f'max-width:560px;padding:8px 12px;z-index:11;">'
        f'<div style="display:flex;gap:8px;align-items:center;">'
        f'<input id="find-input" type="search" autocomplete="off" spellcheck="false"'
        f' placeholder="🔍 AS号 / 名称 · ASN / name (Enter = 下一个)"'
        f' style="flex:1;min-width:0;background:rgba(13,17,23,0.9);color:var(--fg);'
        f'border:1px solid var(--border);border-radius:6px;padding:4px 8px;'
        f'font-size:12px;font-family:inherit;outline:none;">'
        f'<span id="find-hint" style="color:var(--muted);font-size:11px;opacity:0.75;'
        f'white-space:nowrap;min-width:80px;text-align:right;">—</span>'
        f'</div>'
        f'<div id="cloud-chips" style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;"></div>'
        f'</div>'
        f'<div class="tooltip" id="tip"></div>'
        f'<div id="halo-layer" aria-hidden="true"></div>'
        f'<style>'
        f'#halo-layer{{position:absolute;inset:0;pointer-events:none;z-index:15;}}'
        f'.halo{{position:absolute;width:0;height:0;'
        f'transform-style:preserve-3d;perspective:600px;--halo-size:140px;}}'
        f'.halo-ring{{position:absolute;left:0;top:0;border-radius:50%;'
        f'box-sizing:border-box;border-style:solid;'
        f'transform:translate(-50%,-50%) rotateX(72deg) rotateZ(0deg);'
        f'animation:halo-spin 14s linear infinite;}}'
        f'.halo-outer{{width:var(--halo-size);height:var(--halo-size);'
        f'border-width:2.5px;border-color:rgba(255,214,10,0.88);'
        f'box-shadow:0 0 22px rgba(255,214,10,0.55),inset 0 0 10px rgba(255,214,10,0.25);'
        f'animation-duration:14s;}}'
        f'.halo-mid{{width:calc(var(--halo-size)*0.76);height:calc(var(--halo-size)*0.76);'
        f'border-width:2px;border-color:rgba(255,159,10,0.72);'
        f'animation-duration:19s;animation-direction:reverse;}}'
        f'.halo-inner{{width:calc(var(--halo-size)*0.54);height:calc(var(--halo-size)*0.54);'
        f'border-width:1.5px;border-color:rgba(255,90,40,0.55);'
        f'animation-duration:11s;}}'
        f'@keyframes halo-spin{{'
        f'from{{transform:translate(-50%,-50%) rotateX(72deg) rotateZ(0deg);}}'
        f'to  {{transform:translate(-50%,-50%) rotateX(72deg) rotateZ(360deg);}}'
        f'}}'
        f'</style>'
    )


def _build_html(nodes: list[dict], links: list[dict]) -> str:
    data_json = json.dumps({
        'nodes': nodes,
        'links': links,
        'regionColor': REGION_COLOR,
        'regionOrder': REGION_ORDER,
        'regionLabel': {k: {'zh': v[0], 'en': v[1]} for k, v in REGION_LABEL.items()},
        'defaultEdgeDensityPct': DEFAULT_EDGE_DENSITY_PCT,
        'maxEdgesHardCap': MAX_EDGES_HARD_CAP,
    }, ensure_ascii=False, separators=(',', ':'))

    return f"""<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>全球 AS 互联立体图 · Force Topology</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{PAGE_CSS}</style>
</head>
<body>
<div id="viz"></div>
{_banner_html()}

<div id="load-error" style="display:none;position:absolute;top:18px;left:50%;transform:translateX(-50%);z-index:30;background:#ff453a;color:#fff;padding:10px 16px;border-radius:8px;font-size:13px">
  加载失败 · Load failed. Check DevTools console for details.
</div>
<script>
  window.addEventListener('error', function(e) {{
    var el = document.getElementById('load-error');
    if (el) {{ el.textContent = '加载失败 · ' + (e.message || 'unknown'); el.style.display = 'block'; }}
    console.error('[as_force]', e);
  }});
</script>
<script src="https://unpkg.com/3d-force-graph@{FORCE_GRAPH_VERSION}/dist/3d-force-graph.min.js" crossorigin="anonymous"
  onerror="document.getElementById('load-error').textContent='3d-force-graph CDN 加载失败 · CDN load failed';document.getElementById('load-error').style.display='block';"></script>
<script>
(function() {{
  if (typeof ForceGraph3D === 'undefined') {{
    document.getElementById('load-error').textContent = '3d-force-graph 未加载 · library did not load';
    document.getElementById('load-error').style.display = 'block';
    return;
  }}
  const DATA = {data_json};

  // Prepare nodes/links in force-graph's shape. Keep source/target as ints —
  // the lib resolves them against node ids.
  const graphNodes = DATA.nodes.map(n => ({{
    id: n.a, cc: n.c, k: n.k,
    v: n.v, r: n.r, d: n.d, g: n.g,
    org: n.o || '',
    color: DATA.regionColor[n.k] || '#8E8E93',
  }}));

  // Sort edges by combined node radius so "importance" (hub-hub) comes first.
  const nodeById = new Map(graphNodes.map(n => [n.id, n]));
  const sortedLinks = DATA.links.slice().sort((a, b) => {{
    const ra = (nodeById.get(a.s)?.r || 0) + (nodeById.get(a.t)?.r || 0);
    const rb = (nodeById.get(b.s)?.r || 0) + (nodeById.get(b.t)?.r || 0);
    return rb - ra;
  }});

  // Per-node adjacency (indices into sortedLinks, already in importance order).
  const nodeAdjIdx = new Map();
  for (let i = 0; i < sortedLinks.length; i++) {{
    const l = sortedLinks[i];
    if (!nodeAdjIdx.has(l.s)) nodeAdjIdx.set(l.s, []);
    if (!nodeAdjIdx.has(l.t)) nodeAdjIdx.set(l.t, []);
    nodeAdjIdx.get(l.s).push(i);
    nodeAdjIdx.get(l.t).push(i);
  }}

  const activeRegion = new Set(DATA.regionOrder);
  let edgeDensity = DATA.defaultEdgeDensityPct;
  const PER_NODE_QUOTA = 2;  // each node gets ≥2 edges before hubs monopolize budget

  function filterGraph() {{
    const poolNodes = graphNodes.filter(n => activeRegion.has(n.k));
    const allowed = new Set(poolNodes.map(n => n.id));
    const limit = Math.min(
      DATA.maxEdgesHardCap,
      Math.floor(sortedLinks.length * edgeDensity / 100),
    );

    const chosen = new Set();      // indices into sortedLinks
    const perCount = new Map();    // asn -> edges currently in visible set

    // Phase 1 — cover tail first. Iterate nodes in ASCENDING r so small ASes claim
    // their top edges before hubs swallow the budget.
    const ascByR = poolNodes.slice().sort((a, b) => a.r - b.r);
    for (const node of ascByR) {{
      if (chosen.size >= limit) break;
      if ((perCount.get(node.id) || 0) >= PER_NODE_QUOTA) continue;
      const adj = nodeAdjIdx.get(node.id) || [];
      for (const idx of adj) {{
        if ((perCount.get(node.id) || 0) >= PER_NODE_QUOTA) break;
        if (chosen.size >= limit) break;
        if (chosen.has(idx)) continue;
        const l = sortedLinks[idx];
        if (!allowed.has(l.s) || !allowed.has(l.t)) continue;
        chosen.add(idx);
        perCount.set(l.s, (perCount.get(l.s) || 0) + 1);
        perCount.set(l.t, (perCount.get(l.t) || 0) + 1);
      }}
    }}

    // Phase 2 — fill remaining budget with the fattest hub-hub edges we skipped.
    for (let i = 0; i < sortedLinks.length && chosen.size < limit; i++) {{
      if (chosen.has(i)) continue;
      const l = sortedLinks[i];
      if (!allowed.has(l.s) || !allowed.has(l.t)) continue;
      chosen.add(i);
    }}

    const links = [];
    for (const idx of chosen) {{
      const l = sortedLinks[idx];
      // force-graph mutates source/target — clone to a fresh obj each render.
      links.push({{ source: l.s, target: l.t }});
    }}

    // Option 2 — drop nodes with 0 visible edges. No floating debris around the
    // central cluster; the "Nodes" counter reflects the actually-connected set.
    const deg = new Map();
    for (const l of links) {{
      deg.set(l.source, (deg.get(l.source) || 0) + 1);
      deg.set(l.target, (deg.get(l.target) || 0) + 1);
    }}
    const nodes = poolNodes.filter(n => deg.has(n.id));
    return {{ nodes, links }};
  }}

  const el = document.getElementById('viz');
  const Graph = ForceGraph3D()(el)
    .backgroundColor('#05070C')
    .showNavInfo(false)
    .nodeId('id')
    .nodeLabel(() => '')            // disable built-in HTML label; we render our own tooltip
    .nodeColor('color')
    // Drive size from raw IPv4 count (n.v), not step02's r — r is both
    // log-compressed AND capped at 12, which squashes 99% of nodes into a
    // ~1.6× band (p10=5.8, p90=9.4) and hides the real 6+ orders of magnitude
    // of scale. v^0.35 * 0.03 is the cube of "near-linear in log10(v)" and
    // gives ~8× visible radius / ~64× pixel-area hierarchy tier-1 vs tail.
    .nodeVal(n => Math.pow(Math.max(1, n.v || 0), 0.35) * 0.03)
    .nodeResolution(10)
    .nodeOpacity(0.95)
    .linkColor(l => {{
      const s = typeof l.source === 'object' ? l.source : nodeById.get(l.source);
      return s ? (DATA.regionColor[s.k] || '#8E8E93') : '#8E8E93';
    }})
    .linkOpacity(0.18)
    .linkWidth(0.4)
    .linkDirectionalParticles(0)
    .onNodeHover(onHover)
    .onNodeClick(onClick);

  // (Bloom post-process omitted — UnrealBloomPass lives in three's /examples
  // bundle which isn't exposed by 3d-force-graph's CDN build.)

  // Loosen the charge a bit so hubs don't collapse toward center too hard.
  Graph.d3Force('charge').strength(-55);
  Graph.d3Force('link').distance(() => 24);

  function refresh() {{
    const g = filterGraph();
    Graph.graphData(g);
    document.getElementById('n-count').textContent = g.nodes.length.toLocaleString();
    document.getElementById('a-count').textContent = g.links.length.toLocaleString();
  }}
  refresh();

  // ---- Info panel toggle ----------------------------------------------------
  const infoToggle = document.getElementById('info-toggle');
  const infoPanel  = document.getElementById('info-panel');
  infoToggle.addEventListener('click', () => {{
    const collapsed = infoPanel.classList.toggle('collapsed');
    infoToggle.textContent = collapsed ? '说明 ＋' : '说明 －';
  }});

  // ---- Region chips ---------------------------------------------------------
  document.querySelectorAll('.chip[data-region]').forEach(chip => {{
    chip.addEventListener('click', () => {{
      const k = chip.getAttribute('data-region');
      if (activeRegion.has(k)) {{
        activeRegion.delete(k);
        chip.classList.add('off');
      }} else {{
        activeRegion.add(k);
        chip.classList.remove('off');
      }}
      refresh();
    }});
  }});

  // ---- Edge density slider --------------------------------------------------
  const slider = document.getElementById('edge-slider');
  const pctLabel = document.getElementById('edge-pct');
  slider.addEventListener('input', e => {{
    edgeDensity = +e.target.value;
    pctLabel.textContent = edgeDensity + '%';
    refresh();
  }});

  // ---- Tooltip + click-to-focus ---------------------------------------------
  const tip = document.getElementById('tip');
  const focusKV = document.getElementById('focus-kv');
  const focusAsn = document.getElementById('focus-asn');

  // Escape user-sourced strings — AS names come from third-party lists and
  // occasionally contain `<` or `&` (e.g. "Ltd. & Co").
  function esc(s) {{
    return String(s).replace(/[&<>"']/g, c => ({{
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
    }}[c]));
  }}

  function onHover(n) {{
    if (!n) {{ tip.style.display = 'none'; el.style.cursor = 'grab'; return; }}
    el.style.cursor = 'pointer';
    const regionZh = DATA.regionLabel[n.k]?.zh || '';
    const regionEn = DATA.regionLabel[n.k]?.en || '';
    const orgHtml = n.org
      ? `<span class="org" style="margin-left:6px;font-weight:500;opacity:0.92">${{esc(n.org)}}</span>`
      : '';
    tip.innerHTML = `
      <div><span class="asn">AS${{n.id}}</span>${{orgHtml}}
           <span class="kv" style="margin-left:6px">${{esc(n.cc || '??')}} · ${{regionZh}}</span></div>
      <div class="kv">IPv4: ${{(n.v || 0).toLocaleString()}} 地址 addresses</div>
      <div class="kv">对等度 Peering degree (pool): ${{n.d || 0}}</div>
      <div class="kv" style="margin-top:4px;opacity:0.75">${{regionEn}}</div>
    `;
    tip.style.display = 'block';
  }}

  // ---- Halo: one Saturn ring per focused node -----------------------------
  // setFocus([...]) mounts a fresh halo div per node; tickHalo projects each
  // node's world coords to the canvas every frame and writes the position +
  // --halo-size CSS var. Cap at HALO_CAP so a wildcard search like "amazon"
  // (50+ matches) doesn't melt the DOM.
  const haloLayer = document.getElementById('halo-layer');
  const HALO_CAP = 24;
  const HALO_RADIUS_MULT = 2.8;
  const HALO_MIN = 36;
  const HALO_MAX = 520;

  // Each entry is {{node, el}} — one halo div per currently-ringed AS.
  let focusedEntries = [];

  function nodeWorldRadius(n) {{
    // Must mirror .nodeVal: sphere volume = v^0.35 * 0.03, nodeRelSize default 4.
    const val = Math.pow(Math.max(1, n.v || 0), 0.35) * 0.03;
    return Math.cbrt(val) * 4;
  }}

  function createHaloEl() {{
    const h = document.createElement('div');
    h.className = 'halo';
    h.style.display = 'none';
    h.innerHTML =
      '<div class="halo-ring halo-outer"></div>' +
      '<div class="halo-ring halo-mid"></div>' +
      '<div class="halo-ring halo-inner"></div>';
    haloLayer.appendChild(h);
    return h;
  }}

  function setFocus(list) {{
    // Drop old halos wholesale — cheap for tens of elements, keeps logic
    // simple and avoids stale el-to-node associations.
    for (const e of focusedEntries) e.el.remove();
    focusedEntries = [];
    if (!list || !list.length) return;
    const trimmed = list.slice(0, HALO_CAP);
    for (const n of trimmed) focusedEntries.push({{ node: n, el: createHaloEl() }});
  }}

  function updateHaloEntry(entry) {{
    const n = entry.node, h = entry.el;
    if (typeof n.x !== 'number' || !Graph.graph2ScreenCoords) {{
      h.style.display = 'none';
      return;
    }}
    const sc = Graph.graph2ScreenCoords(n.x, n.y, n.z);
    const cam = Graph.camera && Graph.camera();
    if (!sc || !cam || !Number.isFinite(sc.x) || !Number.isFinite(sc.y)
        || sc.x <= -400 || sc.x >= window.innerWidth + 400
        || sc.y <= -400 || sc.y >= window.innerHeight + 400) {{
      h.style.display = 'none';
      return;
    }}
    const dx = n.x - cam.position.x;
    const dy = n.y - cam.position.y;
    const dz = n.z - cam.position.z;
    const dist = Math.hypot(dx, dy, dz);
    const fovRad = ((cam.fov || 60) * Math.PI) / 180;
    const vh = el.clientHeight || window.innerHeight;
    const pxPerUnit = vh / (2 * dist * Math.tan(fovRad / 2));
    const pxRadius = nodeWorldRadius(n) * pxPerUnit;
    const size = Math.max(HALO_MIN, Math.min(HALO_MAX, pxRadius * HALO_RADIUS_MULT * 2));
    h.style.setProperty('--halo-size', size.toFixed(1) + 'px');
    h.style.left = sc.x + 'px';
    h.style.top  = sc.y + 'px';
    h.style.display = 'block';
  }}

  function tickHalo() {{
    for (const entry of focusedEntries) updateHaloEntry(entry);
    requestAnimationFrame(tickHalo);
  }}
  requestAnimationFrame(tickHalo);

  function flyTo(n) {{
    if (!n) return;
    focusKV.style.display = '';
    focusAsn.textContent = 'AS' + n.id + (n.org ? ' · ' + n.org : '') + ' · ' + (n.cc || '??');
    // If the node isn't currently rendered (filtered out by region chip /
    // deg-0), its x/y/z are undefined — skip the fly so we don't lurch to
    // origin. The stats panel still shows the AS for reference.
    if (typeof n.x !== 'number') return;
    const distance = 80;
    const distRatio = 1 + distance / Math.hypot(n.x, n.y, n.z);
    Graph.cameraPosition(
      {{ x: n.x * distRatio, y: n.y * distRatio, z: n.z * distRatio }},
      n,
      1500,
    );
  }}

  function onClick(n) {{
    flyTo(n);
  }}

  // ---- Quick finder: search + cloud-provider shortcuts ---------------------
  // Curated well-known ASNs per cloud (public data from bgp.tools / PeeringDB).
  // Keep small — these are shortcuts; long-tail matches go through search.
  const CLOUD_PROVIDERS = [
    {{label:'AWS',        asns:[16509, 14618, 58838, 8987, 39111, 9059, 2905]}},
    {{label:'GCP',        asns:[15169, 396982, 36492, 36040, 43515, 139070]}},
    {{label:'Azure',      asns:[8075, 8068, 12076, 12271]}},
    {{label:'Cloudflare', asns:[13335, 395747, 209242, 133877]}},
    {{label:'阿里云',     asns:[45102, 37963, 45104, 134963, 59028]}},
    {{label:'腾讯云',     asns:[132203, 45090, 133478, 133199]}},
    {{label:'Baidu',      asns:[38365, 55967]}},
    {{label:'Oracle',     asns:[31898, 14413]}},
    {{label:'IBM',        asns:[36351, 6088, 1024]}},
    {{label:'Akamai',     asns:[20940, 16625, 32787, 21342]}},
    {{label:'DO',         asns:[14061]}},
    {{label:'Hetzner',    asns:[24940]}},
    {{label:'OVH',        asns:[16276]}},
  ];

  const findInput = document.getElementById('find-input');
  const findHint  = document.getElementById('find-hint');
  const chipRow   = document.getElementById('cloud-chips');

  let searchMatches = [];
  let searchIdx = 0;

  function pickBestFromPool(asns) {{
    // From a candidate ASN list, return the nodes that are in the pool,
    // sorted by IPv4 size descending (so the "main" AS comes first).
    const set = new Set(asns);
    return graphNodes
      .filter(n => set.has(n.id))
      .sort((a, b) => (b.v || 0) - (a.v || 0));
  }}

  function setMatches(list, label) {{
    searchMatches = list;
    searchIdx = 0;
    if (!list.length) {{
      setFocus([]);
      findHint.textContent = label ? `未找到 · no match (${{label}})` : '未找到 · no match';
      findHint.style.color = '#ff9f0a';
      return;
    }}
    findHint.style.color = '';
    const haloNote = list.length > HALO_CAP
      ? ` · 光环限前 ${{HALO_CAP}} 个`
      : '';
    findHint.textContent = list.length > 1
      ? `${{list.length}} 个匹配 · Enter 下一个${{haloNote}}`
      : '1 个匹配';
    // All matches light up a halo simultaneously — click a chip and every AS
    // of that cloud provider becomes visible at once. Camera flies to the
    // largest one (list is pre-sorted by IPv4 desc).
    setFocus(list);
    flyTo(list[0]);
  }}

  function focusNext() {{
    if (searchMatches.length <= 1) return;
    searchIdx = (searchIdx + 1) % searchMatches.length;
    findHint.textContent = `${{searchIdx + 1}} / ${{searchMatches.length}}`;
    flyTo(searchMatches[searchIdx]);
  }}

  function runSearch(raw) {{
    const q = (raw || '').trim();
    if (!q) {{
      searchMatches = [];
      setFocus([]);
      findHint.textContent = '—';
      findHint.style.color = '';
      return;
    }}
    const ql = q.toLowerCase();
    const asnMaybe = /^(?:as)?([0-9]+)$/i.exec(q);
    const matches = graphNodes.filter(n => {{
      if (asnMaybe && n.id === parseInt(asnMaybe[1], 10)) return true;
      if (n.org && n.org.toLowerCase().includes(ql)) return true;
      return false;
    }}).sort((a, b) => (b.v || 0) - (a.v || 0));
    setMatches(matches, q);
  }}

  // Debounce keystrokes so we don't re-search on every character.
  let searchTimer = null;
  findInput.addEventListener('input', e => {{
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => runSearch(e.target.value), 220);
  }});
  findInput.addEventListener('keydown', e => {{
    if (e.key === 'Enter') {{
      e.preventDefault();
      if (searchMatches.length > 1) {{
        focusNext();
      }} else {{
        runSearch(findInput.value);
      }}
    }} else if (e.key === 'Escape') {{
      findInput.value = '';
      runSearch('');
      setFocus([]);
      focusKV.style.display = 'none';
      findInput.blur();
    }}
  }});

  // Build cloud chips.
  CLOUD_PROVIDERS.forEach(cp => {{
    const hits = pickBestFromPool(cp.asns);
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.textContent = hits.length ? `${{cp.label}} (${{hits.length}})` : `${{cp.label}} —`;
    chip.disabled = hits.length === 0;
    chip.style.cssText = `
      background:rgba(13,17,23,0.9); color:var(--fg); border:1px solid var(--border);
      border-radius:999px; padding:3px 10px; font-size:11px; font-family:inherit;
      cursor:${{hits.length ? 'pointer' : 'not-allowed'}};
      opacity:${{hits.length ? 1 : 0.4}};
    `;
    chip.addEventListener('click', () => {{
      if (!hits.length) return;
      findInput.value = '';
      setMatches(hits, cp.label);
    }});
    chipRow.appendChild(chip);
  }});

  el.addEventListener('mousemove', e => {{
    tip.style.left = (e.clientX + 14) + 'px';
    tip.style.top  = (e.clientY + 14) + 'px';
  }});

  // ---- Resize ---------------------------------------------------------------
  window.addEventListener('resize', () => {{
    Graph.width(el.clientWidth).height(el.clientHeight);
  }});
}})();
</script>
</body>
</html>
"""


def main() -> int:
    nodes_path = os.path.join(DATA_DIR, 'nodes.json')
    links_path = os.path.join(DATA_DIR, 'links.json')
    out = os.path.join(HTML_DIR, 'as_force.html')
    if not os.path.exists(nodes_path) or not os.path.exists(links_path):
        save_placeholder_html(out,
                              '全球 AS 互联立体图 · 拓扑力图',
                              'Global AS Force Topology · awaiting data')
        print(f'[placeholder] wrote {out} (missing nodes.json/links.json; run step01+02 first)')
        return 0

    with open(nodes_path, encoding='utf-8') as f:
        nodes = json.load(f)
    with open(links_path, encoding='utf-8') as f:
        links = json.load(f)

    html = _build_html(nodes, links)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    size_kb = os.path.getsize(out) // 1024
    print(f'Wrote {out} ({size_kb} KB) — {len(nodes):,} nodes · {len(links):,} links')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
