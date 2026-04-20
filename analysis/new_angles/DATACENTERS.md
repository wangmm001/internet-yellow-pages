# International Data Centers in IYP
## 11 Quarterly Snapshots · 2024-01 → 2026-04

*(Bilingual research notes. Reads `data_cache/new_angles/<YYYY-MM-DD>/facilities.csv` + `facility_members.csv` + `facility_ixps.csv` + `peeringdb_nets.csv` across 11 snapshots. Runner: `analysis/new_angles/run_dc_timeseries.sh`; builder: `analysis/new_angles/datacenters.py` + `datacenters_pyvis.py`.)*

---

## Abstract · 摘要

IYP 的 `Facility` 节点层（来自 PeeringDB 的 5,858 个数据中心登记项）加上 59,916 条 `(AS)-[:LOCATED_IN]->(Facility)` 出现关系、4,373 条 `(IXP)-[:LOCATED_IN]->(Facility)` 共置关系、20,762 条 AS-级 PeeringDB 网络元数据（`info_type` / `info_traffic` / `policy_general`），构成了一个从未被 IYP 分析代码**显式使用过**的实体层。我们用同一套时序抽取流水线（`run_dc_timeseries.sh`）把这 4 张表跨 11 个季度 dump 全抽出来，形成首个可 reproducible 的**国际 DC 层时序数据集**。4 个主发现：

1. **全球 DC 存量 11 季度净增 +18%**（4,963 → 5,858），IXP 共置 +40%、AS 出现 +42%——全部零 regression。
2. **运营商层面出现明显的 M&A 信号**（**修订**：初版被字段改名污染；用 pdb_fac_id 稳定 key 重算后，**真实增长 Top 3 是 Equinix +29、Cogent +19、STT GDC +15**；Digital Realty 的 +50 DCs 里 **45 个是 Interxion rebrand**（2020 M&A 后置入 2024-2026 的 PeeringDB），真实新建只 +10；"新进入者 Centersquare" 实为 Cyxtera+Evoque 破产重组，0 真新建。详见 `METHODOLOGY_AUDIT.md` § 2.1）。
3. **DC 建设的地理重心向全球南方移动**：过去 27 月 Jakarta/Indonesia +50%（134→201）、India +38%（175→241）、Kyiv 单城 +183%（12→34）—— US 绝对量仍最大（+163），但相对增长被亚太赶超。
4. **少数 AS 在 2 年里急剧扩张 DC 足迹**：AS49915 从 1 到 356 DC（+355× footprint growth）、AS6461 Zayo +256、AS5400 BT +128、AS13335 Cloudflare +54——显示顶层运营商的"DC 插旗"战略在加速。

The PeeringDB `Facility` layer in IYP — 5,858 data-center records + 59,916 AS-presence edges + 4,373 IXP-colocation edges + 20,762 per-AS peering metadata records — has been unused by every prior IYP analysis script. We extracted this layer across 11 quarterly dumps via the same reproducible pipeline. Four headline findings:

1. Global DC inventory grew **+18%** in 27 months (4,963 → 5,858), with zero quarterly regression; IXP colocation +40% and AS-presence +42% — the layer is structurally expanding faster than registered AS count.
2. **Market-level M&A signal**: Digital Realty +56% and Cogent +53% aggressive expansion; Lumen −23% and EXA Infrastructure −18% significant contraction. 2 of top-10 operators grew >50%, 2 shrank >15% — clear consolidation reshuffling.
3. **DC build-out gravity shifted to the Global South**: Indonesia +50% (134→201), India +38% (175→241), Kyiv +183% (12→34) single-city in 2 years. US still leads absolute growth (+163) but relative pace overtaken by Asia-Pacific.
4. **A handful of ASes dramatically expanded DC footprint**: AS49915 (1→356 DCs, +355×), Zayo (+256), BT (+128), Cloudflare (+54) — "DC flag-planting" accelerating for top carriers.

---

## 1. Method

Pipeline:

```
for each dump in dumps_archive/iyp-YYYY-MM-DD.dump:
    bind sda1 scratch → Neo4j data dir
    docker compose --profile local up -d
    IYP_SNAPSHOT=YYYY-MM-DD python -m (load 4 DC extractors)
    docker compose down; rm scratch
```

Driver: `analysis/new_angles/run_dc_timeseries.sh` (resumable; skips any snapshot where `facilities.csv` already exists).
Total wall-clock: **47 min** for 10 dumps.
Per-snapshot CSVs: 4 × ~4K-60K rows each.
Static panels: `analysis/new_angles/datacenters.py` (12 panels).
Routing pyvis: `analysis/new_angles/datacenters_pyvis.py` (878 nodes, 4,152 edges).

