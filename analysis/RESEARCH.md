# IYP 研究说明与进展记录

## Research Notes · Philosophy · Requirements · Progress

> 基于 Internet Yellow Pages (IYP) Neo4j 知识图谱的科研分析 · Last updated 2026-04-17

---

## 一、研究思想 · Research Philosophy

### 1.1 总目标 · Overall goal

利用 IYP 作为一个覆盖全球互联网所有主要本体（~40 种节点类型、~34 种关系类型、~50 个数据源）
的"统一知识底座"，从**顶级互联网科学家的视角**回答两类科学问题：

1. **结构问题 (Structure)**：互联网在各个层（BGP / DNS / 物理 / 组织 / 地理）的拓扑是什么？
   有哪些 hub、core、community、依赖路径？
2. **关系问题 (Relation)**：单一实体（AS / 国家 / 组织）在全球互联网中的**位置、角色、脆弱性**
   与其它实体之间如何构成依赖、主权、风险传导链？

Leveraging IYP as a unified knowledge substrate covering all major Internet ontologies
(~40 node types × ~34 relationship types × ~50 data sources), we answer two classes of
scientific questions through the lens of top-tier Internet scientists: **structure**
(what is the topology of each Internet layer?) and **relation** (how is a single entity —
AS, country, organization — positioned in the global hierarchy, and what dependencies /
sovereignty / systemic-risk chains connect it to the rest?).

### 1.2 学术视角 · Academic lenses

每个分析步骤明确标注其"既有科学假设"与"IYP 数据验证/反驳/扩展"的关系。可用视角：

- **复杂网络科学** (Barabási, Newman, Clauset, Fortunato)：幂律 / 小世界 / k-core /
  community / assortativity / 鲁棒性 / 级联失效
- **AS Hegemony** (Fontugne, Pelsser, IHR)：用 BGP 路径份额量化 AS 的"不可绕过性"
- **关键基础设施** (Labovitz, Feamster)：Tier-1 分析、单点失效、路由收敛
- **DNS 主权** (Mueller, ten Oever)：国家域名空间的运营商国籍 / 管辖权 / 弹性
- **审查拓扑** (Roberts, Gill, Filasto)：OONI 检测结果与 AS 拓扑位置的相关性
- **测量方法论** (CAIDA, RIPE Atlas)：探针分布的观测盲点量化

Each analysis step declares the prior-science hypothesis and whether IYP data
confirms / refutes / extends it.

### 1.3 方法论 · Multi-scale method

采用**三尺度金字塔**：

| Scale | 目标 | 代表工作 | 步数 |
|---|---|---|---|
| 全局 Global | 互联网整体拓扑规律 | `analysis/complex_network/` | 24 |
| 单实体 Single-entity | 一个 AS 的全链路画像 | `analysis/cloudflare_analysis.py` | 25 |
| 国家 Country | 一国在全球分层中的位置 | `analysis/china/` | 20 |

同一组本体被反复使用——通过"全局 → 实体 → 国家"的过滤视角在不同尺度产生互补洞见。

---

## 二、工程与交付要求 · Engineering & Deliverable Requirements

### 2.1 每步四件套 · Four-artifact rule

每个分析步骤必须在同一次运行内产出：

1. **Cypher 日志**（脚本 docstring 或 `data/stepNN_query.cql`）— 完整可复现的查询
2. **CSV 数据**（`data/*.csv`）— 本步骤的原始/派生数据
3. **Metrics JSON**（`data/stepNN_metrics.json`）— 关键数值，供总报告自动装配
4. **可视化**（HTML 或 PNG）— 交互式图表（Plotly/Pyvis）或静态 PNG（matplotlib）

### 2.2 可复现性 · Reproducibility

- 所有大原始数据 CSV 进入 `data_cache/` (gitignore)，**不**随代码分发；
  可从 Neo4j 重新生成（见 `analysis/complex_network/step01-04_extract_*.py`）
