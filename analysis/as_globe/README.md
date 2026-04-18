# `as_globe` — 全球 AS 三维互联全景 · Global AS Interconnect in 3D

一个基于 WebGL 的三维可视化，把全球最大的 5,000 个 AS（按 IPv4 地址空间排名）及其对等关系同时呈现在「地理地球」与「力导拓扑」两种视图里。按国家区域着色，按 IPv4 规模缩放，让全球互联网互联架构一眼可见。

A WebGL-based 3D visualization of the top 5,000 ASes by IPv4 address space plus their peering relationships, rendered in both a geographic globe and a force-directed topology view. Nodes are colored by country region and sized by IPv4 address count — the global Internet interconnect fabric at a glance.

## 视图 · Views

| Path | 视图 View | 库 Library | 用途 Purpose |
|------|----------|-----------|-------------|
| `html/as_globe.html` | 地理地球 Geographic Globe | [globe.gl](https://globe.gl) | 展示 AS 在地球上的真实/近似位置与跨境对等弧线 |
| `html/as_force.html` | 拓扑力图 Force Topology | [3d-force-graph](https://github.com/vasturiano/3d-force-graph) | 无地理约束、用力导自然聚出产业/区域社群 |

两个视图消费同一份 `data/nodes.json` + `data/links.json`，所以筛选/配色语义一致。

Both views consume the same `data/nodes.json` + `data/links.json`, so filters and palette stay consistent.

## 区域着色 · Region palette

| Bucket | ISO-2 | Hex | Label |
|--------|-------|-----|-------|
| `cn` | CN, HK, TW, MO | `#FF453A` | 大中华 Greater China |
| `na` | US, CA | `#0A84FF` | 北美 North America |
| `ea` | JP, KR | `#FF9F0A` | 东亚 East Asia (ex-GC) |
| `eu` | DE, GB, FR, NL, IT, ES, SE, CH, IE, BE, AT, DK, NO, FI, PL, PT, CZ, HU, RO, GR, BG, HR, SK, SI, LT, LV, EE, LU, MT, CY, IS | `#30D158` | 欧洲 Europe (EU+EEA+UK+CH) |
| `ot` | everything else | `#8E8E93` | 其他 Other |

节点半径 `r = clip(1.5 + log10(ipv4_count + 1) × 1.3, 1.5, 12)` 像素。

## 步骤 · Steps

| # | Script | Produces |
|---|--------|----------|
| 1 | `step01_extract.py` | `data_cache/as_globe/{as_country,as_ipv4,as_peers,as_geo}.csv` (Neo4j required) |
| 2 | `step02_decimate.py` | `data/nodes.json`, `data/links.json`, `data/step02_metrics.json` |
| 3 | `step03_render_globe.py` | `html/as_globe.html` |
| 4 | `step04_render_force.py` | `html/as_force.html` |

`step02`–`step04` only depend on the previous step's output — you can iterate on rendering without hitting Neo4j.

## 运行 · Running

两条抽取路径选其一 — Pick **one** extractor:

### A. 走 IYP Neo4j（需要本地或可达的 IYP 实例）

```bash
# 从仓库根目录 (repo root) — needs Neo4j on bolt://localhost:7687
python3 -m analysis.as_globe.step01_extract      # ~1–3 min for full IYP
```

### B. 直接从上游（BGPKit + NRO，不需要 Neo4j）

```bash
# ~20 MB 下载、~15 秒完成；用 IYP 的上游数据源（BGPKit pfx2as + as2rel-v4，
# NRO delegated stats）——和 IYP 抽取的结果在几何上对等，区别见 IMPLEMENTATION.md。
python3 -m analysis.as_globe.step01_extract_bgpkit
```

### 剩余步骤相同 · Rest is identical

```bash
python3 -m analysis.as_globe.step02_decimate     # seconds
python3 -m analysis.as_globe.step03_render_globe # seconds
python3 -m analysis.as_globe.step04_render_force # seconds

python3 -m analysis.web.build                    # wire into unified site

# Serve from repo root so cross-track iframe paths resolve.
python3 -m http.server 8000
# Open http://localhost:8000/analysis/web/site/globe/
```

Or open the rendered HTMLs standalone without the unified site:

```bash
open analysis/as_globe/html/as_globe.html
open analysis/as_globe/html/as_force.html
```

## 选择策略 · Decimation strategy

- 80K+ ASes 全量渲染会把浏览器拖死。
- 先按 **IPv4 源发地址数量** 取 Top 3,000（经济意义上的「大 AS」）。
- 再把与前 3K 至少有 2 条对等关系的邻居补进来，直到 5,000 为止（结构意义上的「支撑 AS」）。
- 丢弃端点不在池子里的对等边。
- 结果：~5K 节点 + 20K–60K 对等边，WebGL 下流畅。

## 数据来源 · Data provenance

- `:AS` → `:Country` (`COUNTRY`)：NRO delegated-stats + CAIDA ASRank
- `:AS` → `:BGPPrefix` (`ORIGINATE`)：BGPKIT pfx2asn
- `:AS` ↔ `:AS` (`PEERS_WITH`)：BGPKIT AS2Rel v4
- `:AS` → `:Point` (`LOCATED_IN`)：CAIDA ASRank（部分 AS 才有真实坐标；缺失时用国家质心 + 确定性抖动）

## 相关文件 · Related files

- 复用查询模式：`analysis/complex_network/step01_extract_bgp_layer.py`
- HTML 辅助：`analysis/china/common.py`（`save_plotly_html`, `try_neo4j_or_cached`）
- 站点接入：`analysis/web/nav.py`（`_build_globe_track`）+ `analysis/web/build.py`（`TRACK_BADGES['globe']`）
