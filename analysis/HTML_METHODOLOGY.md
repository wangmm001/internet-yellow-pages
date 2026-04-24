# IYP 离线分析站点 · 研究方法说明

> `analysis/*/html/` 下所有交互式页面（china 32 · countries 47 · new_angles 34 · as_galaxy 1 · as_globe 3）的生产方法。

## 1. 数据底座

- **IYP Neo4j 知识图谱**：~40 种节点、~34 种关系、~50 个数据源，覆盖 BGP / DNS / 物理 / 组织 / 地理五层。
- **季度快照存档**：`dumps_archive/iyp-<date>.dump`，2024-01 → 2026-04 共 11 个快照；每次仅加载一份（`dumps/neo4j.dump` → `docker compose --profile local up` → 抽取 → 卸载），由 `analysis/countries/extract_snapshot.sh`、`analysis/new_angles/load_and_extract.sh` 编排。

## 2. 研究思想：三尺度金字塔

| 尺度 | 目标 | 代表目录 | 步数 |
|---|---|---|---|
| 全局 | 互联网整体拓扑规律 | `complex_network/` | 24 |
| 单实体 | 单个 AS 全链画像 | `cloudflare_analysis.py` | 25 |
| 国家 | 一国在全球分层的位置 | `china/` · `countries/` | 20 (× 9 国 × 2 快照) |
| 补充视角 | 低利用数据源挖掘 | `new_angles/` | 21 topics |
| 可视化视角 | 3D/沉浸式 AS 视图 | `as_galaxy/` · `as_globe/` | 4 |

每步都明确声明所依据的学术透镜（复杂网络、AS Hegemony、DNS 主权、审查拓扑、测量方法论……），并说明 IYP 数据是**确认 / 反驳 / 扩展**该假设。

## 3. 每步四件套（Four-artifact rule）

单步运行内必须产出：

1. **Cypher 查询**（脚本 docstring 或 `data/stepNN_query.cql`）
2. **CSV 数据**（大的入 `data_cache/`，小的入 `analysis/*/data/` 随代码提交）
3. **Metrics JSON**（`data/stepNN_metrics.json`，供总报告自动装配）
4. **可视化 HTML**（Plotly `include_plotlyjs='inline'` 保证离线可读；网络图用 Pyvis）

Neo4j 不可用时通过 `common.try_neo4j_or_cached()` 回退到缓存 CSV，或由 `save_placeholder_html()` 生成带补齐指引的占位页。

## 4. 工程规范

- **复用优先**：`complex_network/utils.py`（COLORS / run_query / save_fig）、`step13` Gini/HHI、`step07` 中心性 CSV、`china/common.py`（save_plotly_html / writeup / iso2_to_iso3）不得重写。
- **视觉统一**：暗色主题 `#0D1117` / `#161B22` / `#30363D` / `#E6EDF3`；国家色 CN `#FF6B6B` · US `#45B7D1` · EU `#B39DDB`。
- **双语输出**：中文主位、英文次位；表头与 writeup 同时展示。
- **告警块**：`⚠️ 数据缺口 / 维度缺失` 一律用 `warning_block()` 的可折叠 `<details>`。

## 5. 编排入口

```bash
# 中国 20 步
python3 -m analysis.china.run_all [--step N | --verify | --report]
# 9 国 × 2 快照
python3 -m analysis.countries.run_all [--snapshot YYYY-MM | --countries CC,CC]
# 21 个未充分利用数据源主题
python3 -m analysis.new_angles.extract_data   # 先填 data_cache/new_angles/
python3 -m analysis.new_angles.<topic_script> # 各主题脚本
```

`run_all.py --report` 读取所有 metrics JSON 自动重建双语 README；`--verify` 校验四件套齐全。

## 6. 使用 Claude Code 驱动研究过程

本研究中几乎所有脚本、查询、双语 writeup、README 与 shell 编排都由 **Claude Code** 与研究者协作生成。协作工作流如下：

### 6.1 上下文注入：让 Claude 开口就懂项目

- **`CLAUDE.md`**（仓库根）：每个会话启动时自动注入，声明管线约定、`dumps_archive/` 单快照生命周期、`data_cache/` 数据路径、四件套规则、暗色主题调色板、可复用函数清单。是 Claude 理解项目骨架的"首页"。
- **用户级 auto-memory**（`~/.claude/.../memory/`）：跨会话持久化关键事实，如"dumps 真正的源在 `dumps_archive/` 而非 `dumps/`"、"磁盘不够时溢写到 `/home/wangmm/work/memory/…`"。避免每次重述背景。
- **`analysis/RESEARCH.md`**：研究哲学、学术透镜、已完成发现与限制，作为"研究大纲"喂给 Claude，保证每步新分析都能接回既有叙事线。