- 所有分析结果（小 CSV + metrics JSON + HTML/PNG）进入 `analysis/`，**随代码提交**
- 数据路径通过 `analysis/complex_network/utils.py` 的 `DATA_DIR` 统一，
  支持环境变量 `IYP_ANALYSIS_DATA_DIR` 覆盖
- Neo4j 不可用时优雅降级（`common.try_neo4j_or_cached()`），生成 placeholder HTML
  指示如何补齐

### 2.3 代码复用 · Reuse-first

禁止重写已有功能。必须复用的：

- `analysis/complex_network/utils.py`：`COLORS`, `DARK_BG/PANEL/BORDER`, `run_query`,
  `get_neo4j_driver`, `save_fig`
- `analysis/complex_network/step13_concentration_hhi.py`：`gini_coefficient`,
  `hhi_index`, `lorenz_curve`
- `analysis/complex_network/step07_centrality_analysis.py`：中心性 CSV 格式
- `analysis/complex_network/step08_kcore.py`：k-core CSV 格式
- `analysis/china/common.py`：`save_plotly_html`, `save_pyvis_html`,
  `save_placeholder_html`, `writeup`, `load_cn_ases`, `iso2_to_iso3`

### 2.4 视觉规范 · Visual conventions

- 暗色主题：`#0D1117` 背景 / `#161B22` 面板 / `#30363D` 边框 / `#E6EDF3` 主文本
- 国家强调色：CN `#FF6B6B` / US `#45B7D1` / EU `#B39DDB` / 其它 `#4ECDC4`
- Plotly 使用 `include_plotlyjs='inline'`（离线可阅）；大型网络图使用 Pyvis
- 标题与说明双语：中文主位、英文次位；表头同时展示两种

### 2.5 文档规范 · Documentation

- 每个子分析目录必须有一个 `README.md`（中文主，英文次）
- 每步脚本 docstring 包含：维度 / 数据 / 输出 / 可选命令
- `run_all.py --report` 必须能从 metrics JSON 自动重生成 README

---

## 三、已完成工作 · Completed Work

### 3.1 全球复杂网络分析（24 步） · Global complex-network analysis

**路径**：`analysis/complex_network/` · **报告**：`analysis/Complex-Network-Analysis-Report.md`

关键发现：

- 网络规模：~87K AS 节点、~710K 对等边、四层（BGP/DNS/物理/组织）
- **小世界**：聚类系数是随机图的 **1,675 倍**，`σ_SW = 1,819.72`
- **负同配性** `r = −0.300`：hub-and-spoke 结构
- **k-core**：最内核 `k_max = 197`，仅 **340 个 AS (< 0.4%)**
- **脆弱性双面**：随机攻击需 30% 节点才瓦解；PageRank 定向攻击仅需 1.5%
- **级联放大**：单点 AS6939 失效可波及 93% 全球 AS
- **108 个社区** (Louvain modularity `Q = 0.445`)

### 3.2 Cloudflare 全链分析（25 步） · Cloudflare single-AS deep-dive

**路径**：`analysis/cloudflare_analysis.py` · **报告**：`analysis/Cloudflare-Full-Analysis.md`

覆盖 AS13335 的身份 → BGP → IXP/Facility → Org → DNS/Web → Ranking → Censorship →
Geography → Atlas → Risk 共 25 步，建立了"单实体全链画像"方法论模板。

### 3.3 中国在全球互联网分层中的位置（20 步）· China study

**路径**：`analysis/china/` · **报告**：`analysis/china/README.md` ·
**入口**：`python3 -m analysis.china.run_all`

完成日期：2026-04-16 ~ 2026-04-17。核心成果：

**规模维度 · Scale**

| 指标 Metric | CN 全球排名 | 数值 |
|---|---|---|
| AS 数 | #3 | 6,660 |
| BGP 前缀数 | #3 | 109,409 |
| IXP 数 | #16 | 19 |
| Facility 数 | #33 | 30 |