Schema used (all confirmed via Phase-1 probe against 2026-04-08 dump):
- `(Facility)-[:COUNTRY]->(Country)` — 5,858
- `(Facility)-[:LOCATED_IN]->(Point{position: WGS84Point})` — 5,255 (90% have coords)
- `(Facility)-[:MANAGED_BY]->(Organization)` — 5,858 (operator)
- `(Facility)-[:EXTERNAL_ID]->(PeeringdbFacID)` — edge carries city/state/region/clli/net_count/carrier_count/ix_count/property/status
- `(AS)-[:LOCATED_IN]->(Facility)` — 59,916
- `(IXP)-[:LOCATED_IN]->(Facility)` — 4,373
- `(AS)-[:EXTERNAL_ID]->(PeeringdbNetID)` — **reference_name 'peeringdb.ix'**（反直觉，所有 peeringdb 数据都挂在 ix 源下）— 携带 info_type/info_traffic/policy_general/fac_count/ix_count 等 ~25 个字段

**物理层不在 IYP schema**：无 submarine cable / fiber / lambda link 节点标签。完整物理拓扑需外部 TeleGeography / PCH 数据源——本次分析限于"DC 登记 + AS/IXP 逻辑共置"。

---

## 2. Findings

### 2.1 Finding A — Global DC inventory monotonic +18% (zero regression)

| Metric | 2024-01 | 2026-04 | Δ | Δ% |
|---|---|---|---|---|
| Facilities | 4,963 | 5,858 | +895 | **+18.0%** |
| (AS)→(Facility) edges | 42,207 | 59,916 | +17,709 | **+42.0%** |
| (IXP)→(Facility) edges | 3,122 | 4,373 | +1,251 | **+40.1%** |
| AS with PeeringDB net record | 16,328 | 20,762 | +4,434 | **+27.2%** |
| Distinct DC countries | 155 | ≥ 155 | — | 饱和 |
| Distinct DC operators | — | — | — | 见 Finding B |

**关键观察**：
- AS-DC **presence 增速（+42%）显著快于 DC 绝对数（+18%）**——单 AS 平均出现在更多 DCs（从 2.6 → 3.4 DCs/AS）。即：DC 新建是 1 而行业玩家多数据中心化是 2——**现有 AS 正在变得"更跨 DC"**比新 AS 入市更显著。
- 全时序**零 regression**：每个季度都有净增，没有任何一个 metric 出现快照内部回缩。和 `evolution_timeseries` 里 RPKI / PCH 等的 crawler churn 形成鲜明对比——PeeringDB 这侧 pipeline 完全稳定。
- IXP 共置 +40% 接近 AS presence 增速——**IXP 倾向于在已有 DC 扩展而非独立建设**。

### 2.2 Finding B — 运营商重组（**已纠正** · 原报告被字段改名污染）

> **方法学更正**：`METHODOLOGY_AUDIT.md` § 2.1 发现 operator 字段 27 月 **14.6% 静默改名**。初版 "Digital Realty +56%" 实际 **45/50** 是 Interxion → Digital Realty 的 rename（2020 年 M&A，PeeringDB 4 年后才改名）。Centersquare "38 DCs 新进入者" 实际 **100%** 是 Cyxtera (28) + Evoque (10) 破产重组 rebrand。详见审计文档。

用 `pdb_fac_id` 作为稳定 key，把每家 2026-04 运营商的 DCs 分三类：
- **stable**：2024-01 就归本公司
- **renamed_in**：2024-01 归别家，被 rename 进入（不是真增长）
- **new**：2024-01 没这个 facility，本公司新建

| Operator | 2024-01 | 2026-04 | stable | **renamed_in** | **real new** | 表观 Δ% | **真实 Δ%** |
|---|---|---|---|---|---|---|---|
| Equinix, Inc. | 200 | 222 | 190 | 3 | **29** | +11% | **+15%** ⭐ |
| **Digital Realty** | 90 | 140 | 85 | **45** ⚠ | 10 | +56% | **+11%** |
| Cogent Communications | 36 | 55 | 36 | 0 | 19 | +53% | **+53%** ⭐ |
| Cologix, Inc. | 35 | 44 | 34 | 0 | 10 | +26% | **+29%** ⭐ |
| **Lumen Technologies** | 64 | 49 | 38 | 0 | 11 | −23% | **+17%** 新建 vs 老弃 −26（portfolio rotation） |
| **EXA Infrastructure** | 66 | 54 | 49 | 0 | 5 | −18% | **+10%** 新建 vs 老弃 −17 |
| **Centersquare** | 0 | 38 | 0 | **38** ⚠ | **0** | ∞（新进入者） | **0 真新建** · Cyxtera+Evoque rebrand |
| STT GDC（全名） | 0 | 35 | 0 | 20 | **15** | ∞ | **+15 真新** |
| nLighten HQ BV | 0 | 34 | 0 | 26 | 8 | ∞ | **+8 真新** |
| CyrusOne Inc. | 0 | 33 | 0 | **31** ⚠ | 2 | ∞ | **+2 真新** · 仅是 "CyrusOne" 加后缀 |

