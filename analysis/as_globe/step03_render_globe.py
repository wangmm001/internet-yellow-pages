"""Step 3: Render `html/as_globe.html` — geographic globe view.

Uses globe.gl (WebGL, from CDN). Self-contained HTML with inlined data.
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


GLOBE_GL_VERSION = '2.32'    # pinned; ships its own bundled Three.js.

DEFAULT_ARC_DENSITY_PCT = 25   # start at 25% to stay smooth on low-end GPUs
MAX_ARCS_HARD_CAP = 12000      # even at 100% never render more than this


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
        f'<div class="overlay top-left">'
        f'<h1>全球 AS 互联立体图 · 地球视图</h1>'
        f'<h2>Top 5,000 ASes · colored by region · sized by IPv4 space · peering arcs</h2>'
        f'<p>旋转拖拽地球，点击/悬停某个 AS 查看详情。</p>'
        f'<p>Drag to rotate. Hover a dot for AS details. '
        f'Toggle a region chip below to hide/show it.</p>'
        f'</div>'
        f'<div class="overlay top-right" id="stats-panel">'
        f'<div class="kv">节点 Nodes: <span id="n-count">…</span></div>'
        f'<div class="kv">对等弧 Arcs: <span id="a-count">…</span></div>'
        f'<div class="kv">真实坐标 Real geo: <span id="g-count">…</span></div>'
        f'</div>'
        f'<div class="overlay bottom">'
        f'{legend_html}'
        f'<div class="slider-row">'
        f'<span>对等弧密度 Arc density</span>'
        f'<input type="range" id="arc-slider" min="0" max="100" step="5" value="{DEFAULT_ARC_DENSITY_PCT}">'
        f'<span id="arc-pct">{DEFAULT_ARC_DENSITY_PCT}%</span>'
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
        'defaultArcDensityPct': DEFAULT_ARC_DENSITY_PCT,
        'maxArcsHardCap': MAX_ARCS_HARD_CAP,
    }, ensure_ascii=False, separators=(',', ':'))

    return f"""<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>全球 AS 互联立体图 · Global AS Globe</title>
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
    console.error('[as_globe]', e);
  }});
</script>
<script src="https://unpkg.com/globe.gl@{GLOBE_GL_VERSION}/dist/globe.gl.min.js" crossorigin="anonymous"
  onerror="document.getElementById('load-error').textContent='globe.gl CDN 加载失败 · CDN load failed';document.getElementById('load-error').style.display='block';"></script>
