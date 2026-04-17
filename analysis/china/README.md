# 中国在全球互联网分层中的位置 · 20 步分析报告
## China in the Global Internet Hierarchy · 20-Step IYP Analysis

> 基于 Internet Yellow Pages (IYP) Neo4j 知识图谱 · 快照 2026-04 · 分析日期 2026-04-16
> Based on IYP Neo4j knowledge graph (snapshot 2026-04, generated 2026-04-16)

## 概览 · Overview

| 指标 Metric | 数值 Value | 解读 Interpretation |
|---|---|---|
| AS 数量 全球排名 / AS count rank | #3 (6,660) | 接近头部 (US/BR/IN 之后) |
| BGP 前缀数 全球排名 / Prefix rank | #3 (109,409) | 规模靠前 |
| IXP 数 全球排名 / IXP rank | #16 (19) | 互联基础设施相对薄弱 |
| Facility 数 全球排名 / Facility rank | #33 (30) | 机房密度明显偏低 |
| 主权综合指数 / Sovereignty Index | **0.256** | 五维加权平均 |

### 主权指数分项 Sovereignty Components

- Hosting Sovereignty / 托管自给率: **0.934**
- DNS Sovereignty / DNS 自主率: **0.143**
- RPKI Adoption / 路由安全: **0.156**
- IXP Domesticization / IXP 本地化: **0.025**
- Hub-Ratio / 入向/出向: **0.019**

## 六阶段结构 · Six Phases

### Phase A · 范围与身份 Scope & Identity

#### Step 01 · 中国自治系统清册 / China AS Inventory & Scope

- 本体维度 / Ontology: _(see script docstring)_
- HTML: [`html/step01_scope.html`](html/step01_scope.html)
- total_greater_china_asns: **8624**
- cn_asns: **6660**
- hk_asns: **1468**
- tw_asns: **474**
- mo_asns: **22**
- cn_tag_categories: `{"Other": 5118, "ISP": 931, "Unknown": 284, "Enterprise": 99, "Academic/Edu": 99, "Content/CDN": 78, "Eyeball": 34, "Government": 17}`

#### Step 02 · 头部自治系统身份档案 / Top-20 Chinese ASes · Identity

- 本体维度 / Ontology: _(see script docstring)_
- HTML: [`html/step02_top_as.html`](html/step02_top_as.html)
- top_ases_analyzed: **20**
- total_prefixes_top20: **47744**
- asns: `[23911, 38255, 4134, 4837, 4538, 9808, 17621, 58543, 4847, 17622, 4812, 4808, 9929, 45102, 7497, 17623, 58466, 56040, 24490, 10111]`

#### Step 03 · 全球规模排名 / China vs World at a Glance

- 本体维度 / Ontology: _(see script docstring)_
- HTML: [`html/step03_global_ranks.html`](html/step03_global_ranks.html)
- cn_ranks_by_metric: `{"as_count": {"rank": 3, "value": 6660}, "prefix_count": {"rank": 3, "value": 109409}, "ixp_count": {"rank": 16, "value": 19}, "facility_count": {"rank": 33, "value": 30}}`

### Phase B · BGP 拓扑位置 BGP Topology

#### Step 04 · BGP 前缀与 RPKI / CN BGP Prefix Footprint

- 本体维度 / Ontology: _(see script docstring)_
- HTML: [`html/step04_prefixes.html`](html/step04_prefixes.html)
- cn_originators: **5211**
- v4_prefixes: **71967**
- v6_prefixes: **48702**
- rpki_rate_pct: **15.59**
- anycast_prefixes: **372**
- top5_originators: `[[9808, 21046], [4538, 10327], [56046, 5209], [23910, 4104], [56041, 3768]]`

#### Step 05 · 对等互联子图 / CN AS Peering Subgraph

- 本体维度 / Ontology: _(see script docstring)_
- HTML: [`html/step05_peering_graph.html`](html/step05_peering_graph.html)
- nodes_total: **400**
- cn_nodes: **60**
- foreign_nodes: **340**
- edges: **2450**
- top_foreign_countries: `{"US": 48, "DE": 26, "CH": 23, "HK": 22, "FR": 19, "GB": 19, "NL": 18, "AU": 16, "SG": 12, "BR": 11}`

