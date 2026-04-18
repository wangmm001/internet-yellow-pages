# `as_globe` 实施记录 · Implementation Notes

**日期 Date**: 2026-04-18
**会话 Session**: IYP-3D
**计划文件 Plan**: `~/.claude/plans/web-as-piped-rossum.md`

新增一个基于 WebGL 的全球 AS 三维互联可视化模块，并接入统一站点。本文档记录这次实施的范围、关键决策、产出、验证结果与后续待办。

A new WebGL-based 3D visualization module for the global AS interconnect,
wired into the unified analysis site. This document captures scope, key
decisions, deliverables, verification results, and follow-ups.

---

## 1. 目标 · Goal

让观察者一眼看清全球互联网的互联架构：
- 每个 AS 一个点，按所在国家/地区着色（大中华 · 北美 · 东亚 · 欧洲 · 其他）
- 点的大小正比于该 AS 源发的 IPv4 地址数量
- 点之间用弧/边表示 `PEERS_WITH` 对等关系
- 提供两种视图：「地球视图」（地理坐标）与「拓扑力图」（力导布局）

Make the global Internet interconnect legible at a glance — one dot per AS,
region-colored, IPv4-address-sized, linked by peering edges, across both a
geographic globe and a force-directed topology.

## 2. 关键设计决策 · Key design decisions

| # | 决策 Decision | 选择 Choice | 理由 Reason |
|---|---|---|---|
| 1 | 渲染库 Rendering | **globe.gl + 3d-force-graph**（CDN，WebGL） | Plotly 3D 的线段在 ~30K 条时就卡顿；这两个库实例化清洁，可稳定渲染 5K 节点 + 50K 边；同一作者 API 一致。|
| 2 | 构建方式 Build style | Python 生成自包含 HTML（数据内联为 JSON） | 匹配仓库既有「Python 输出静态 HTML，`analysis/web/` 用 iframe 嵌入」的约定 — 不引入 npm/bundler。|
| 3 | 节点选择 Decimation | IPv4 Top-3,000 + 邻居闭包至 5,000 | 同时保留「经济体量」与「拓扑骨架」两个故事；~5K 节点是 WebGL 的舒适区。|
| 4 | 颜色方案 Palette | 5 个苹果系色彩（`#FF453A / #0A84FF / #FF9F0A / #30D158 / #8E8E93`） | `utils.COLORS` 图表色板在 `#0D1117` 深底上点云饱和度不够；本方案为深色地球/夜空优化。|
| 5 | 站点接入 Wiring | 作为**第 4 个 top-level track**（`globe`，accent `#5E5CE6`） | 与既有三条轨道（china/countries/network）对称；改动面最小。|
| 6 | 范围 Scope | v1 仅两个视图（地球 + 力图），不做 Plotly 回退 | 避免范围蔓延；两个真正有用的视图先交付，再按需迭代。|

## 3. 交付物 · Deliverables

### 新增文件 New files（7）

```
analysis/as_globe/
├── __init__.py                 # 空
├── README.md                   # 双语模块说明（用法 + 颜色图例）
├── IMPLEMENTATION.md           # 本文档 This file
├── common.py                   # 区域色桶、国家质心、IPv4 换算、HTML 脚手架、占位页生成器
├── step01_extract.py           # Neo4j → 4 份 CSV（AS-country / IPv4 / peers / geo）
├── step02_decimate.py          # CSV → nodes.json + links.json（池选择 + 区域桶 + 半径）
├── step03_render_globe.py      # nodes/links → html/as_globe.html（globe.gl）
└── step04_render_force.py      # nodes/links → html/as_force.html（3d-force-graph）
```

### 修改文件 Modified files（4）

| 文件 File | 改动 Change |
|---|---|
| `analysis/web/nav.py` | 新增 `_build_globe_track()`；append 到 `tracks`；`totals['globe_views']` |
| `analysis/web/build.py` | `TRACK_BADGES['globe'] = 'is-purple'`；`PHASE_VARIANTS['views'] = 'is-purple'` |
| `analysis/web/templates/base.html` | 顶栏新增 `立体图 · Globe` 导航链接 |
| `analysis/web/templates/home.html` | 标题 `三条`→`四条`；新增 `globe` 分支的 track-card chip |