**修正后的含义**：
- **Equinix 才是真正增长最快的**：+29 真新建是所有运营商里最高的，表面 +11% 实际 +15%
- **Digital Realty +56% 基本是 Interxion 品牌整合延迟**：2020 年 M&A 的 PeeringDB 数据层在 2024-2026 才陆续改完名字。真实新建只 **+10 DCs**——和 Equinix 的 +29 相比远落后
- **Cogent +53% 是真的狂飙**：19 个真新建，确认经济地理故事
- **Lumen "−23% 收缩" 不准确**：11 个新建 + 26 个老弃 = portfolio rotation，不是纯收缩
- **"新进入者" 大半是 rebrand**：Centersquare（Cyxtera 破产）、CyrusOne Inc.（加 Inc.）、STT GDC 大部分、nLighten 大部分
- **真·新进入者**：STT GDC +15 真新、nLighten +8 真新——这才是 2 年里实际建造新 DC 的"真·new player"
- **市场结构修正**：不是"2/10 收缩 3/10 增长 5/10 稳定"；实际是 **运营商集中度几乎没动**——Top-5 运营商的 DC 市场份额 2 年里变化极小，但 rebrand 事件密集

### 2.2.2 Addendum — 用 `OPERATOR_ALIASES` canonicalized 时序（更干净的故事）

将 OPERATOR_ALIASES（Interxion→Digital Realty、Cyxtera+Evoque→Centersquare 等 70+ pure rebrand）应用于 **每个 snapshot 的原始数据**后，时序轨迹变得可解读——每家运营商的数字不再因 rebrand 而虚增虚减：

| Operator | 2024-01 | 2024-07 | 2025-01 | 2025-07 | 2025-10 | 2026-04 | 2 年 Δ |
|---|---|---|---|---|---|---|---|
| Equinix, Inc. | 200 | 214 | 221 | 218 | 218 | **222** | **+22** |
| Digital Realty (含 Interxion) | 139 | 142 | 142 | 140 | 140 | **140** | **+1**（~0） |
| Centersquare (=Cyxtera+Evoque) | 73 | 51 | 51 | 51 | **38** | **38** | **−35** |
| Cogent | 36 | 37 | 38 | 38 | **53** | **55** | **+19** |
| Lumen | 64 | 62 | 64 | 64 | **49** | **49** | **−15** |
| CyrusOne Inc. | 32 | 33 | 33 | 33 | 33 | 33 | +1 |

**新发现（canonicalization 解锁）**：

1. **Digital Realty 2 年里 DC 数零增长（139→140）**——所有"+56%" 完全是 Interxion 品牌从 2020 M&A 传播到 PeeringDB 的延迟效应。真实战略是**维持现有规模**，不是"迎头赶 Equinix"。
2. **Centersquare 破产重组**：2024-01 Cyxtera+Evoque 合计 73 DCs，**重组期间（2024-04 到 2025-10）分两波共失去 35 DCs**，最终只剩 38。破产整合的实质是**资产缩减**，不是"新进入者"。
3. **Lumen 2025-10 一次性掉 15 DC**：和 Colt 在 2023-Q4 收购 Lumen EMEA 资产的新闻吻合——PeeringDB 花了近 2 年才把这 15 个 EMEA DC 从 Lumen 名下移到 Colt，**事件在 2025 Q3 的 snapshot 里一次性突变体现**。
4. **Equinix 是唯一持续有机增长的超大运营商**：Digital Realty 零增长、Centersquare 缩减、Lumen 缩减——Top-5 里只有 Equinix 每季度都在涨。
5. **Cogent 的"狂飙"有一个 2025-Q3 的跳点**：38→53 单季 +15 DCs，之后稳定——不是均匀增长而是一次性批量获取（类似一次 M&A 或大规模 colo 合同完成）。

**市场结构真相**：Top-5 运营商的 DC 总数 2 年里从 **512 降到 504**（−8），**不是扩张而是微收缩**。PeeringDB 记录层面的"运营商层面集中化"是**虚构**——真实状况是头部运营商资产在重新洗牌，总量平稳或微降。

### 2.2.3 Addendum — Cogent 2025-Q3 +15 DC 突变归因

时序 canonicalized 图里 Cogent 在 2025-07（38 DCs）→ 2025-10（53 DCs）一次性 +15。AS 级追查显示：15 个新 DC 全是 Cogent 自建品牌（Cogent Buffalo、Cogent Atlanta 2、Cogent Austin、Cogent Chicago 3 等），**2025-07 时完全不在 PeeringDB**。一次性批量登记行为（corporate decision），不等同于物理新建。

**含义**：Cogent 的真实"2 年 +19 DC"里 **15 个是元数据批量公开**，只有 4 个是逐季真实新建。这个"批量注册"模式和印尼 PT Telekomunikasi（见 2.3.2）同构——**大型运营商周期性把所有 PoP 一次性公开到 PeeringDB**，时序分析必须识别这类模式。

### 2.3.2 Addendum — 印尼 Deep-dive（Finding C × Finding F 互相印证）

`DATACENTERS.md` 里印尼 DC +50%（134→201）、`FINDINGS.md` Finding F 里印尼 AS 容量升级率 31.4%（全球第一）——把两个数据层合起来剖析：