### 6.2 任务节奏：Plan → TodoWrite → 分步执行 → Verify

- **Plan mode / `superpowers:writing-plans`**：遇到多步任务（"加一个主题 21 / 回填 2024 快照"）先让 Claude 产出书面实现计划、对齐后再动代码。
- **TodoWrite**：长任务（20 步 × 9 国 × 多快照）拆为逐步 todo，Claude 每做完一步立即标记 completed，避免半途失焦。
- **`run_all.py --verify`**：Claude 写完新 step 后自跑 verify，确认四件套（Cypher / CSV / metrics JSON / HTML）齐全；缺失即补。
- **`superpowers:verification-before-completion`**：Claude 在声明"完成"前必须展示实际验证输出，而不是靠编译通过就交差。

### 6.3 并发与长任务：子代理 + 后台

- **Explore / general-purpose 子代理**：代码检索、跨目录盘点（"谁在用 `gini_coefficient`？"）交给子代理并行完成，主上下文不被大量 grep 结果淹没。
- **`run_in_background`**：提取一个季度快照需 10–30 min，Claude 用后台 bash 跑 `extract_snapshot.sh`，完成后收到通知再继续；期间可并行做其它分析。
- **`superpowers:dispatching-parallel-agents`**：9 国 × 2 快照的独立抽取可一次派出多个无共享状态的子代理。

### 6.4 复用先于重写

CLAUDE.md 把"复用优先"写进硬约束：Claude 被要求先 grep `utils.py` / `common.py` 的既有函数，再决定是否新增。这保证了所有 HTML 共享同一套 `save_plotly_html`、`warning_block`、`try_neo4j_or_cached`、`COLORS` 调色板，不会因为不同会话产生视觉/行为漂移。

### 6.5 定时与后续：`/loop` 与 `/schedule`

- **`/loop`**：用于等待 Neo4j 加载完成、轮询长任务、周期性刷新仪表板。
- **`/schedule`**：把"新快照发布时自动回填一列时序数据"等未来一次性任务托管给后台 agent，到点自动开 PR。

### 6.6 典型协作循环（一次新分析的生命）

```
User: 给 countries 加 topic22 — IPv6 采用率分层
  │
  ├─ Claude 读 CLAUDE.md + RESEARCH.md + 最近 step 的 docstring
  ├─ Plan：列出 Cypher / 复用函数 / 预期 HTML 结构（人审核）
  ├─ TodoWrite：拆成 query → extract CSV → metrics → HTML → writeup → index 收录
  ├─ 写 step 脚本（复用 run_query / save_plotly_html / COLORS）
  ├─ 后台跑 --step 22，返回后补 metrics JSON
  ├─ --verify 四件套 → --report 重建双语 README
  └─ git commit（按 wip/feat/... 分支命名规范）
```

人类负责**科学判断**（该问什么问题、结果解释是否靠谱、视觉是否达标），Claude 负责**机械执行与一致性维护**（查询、脚本、双语文案、规范遵守），这是 `analysis/*/html/` 下一百多个页面能保持同一风格与可复现标准的关键。

## 7. 产物汇总到 HTML 站点

- `analysis/china/html/index.html`、`analysis/countries/html/index.html` 为各自子站入口，页内并列嵌入各 `stepNN_*.html` / `profile_<CC>.html`。
- `new_angles` 部分结果按短名镜像到 `countries/html/`（`topic2_routing_security.html → routing_security.html`，topic16–21 同名镜像），以便跨研究统一导航。
- 合成仪表板：`cross_country.html`、`dependency_matrix.html`、`content_geography.html`、`evolution*.html`、`synthesis.html`、`schema_gaps.html`、`country_scorecards.html`。

## 8. 可复现性承诺

- 大原始 CSV（`data_cache/`，>200 MB）**不入库**，可由 `complex_network/step01-04_extract_*` 与 `new_angles/extract_data` 从 Neo4j 重建；路径由 `utils.DATA_DIR` 统一，`IYP_ANALYSIS_DATA_DIR` 可覆盖。
- 小结果 CSV + metrics JSON + HTML **入库**，作为产出证据与自动报告的输入。
- 详细研究哲学、已完成发现、当前限制与后续方向见 `analysis/RESEARCH.md`；目录索引见 `analysis/README.md`。