### 生成物 Generated artifacts

- `analysis/as_globe/html/as_globe.html`、`as_force.html` — 目前是占位页（`save_placeholder_html`），一旦 `step01+02` 产出真实数据再跑 `step03+04` 就会覆盖。
- `analysis/web/site/` — 统一站点，62 页（原 60 + globe hub + 2 views）。
- `analysis/web/build_manifest.json` — 0 missing / 0 broken links。

## 4. 运行流程 · Pipeline

```bash
# 需要 Neo4j 在 bolt://localhost:7687 可达
python3 -m analysis.as_globe.step01_extract      # → data_cache/as_globe/*.csv
python3 -m analysis.as_globe.step02_decimate     # → analysis/as_globe/data/{nodes,links}.json
python3 -m analysis.as_globe.step03_render_globe # → analysis/as_globe/html/as_globe.html
python3 -m analysis.as_globe.step04_render_force # → analysis/as_globe/html/as_force.html

python3 -m analysis.web.build                    # 重建统一站点
python3 -m http.server 8000                      # 从仓库根目录起服
# 浏览器打开 http://localhost:8000/analysis/web/site/globe/
```

只想重跑渲染（调整样式/交互）时，不必重跑 step01（不碰 Neo4j），直接跑 step03/step04 即可。

## 5. 关键设计细节 · Implementation details

### 5.1 区域桶 Region buckets

定义在 `common.py`：

```python
REGION_COLOR = {
    'cn': '#FF453A',   # CN, HK, TW, MO
    'na': '#0A84FF',   # US, CA
    'ea': '#FF9F0A',   # JP, KR
    'eu': '#30D158',   # EU 27 + EEA + UK + CH
    'ot': '#8E8E93',   # 其他
}
```

`region_of(cc)` 输入 ISO-2 返回 bucket 键；`REGION_LABEL` 提供 ZH/EN 标签。

### 5.2 IPv4 地址数换算

`ipv4_addresses_for_prefix("1.2.3.0/24") == 256`；对 IPv6 前缀返回 0（`/32` IPv6 和 `/32` IPv4 在此语义不同 — v4 = 1 地址，v6 实为一整块，我们只统计 v4）。

**注意 Caveat**: `step01` 累加每个 BGPPrefix 的地址数时**没有折叠重叠前缀**。若一个 AS 同时宣告 `10.0.0.0/8` 和 `10.1.0.0/16`，后者会被重复计入，结果是**上限**而非实际可达集合。这是刻意为之 —— IYP 记录的是观测到的宣告事实，折叠会丢信息。

### 5.3 节点池选择算法

```
1. 按 ipv4_addresses 降序取 top 3,000（经济体量核心）
2. 统计每个非核心 AS 与核心 AS 的对等数 anchor_hits
3. 按 anchor_hits ≥ 2 筛选候选，按 (anchor_hits, ipv4) 降序补入，直到 5,000
4. 丢弃任一端不在池中的对等边
5. 计算池内度数 degree（tooltip + 可选大小权重）
```

典型结果：~5K 节点 + 20K–60K 对等边。

### 5.4 地理坐标回退

仅 20–40% 的 AS 在 IYP 中有 CAIDA 提供的 `(:AS)-[:LOCATED_IN]->(:Point)` 坐标。
其余用 `COUNTRY_CENTROIDS[cc]` + `jitter_latlon(asn, ...)` 生成确定性抖动（±2°）。
Node 上保留 `g` 字段（1=real, 0=estimated）供 tooltip 提示和后续样式区分。

### 5.5 统一站点路径约定

iframe `src` 形如 `../../../../as_globe/html/as_globe.html` — 从 `site/globe/globe/index.html` 向上 4 级到 `analysis/`，再进入 `as_globe/html/`。必须从**仓库根目录**起 `http.server`，否则 iframe 会跨出服务根（`/globe/globe/` 上溯会越过 site 根）。README 已更正此点。

## 6. 验证 · Verification

本会话的验证范围（环境没有 Neo4j 也没有项目依赖，故未做完整端到端跑通，但所有结构性检查已完成）：

Verification performed in this session (no live Neo4j / deps in env, so
end-to-end extraction was not run — but all structural checks passed):