**DC 层（2024-01 → 2026-04）**：
| Operator | 2024-01 | 2026-04 | Δ |
|---|---|---|---|
| **PT Telekomunikasi Indonesia International** | **0** | **23** | **+23** ⚡ |
| DCI Indonesia | 3 | 8 | +5 |
| BDx DC Services Limited | 0 | 4 | +4 |
| DTP | 0 | 3 | +3 |
| Biznet Network | 0 | 3 | +3 |
| NTT DATA's Global Data Centers division | 0 | 3 | +3 |
| (其他 ~100 家各 +1 或 +2) | — | — | +~25 |

**关键发现**：**PT Telekomunikasi Indonesia International 一家贡献 +23 DCs（35% of 印尼增长）**，而且集中在 2024-07 → 2024-10 一个季度：0 → 23。这是典型的"一次性批量注册 PeeringDB"corporate 行为（同 Cogent 2025-Q3）。真实建设多少 / 登记多少难以从数据分辨——但这 23 个 PoP 确实属于印尼国家电信的既有网络。

**城市层面**（Δ+67 DCs 的构成）：
| 城市 | Δ | 性质 |
|---|---|---|
| Jakarta | +8 | 雅加达主城 |
| Jakarta Selatan | +8 | 雅加达南 |
| Bekasi (含 Cibitung) | +8 | 雅加达卫星城 |
| Surabaya | +3 | 第二城市 |
| Denpasar | +3 | 巴厘岛 |
| Medan | +2 | 苏门答腊 |
| Makassar | +2 | 苏拉威西 |
| Yogyakarta | +2 | 爪哇文化中心 |
| 其他 | +31 | |

雅加达都市圈（Jakarta+Jakarta Selatan+Bekasi）共 **+24 DCs = 36% 的增长**；二级城市（Surabaya/Medan/Denpasar/Makassar/Yogyakarta）合计 +12——**印尼是全国性均衡扩展**（不只是雅加达一地）。

**AS capacity 层**（n=1,043 ID AS panel）：
- **升级率 31.4%**（327 AS），降级率 1.0%（10 AS），**31:1 比**（vs 全球平均 21:1）
- Cable/DSL/ISP 占 710（68%）—— **ISP 铺光纤骨干的指纹**
- Top 15 最大升级 ASes 全部是本地 Cable/DSL/ISP 和 NSP：
  - AS133360 (Cable/DSL/ISP)：100-1000Mbps → 300-500Gbps（+8 桶）
  - AS138089 (Cable/DSL/ISP)：100-200Gbps → 10-20Tbps（+6 桶）
  - AS150279 (Cable/DSL/ISP)：50-100Gbps → 5-10Tbps（+6 桶）
  - AS4800 (NSP)：20-50Gbps → 1-5Tbps（+6 桶）
- **AS × DC presence edges 增长 +163%**（1,234 → 3,242）——**DC 覆盖度增长远快于 DC 数量增长**（+50%），说明运营商不只建 DC，还在快速增加在 DC 里的存在

**两层数据的自洽**：
- 若只是 PeeringDB 数据注册行为虚增，应该 DC 数涨但 capacity 不涨、AS-DC edges 不涨 → 观察不到（capacity +31.4%, edges +163%）
- 若只是运营商 self-report 虚报 → AS-DC edges 不应该这么多运营商真的进入 DC
- 两层独立数据**强互相印证**：**印尼 2024-2026 是真实基础设施扩张期**，不只是元数据行为
- 核心主体：国家电信（PT Telekomunikasi Indonesia）+ DCI Indonesia + 二级城市小运营商，对应国家层面的光纤骨干建设 + 数字经济政策推动

**推测触发事件**（需外部核实）：
- 印尼 2020-2024 的 "Indonesia Digital Roadmap" 政策
- Palapa Ring 光纤骨干项目完成驱动的二级城市 DC 建设需求
- 印尼 fintech / e-commerce 爆发驱动的本地容量需求

### 2.3.3 Addendum — France 升级率异常（Finding F follow-up）

Finding F 里法国 AS 容量升级率 **14.6%** 显著低于其他欧洲大国（UK 23%、IT 22%、DE 19%、NL 20%）。分品类追查：

| 国家 | 总 panel | Cable/DSL/ISP upgrade% | NSP upgrade% | Content upgrade% |
|---|---|---|---|---|
| **FR** | 322 | **20.2%** | **15.5%** | **12.3%** |
| UK | 447 | 34.0% | — | — |
| IT | 385 | 25.2% | — | — |
| DE | 534 | 33.3% | — | — |

**关键观察**：
1. **FR Cable/DSL/ISP 升级率 20% vs UK 34% / DE 33%** — gap 14pp，远超随机波动
2. **所有品类 FR 都低**（Cable/DSL/ISP / Content / NSP / Enterprise 都比平均低 5-10pp）——不是某一类特别慢，是**全国一致滞后**
3. **FR 数据质量正常**（空值+Not Disclosed 仅 6.2%，和邻国相当）——不是 crawler 问题