#### Step 06 · 全球中心性位置 / CN in Global Centrality

- 本体维度 / Ontology: _(see script docstring)_
- HTML: [`html/step06_centrality.html`](html/step06_centrality.html)
- cn_count: **5221**
- best_pagerank_rank: **1**
- best_degree_rank: **23**
- best_betweenness_rank: **3**
- top5_by_pagerank: `[[38255, 1], [4134, 205], [4837, 390], [24429, 521], [9425, 575]]`

#### Step 07 · k-core 层级位置 / CN in Global k-Core

- 本体维度 / Ontology: _(see script docstring)_
- HTML: [`html/step07_kcore.html`](html/step07_kcore.html)
- global_max_k: **197**
- cn_deepest_coreness: **197**
- cn_count_k_ge_30: **18**
- cn_count_k_ge_100: **5**
- cn_top5_coreness: `[[24429, 197], [132203, 197], [45102, 187], [55967, 157], [4134, 125]]`

### Phase C · 依赖与 Hegemony

#### Step 08 · 出向 Hegemony / Who Does China Depend On

- 本体维度 / Ontology: _(see script docstring)_
- HTML: [`html/step08_depends_on_world.html`](html/step08_depends_on_world.html)
- total_outbound_edges_hege_ge_005: **7505**
- foreign_ases_depended_on: **269**
- top5_foreign_upstream: `[[6939, 5062, "US"], [1299, 447, "SE"], [3356, 292, "US"], [174, 200, "BE"], [2914, 145, "HK"]]`
- top_destination_countries: `{"US": 5565, "HK": 623, "SE": 449, "BE": 203, "AU": 199, "GB": 74, "BH": 56, "DE": 54}`

#### Step 09 · 入向 Hegemony / Who Depends on China

- 本体维度 / Ontology: _(see script docstring)_
- HTML: [`html/step09_dependents.html`](html/step09_dependents.html)
- total_inbound_edges_hege_ge_003: **144**
- foreign_dependents: **88**
- top5_cn_upstream: `[[10111, 33], [213605, 14], [4837, 12], [4134, 7], [134578, 7]]`
- top_dependent_countries: `{"US": 15, "HK": 12, "GB": 9, "ZZ": 6, "TW": 3, "JP": 2, "CA": 2, "IT": 2, "SG": 1, "MY": 1}`

#### Step 10 · 集中度与 HHI / China Concentration & HHI

- 本体维度 / Ontology: _(see script docstring)_
- HTML: [`html/step10_concentration.html`](html/step10_concentration.html)
- cn_gini_prefix: **0.9429**
- global_gini_prefix: **0.8495**
- cn_gini_hostname: **0.9016**
- global_gini_hostname: **0.9921**
- cn_gini_org: **0.3119**
- global_gini_org: **0.1994**
- cn_gini_ixp: **0.5303**
- global_gini_ixp: **0.522**
- cn_hhi_prefix: **0.0475**
- global_hhi_prefix: **0.0014**
- cn_hhi_hostname: **0.054**
- global_hhi_hostname: **0.0081**

### Phase D · 物理基础设施 Physical Infrastructure

#### Step 11 · IXP 互联生态 / Chinese IXP Landscape

- 本体维度 / Ontology: _(see script docstring)_
- HTML: [`html/step11_ixp_landscape.html`](html/step11_ixp_landscape.html)
- cn_ixp_memberships_total: **839**
- distinct_cn_ixps_participated: **198**
- domestic_ixps_with_cn: **6**
- foreign_ixps_with_cn: **19**
- top5_foreign_ixps: `[["ZXIX Hong Kong", 35], ["4b42 Internet Exchange Point", 30], ["FogIXP", 26], ["Protocol 7 IX - Hong Kong", 22], ["Poema IX", 18]]`
- top5_domestic_ixps: `[["CNIX", 20], ["SHIXP", 19], ["ZXIX Hangzhou", 18], ["LoLi-IX - NGB", 10], ["NNIX", 10]]`
- top5_countries_hosting_cn_presence: `{"US": 127, "CN": 127, "HK": 123, "DE": 79, "CH": 74}`

