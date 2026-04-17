# IYP 科研分析目录 · Research Analysis Directory

本目录汇集基于 Internet Yellow Pages (IYP) Neo4j 知识图谱的全部科研分析代码与结果。
This directory collects all research analysis code and results built on the Internet Yellow
Pages (IYP) Neo4j knowledge graph.

## 目录结构 · Layout

```
analysis/
├── README.md                         # 本文件 · this file
├── Complex-Network-Analysis-Report.md
│                                     # 24-step 全球复杂网络分析报告
├── complex_network/                  # 全球 24 步复杂网络分析 · code
│   ├── utils.py
│   └── step01_*.py … step24_*.py
├── complex_network_images/           # 全球分析 PNG 输出 · outputs
│   └── *.png
├── china/                            # 20 步「中国在全球互联网中的位置」分析
│   ├── README.md                     # 双语子报告
│   ├── common.py / run_all.py
│   ├── step01_*.py … step20_*.py
│   ├── data/                         # CN 专属分析结果 (small CSVs + JSON)
│   └── html/                         # 21 个交互式 HTML (含 index.html)
├── exploratory/                      # 早期探索脚本与 PNG · early scripts
│   ├── as_peering_graph.py / as_peering_extended.py
│   ├── cdn_detection.py / hostname_analysis.py
│   └── *.png
├── cloudflare_analysis.py            # Cloudflare 25 步全链分析
└── ontology_visualization.py         # IYP 本体与初始中国依赖可视化
```

## 大文件策略 · Large-file policy

原始及派生 CSV 数据（可从 Neo4j 重新生成）保存在仓库根部 `data_cache/`，
已加入 `.gitignore`，不随代码分发。分析脚本通过
`analysis/complex_network/utils.py` 中的 `DATA_DIR` 查找这些文件，
也可用环境变量 `IYP_ANALYSIS_DATA_DIR` 覆盖。

Raw / derived CSVs (regeneratable from Neo4j) live under `data_cache/` at the repo root
and are git-ignored. Scripts find them via `DATA_DIR` in
`analysis/complex_network/utils.py`; override with `IYP_ANALYSIS_DATA_DIR=/other/path`.

```bash
# 重新生成 data_cache/complex_network/*.csv
python3 -m analysis.complex_network.step01_extract_bgp_layer
python3 -m analysis.complex_network.step02_extract_dns_layer
python3 -m analysis.complex_network.step03_extract_physical_layer
python3 -m analysis.complex_network.step04_extract_org_censorship
```

## 主要分析 · Primary analyses

| Analysis | 步数 | 入口 Entry Point | 视角 Lens |
|---|---|---|---|
| 全球复杂网络 · Global complex network | 24 | `analysis/complex_network/step*` | Barabási / Newman |
| Cloudflare 全链 · Cloudflare full-chain | 25 | `analysis/cloudflare_analysis.py` | Single-AS deep-dive |
| 中国位置 · China in Global Internet | 20 | `analysis/china/run_all.py` | 互联网主权 + Hegemony |
| 九国跨国+时序 · Cross-Country + Time-Series | 20 × 9 × 2 | `analysis/countries/run_all.py` | Cross-country comparison, YoY evolution |

## 快速开始 · Quick start

```bash
# 安装依赖 dependencies
pip install -r requirements.txt
pip install plotly pyvis kaleido

# 启动 Neo4j (见顶层 README)

# 首次 — 重建原始数据缓存 (约 10-30 分钟)
python3 -m analysis.complex_network.step01_extract_bgp_layer
python3 -m analysis.complex_network.step02_extract_dns_layer
python3 -m analysis.complex_network.step03_extract_physical_layer
python3 -m analysis.complex_network.step04_extract_org_censorship

# 运行中国分析 (20 步)
python3 -m analysis.china.run_all

# 打开交互式仪表板
xdg-open analysis/china/html/index.html
```