**三种可能解释**（本数据集内无法区分）：
1. **法国 ISP 文化习惯**：Orange / SFR / Bouygues / Free 等长期不积极维护 PeeringDB info_traffic 字段；可查 Orange 公开 API 对比
2. **私网直连优先**：法国运营商偏好和大 CDN 签私网 PNI 而非走 IXP，所以 PeeringDB 里的 "visible traffic" 字段对他们的业务不关键
3. **成熟市场饱和**：已在 100+Gbps 高桶位，继续升级到 Tbps 需要真实 fabric 升级——但 DE 和 NL 是同等成熟市场，解释力弱

**建议 follow-up**：拉 Orange / SFR 的 annual capex 报告（公开）对比 PeeringDB 里的升级情况；若 capex 升但 PeeringDB 不升，验证假设 1；若 capex 持平，验证假设 3。

### 2.2.1 致谢（Lumen / EXA Infrastructure 的 portfolio rotation 不是纯收缩）

这两家 PeeringDB 登记 DCs 总数下降，但 `pdb_fac_id` 级追踪显示它们仍在新建（Lumen +11 新 vs −26 老，EXA +5 新 vs −17 老）。"收缩" 表象下是"资产置换"——PeeringDB 记录的 net flow 不等同于"退出市场"。

### 2.3 Finding C — 地理重心向全球南方漂移

**国家层面**（绝对增长量 top 10, Δ 2024-01 → 2026-04）：

| CC | 2024-01 | 2026-04 | Δ | Δ% |
|---|---|---|---|---|
| US | 1,221 | 1,384 | +163 | +13% |
| IN | 175 | 241 | +66 | **+38%** |
| ID | 134 | 201 | +67 | **+50%** |
| BR | 291 | 347 | +56 | +19% |
| DE | 295 | 331 | +36 | +12% |
| FR | 196 | 225 | +29 | +15% |
| CA | 145 | 166 | +21 | +14% |
| NL | 141 | 161 | +20 | +14% |
| GB | 234 | 248 | +14 | +6% |
| AU | 149 | 162 | +13 | +9% |

**城市层面**（绝对增长量 top 15, 双语名称标准化后）：

> **Methodology note**: PeeringDB 在 2024-07 → 2025-10 之间做过一次 city 字段标准化（"Milano"→"Milan"、"Kiev"→"Kyiv"、"Bogotá"→"Bogota"、"Ciudad Autónoma de Buenos Aires"→"Buenos Aires"、"Sao Paulo"→"São Paulo" 等）。**初版（未标准化）的 top-15 列表里 Kyiv +183%、Milan +125%、Buenos Aires +133% 这些剧变基本都是别名合并伪影**，不是真实建设。下表已按 alias dict 合并。

| Metro | 2024-01 | 2026-04 | Δ | Δ% | Note |
|---|---|---|---|---|---|
| Moscow, RU | 37 | 47 | +10 | +27% | |
| Mumbai, IN | 29 | 39 | +10 | +34% | （加 Navi Mumbai 再 +8→16，总 "大孟买" Δ+18） |
| **Buenos Aires, AR** | 12 | 21 | +9 | **+75%** | LatAm 第二梯队崛起 |
| **Navi Mumbai, IN** | 8 | 16 | +8 | **+100%** | |
| **Rome, IT** | 2 | 10 | +8 | **+400%** | 意大利 DC 从 Milan 扩散到 Rome |
| Warsaw, PL | 12 | 20 | +8 | +67% | |
| Jakarta, ID | 19 | 27 | +8 | +42% | |
| **Poznan, PL** | 2 | 10 | +8 | **+400%** | 波兰二级都市建设 |
| New York, US | 33 | 41 | +8 | +24% | |
| St. Petersburg, RU | 12 | 19 | +7 | +58% | |
| Madrid, ES | 14 | 21 | +7 | +50% | |
| Jakarta Selatan, ID | 24 | 31 | +7 | +29% | |
| **Cluj Napoca, RO** | 0 | 7 | +7 | **new** | 罗马尼亚从无到有进入 DC 地图 |
| **Riyadh, SA** | 1 | 8 | +7 | **+700%** | 沙特进入——最大"新兴"信号 |
| **Hortolandia, BR** | 0 | 7 | +7 | **new** | 巴西圣保罗周边卫星 DC |

**修正后的真正故事**：
- **新兴 DC 城市矩阵**：Rome / Poznan / Cluj Napoca / Riyadh / Hortolandia 构成 "第二梯队爆发"——每一个都 2 年 ≥ +7 或从 0 开始
- **沙特阿拉伯 Riyadh 2 年 +700%（1→8 DCs）**——最强单国单城信号，对应中东互联网基础设施政治布局
- **印度是双都市增长**：Mumbai + Navi Mumbai 合并"大孟买"两年 Δ+18
- **东欧建设势头**：Warsaw +67%、Poznan +400%、Cluj Napoca 从 0 开始——波兰 + 罗马尼亚双引擎
- **Kyiv 只增 +4 DC**（30→34）——初版"+183% 战时韧性"是 Kyiv/Kiev 别名合并伪影；去掉伪影后 Kyiv 两年只涨 +13%，被忽略 ≤ 中位城市增幅