#### Step 12 · 机房部署 / CN AS Facility Co-location

- 本体维度 / Ontology: _(see script docstring)_
- HTML: [`html/step12_facilities.html`](html/step12_facilities.html)
- total_cn_as_facility_records: **276**
- distinct_facilities_with_cn: **147**
- top5_countries_by_cn_facility_presence: `{"HK": 57, "US": 56, "JP": 25, "CN": 24, "SG": 14}`
- top5_facilities: `[["MEGA-i (iAdvantage Hong Kong)", 14, "HK"], ["Equinix HK2 - Hong Kong", 13, "HK"], ["Equinix SV1/SV5/SV10 - Silicon Valley, San Jose", 8, "US"], ["Digital Realty Frankfurt FRA1-2…`

#### Step 13 · IXP×机房三部图 / IXP+Facility Tripartite

- 本体维度 / Ontology: _(see script docstring)_
- HTML: [`html/step13_ixp_fac_bridge.html`](html/step13_ixp_fac_bridge.html)
- total_tripartite_rows: **19414**
- distinct_ixps_cn_used: **198**
- distinct_facilities_used_via_ixp: **658**
- top5_ixps_for_cn: `[["DE-CIX Frankfurt", 4862, "DE"], ["NL-ix", 1458, "NL"], ["LINX LON1", 1386, "GB"], ["IX.br (PTT.br) São Paulo", 1170, "BR"], ["DE-CIX New York", 660, "US"]]`

### Phase E · DNS / 内容 / 排名 DNS / Content / Rankings

#### Step 14 · DNS 托管版图 / CN DNS Hosting Footprint

- 本体维度 / Ontology: _(see script docstring)_
- HTML: [`html/step14_dns_hosting.html`](html/step14_dns_hosting.html)
- cn_hosting_ases: **437**
- cn_total_hostnames_hosted: **280224**
- top5_cn_hosters: `[[45102, 41109], [37963, 27578], [24429, 24082], [4837, 17840], [132203, 14653]]`
- global_rank_of_cn_by_hosting: **42**
- cloud_vs_isp_split_hostnames: `{"cloud_cdn": 199163, "isp": 60124, "other": 20937}`

#### Step 15 · .cn DNS 主权 / .cn DNS Sovereignty

- 本体维度 / Ontology: _(see script docstring)_
- HTML: [`html/step15_dns_authority.html`](html/step15_dns_authority.html)
- ns_sampled_for_cn_tld: **500**
- total_cn_domains_covered: **31036**
- cn_operator_share_pct: **14.34**
- us_operator_share_pct: **5.06**
- top5_providers: `[["Other (com)", 13826], ["Other (cn)", 7739], ["Other (net)", 3086], ["Aliyun", 2832], ["Cloudflare", 1537]]`
- cn_operated_ns_serving_foreign_top: `[["vip3.alidns.com", 4505], ["vip4.alidns.com", 4500], ["vip7.alidns.com", 3957], ["vip8.alidns.com", 3954], ["f1g1ns2.dnspod.net", 3187]]`

#### Step 16 · CNAME 跨境链 / Cross-Border CNAME Chains

- 本体维度 / Ontology: _(see script docstring)_
- HTML: [`html/step16_cname_chains.html`](html/step16_cname_chains.html)
- alias_edges_sampled: **2500**
- distinct_cn_cloud_targets: **1472**
- top_target_families: `{"Aliyun": 1323, "Huawei CDN": 944, "Tencent Cloud": 141, "Aliyun CDN": 58, "Baidu": 17, "Huawei": 11, "Wangsu CDN": 3, "Huawei Cloud": 2}`
- top_individual_targets: `[["nlb-3svc79r8fxqv73kn0r.ap-southeast-1.nlb.aliyuncsslbintl.com", 382], ["nlb-wwwzr8hg1c5vya400c.ap-southeast-1.nlb.aliyuncsslbintl.com", 36], ["hcdnwsa.ovc.baimingdan.cdnhwcbie12…`