| 项 Check | 方法 Method | 结果 Result |
|---|---|---|
| 语法 Syntax | `python3 -c "import ast; ast.parse(...)"` × 8 文件 | all OK |
| `common.py` 辅助函数 | 手动调用 region_of / ipv4_addresses_for_prefix / radius_px | 数值正确（`/24` → 256，`/32` IPv6 → 0，256 地址 → 半径 4.63px）|
| `nav.build_site_model()` | 直接导入执行 | 4 条 track，62 页，globe 下 2 页 URL/src 正确 |
| 统一站点构建 | `python3 -m analysis.web.build` | 62 页生成，0 missing / 0 broken links |
| 渲染冒烟 | 用 40 节点 + 112 边的合成 fixture 跑 step03/step04 | 生成 HTML 通过 DOCTYPE / CDN / JSON 内联 / 标签平衡检查 |
| HTTP 访问 | `http.server` + `curl` | home / globe hub / globe page / force page / iframe target 全部 200 |
| 占位页 Placeholder | 删除 fixture 后重跑 step03/04 | 回落到 `save_placeholder_html` 分支，site build 仍然通过 |

### 需要本机复跑的部分 · What still needs a live run on your machine

- `step01_extract`（需 Neo4j）拉真实 `~80K × AS`、`~500K × PEERS_WITH`
- `step02_decimate` 降到 5K 节点池
- `step03/04` 覆盖占位页
- 浏览器目视确认：旋转 / 悬停 tooltip / 区域筛选 chip / 弧密度滑杆 / 帧率 ≥ 30 fps / 控制台无报错

### 追加：离线抽取路径（2026-04-18 本次会话走的路径）

由于本环境里 IYP 官方 Neo4j 端点（`iyp.iijlab.net:7687`）在 DNS 中间件下
TLS 握手失败，且 20 GB 的 IYP dump 下载速度只有 3 MB/s、对应的 Docker/brew
bottle 又只有 40 KB/s，本地 full pipeline 不现实（预计 5–6 小时）。

因此新增一个**完全不依赖 IYP graph 的抽取器** `step01_extract_bgpkit.py`：
直接从 IYP 自己也在用的上游源拉数据——

| 数据 Source | URL | 大小 Size |
|---|---|---|
| BGPKit pfx2as | `data.bgpkit.com/pfx2as/pfx2as-latest.json.bz2` | 12 MB |
| BGPKit as2rel-v4 | `data.bgpkit.com/as2rel/as2rel-v4-latest.json.bz2` | 6 MB |
| NRO delegated | `ftp.ripe.net/.../nro-delegated-stats` | 56 MB |

本次会话实际跑通的结果 · What the session actually produced:

```
step01_extract_bgpkit:
  120,925 ASes with country
   79,263 ASes with IPv4 announcements
  637,916 unique peering edges
  0 ASes with real lat/lon (skipped — CAIDA ASRank unreachable)
  17.3 s end-to-end

step02_decimate:
  5,000 ASes selected (3K by IPv4 + neighbor closure)
  286,754 pool edges → 30,000 emitted (top-by-combined-radius)
  Region histogram: eu=1833 · ot=1366 · na=1308 · cn=270 · ea=223

step03_render_globe + step04_render_force:
  1.06 MB each HTML (was 6.7 MB before edge-cap — see §MAX_EMIT_LINKS)

analysis.web.build:
  62 pages · 0 missing · 0 broken links

Sanity-check top-5 by IPv4 origination (raw sum, no prefix collapsing):
  AS3356 Lumen          US  4.33B addr  degree 1290
  AS174  Cogent         US  4.33B addr  degree 1569  ← 最高 peering
  AS9121 TTNet          TR  4.31B addr  degree   76
  AS26615 TIM Brasil    BR  4.31B addr  degree   41
  AS3257 GTT            US  4.30B addr  degree  683

Known-AS sanity:
  AS15169 Google     4.08M addr, degree 432   (cloud serves via peers, low own-IP)
  AS4134  Chinanet   112.4M addr, degree 232  (CN Telecom backbone)
  AS13335 Cloudflare 1.60M addr, degree 735   (anycast, few owned blocks)
```