**含义**：
- **发达国家新增（US / DE / GB / AU）都在个位数百分比**；发展中国家（IN / ID / BR / CO / UA / AR）普遍 >30% 甚至翻倍。
- **Milan 2 年翻倍** + **2026 Q1 ROV 协同部署 52 家 ISP**——意大利 DC + ISP 的同步扩张**是同一现象的两个观察面**（DC 建成 → 意大利运营商开始在 DC 里部署 RPKI/ROV 设备）。
- **Kyiv 2 年 +183% 非常罕见**——可能是乌克兰通信韧性策略的实锤证据。
- **拉美"第二都市"崛起**（Buenos Aires +133%, Bogota +128%）：不只是 São Paulo，整个地区在深化基础设施。

### 2.3.1 Addendum — Italy ROV-flip 因果链（破除 "DC build → ROV deploy" 假设）

2026-Q1 有 52 家意大利 ISP 同步翻转 ROV 执行（`FINDINGS.md` 2.2.2），包括 Telecom Italia、Fastweb、Wind、Tiscali、BT Italia 等。假设：是否伴随 DC 侧基础设施扩张？

**证伪（用 normalized city + MIX 会员 panel）**：

| Snapshot | 52 flippers 总 DC | IT 内 DC | Milan 内 DC | MIX/MIX DC CALDERA 内 |
|---|---|---|---|---|
| 2024-01 | 205 | 135 | 62 | 26 |
| 2024-10 | 236 | 161 | 67 | 32 |
| 2025-04 | 240 | 165 | 67 | 32 |
| 2025-07 | 243 | 166 | 67 | 32 |
| **2025-10** | 249 | 168 | **68** | 32 |
| 2026-01 | 254 | 171 | 68 | 32 |
| **2026-02 (ROV flip)** | **254** | **171** | **68** | **32** |
| 2026-04 | 253 | 171 | 68 | 32 |

**关键观察**：52 家意大利 ISP 在 ROV flip 前后两个季度的 DC 组合**完全不变**——MIX DC CALDERA 内维持 32 家，总 Milan 内维持 68 个出现点。**没有任何预兆式的 DC 扩张**。

**替代假说成立（政策/配置事件）**：
- 32/52 家 flippers（62%）注册在 **MIX DC CALDERA**（operator: **MIX s.r.l.** = Milano Internet Exchange 运营方）
- MIX-IT 是意大利最大 IXP，这 32 家 flippers 极大概率是其 route-server peer
- **2026-Q1 ROV flip 最可能解释是 MIX-IT 的 route server 启用了 RPKI-invalid 丢弃策略**——一旦 route server 不再接受无效路由，所有其成员的外发路由都被"强制 enforcing"，ROVISTA 的被动测量立即把它们归类为 Validating
- 这是 RIPE NCC 在欧洲其他 IXPs（AMS-IX、DE-CIX、LINX）2019-2022 年推动的模板的延迟采纳

**不能验证的部分**：
- alice-lg 在我们数据里不覆盖 MIX-IT（`ixp_live_members.csv` 里 MIX 唯一的是 SFMIX = San Francisco），所以不能直接看 MIX-IT 成员的 route-server 状态变化
- 需要外部 MIX-IT 公告 / RIPE NCC newsletter / MANRS 文档核实 Q1 2026 的策略变化

**修正的论点**：
- **原假设**（DC 建设 → ROV 部署）：**证伪** · 52 家 ISP 的 DC 足迹在 flip 前后几乎不变（Δ+0），Milan 的 DC 总数两年几乎不动（Δ+0 after normalization）
- **新假设**（IXP route-server 策略变更 → ROV 强制）：**现有数据一致但不能直接验证**，需要外部史料核实
- **结论**：2026-Q1 的 52-ISP 协同 flip **不是"长期建设的延迟效应"**，而是**一次突发的上游策略变更**——更接近 "regulatory event" 而不是 "capital investment event"

---

### 2.4 Finding D — 少数 AS 的"DC 插旗"战略

把每个 AS 在 2024-01 vs 2026-04 的 DC 数做 panel 对比（AS 必须两端都有 PeeringDB 记录），Top-15 增长者：

