# 九国互联网分层跨国对比与时序演化

## Nine-Country Cross-Country + Time-Series Internet Hierarchy Analysis

> 基于 Internet Yellow Pages (IYP) Neo4j 知识图谱 · 快照 2026-04 与 2025-04
> Based on IYP knowledge graph · snapshots 2026-04 and 2025-04

## 概览 · Overview

在 `analysis/china/` 20 步方法论基础上，将同样的"本体全覆盖 + 多尺度"分析方法
扩展到 **9 个重点国家**（US / CN / JP / IN / DE / GB / FR / NL / RU），并进一步
对比 **2025-04 → 2026-04** 两个快照的演化。

Extends the `analysis/china/` 20-step methodology to **9 countries**
(US / CN / JP / IN / DE / GB / FR / NL / RU) on the current 2026-04 snapshot,
then adds **2025-04 → 2026-04** year-over-year time-series evolution.

## 目录结构 · Layout

```
analysis/countries/
├── README.md                   # 本文件
├── common.py                   # 国家参数化 helpers（继承自 analysis/china/common.py）
├── step_lib.py                 # 20 个国家参数化 step_NN(country, snapshot)
├── country_pipeline.py         # 一国跑 20 步 + 生成 profile_<CC>.html
├── cross_country.py            # 跨国对比合成仪表板（2026-04）
├── dependency_matrix.py        # 9×9 跨国依赖矩阵
├── content_geography.py        # 可见 Web 的物理托管分布
├── evolution.py                # 2025 vs 2026 时序演化
├── run_all.py                  # 主编排（--snapshot / --countries / --verify / --report）
├── snapshot_swap.sh            # 辅助脚本：数据库 dump 切换
├── data/
│   ├── 2026-04/<CC>/step*_metrics.json + *.csv
│   └── 2025-04/<CC>/...（dump swap 后）
└── html/
    ├── index.html              # 主导航
    ├── profile_<CC>.html       # 9 个国家 profile（~4.9 MB each）
    ├── cross_country.html      # 跨国合成仪表板
    ├── dependency_matrix.html  # 9×9 依赖矩阵
    ├── content_geography.html  # 内容地理
    └── evolution.html          # 时序演化（dump swap 完成后生成）
```

## 复现 · Reproduce

```bash
# 依赖
pip install plotly pyvis kaleido networkx matplotlib neo4j pandas numpy

# 确保 data_cache/complex_network/*.csv 已生成（见 analysis/RESEARCH.md §6）

# 一次运行 9 国 × 20 步（当前 Neo4j 快照）
python3 -m analysis.countries.run_all --snapshot 2026-04

# 单国单步重跑
python3 -m analysis.countries.country_pipeline --country US --snapshot 2026-04

# 合成仪表板
python3 -m analysis.countries.cross_country      --snapshot 2026-04
python3 -m analysis.countries.dependency_matrix  --snapshot 2026-04
python3 -m analysis.countries.content_geography  --snapshot 2026-04

# 切换到 2025-04 dump 以做时序分析
analysis/countries/snapshot_swap.sh 2025-04-08
# 等待 Neo4j 加载完成（几分钟）
python3 -m analysis.countries.run_all --snapshot 2025-04
python3 -m analysis.countries.evolution --old 2025-04 --new 2026-04

# 生成主导航
python3 -m analysis.countries.run_all --report

# 验证
python3 -m analysis.countries.run_all --verify

# 查看
xdg-open analysis/countries/html/index.html
```

## 2026-04 快照发现 · 2026-04 Findings

主权指数排名（由高到低）· Sovereignty Index ranking:

| Rank | Country | Sov Idx | 托管 Hosting | DNS 主权 | RPKI | IXP 本地化 | Hub 比 |
|---|---|---|---|---|---|---|---|
| 1 | FR 🇫🇷 | 0.753 | high | — | — | — | — |
| 2 | US 🇺🇸 | 0.740 | saturated | high | — | — | — |
| 3 | NL 🇳🇱 | 0.678 | high | — | — | — | — |
| 4 | GB 🇬🇧 | 0.613 | — | — | — | — | — |
| 5 | IN 🇮🇳 | 0.533 | — | — | — | — | — |
| 6 | DE 🇩🇪 | 0.529 | — | — | — | — | — |
| 7 | JP 🇯🇵 | 0.486 | — | — | — | — | — |
| 8 | RU 🇷🇺 | 0.480 | — | — | — | — | — |
| 9 | CN 🇨🇳 | 0.269 | high | low | low | low | low |

CN 在"规模指标"领先（AS #3, Prefix #3），但"互联本地化" / "DNS 主权" / "Hub 比"皆低。
FR/US/NL 在五分项上整体均衡最高。详见 `cross_country.html`。

## 方法论要点 · Methodology

- **20 个本体维度指标**参数化，每国统一可比（见 `step_lib.py` 的 `STEP_TITLES`）
- **主权综合指数**（0-1）= 五个子分量的算术平均：
  1. Hosting 托管自给率
  2. DNS 主权率
  3. RPKI 覆盖率
  4. IXP 本地化比例
  5. Hub 比率（入向/出向 hegemony）
- **lru_cache** 在单次进程内共享重缓存（~230 MB CSVs 仅加载一次），9 国串行约 4 分钟
- Neo4j 查询失败时优雅降级，返回 `{'_error': ...}`，不中断其他步骤

## 关联文档 · Related docs

- `analysis/RESEARCH.md` — 总体研究思想与进展记录
- `analysis/china/README.md` — 原 20 步中国分析报告
- `analysis/complex_network/` — 24 步全局复杂网络分析基础