**拓扑位置 · Topology** — 超出预期的"头部"表现：

- `AS38255 (CERNET)` 全球 PageRank **#1**
- `5 个 CN AS` 进入全球 k-core `k ≥ 100` 最深层
- 最佳 Betweenness 排名 **#3**（超过部分 Tier-1）

**依赖关系 · Hegemony**

- **出向**：7,505 条依赖边，`AS6939 (Hurricane Electric, US)` 被 **5,062 个 CN AS** 依赖
- **入向**：仅 144 条边、88 个外部依赖者 → CN 以**终端**角色为主，尚未成为全球中继

**集中度 · Concentration**

- CN 前缀 Gini `0.943` vs 全球 `0.849` → CN 更加集中
- CN 前缀 HHI `0.0475` vs 全球 `0.0014` → CN ≈ **34×** 更集中

**物理层 · Physical**

- IXP 互联 839 条记录中 **境内仅 6 IXP 参与**；主要境外枢纽：DE-CIX Frankfurt、ZXIX HK、NL-ix、LINX
- CN AS 机房分布：HK(57) · US(56) · JP(25) · CN(24) · SG(14) — 香港是最大"出境"枢纽

**DNS 与内容 · DNS & content**

- CN AS 托管 `280,224` 个 HostName，全球排名 `#42`
- Top 托管方：`AS37963 (Aliyun)`、`AS24429 (Tencent)`、`AS45102`
- **`.cn` 域名 NS 主权率 仅 14.34%**（Aliyun 占主导，Cloudflare/GoDaddy 等境外运营商显著）
- CNAME 链：1,472 个跨境别名目标指向 Aliyun / Huawei CDN / Tencent Cloud

**安全与可观测 · Security & measurement**

- 23 个 CN AS 检出 OONI 审查信号（总 637 次）；与 `AS45102 / AS4837 / AS4134` 高度相关
- CN 境内 RIPE Atlas 探针 698 个（全球相对稀少，仍是测量盲点）

**综合主权指数 · Composite Sovereignty Index = 0.256** (five components, range 0-1)

| Component | 值 |
|---|---|
| 托管自给率 Hosting Sovereignty | **0.934** |
| DNS 自主率 DNS Sovereignty | 0.143 |
| 路由安全 RPKI Adoption | 0.156 |
| IXP 本地化 IXP Domesticization | 0.025 |
| 入向/出向 Hub-Ratio | 0.019 |

→ 综合叙事：中国在**规模**与**托管容量**上已进入全球第一梯队，但**互联基础设施密度**、
**DNS 主权**、**全球转运角色**仍显著落后。

---

## 四、当前限制 · Current Limitations

1. **Step 19 Atlas 坐标查询**：`AtlasProbe → Point` 关系在 IYP 当前 schema 下未直接挂接，
   导致地理散点图缺失；需要改用 AS→Country 聚合绘制
2. **HTML 体积**：91 MB（`include_plotlyjs='inline'` 每文件 ~4.5 MB），
   未来可切换 `'cdn'` 或 `'directory'` 模式
3. **`.cn` 域名枚举 LIMIT 500**：仅代表 NS 提供商分布，非全量；需要更细粒度查询后再结论
4. **审查数据稀疏**：仅 148 条 CN 记录，不足以区分系统性 vs 偶发
5. **时间维度缺失**：所有分析基于 2026-04 单时点快照；演化趋势未触及
6. **HK / TW / MO 单独列出**，但未做跨境依赖细分分析

---

## 五、后续研究方向 · Future Directions

### 5.1 近期 · Near-term