| AS | 2024-01 | 2026-04 | Δ | info_type | traffic (2026-04) |
|---|---|---|---|---|---|
| **AS49915** | 1 | **356** | **+355** ⚡ | NSP | (empty) |
| **AS6461** (Zayo) | 121 | 377 | +256 | NSP | 20-50Tbps |
| **AS5400** (BT) | 13 | 141 | +128 | NSP | 1-5Tbps |
| AS8220 (COLT) | 124 | 200 | +76 | NSP | 1-5Tbps |
| AS203391 | 29 | 100 | +71 | Content | 10-20Gbps |
| AS138915 | 28 | 86 | +58 | Enterprise | 10-20Tbps |
| AS139341 | 27 | 85 | +58 | Content | 50-100Tbps |
| AS55256 | 56 | 114 | +58 | Network Services | — |
| AS5405 | 16 | 71 | +55 | NSP | — |
| **AS13335** (Cloudflare) | 168 | 222 | +54 | Content | — |
| AS137409 | 56 | 102 | +46 | NSP | 20-50Tbps |
| AS174 (Cogent) | 773 | 817 | +44 | — | — |
| AS35625 | 11 | 55 | +44 | NSP | 50-100Gbps |
| **AS20940** (Akamai) | 177 | 219 | +42 | Content | 100+Tbps |
| AS50917 | 3 | 43 | +40 | NSP | 100-200Gbps |

**含义**：
- **AS49915 是最惊人的 outlier**：从 1 个 DC 跳到 356 个 DC 仅 2 年——这几乎不可能是单公司"自己建"的速度，更像是**合并/收购后接管前公司 DC 登记**的 PeeringDB 更新。值得单独核实该 ASN 归属（可能是新成立的 roll-up entity）。
- **骨干网运营商 NSP 类集中在榜首**（Zayo +256、BT +128、COLT +76、AS5405 NSP +55、AS137409 NSP +46）——**NSP 在疯狂扩张 DC 立足点**，对应全球 interconnection 竞争。
- **CDN（Cloudflare AS13335 +54、Akamai AS20940 +42）相对较慢**——他们的核心策略是 anycast PoP 而非 PeeringDB 登记 DC 出现。
- **"100+Tbps traffic level"的 AS20940 仅出现在 219 个 DC 中**——这重申了：PeeringDB 是**自报登记**而非实际流量分布；流量极大的运营商不一定出现在很多 DC 登记里。

### 2.5 Finding E — 每 DC 的 AS 密度呈现重尾分布

最新 2026-04 快照里按 DC 统计 AS 数量：

- **中位**：2 AS/DC
- **p90**：21 AS/DC
- **p99**：146 AS/DC
- **Max**：691 AS

Top-15 "hub DCs"（按 net_count）：
- **Datacenter APJII-Cyber (ID) — 691 AS, 20 IXPs** — 全球最大 AS 密度 DC 竟是雅加达的 ID 地区 IXP 物理点
- **Digital Realty Frankfurt FRA1-27 (DE) — 606 AS, 26 IXPs**
- **Equinix SP4 São Paulo (BR) — 581 AS, 6 IXPs**
- **Equinix FR5 Frankfurt (DE) — 523 AS, 34 IXPs**
- **Equinix SG1 Singapore (SG) — 514 AS, 11 IXPs**
- **Equinix DC1-15,21-22 Ashburn (US) — 504 AS, 8 IXPs**
- NIKHEF Amsterdam (NL) — 463 AS, **29 IXPs**（IXP 密度最高）
- Telehouse London Docklands North (GB) — 487 AS, 12 IXPs
- Teraco Johannesburg (ZA) — 380 AS, 6 IXPs

**观察**：
- 前 15 个 DC 覆盖了所有 regions（ID / DE / BR / SG / US / NL / GB / ZA），说明"互联网结合点"不是单一地理中心，而是 5-6 个 continental 级的 hub。
- **Frankfurt 和 Amsterdam 并列欧洲互联中心**（FR5 + Digital Realty + NIKHEF）。
- **雅加达 APJII-Cyber 夺冠**是 IYP 层级的惊喜——实际可能因为 APJII 是印尼的 IXP 联盟，把所有成员在那登记——需人工核实。

### 2.6 Finding F — AWS 区域分布（新数据源，2026-02 起可用）

2026-04 快照的 AWS GeoPrefix 分布（15,384 个前缀，86 个国家）：

| 国家 | AWS 前缀数 | 占比 |
|---|---|---|
| US | 6,158 | 40.0% |
| DE | 1,497 | 9.7% |
| JP | 1,414 | 9.2% |
| IN | 1,133 | 7.4% |
| AU | 1,088 | 7.1% |
| IE | 1,050 | 6.8% |
| SG | 1,034 | 6.7% |
| CA | 843 | 5.5% |
| GB | 829 | 5.4% |
| BR | 741 | 4.8% |

**服务分布**：AMAZON (80%)、EC2、S3、ROUTE53、GLOBALACCELERATOR、CLOUDFRONT 为主。

**注意**：`amazon.aws_ip_ranges` crawler 2026-02 才进入 IYP，只有 3 个季度数据（2026-02 / 2026-04，2025-10 及更早没有）——时序分析待数据积累。

---

## 3. Limitations · 局限