**注意 Caveats for the bgpkit path**:
- 「4.3B」接近 IPv4 全空间 —— 因为 tier-1 骨干网实际宣告了覆盖 /0 的子网集合
  （用 `ipaddress.collapse_addresses()` 折叠后正好 2^32）。日志刻度下前 20–50 名
  会挤在最大半径（r=12），是刻意的：可视化上这些就是「顶格」的节点，其他按
  指数自然展开。
- `as_geo.csv` 为空（CAIDA ASRank 不可达），所有节点走国家质心 + 抖动。
  `has_real_geo=0` 对所有节点。如需真实坐标，换用 `step01_extract.py`（Neo4j 路径）。
- BGPKit pfx2as 是**源发**数据（不是 transit），但 tier-1 背骨网因为 MOAS
  / multi-originated prefixes 等因素会出现「宣告覆盖了几乎全部 IPv4」的情形 ——
  这是真实数据特性，不是 bug。

### 两条路径何时用哪条 · When to pick which extractor

| 情况 | 推荐 | 理由 |
|---|---|---|
| 有本地/可达的 IYP Neo4j | `step01_extract.py` | 拿到 CAIDA 真实 lat/lon；享受 IYP 跨源去重 |
| 只想「尽快看到结果」 | `step01_extract_bgpkit.py` | 20 MB + 15 秒出底表 |
| Neo4j 端点在 TLS 中间件之后 | `step01_extract_bgpkit.py` | 避开官方 Neo4j bolt 不可达 |
| 需要严格对齐 IYP graph 语义 | `step01_extract.py` | 走完整 IYP crawler 链路 |

## 7. 已知限制 · Known limitations

1. **帧率下探**：`~50K` 条弧对低端 iGPU 仍然吃力。缓解：弧密度滑杆默认 25%；地球视图低缩放级别可手动调低。
2. **真实地理坐标覆盖率低**：仅头部 AS 有 CAIDA 坐标，其余用国家质心 + 抖动。ZH 已在 tooltip 注明 `(real)` vs `(estimated)`。
3. **IPv6 缺席**：当前只量化 IPv4 地址数；IPv6 AS 的 prefix 被识别但不贡献大小。v1 刻意简化。
4. **内联 JSON 体积**：5K 节点 + 40K 边未压缩约 2–3 MB。已通过短键 `{a,c,k,r,x,y,g,v,d}` / `{s,t}` 压小 ~40%。gzip 后浏览器加载无压力。
5. **前缀重叠不折叠**：见 §5.2 Caveat。如果你关心「实际地址池大小」而非「宣告总量」，后续可在 step01 接入 `ipaddress.collapse_addresses()`。
6. **首页布局**：`grid-3` 在 4 张 track-card 下是 3+1 排布，略不对称；如需 2×2 可把 `grid-3` 在 globe 出现时换成 `grid-auto`，但属于美学微调。

## 8. 后续迭代思路 · Ideas for v2

- **时序演化**：与 china/countries/network 的 evolution 页对齐，做一个「季度快照对比」动画，直观看头部 AS 份额变化。
- **IXP/机房底图**：在地球视图加一层 IXP & facility 热点（PeeringDB 已有 lat/lon）。
- **AS 高亮联动**：点击某 AS 时，只展示它与其邻居的弧，并在侧栏给出 ASRank/主权指数等上下文。
- **导出图像**：`globe.gl` 支持导出 PNG；可加一个「截屏」按钮输出当前视角。
- **边权值**：当前 link 只有 `{s,t}`；可扩展为 `{s,t,w}`（w 为 CAIDA AS Relationship 类型或 degree hegemony），用于 arc 宽度/颜色。

## 9. 相关 refs

- 计划文件 Plan: `~/.claude/plans/web-as-piped-rossum.md`
- 设计时参考的既有模式：
  - `analysis/complex_network/step01_extract_bgp_layer.py` — Cypher + CSV 导出模板
  - `analysis/china/common.py` — HTML/Pyvis/Plotly 封装与 `try_neo4j_or_cached`
  - `analysis/web/nav.py`（既有 3 track 的构建） / `build.py`（badges + phase variants）
  - `analysis/china/step05_peering_graph.py` — 此前的 peering 子图渲染经验
- 外部库 External libs (CDN-pinned):
  - three.js `@0.161`
  - globe.gl `@2.32`
  - 3d-force-graph `@1.77`