- **美国 / 俄罗斯 / 日本 / 欧盟** 平行 20 步分析，形成跨国对比矩阵
- Step 19 改用"AS+Country 聚合地理散点"替代 Point 查询
- HTML 切换 Plotly `'directory'` 模式（单次 plotly.min.js，减少 ~85% 仓库体积）
- `.cn` 全量枚举 (`LIMIT` 提升至 50,000+) 重跑 Step 15

### 5.2 中期 · Mid-term

- **时序演化**：对比不同快照（2024-04 / 2025-04 / 2026-04）的 CN 主权指数、hub-ratio、
  RPKI 覆盖率变化曲线
- **跨国依赖二次图**：将各国 20 步结果投射为"国家 × 国家"依赖矩阵，量化数字地缘结构
- **内容地理**：结合 CrUX Top-1M × HostName → IP → Prefix → AS → Country 链路，
  度量"用户可见 Web"的国家分布

### 5.3 长期 · Long-term

- **跨层级因果**：在 BGP 断联、DNS 劫持、RPKI ROA 更改等事件发生前后做时间窗对比，
  推断不同本体层之间的因果传导速度
- **可观测性补全**：结合 Cloudflare Radar、Google CrUX、APNIC Eyeball 构造复合可观测性指数
- **模型化**：将"主权指数"拓展为含不确定度的 Bayesian 模型；与 OECD ICT 指标对齐

---

## 六、复现要点 · How to reproduce

```bash
# 环境 Environment
pip install -r requirements.txt
pip install plotly pyvis kaleido

# 启动 Neo4j (参见顶层 README)

# 首次：重建数据缓存（约 10-30 min）
python3 -m analysis.complex_network.step01_extract_bgp_layer
python3 -m analysis.complex_network.step02_extract_dns_layer
python3 -m analysis.complex_network.step03_extract_physical_layer
python3 -m analysis.complex_network.step04_extract_org_censorship

# 运行各主线分析
python3 -m analysis.complex_network.step05_degree_distribution    # ... step24
python3 analysis/cloudflare_analysis.py
python3 -m analysis.china.run_all                                  # 20 步

# 单步重跑 / 验证 / 重生成索引
python3 -m analysis.china.run_all --step 7
python3 -m analysis.china.run_all --verify
python3 -m analysis.china.run_all --report

# 查看
xdg-open analysis/china/html/index.html
```

---

## 七、变更日志 · Change log

| 日期 Date | 变更 Change |
|---|---|
| 2026-04-16 | 新增 24-step 全球复杂网络分析（`complex_network/`） |
| 2026-04-16 | 新增 25-step Cloudflare 全链分析（`cloudflare_analysis.py`） |
| 2026-04-16~17 | 新增 20-step 中国分析（`china/`），含综合主权指数 |
| 2026-04-17 | 目录重组：原始 CSV 迁入 `data_cache/` (gitignore)，`exploratory/` 归集根级脚本 |
| 2026-04-17 | 新增 `analysis/README.md` 目录索引、`analysis/RESEARCH.md` 本研究说明 |
| 2026-04-17 | 新增 9 国跨国分析（`countries/`）：US/CN/JP/IN/DE/GB/FR/NL/RU × 20 步；per-country profile + cross_country / dependency_matrix / content_geography 四个合成仪表板 |
| 2026-04-17 | 2026-04 快照主权指数: FR 0.753 · US 0.740 · NL 0.678 · GB 0.613 · IN 0.533 · DE 0.529 · JP 0.486 · RU 0.480 · CN 0.269 |
| 2026-04-17 | 下载 2025-04-08 dump (10 GB)、dump swap、加载 ~85 GB DB，完成 2025-04 快照 9 国提取 |
| 2026-04-17 | 2025-04 快照主权指数: NL 0.694 · FR 0.650 · US 0.616 · RU 0.602 · DE 0.594 · GB 0.591 · JP 0.580 · IN 0.508 · CN 0.220 |
| 2026-04-17 | 新增 `evolution.html` · 时序演化仪表板 (2025→2026 slope / delta heatmap / bump chart) |
