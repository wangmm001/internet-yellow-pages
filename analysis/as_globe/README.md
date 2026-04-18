# `as_globe` — 全球 AS 三维互联全景 · Global AS Interconnect in 3D

一个基于 WebGL 的三维可视化，把全球最大的 5,000 个 AS（按 IPv4 地址空间排名）及其对等关系同时呈现在「地理地球」与「力导拓扑」两种视图里。按国家区域着色，按 IPv4 规模缩放，让全球互联网互联架构一眼可见。

A WebGL-based 3D visualization of the top 5,000 ASes by IPv4 address space plus their peering relationships, rendered in both a geographic globe and a force-directed topology view. Nodes are colored by country region and sized by IPv4 address count — the global Internet interconnect fabric at a glance.

## 视图 · Views

| Path | 视图 View | 库 Library | 用途 Purpose |
|------|----------|-----------|-------------|
| `html/as_strata.html` | **AS 都会 · Country Canopy**（旗舰）| raw Three.js r160 (ESM) | 一眼看懂「哪国占比多」+「谁跟谁 peer」+「谁是 tier-1」 |
| `html/as_globe.html` | 地理地球 Geographic Globe | [globe.gl](https://globe.gl) | 展示 AS 在地球上的真实/近似位置与跨境对等弧线 |
| `html/as_force.html` | 拓扑力图 Force Topology | [3d-force-graph](https://github.com/vasturiano/3d-force-graph) | 无地理约束、用力导自然聚出产业/区域社群 |

三个视图共用同一份 `data/nodes.json` + `data/links.json`，`as_strata` 额外读 `data/strata_cells.json` 与 `data/strata_bundles.json`（step05 产出）。

All three views consume `data/nodes.json` + `data/links.json`; `as_strata` additionally reads `data/strata_cells.json` + `data/strata_bundles.json` (produced by step05).

---

## AS 都会使用手册 · How to use `as_strata.html`

打开 `http://localhost:8000/analysis/web/site/globe/strata/`（或直接双击 `html/as_strata.html`）。

Open `http://localhost:8000/analysis/web/site/globe/strata/` (or double-click `html/as_strata.html` directly).

### 五通道视觉编码 · Five visual channels

The whole page answers "who owns what slice of the Internet" and "who peers with whom" with five orthogonal visual channels. Every pixel is measurable.

| # | 通道 Channel | 数据 Data | 直观含义 Reading |
|---|---|---|---|
| 1 | **扇区弧宽** Sector angular width | 该国在 Top-5K 中的 AS 数占比 | 本国养活了多少自治域 |
| 2 | **柱高** Pillar height | `log10(总对等边数)` | 该国 AS 的**对等密度** — 跑了多少条 peering |
| 3 | **柱粗** Pillar radius | `√(伙伴国数)` | 该国的**对等广度** — 接到多少个不同国家 |
| 4 | **球大小/高度** Sphere size + altitude | 单个 AS 的 IPv4 地址数（未截断，log）| 这是谁家的 tier-1 backbone |
| 5 | **柱顶环** Ring on top of pillar | `log10(国内 intra-country 对等边)` | 这个国的 AS 之间自己互联多不多 |
| 6 | **丝带** Ribbon between pillars | `log10(国家对的对等边数)` | 两国之间 peering 的厚度 |

**区域配色**（复用 IYP 全站语言）：大中华 🔴 · 北美 🔵 · 东亚 🟠 · 欧洲 🟢 · 其他 ⚪。**环色**为各自区色的高亮变体（浅珊瑚/粉蓝/杏色/薄荷/银），与柱色同色相但亮度高出一档，便于区分"柱身"与"柱顶"。

### 操作 · Controls

| 操作 | 行为 |
|---|---|
| 鼠标拖拽 | 旋转轨道相机 orbit |
| 滚轮 | 缩放 zoom |
| **点击柱子** | **只看该国的连线** — 其他国家的丝带 / 其他 AS 球全部变暗，相机飞到该国柱子上方。再次点击同一柱子或按 `R`/`Esc` 恢复。|
| **点击 AS 球** | 飞向该 AS，展开它的 peer 扇（其他所有对等丝带会变暗），右侧弹出信息面板 |
| **鼠标悬停** | 柱子显示国家 / AS 数 / 对等边 / 伙伴国数；球显示 ASN / IPv4 / 对等度 |
| **点击 `Esc`** 或 **`R`** | 清除所有聚焦（AS 或 国家），把所有丝带 / 环 / 柱恢复默认亮度 |
| **`T`** | 切到俯视（纯 treemap 读图 — 只看扇区占比）|
| **`G`** | 切到地平视角（天际线读图 — 看柱子高度对比）|
| **`R`** | 重置相机到默认斜视角 |
| **底栏 · 区域 chip**（🔴 🔵 🟠 🟢 ⚪） | 点击切换该区所有扇区+柱子+环+球的可见性（变暗到 0.05）|
| **底栏 · `Bundle floor` 滑块** | 隐藏对等数小于阈值的丝带。默认 `≥3`；拖到 `≥100` 只剩最粗的几十条骨干 |
| **底栏右下 · `图例 ＋`** | 展开完整通道说明（默认折叠）|

### 30 秒读图三步 · Read the chart in 30 s

1. **看扇区圆环**（俯视最清楚）：谁占得多？`EU` ≈ 37% 和 `NA` ≈ 26% 是大头，`CN` 只 5%。这是**按 AS 户籍人口**的分布。
2. **扫一眼柱子高度和粗细**：
   - **又高又粗** = 真 tier-1 枢纽（US / GB / CH / SG / BR）
   - **高但瘦** = 深度 peering 但伙伴少（JP 典型）
   - **矮但粗** = peering 广但每对都浅（AO 等小国海缆登陆点）
   - **矮又瘦** = 末端 stub 网络
3. **顺着丝带走**：最粗的几条 = 全球骨干。试把 `Bundle floor` 拖到 `≥300`，图上只剩 **GB↔US · AU↔US · CH↔DE · BR↔US · CH↔US · intra-US** —— 这就是全球对等骨架的最简地图。

### 环的读法 · Reading the rings

**只有自己国内 AS 之间有 peer 才会长出环**。9 个国家内部 mesh 强度最显眼（按对等边数排序）：

- **US 1942** — 美国是一张"自成一体"的网（环粗 28，次第缩小）
- **GB 302 · BR 242 · DE 202 · CN 187 · RU 180 · FR 155 · JP 139 · IT 110 · KR 93**

反过来，**CH / SG / NL 几乎没有环** — 它们作为中立交换枢纽的意义在**跨境**，不在国内。这个信号在扇区和柱子上都读不出来，**只有环能说出**。

### 聚焦一个 AS · Focusing on a single AS

点任意 AS 球 →
1. 相机飞到那一粒球的视角；
2. 所有 peer 连成一束"frayed" Bézier 曲线从它出发；
3. 右侧面板给出 ASN、IPv4、对等度、前 10 个样本 peer（编号 + 国家代码）；
4. 底栏 `聚焦` chip 显示当前焦点 ASN。

常见试水：**AS3356 (Lumen)** / **AS174 (Cogent)** / **AS15169 (Google)** / **AS13335 (Cloudflare)** / **AS4134 (ChinaNet)** — tier-1 一目了然。

### 读图进阶 · What questions the view answers

| 问题 Question | 怎么看 How |
|---|---|
| 哪些国家是全球对等骨干？| 柱最粗 + 柱最高 + 接入丝带最厚 → US / GB / DE / CH / BR |
| 哪些国家"AS 多但连接少"？| 扇区大但柱矮/细 → NL（209 AS 但 intra 只 15 条）|
| 哪些国家"AS 少但连接广"？| 扇区小但柱粗 → SG（47 AS · 82 伙伴国，全球最高）|
| 中国大陆怎么走向世界？| 拖 `Bundle floor` ≥50 观察哪些 CN↔X 丝带留到最后 → 主要通过 HK，少量直连 US / RU |
| 一个具体 AS 的出口依赖？| 点该 AS，看右侧 top-10 peer 的国家分布 |

### 如果数据缺失 · If the JSON isn't there

如果 `data/nodes.json` 或 `data/links.json` 不存在，`step05_render_strata.py` 会写一个占位 HTML（解释缺什么、怎么补）。`analysis/web/build.py` 不会因此失败 —— 统一站点仍可全量构建。

If `data/nodes.json` or `data/links.json` is missing, `step05_render_strata.py` emits a placeholder HTML telling you what to regenerate. `analysis/web/build.py` stays green — the unified site still builds.

---

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
| 1b | `step01_extract_bgpkit.py` | same four CSVs, via BGPKit + NRO — no Neo4j required |
| 2 | `step02_decimate.py` | `data/nodes.json`, `data/links.json`, `data/step02_metrics.json` |
| 3 | `step03_render_globe.py` | `html/as_globe.html` |
| 4 | `step04_render_force.py` | `html/as_force.html` |
| 5 | `step05_render_strata.py` | `html/as_strata.html` + `data/strata_cells.json` + `data/strata_bundles.json` + `data/step05_metrics.json` |

`step02`–`step05` only depend on the previous step's output — you can iterate on rendering without hitting Neo4j.

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
python3 -m analysis.as_globe.step02_decimate       # seconds
python3 -m analysis.as_globe.step03_render_globe   # seconds
python3 -m analysis.as_globe.step04_render_force   # seconds
python3 -m analysis.as_globe.step05_render_strata  # seconds (flagship view)

python3 -m analysis.web.build                      # wire into unified site

# Serve from repo root so cross-track iframe paths resolve.
python3 -m http.server 8000
# Open http://localhost:8000/analysis/web/site/globe/
```

Or open the rendered HTMLs standalone without the unified site:

```bash
open analysis/as_globe/html/as_strata.html   # 旗舰视图 · flagship
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