<script>
(function() {{
  if (typeof Globe === 'undefined') {{
    document.getElementById('load-error').textContent = 'globe.gl 未加载 · library did not load';
    document.getElementById('load-error').style.display = 'block';
    return;
  }}
  const DATA = {data_json};

  // ---- Index & derived structures --------------------------------------------
  const nodeById = new Map(DATA.nodes.map(n => [n.a, n]));
  const activeRegion = new Set(DATA.regionOrder);

  function arcForLink(l) {{
    const a = nodeById.get(l.s), b = nodeById.get(l.t);
    if (!a || !b) return null;
    return {{
      startLat: a.x, startLng: a.y,
      endLat:   b.x, endLng:   b.y,
      colorStart: DATA.regionColor[a.k] || '#8E8E93',
      colorEnd:   DATA.regionColor[b.k] || '#8E8E93',
      regions: [a.k, b.k],
    }};
  }}

  // Sort by summed node radius so the most-important (big-AS) links render first.
  const linkImportance = (l) => {{
    const a = nodeById.get(l.s), b = nodeById.get(l.t);
    return (a?.r || 0) + (b?.r || 0);
  }};
  const sortedLinks = DATA.links.slice().sort((x, y) => linkImportance(y) - linkImportance(x));

  function filteredArcs(densityPct) {{
    const keep = [];
    const pct = Math.max(0, Math.min(100, densityPct)) / 100;
    const limit = Math.min(DATA.maxArcsHardCap, Math.floor(sortedLinks.length * pct));
    for (let i = 0; i < sortedLinks.length && keep.length < limit; i++) {{
      const l = sortedLinks[i];
      const a = nodeById.get(l.s), b = nodeById.get(l.t);
      if (!a || !b) continue;
      if (!activeRegion.has(a.k) || !activeRegion.has(b.k)) continue;
      keep.push(arcForLink(l));
    }}
    return keep;
  }}

  function filteredNodes() {{
    return DATA.nodes.filter(n => activeRegion.has(n.k));
  }}

  // ---- Globe initialization --------------------------------------------------
  const el = document.getElementById('viz');
  const world = Globe()(el)
    .backgroundColor('#05070C')
    .globeImageUrl('https://unpkg.com/three-globe@2.31/example/img/earth-dark.jpg')
    .showAtmosphere(true)
    .atmosphereColor('#5E5CE6')
    .atmosphereAltitude(0.17)
    .pointsMerge(false)
    .pointAltitude(n => 0.005 + (n.r || 1.5) * 0.0025)
    .pointRadius(n => (n.r || 1.5) * 0.05)
    .pointColor(n => DATA.regionColor[n.k] || '#8E8E93')
    .pointResolution(6)
    .arcStroke(0.25)
    .arcAltitudeAutoScale(0.35)
    .arcDashLength(0.5)
    .arcDashGap(1.2)
    .arcDashAnimateTime(3200)
    .arcColor(a => [a.colorStart, a.colorEnd])
    .arcsTransitionDuration(0)
    .onPointHover(onHover)
    .onPointClick(onClick);

  // Auto-rotate lazily
  world.controls().autoRotate = true;
  world.controls().autoRotateSpeed = 0.35;

  // ---- Rendering update hooks -----------------------------------------------
  let arcDensity = DATA.defaultArcDensityPct;

  function refresh() {{
    const pts = filteredNodes();
    const arcs = filteredArcs(arcDensity);
    world.pointsData(pts).arcsData(arcs);
    document.getElementById('n-count').textContent = pts.length.toLocaleString();
    document.getElementById('a-count').textContent = arcs.length.toLocaleString();
    document.getElementById('g-count').textContent =
      pts.filter(n => n.g).length.toLocaleString() + ' / ' + pts.length.toLocaleString();
  }}

  refresh();

  // ---- Region filter chips ---------------------------------------------------
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

  // ---- Arc density slider ----------------------------------------------------
  const slider = document.getElementById('arc-slider');
  const pctLabel = document.getElementById('arc-pct');
  slider.addEventListener('input', e => {{
    arcDensity = +e.target.value;
    pctLabel.textContent = arcDensity + '%';
    refresh();
  }});

  // ---- Hover tooltip ---------------------------------------------------------
  const tip = document.getElementById('tip');

  function onHover(n) {{
    if (!n) {{ tip.style.display = 'none'; el.style.cursor = 'grab'; return; }}
    el.style.cursor = 'pointer';
    const regionZh = DATA.regionLabel[n.k]?.zh || '';
    const regionEn = DATA.regionLabel[n.k]?.en || '';
    const realGeo = n.g ? '(real)' : '(estimated)';
    tip.innerHTML = `
      <div><span class="asn">AS${{n.a}}</span>
           <span class="kv" style="margin-left:6px">${{n.c || '??'}} · ${{regionZh}}</span></div>
      <div class="kv">IPv4: ${{(n.v || 0).toLocaleString()}} 地址 addresses</div>
      <div class="kv">对等度 Peering degree: ${{n.d || 0}}</div>
      <div class="kv" style="margin-top:4px;opacity:0.75">${{regionEn}} ${{realGeo}}</div>
    `;
    tip.style.display = 'block';
  }}

  function onClick(n) {{
    if (!n) return;
    // Smoothly rotate so the clicked AS faces the camera.
    world.pointOfView({{ lat: n.x, lng: n.y, altitude: 1.6 }}, 1200);
  }}

  el.addEventListener('mousemove', e => {{
    tip.style.left = (e.clientX + 14) + 'px';
    tip.style.top  = (e.clientY + 14) + 'px';
  }});

  // ---- Resize ---------------------------------------------------------------
  window.addEventListener('resize', () => {{
    world.width(el.clientWidth).height(el.clientHeight);
  }});
}})();
</script>
</body>
</html>
"""


def main() -> int:
    nodes_path = os.path.join(DATA_DIR, 'nodes.json')
    links_path = os.path.join(DATA_DIR, 'links.json')
    out = os.path.join(HTML_DIR, 'as_globe.html')
    if not os.path.exists(nodes_path) or not os.path.exists(links_path):
        save_placeholder_html(out,
                              '全球 AS 互联立体图 · 地球视图',
                              'Global AS Globe · awaiting data')
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