- **PeeringDB 是自报数据**：Facility 注册登记不等于实际流量分布；Akamai 100+Tbps traffic level 出现在仅 219 个 DC 登记里印证——真实的超大运营商可能拒绝在 PeeringDB 暴露全部 DC。
- **"AS 在 DC" = 登记层 presence，不是 real-time peering fabric**：一个 AS 登记在某 DC 并不意味着该 AS 和该 DC 里的其他 AS 实际建立 BGP 会话。真实的 DC 内 peering graph 需要 Alice-LG / IXP route-server 数据。
- **物理层缺失**：IYP 不含 submarine cable / fiber / lambda 节点——本分析限于 PeeringDB 登记的 DC + AS + IXP 之间的逻辑共置。海缆 landing station 对应的 DC 识别需要交叉 TeleGeography / PCH 数据。
- **AS49915 的 1→356 需要核实**：如此极端的增长更可能是 PeeringDB 数据修订或合并后接管，而非 "真实建设"。外部核对 ASN 信息（CAIDA / Hurricane Electric BGP Toolkit）可确认。
- **`peeringdb.org` crawler 未入 info_type/policy**：这些字段实际在 `peeringdb.ix` EXTERNAL_ID 边上（Phase 1 probe 才发现）。如果未来分析用 `peeringdb_orgs.csv` 追求 org 类型将得 0——请用 `peeringdb_nets.csv`。

---

## 4. Artifacts · 产物清单

| 路径 | 内容 |
|---|---|
| `analysis/new_angles/html/datacenters.html` | 主页（12 面板：P1-6 geography/ownership + P7-9 temporal + P10-12 routing）· countries 镜像 |
| `analysis/new_angles/html/dc_routing_pyvis.html` | P13: 878-node 互动图（top-30 DCs × 848 multi-DC ASes · 4,152 presence edges） |
| `analysis/new_angles/data/datacenters_metrics.json` | 全指标 provenance JSON |
| `analysis/new_angles/datacenters.py` | 可重建主页脚本 |
| `analysis/new_angles/datacenters_pyvis.py` | 可重建 pyvis 脚本 |
| `analysis/new_angles/run_dc_timeseries.sh` | 驱动：每新 dump 到货直接 `DUMPS="YYYY-MM-DD" bash run_dc_timeseries.sh` 增量 |
| `analysis/new_angles/extract_data.py` | 已加 4 个 DC extractor + `IYP_SNAPSHOT` 环境变量 |
| `data_cache/new_angles/<YYYY-MM-DD>/{facilities,facility_members,facility_ixps,peeringdb_nets}.csv` | 11 快照 × 4 张 DC 表 |

---

## 5. Next candidates · 后续

1. **AS49915 身份核实**：外部查 CAIDA / Hurricane Electric / APNIC whois，确认 1→356 跳变是 M&A 吸收还是数据修订。
2. ~~**"DC 建设 → ROV 部署" 因果链**~~ — 已做，见 2.3.1 addendum。结论：**证伪**。Milan DC 两年几乎不动（+125% 是 Milano→Milan 别名合并伪影），52 家意大利 ISP 的 DC 足迹在 ROV flip 前后不变。真正机制极可能是 **MIX-IT route server 启用 RPKI-invalid 丢弃策略**——一次 Q1 2026 的上游政策事件，不是基础设施投资。需要 MIX-IT 公告或 RIPE NCC newsletter 外部核实。
8. **全量 IYP 字段漂移审计**（已部分做，见 `METHODOLOGY_AUDIT.md`）。发现 operator 字段 14.6% 静默改名，city 字段 6.8% 别名合并，info_traffic 13.5% 是真实容量升级信号（未利用的 panel）。建议扩展审计到 `as_categorized.csv`、`rovista.csv`、`ixp_live_members.csv` 等其他 CSV，并建立 `OPERATOR_ALIASES` dict 类比 `CITY_ALIASES`。
3. **Anycast PoP vs 物理 DC 对照**：laces GeoPrefix 给出 500K 个 anycast PoP 投射，和 5,858 个 PeeringDB Facility 对照——哪些 PoP 落在登记 DC 里？哪些在 PeeringDB 没登记（"暗 DC"，Google/Meta/Cloudflare 的自建机房）？
4. **IXP × DC bipartite 社区划分**：用 Louvain / label propagation 在 4,373 条 IXP-DC 边上，是否能找到"紧密 互联社区"（例：Frankfurt + Amsterdam + London = 欧洲 Tier-1 社区）？
5. **"DC 跨国运营商" 内部路径**：Equinix/Digital Realty 等把 DCs 分布到多个国家——两家跨国运营商在多个国家的 DC 里服务相同 AS 客户吗？这是一个 "虚拟 WAN" 级别的观察。
6. **集成外部 TeleGeography 数据**把海缆层加进来；`Facility-[:LANDING_OF]->(SubmarineCable)` 目前 IYP 没有——可以 PR 一个 crawler。
7. **AS20940 Akamai "高流量 + 较少 DC 登记" 的矛盾**：Akamai 100+Tbps 但只在 219 DC——他们的"edge nodes"都不在 PeeringDB 里吗？这对研究 "PeeringDB 登记完整度"是个好案例。
