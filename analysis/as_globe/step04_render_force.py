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
        f'<div class="tooltip" id="tip"></div>'
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
    // r ∈ [1.5, 12] (log-scale of IPv4). force-graph's nodeVal is volume, so
    // screen radius ∝ nodeVal^(1/3). Using r^2.5 makes screen radius ~ r^0.83,
    // which stretches the visible ratio from ~1.8× to ~4.5× — hubs become
    // obvious planets, long tail stays as pebbles.
    .nodeVal(n => Math.max(0.3, Math.pow(n.r || 1.5, 2.5) * 0.05))
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

  function onHover(n) {{
    if (!n) {{ tip.style.display = 'none'; el.style.cursor = 'grab'; return; }}
    el.style.cursor = 'pointer';
    const regionZh = DATA.regionLabel[n.k]?.zh || '';
    const regionEn = DATA.regionLabel[n.k]?.en || '';
    tip.innerHTML = `
      <div><span class="asn">AS${{n.id}}</span>
           <span class="kv" style="margin-left:6px">${{n.cc || '??'}} · ${{regionZh}}</span></div>
      <div class="kv">IPv4: ${{(n.v || 0).toLocaleString()}} 地址 addresses</div>
      <div class="kv">对等度 Peering degree (pool): ${{n.d || 0}}</div>
      <div class="kv" style="margin-top:4px;opacity:0.75">${{regionEn}}</div>
    `;
    tip.style.display = 'block';
  }}

  function onClick(n) {{
    if (!n) return;
    focusKV.style.display = '';
    focusAsn.textContent = 'AS' + n.id + ' · ' + (n.cc || '??');
    // Fly camera to node.
    const distance = 80;
    const distRatio = 1 + distance / Math.hypot(n.x, n.y, n.z);
    Graph.cameraPosition(
      {{ x: n.x * distRatio, y: n.y * distRatio, z: n.z * distRatio }},
      n,
      1500,
    );
  }}

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