#### Step 17 · 多排名位置 / CN in Global Rankings

- 本体维度 / Ontology: _(see script docstring)_
- HTML: [`html/step17_rankings.html`](html/step17_rankings.html)
- rankings_used: `["CAIDA ASRank", "APNIC eyeball estimates (CN)", "IHR country ranking: Total eyeball (CN)", "IHR country ranking: Total AS (CN)", "CrUX top 1M (CN)"]`
- per_ranking_cn_count: `{"CAIDA ASRank": 2000, "APNIC eyeball estimates (CN)": 416, "IHR country ranking: Total eyeball (CN)": 64, "IHR country ranking: Total AS (CN)": 46, "CrUX top 1M (CN)": 0}`
- cn_ases_with_any_rank: **644**
- top5_in_primary: `[[24490, 60], [4134, 129], [4837, 229], [9808, 294], [4808, 602]]`

### Phase F · 安全 / 测量 / 综合 Security / Measurement / Synthesis

#### Step 18 · 审查拓扑 / Censorship Topology in CN

- 本体维度 / Ontology: _(see script docstring)_
- HTML: [`html/step18_censorship.html`](html/step18_censorship.html)
- cn_ases_with_censorship_signal: **23**
- cn_total_detections: **637**
- top5_censoring_ases: `[[45102, 81], [4837, 48], [4134, 45], [24400, 44], [4538, 43]]`
- top5_tests: `[["ooni.tor", 352], ["ooni.stunreachability", 157], ["ooni.whatsapp", 18], ["ooni.httpinvalidrequestline", 18], ["ooni.psiphon", 17]]`
- coreness_median_censoring: **5**
- coreness_median_non_censoring: **1.0**

#### Step 19 · Atlas 观测点 / RIPE Atlas Presence in CN

- 本体维度 / Ontology: _(see script docstring)_
- HTML: [`html/step19_atlas.html`](html/step19_atlas.html)
- cn_probes_count: **698**
- cn_probes_with_coords: **0**
- cn_rank_global_probe_count: **None**
- target_measurement_counts: `{"AS": 108, "HostName": 7}`

#### Step 20 · 综合仪表板 / Synthesis Dashboard

- 本体维度 / Ontology: _(see script docstring)_
- HTML: [`html/step20_synthesis.html`](html/step20_synthesis.html)
- composite_sovereignty_index: **0.2556**
- components: `{"Hosting Sovereignty\n托管自给率": 0.9341, "DNS Sovereignty\nDNS 自主率": 0.1434, "RPKI Adoption\n路由安全": 0.1559, "IXP Domesticization\nIXP 本地化": 0.0253, "Hub-Ratio\n入向/出向": 0.0192}`
- source_steps: `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]`

## 复现 · Reproduction

```bash
# 依赖 Dependencies
pip install plotly pyvis kaleido networkx matplotlib neo4j pandas numpy

# 运行全部 20 步 Run all 20 steps
python3 -m analysis.china.run_all

# 只运行一步 Run a single step
python3 -m analysis.china.run_all --step 7

# 生成报告与索引 Regenerate report & index
python3 -m analysis.china.run_all --report

# 验证 Verify
python3 -m analysis.china.run_all --verify
```

## 数据源 · Data Sources

- IYP Neo4j 知识图谱 · 40+ node types · 34 relationship types
- 复用全局缓存 CSV: `analysis/complex_network/data/`
- 主要数据提供方 (via IYP): BGPKIT, CAIDA, PeeringDB, OpenINTEL, IHR, APNIC, Tranco, RIPE NCC, OONI, RIPE Atlas

## 科学视角 · Scientific Lenses

- 复杂网络: Barabási, Newman (度分布 / k-core / 中心性)
- 互联网 Hegemony: Pelsser/IHR
- 关键基础设施: Labovitz, Feamster
- 互联网主权: Milton Mueller, Niels ten Oever
- 测量方法: CAIDA, RIPE Atlas