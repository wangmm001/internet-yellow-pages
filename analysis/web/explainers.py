'''Plain-language chart explainers (图解) for every non-China page.

Follows the tone & structure of the existing China pages:
  这是什么图 / 怎么读 / 能看出什么 — accessible, not academic.

Keyed by canonical page URL (matches ``nav.Page.url``).  Missing entries
render the wrapper without a 图解 button.
'''
from __future__ import annotations

EXPLAINERS: dict[str, dict] = {}


def _add(url: str, title_zh: str, title_en: str, *, what: tuple[str, str],
         how: tuple[str, str] | None = None,
         see: tuple[str, str],
         keyterm: tuple[str, str, str] | None = None) -> None:
    EXPLAINERS[url] = {
        'title_zh': title_zh, 'title_en': title_en,
        'what_zh': what[0], 'what_en': what[1],
        'how_zh': how[0] if how else None,
        'how_en': how[1] if how else None,
        'see_zh': see[0], 'see_en': see[1],
        'keyterm_zh': keyterm[1] if keyterm else None,
        'keyterm_en': keyterm[2] if keyterm else None,
        'keyterm_label': keyterm[0] if keyterm else None,
    }


# ======================================================================
# COUNTRIES · 9 profiles
# ======================================================================

_add('/countries/US/', '美国互联网分层', 'United States · Internet Hierarchy',
     what=(
         '把美国在全球互联网中的位置铺成一张多维画像：AS 清册、BGP 前缀、上游/下游依赖、'
         'IXP 与机房、DNS 托管、CNAME 链、OONI 审查、Atlas 观测点，共 20 步。',
         'A 20-step portrait of the United States as a node in the global Internet — '
         'AS inventory, BGP prefix footprint, upstream/downstream Hegemony, IXPs and facilities, '
         'DNS hosting, CNAME chains, OONI censorship, RIPE Atlas probes.'),
     how=(
         '每一步都是一张同样尺寸的卡片：左上为中文标题、右上为英文副标题。从上向下滚动可看到 '
         '"范围 → BGP → 依赖 → 物理基础设施 → DNS/内容 → 安全测量 → 综合主权指数" 的完整链路。',
         'Scroll top-down for a six-phase narrative: scope → BGP topology → dependency → '
         'physical infrastructure → DNS/content → security/measurement → composite sovereignty.'),
     see=(
         '美国是典型的"输出型"互联网经济体：AS 数与前缀量全球第 1，Tier-1 主干密布，主要内容企业'
         '(Google/Meta/AWS/Cloudflare) 本土注册；主权指数 2026-04 为 0.740，接近满分，反映 DNS/'
         'RPKI/IXP/内容四维度都在本土闭环。',
         'The US is the archetypal "exporter" economy — #1 in AS count and prefixes, dense Tier-1 '
         'backbone, Google/Meta/AWS/Cloudflare all domiciled domestically. Sovereignty index 0.740 '
         '(2026-04) reflects near-complete domestic closure of DNS/RPKI/IXP/content.'),
     keyterm=('主权指数', '主权指数 (Sovereignty Index) 是本研究定义的 5 维综合分数：托管、DNS、RPKI、'
              'IXP、枢纽比率各 1 分，加权求和。分数越高意味着该国互联网资源在自己国境内越"闭环"。',
              'The Sovereignty Index is a composite score over five dimensions (hosting, DNS, RPKI, '
              'IXP, hub ratio). Higher = more self-contained on home soil.'))

_add('/countries/CN/', '中国互联网分层', 'China · Internet Hierarchy',
     what=(
         '把中国作为"单一国家"重新拼出它在全球互联网中的 20 维画像。与中国专题不同的是，这里使用'
         '九国统一管线，指标可与美、欧、亚等同口径对比。',
         'China as a single country, re-assembled through the same 20-metric pipeline used for '
         'the other 8 peers. All numbers here are directly comparable with US/EU/JP.'),
     how=(
         '向下滚动可见 6 个研究阶段，最后一张"综合主权指数"面板汇总 5 个分项：托管、DNS、RPKI、IXP、'
         '枢纽比率；每项从 0 到 1。',
         'Scroll to the final dashboard: a 5-dimension sovereignty composite — hosting, DNS, RPKI, '
         'IXP, hub ratio — each on 0..1.'),
     see=(
         '中国呈现"主权悖论"：托管维度接近满分(0.93) 意味着中国网站大多托管在中国境内；但 DNS、'
         'RPKI、IXP、枢纽比率都很低，说明底层解析与路由仍严重依赖境外。2026-04 综合分 0.269，较 2025 '
         '年 +0.050，全球排名第 9/9——九国中最低。',
         'China displays a "sovereignty paradox" — hosting near 1.0 (sites live on-shore), but DNS, '
         'RPKI, IXP, and hub-ratio all low (resolution + routing still depend on offshore actors). '
         'Composite 0.269 in 2026-04 (+0.050 YoY), last of 9.'))

_add('/countries/JP/', '日本互联网分层', 'Japan · Internet Hierarchy',
     what=('日本的 20 步画像：从 AS 数 (全球前 10)、Tier-1 连通度，到 JPIX/JPNAP 等内部 IXP、域名 .jp '
           '的本土运营度、以及对美依赖深度。',
           'A 20-step portrait of Japan — AS count (global top-10), Tier-1 connectivity, JPIX/JPNAP '
           'IXPs, .jp domestic operation, and depth of US dependence.'),
     how=('阶段 D (物理基础设施) 是日本的亮点：JPIX 和 JPNAP 的会员数和交换流量在亚太仅次于 HK；阶段 E '
          '则显示 .jp 的权威 NS 几乎全部本土运营。',
          'Phase D (physical infra) is Japan\'s strength — JPIX/JPNAP rank second in APAC behind HK. '
          'Phase E shows .jp authoritative NS is almost entirely domestic.'),
     see=('2026-04 主权分 0.486 (−0.095 YoY)：下滑主要来自 CDN/云端内容向美国回迁；但 DNS 与 IXP '
          '维度仍保持在 0.6-0.7，反映日本"南北向下沉而东西向依旧独立"的格局。',
          'Sovereignty 0.486 in 2026-04 (−0.095 YoY). The drop came from CDN/cloud content shifting '
          'back to US edges; DNS and IXP dimensions still sit at 0.6-0.7 — Japan remains east-west '
          'independent while its north-south stack leaks.'))

_add('/countries/IN/', '印度互联网分层', 'India · Internet Hierarchy',
     what=('印度从 2015 年后以"人口红利 + Jio 革命"迅速扩张，20 步画像回答：印度互联网是在复刻中国'
           '(自建闭环) 还是复刻东南亚 (依赖美云) ？',
           'India has exploded post-Jio (2016+). Is its topology heading toward a China-style closed '
           'loop, or an SEA-style US-cloud dependence?'),
     how=('重点看阶段 C (出向 Hegemony) 与阶段 E (DNS 托管)：前者揭示印度对谁最依赖，后者反映印度'
          '本土 DNS/内容有多大份额在自家手里。',
          'Focus on Phase C (upstream Hegemony) and Phase E (DNS hosting share) — the former shows '
          'who India depends on, the latter how much home-grown DNS/content stays on-shore.'),
     see=('2026-04 主权 0.533 (+0.025)：Jio/Airtel/BSNL 构成本土 AS 骨架但上游主导权仍在美国云；'
          'IXP 密度偏低(NIXI 仅 4 个主节点)，印度正在复刻"大市场、弱交换"的东南亚范式而非中国范式。',
          'Sovereignty 0.533 (+0.025). Jio/Airtel/BSNL form the domestic AS spine, but upstream '
          'dominance remains US cloud. IXP density is low (NIXI only 4 major POPs) — India is '
          'tracking a "big-market, thin-exchange" SEA pattern rather than China\'s closed loop.'))

_add('/countries/DE/', '德国互联网分层', 'Germany · Internet Hierarchy',
     what=('德国是欧洲互联网的"交换之都"——DE-CIX (法兰克福) 是全球流量最大的 IXP 之一。20 步画像'
           '考察：这种 IXP 中心性是否外溢成全链路自主权？',
           'Germany is Europe\'s "exchange capital" — DE-CIX (Frankfurt) is one of the largest IXPs '
           'globally. Does that IXP centrality translate to full-stack sovereignty?'),
     how=('阶段 D (IXP × 机房) 的 Sankey 图应最能说明问题：看 DE-CIX 的会员构成与非德国 AS 在德国境内'
          '的机房分布。',
          'Phase D (IXP × facility Sankey) is the key view — DE-CIX member mix and the footprint of '
          'non-German ASes colocated in German carriers.'),
     see=('2026-04 主权分 0.529 (−0.065)：法兰克福的 IXP 霸主地位带来很高的 IXP 分，但 DNS 和托管'
          '双维度被美国云拉低。德国在"物理层高度主权、应用层中度依赖"的光谱上。',
          'Sovereignty 0.529 (−0.065 YoY). Frankfurt\'s IXP primacy lifts the IXP sub-score, but US-'
          'cloud pressure drags DNS/hosting down — Germany sits on a "physical-layer sovereign, '
          'application-layer dependent" axis.'))

_add('/countries/GB/', '英国互联网分层', 'United Kingdom · Internet Hierarchy',
     what=('英国以 LINX (伦敦) + 跨大西洋海缆为核心，是欧洲通向美国的主要走廊。20 步画像回答：'
           '英国是"地理中介" 还是"独立节点" ？',
           'The UK sits at the nexus of LINX + transatlantic cables, Europe\'s primary corridor to '
           'the US. Is Britain more a "geographic intermediary" or a standalone node?'),
     how=('阶段 B (BGP 拓扑位置) + 阶段 C (依赖) 对比看：若英国 AS 大量承担过境流量、自身又高度'
          '依赖美云，则其"中介属性"压过"主权属性"。',
          'Compare Phase B (topology) with Phase C (dependency) — if UK ASes carry heavy transit '
          'while depending heavily on US cloud, intermediary > sovereign.'),
     see=('2026-04 主权 0.613 (+0.022)：英国在 IXP (LINX 排名顶级) 和 RPKI 部署上表现强，'
          'DNS/托管维度因伦敦金融科技企业的欧美混合云架构而偏中。',
          'Sovereignty 0.613 (+0.022). Strong on IXP (LINX is top-tier) and RPKI adoption; DNS/'
          'hosting middling due to City fintech\'s hybrid US-EU cloud stacks.'))

_add('/countries/FR/', '法国互联网分层', 'France · Internet Hierarchy',
     what=('法国 2026-04 取代美国登顶主权榜——这份画像揭开其"全维主权栈"的底牌：从 .fr 的 Afnic '
           '自持，到 OVH/Scaleway 本土云，到 France-IX 的内部互联。',
           'France topped the 2026-04 sovereignty leaderboard. This profile opens the hood on its '
           'full-stack domestic: Afnic-operated .fr, OVH/Scaleway domestic cloud, France-IX '
           'interconnection.'),
     how=('阶段 E 最亮眼：.fr 的权威 NS 基本在 FR 本土 AS 中；OVH (AS 16276) 把托管维度直接拉到 0.85+。',
          'Phase E is the standout — .fr authoritative NS sits on FR-domestic ASes; OVH (AS 16276) '
          'pushes the hosting dimension above 0.85.'),
     see=('2026-04 主权分 0.753 (+0.104)：法国是证明"中等经济体可凭政策 + 本土云实现数字主权"的样本；'
          'YoY +0.104 反映 OVHcloud 过去一年的积极扩张。',
          'Sovereignty 0.753 (+0.104) — France proves mid-size economies can achieve digital '
          'sovereignty via policy + domestic cloud. The +0.104 YoY reflects aggressive OVHcloud '
          'expansion.'))

_add('/countries/NL/', '荷兰互联网分层', 'Netherlands · Internet Hierarchy',
     what=('荷兰的 AS/人口比是欧洲最高之一，AMS-IX 长期位列全球流量三甲。20 步画像考察：'
           '一个小国能否靠"交换 + 透明政策"成为自主权范例？',
           'The Netherlands has one of Europe\'s highest AS/capita ratios; AMS-IX has long sat in '
           'the global top-3 by traffic. Can a small country become a sovereignty exemplar via '
           '"exchange + transparency"?'),
     how=('阶段 D (机房) + 阶段 B (centrality) 叠看：荷兰 AS 数远超其人口对应的比例，是被大量海外 '
          'AS "借壳" 到荷兰经 AMS-IX 互联的结果。',
          'Phase D (facilities) × Phase B (centrality) — NL AS count far exceeds its population '
          'share because many foreign ASes register NL presence to tap AMS-IX.'),
     see=('2026-04 主权 0.678 (−0.016)：AMS-IX 带来极高的 IXP/枢纽分，但 DNS 托管因为大量"镜像式"'
          '海外企业在荷兰注册 AS 而拉低；整体仍位列九国第三。',
          'Sovereignty 0.678 (−0.016). AMS-IX drives IXP/hub sub-scores sky-high, but hosting '
          'dilutes because many foreign "shell" ASes register NL presence — overall 3rd of 9.'))

_add('/countries/RU/', '俄罗斯互联网分层', 'Russia · Internet Hierarchy',
     what=('俄罗斯是 "受压-隔离-半脱钩" 的特殊样本。2022 年以来西方 AS 大量撤出，OONI 审查检测量跃居'
           '全球第一。20 步画像量化这一变迁。',
           'Russia is a stressed/isolating/semi-decoupled special case. Western ASes have withdrawn '
           'en masse post-2022, and OONI censorship detections now rank #1 globally. This profile '
           'quantifies the shift.'),
     how=('阶段 F (安全测量) 是俄罗斯最有戏剧性的视角：CENSORED 检测量远超其它国家；阶段 C 的出向'
          'hegemony 显示俄罗斯对亚洲 (CN/HK/KZ) 上游的新依赖。',
          'Phase F (security/measurement) is the dramatic view — CENSORED detections dominate. '
          'Phase C (upstream Hegemony) reveals new dependence on Asian (CN/HK/KZ) upstreams.'),
     see=('2026-04 主权 0.480 (−0.122 YoY)：俄罗斯正同时经历"主动孤立 + 被动脱钩"——本土 DNS/RPKI '
          '建设加速，但托管维度因西方云撤出和本土替代尚未成熟而双重下行。',
          'Sovereignty 0.480 (−0.122 YoY). Russia is simultaneously self-isolating and being cut '
          'off — domestic DNS/RPKI builds are accelerating, but hosting falls on both ends (Western '
          'clouds leaving, local alternatives still nascent).'))


# ======================================================================
# COUNTRIES · 4 synthesis dashboards
# ======================================================================

_add('/countries/dashboards/cross-country/', '九国横向对比', 'Cross-Country Dashboard',
     what=('把九国在 20 个维度上的表现拉到一张雷达/矩阵图上，便于一眼看出谁强在哪、谁弱在哪。',
           'Nine countries × 20 metrics on a single radar/matrix — quick read of each nation\'s '
           'strengths and weaknesses.'),
     how=('雷达的每个顶点是一个指标 (AS 数、前缀、IXP、主权分项等)；外圈越远代表数值越大。叠放九国的'
          '雷达可发现"形状相似的邻居 "。',
          'Each radar axis is one metric (AS count, prefixes, IXP, sovereignty sub-scores …). '
          'Farther from center = larger. Overlaying nine radars reveals "shape neighbours".'),
     see=('可以观察到两个显著的"形状 cluster "：(1) US/CN/FR 的全维领先雷达；(2) JP/DE/GB 中等全面型；'
          'RU/IN 呈现特殊 "凹陷"。',
          'Two notable shape clusters emerge — (1) US/CN/FR as full-dimension leaders, (2) JP/DE/GB '
          'as balanced mid-tier, and RU/IN showing characteristic "dents".'))

_add('/countries/dashboards/evolution/', '时序演化 · 2025 → 2026', 'Time-Series Evolution',
     what=('把九国 20 个指标在 2025-04 和 2026-04 两个快照之间的变化画成瀑布/迁移图，量化"一年发生了什么"。',
           'Nine countries × 20 metrics across 2025-04 and 2026-04 snapshots — a waterfall / '
           'migration view that quantifies what changed in one year.'),
     how=('每一条柱子代表一国在某指标上的 Δ。绿色上行、红色下行；最粗的柱子即过去一年最大变化。',
          'Each bar = a country\'s Δ on one metric. Green = up, red = down; thickest bar = biggest '
          'shift YoY.'),
     see=('主权指数层面：FR/US 涨幅最大 (+0.104 / +0.124)，RU/JP 跌幅最大 (−0.122 / −0.095)；一个明显的'
          '趋势是"主权向头部集中"——强者愈强。',
          'Sovereignty deltas: FR/US gained the most (+0.104 / +0.124), RU/JP lost the most (−0.122 / '
          '−0.095). A clear "sovereignty to the top" trend — the strong get stronger.'))

_add('/countries/dashboards/matrix/', '九国依赖矩阵', 'Cross-Country Dependency Matrix',
     what=('一张 9×9 热图：行 i 列 j 的格子颜色深浅代表 "国家 i 有多少前缀走 j 国家的上游"。'
           '红色 = 依赖深、蓝色 = 依赖浅。',
           'A 9×9 heatmap: cell (i,j) color intensity = fraction of country-i prefixes transiting '
           'through country-j upstreams. Red = deep dep, blue = shallow.'),
     how=('对角线是自依赖 (正常情况下最红)；某行的 j 列显眼 = 该国对 j 高度依赖。',
          'Diagonal = self-dependency (normally reddest). Off-diagonal bright cells flag heavy '
          'bilateral dependencies.'),
     see=('九国之外最亮的列永远是美国——即使法国/德国/日本这些"主权高分"国家，其上游依赖依然有 '
          '30-60% 落在 US 境内。这说明主权是"资源归属"而非"路径独立"。',
          'Beyond the diagonal, the brightest column is always the US — even "high-sovereignty" '
          'FR/DE/JP still transit 30-60% through US networks. Sovereignty ≠ path independence.'))

_add('/countries/dashboards/geography/', '内容地理分布', 'Content Geography',
     what=('把全球主流 CDN/云厂商 (Cloudflare/Akamai/Fastly/Google/AWS/Alibaba) 的物理机房'
           '落点投射到地图上，看内容分发的"地理脚印"在哪儿密集。',
           'Physical facility footprint of major CDNs/clouds (Cloudflare/Akamai/Fastly/Google/AWS/'
           'Alibaba) on a world map — where the content-delivery "feet" cluster.'),
     how=('每个点是一个机房，颜色按厂商区分；点的大小按该机房下承载的 AS 数；叠加九国国界便于对比。',
          'Each dot = one facility, colour = provider, size = # of ASes colocated there. Country '
          'borders overlaid for reference.'),
     see=('亚洲内容密度显著低于欧美——尤其中国大陆几乎无 Cloudflare/Akamai/Fastly 节点；但 Alibaba 的'
          '点把东亚补上一个独立"岛"；俄罗斯 2022 后几乎看不到西方 CDN 节点。',
          'Asia holds far less density than US/EU — mainland China has essentially no '
          'Cloudflare/Akamai/Fastly presence, though Alibaba fills a separate East-Asian "island". '
          'Russia post-2022 shows almost zero Western CDN dots.'))


# ==================== CHINA (track) ====================

_add('/china/evolution/', '时序演化', 'Network Time-Series',
     what=(
         '把中国大陆互联网的 20 项核心指标（AS 数、前缀量、IXP 成员数、主权指数等）按时间'
         '轴展开，覆盖 2024-01 到 2026-04 共 11 个季度快照，让读者一眼看出哪些维度在增长、'
         '哪些在停滞或收缩。',
         'Eleven quarterly snapshots (2024-01 → 2026-04) of 20 core metrics for '
         'mainland China — AS count, prefix volume, IXP membership, sovereignty index, '
         'and more — laid out as a multi-panel time series so trends and stagnations '
         'are immediately visible.'),
     see=(
         '大陆 AS 总数从 2024-01 约 6,100 稳步攀升至 2026-04 的 6,660；BGP 前缀量呈同向'
         '增长；而 IXP 成员数和主权指数在多数季度几乎持平，暗示底层互联架构的改变远慢于地址空间扩张。',
         'Mainland AS count grew steadily from ~6,100 (2024-01) to 6,660 (2026-04); '
         'BGP prefix volume tracks in step. By contrast, IXP membership and the '
         'sovereignty index barely moved across most quarters, suggesting the '
         'underlying interconnect architecture changes far slower than address-space '
         'expansion.'))

_add('/china/step01/', 'AS 清册与范围', 'AS Inventory & Scope',
     what=(
         '列出归属于中国大陆、中国香港和中国台湾的全部 AS，按注册机构（APNIC/ARIN/RIPE）、'
         'AS 类型（ISP/内容/企业）和所在地理区域分组，给出每个维度的数量与占比，'
         '是整个中国专题的"人口普查"底牌。',
         'A census of all ASes registered to mainland China, Hong Kong, and Taiwan — '
         'broken down by registry (APNIC/ARIN/RIPE), AS type (ISP/content/enterprise), '
         'and geographic sub-region. Numbers and share per slice form the baseline '
         'for all subsequent steps.'),
     see=(
         '中国大陆共 6,660 个 AS，中国香港 1,468 个，中国台湾 474 个；三地合计超过 8,600 个。'
         '大陆 AS 中 ISP 类型占多数，企业直联 AS 比例近年稳步上升，折射出大型互联网企业自建网络的趋势。',
         'Mainland China has 6,660 ASes, Hong Kong 1,468, Taiwan 474 — over 8,600 '
         'combined. ISP-type ASes dominate the mainland, but enterprise-direct ASes '
         'have grown steadily, reflecting the trend of large internet companies '
         'building their own networks.'))

_add('/china/step02/', '头部 AS 身份档案', 'Top AS Identity Profiles',
     what=(
         '对中国大陆流量最大的 Top-20 AS 逐一建档：AS 号、注册机构、ASN 持有人、'
         '前缀数量、IXP 出席数、上游依赖等，将量化数据与组织背景并排呈现，'
         '回答"谁是中国互联网的骨干运营者"。',
         'Individual profiles for the Top-20 Chinese mainland ASes by prefix count — '
         'ASN, registry, operator name, prefix footprint, IXP presence, and upstream '
         'dependencies presented side by side, answering "who runs the Chinese Internet '
         'backbone?"'),
     see=(
         'Top-20 AS 合计持有约 44% 的大陆 BGP 前缀，高度集中于中国电信（AS 4134/4809）、'
         '中国联通（AS 4837）和中国移动（AS 9808）三家运营商；其余头部 AS 来自阿里云、'
         '腾讯和华为，反映运营商与互联网巨头的双轨格局。',
         'The Top-20 ASes collectively hold ~44% of mainland BGP prefixes, heavily '
         'concentrated in China Telecom (AS 4134/4809), China Unicom (AS 4837), and '
         'China Mobile (AS 9808). Remaining top entries come from Alibaba Cloud, '
         'Tencent, and Huawei — a dual-track of carriers plus internet giants.'))

_add('/china/step03_part1/', '全球排名 · 规模', 'Global Rankings · Scale',
     what=(
         '把中国大陆的 AS 数量、BGP 前缀量和 IXP 出席数放入全球国家排行榜，'
         '用横条图展示中国与美国、德国、日本等国的绝对差距，坐标轴使用对数刻度以便容纳极端值。',
         'Places mainland China\'s AS count, BGP prefix volume, and IXP presence on '
         'global country leaderboards. Horizontal bar charts with log-scale axes '
         'compare China against the US, Germany, Japan, and other major peers.'),
     see=(
         '中国大陆 AS 数全球第 3（仅次于美国和巴西）、BGP 前缀全球第 3；但 IXP 出席数仅排第 16，'
         '远低于同体量国家，说明中国在物理互联层的参与度与其地址空间规模严重不匹配。',
         'Mainland China ranks #3 globally in both AS count and BGP prefix volume '
         '(behind only the US and Brazil). IXP presence, however, sits at just #16 — '
         'far below peers of similar scale, exposing a sharp mismatch between '
         'address-space mass and physical interconnect participation.'))

_add('/china/step03_part2/', '全球排名 · 连通度', 'Global Rankings · Connectivity',
     what=(
         '从连通度角度衡量中国在全球的位置：出向和入向 BGP 路径多样性、Hegemony 中位数、'
         '平均 AS 跳数等指标在全球 200+ 国家中的排名，横条图逐指标展开。',
         'Connectivity-oriented global rankings for mainland China — outbound and '
         'inbound BGP path diversity, median Hegemony score, average AS hop count — '
         'across 200+ countries, one bar chart per metric.'),
     see=(
         '中国大陆的出向路径多样性偏低，表明到达国际互联网的路由出口相对集中，'
         '约 70% 以上的境外流量需经由少数骨干 AS 的上游传输，'
         '连通度排名与体量排名存在明显落差。',
         'Mainland China\'s outbound path diversity is below-average; over 70% of '
         'international traffic is funnelled through a handful of backbone upstreams. '
         'Connectivity rankings lag notably behind scale rankings, confirming a '
         'structural bottleneck at the border.'))

_add('/china/step03_part3/', '全球排名 · 内容', 'Global Rankings · Content',
     what=(
         '从内容维度评估中国大陆的全球位置：Tranco / CrUX 排行榜中注册在大陆的域名占比、'
         'DNS 托管在境内的比例、全球 CDN 节点在中国大陆的覆盖密度，各项指标排名并列展示。',
         'Content-layer global rankings for mainland China — share of Tranco/CrUX '
         'top-list domains registered domestically, fraction of DNS hosted on-shore, '
         'and global CDN node density inside China, all ranked country-by-country.'),
     see=(
         'Tranco 百万榜中大陆注册域名比例可观，但境外 CDN（Cloudflare/Akamai）在中国大陆'
         '几乎没有落地节点，导致"内容生产在国内、分发基础设施在境外"的结构性矛盾，'
         '中国大陆内容指标排名低于其域名数量本应对应的位置。',
         'A notable share of Tranco million-domain registrations are mainland-based, '
         'but global CDNs (Cloudflare, Akamai) have virtually no presence inside '
         'mainland China. This yields a structural paradox: content is produced '
         'domestically, but the distribution infrastructure is largely offshore.'))

_add('/china/step03_part4/', '全球排名 · 综合', 'Global Rankings · Composite',
     what=(
         '把规模、连通度、内容三个子维度合并成一个综合得分，与全球 200+ 国家横向比较，'
         '用雷达图 + 排行条形图双视角呈现中国大陆在"体量型 vs 效率型"轴上的位置。',
         'Aggregates scale, connectivity, and content sub-scores into a composite '
         'ranking across 200+ countries. A radar plus bar-chart dual view places '
         'mainland China on a "mass vs. efficiency" axis.'),
     see=(
         '综合来看，中国大陆是典型的"体量领先、效率偏低"国家：规模维度全球前 3，'
         '但连通度和内容分发效率双双拖后腿；若按综合得分排名，实际位次在 5-10 名之间浮动，'
         '说明体量并不直接等于互联网影响力。',
         'Overall, mainland China is a "high-mass, low-efficiency" nation — top-3 '
         'on scale but dragged down by connectivity and content distribution scores. '
         'On the composite ranking it floats between 5th and 10th globally, '
         'demonstrating that raw size does not automatically translate to influence.'))

_add('/china/step04_part1/', 'BGP 前缀与 RPKI · 分布', 'BGP Prefixes & RPKI · Distribution',
     what=(
         '展示中国大陆 BGP 前缀的地址族（IPv4 vs IPv6）分布、前缀长度直方图以及'
         'RPKI 覆盖状态（Valid/Invalid/NotFound）的饼图，让读者直观掌握路由公告的整体构成。',
         'Distribution of mainland China\'s BGP prefixes by address family (IPv4 vs '
         'IPv6), prefix-length histogram, and RPKI coverage status (Valid / Invalid / '
         'NotFound) as a pie chart — a structural snapshot of China\'s routing '
         'advertisement landscape.'),
     see=(
         '中国大陆共公告约 109,409 条前缀，IPv4 占绝大多数；RPKI 覆盖率约在中等水平——'
         'Valid 占比低于全球平均，NotFound 比例偏高，说明大量前缀尚未签署 ROA，'
         '存在路由劫持风险。',
         'Mainland China announces ~109,409 prefixes, overwhelmingly IPv4. RPKI '
         'coverage is moderate — the Valid fraction sits below global average, and '
         'NotFound is high, meaning a large share of prefixes lack signed ROAs and '
         'remain exposed to route-hijack risk.'))

_add('/china/step04_part2/', 'BGP 前缀与 RPKI · 采纳', 'BGP Prefixes & RPKI · Adoption',
     what=(
         '聚焦 RPKI 采纳进度：分运营商（按前缀量 Top-10）显示各家的 Valid/NotFound 比率，'
         '并与 2024-01 基线对比，衡量过去两年中国大陆的 RPKI 部署进展。',
         'Zooms in on RPKI adoption per operator — Valid/NotFound ratio for the '
         'Top-10 Chinese ASes by prefix count, compared with the 2024-01 baseline '
         'to measure two years of deployment progress.'),
     see=(
         '中国电信和中国联通的 RPKI Valid 比率在 2024-2026 间有所提升，但仍落后于欧洲同类运营商；'
         '中国移动进展相对迟缓；小型内容 AS 的 ROA 覆盖普遍偏低，'
         '整体采纳速度明显慢于全球中位数。',
         'China Telecom and China Unicom\'s RPKI Valid ratios improved from 2024 to '
         '2026, but still trail European peers. China Mobile shows slower progress; '
         'smaller content ASes have minimal ROA coverage. Overall adoption pace is '
         'notably below the global median.'))

_add('/china/step05/', 'AS 对等子图', 'AS Peering Subgraph',
     what=(
         '抽取中国大陆及中国香港的 BGP 对等关系，用力导向布局绘制一张交互式网络图：'
         '节点 = AS，边 = 对等或客户-提供商关系，节点大小按前缀数着色，'
         '聚焦"大陆-香港-全球"三层连通结构。',
         'Extracts BGP peering links among mainland China and Hong Kong ASes and '
         'renders an interactive force-directed graph (nodes = ASes, edges = '
         'peer or customer-provider). Node size scales with prefix count; colour '
         'highlights the mainland–HK–global three-layer structure.'),
     see=(
         '图中约 400 个节点、2,450 条边；中国电信、中国联通、中国移动三者处于中心，'
         '大量小 AS 作为叶节点依附其上。中国香港 AS 形成明显的"跨境枢纽"子群，'
         '是大陆 AS 连接国际互联网的主要桥梁之一。',
         'The graph contains ~400 nodes and ~2,450 edges. China Telecom, Unicom, and '
         'Mobile occupy the centre; scores of smaller ASes hang as leaves. '
         'Hong Kong ASes form a visible "cross-border hub" subcluster, serving as '
         'one of the primary bridges between the mainland and global Internet.'))

_add('/china/step06/', '全球中心性位置', 'Global Centrality Position',
     what=(
         '将中国大陆的 AS 们放入全球 BGP 图中计算四种中心性指标（度中心性、介数、'
         '特征向量、PageRank），并在全球排名分布中标出中国大陆的位置，'
         '展示其在全球路由网络中的影响力。',
         'Computes four centrality metrics (degree, betweenness, eigenvector, '
         'PageRank) for mainland China\'s ASes within the full global BGP graph, '
         'then marks China\'s position inside each global ranking distribution — '
         'a holistic view of influence within the routing graph.'),
     see=(
         '中国大陆 AS 群整体 PageRank 中等（未进全球前 10）但度数偏高（全球前 5）：'
         '这意味着中国 AS 连接了大量本土节点，但在全球路由决策中的权重低于体量预期，'
         '反映"内向型"网络拓扑特征。',
         'Mainland China\'s ASes show moderate aggregate PageRank (outside global '
         'top-10) but high degree centrality (top-5 globally). This means China\'s '
         'ASes connect to many domestic nodes but carry less global routing weight '
         'than their scale suggests — a signature of an inward-facing topology.'))

_add('/china/step07/', 'k-core 层级位置', 'k-Core Layer Position',
     what=(
         '在全球 BGP 图的 k-core 分解结果中，标出中国大陆各 AS 所在的核层深度（k 值），'
         '并与美国、欧洲 AS 的层级分布对比，回答"中国大陆有多少 AS 进入了全球互联网的'
         '真正核心"。',
         'Labels each mainland China AS with its k-core depth in the global BGP graph, '
         'then compares the resulting layer-depth distribution against US and European '
         'ASes — answering "how many Chinese ASes are in the genuine global backbone?"'),
     see=(
         '绝大多数中国大陆 AS 集中在 k=1-10 的浅层；只有少数（主要是中国电信 AS 4134、'
         '中国联通 AS 4837）进入 k=30 以上的深层核心，'
         '与美国超大型运营商相比核心层密度明显较低。',
         'The vast majority of mainland ASes cluster in the shallow k=1–10 range. '
         'Only a handful — primarily China Telecom (AS 4134) and China Unicom '
         '(AS 4837) — reach k=30+. Core-layer density is markedly lower than '
         'US hyperscale operators.'))

_add('/china/step08/', '出向 Hegemony', 'Outbound Hegemony',
     what=(
         '用 IHR Hegemony 指数量化中国大陆每条前缀到达全球其他 AS 时必须经过哪些"中间人"，'
         '累计得出每个上游 AS 对大陆流量的控制比例，并绘制成 Sankey 或热图。',
         'Uses the IHR Hegemony index to quantify which intermediary ASes mainland '
         'China\'s prefixes must traverse to reach the rest of the Internet. '
         'The cumulative control share of each upstream AS is rendered as a Sankey '
         'or heatmap.'),
     see=(
         '超过 70% 的大陆出向路由依赖中国电信、中国联通等极少数境内骨干，'
         '而境外上游主要集中在美国云/Tier-1（NTT、GTT、Telia），'
         '形成"境内少数骨干 → 境外少数 Tier-1"的双重集中格局。',
         'Over 70% of mainland outbound routing depends on a tiny set of domestic '
         'backbones (China Telecom, Unicom). Beyond the border, the upstreams '
         'concentrate on US Tier-1s (NTT, GTT, Telia) — a double-concentration '
         'pattern of domestic bottleneck followed by offshore bottleneck.'))

_add('/china/step09/', '入向 Hegemony', 'Inbound Hegemony',
     what=(
         '翻转视角——看全球其他国家的前缀有多大比例必须经过中国大陆的 AS 才能到达目的地，'
         '衡量中国大陆在全球路由体系中扮演"过境提供商"的程度。',
         'Flips the perspective — measures what fraction of prefixes from other '
         'countries must transit mainland China\'s ASes to reach their destination, '
         'quantifying how much China acts as a global transit provider.'),
     see=(
         '外国前缀依赖中国大陆 AS 的比例整体较低，大多数国家的对华依赖 Hegemony 分低于 0.1；'
         '少数例外是与中国大陆直连且路由选项有限的中亚小国，'
         '说明中国大陆目前并非全球路由核心，而更多是"受保护的目的地"。',
         'The fraction of foreign prefixes transiting mainland China is generally low; '
         'most countries\' inbound Hegemony toward China is below 0.1. A few '
         'exceptions are small Central Asian nations with limited routing alternatives. '
         'Mainland China is currently a "protected destination", not a global transit '
         'hub.'))

_add('/china/step10/', '集中度与 HHI', 'Concentration & HHI',
     what=(
         '计算中国大陆 BGP 前缀市场的 HHI（赫芬达尔-赫希曼指数）和 Gini 系数，'
         '并绘制 Lorenz 曲线，衡量前缀资源在大陆 6,660 个 AS 之间的分布均匀程度。',
         'Computes HHI (Herfindahl-Hirschman Index) and Gini coefficient for the '
         'mainland China BGP prefix market, plus a Lorenz curve — measuring how '
         'evenly prefix resources are distributed across 6,660 mainland ASes.'),
     see=(
         'HHI 偏高，接近或超过 2500（高集中阈值），头部三家运营商合计持有超过 60% 的前缀；'
         'Gini 系数约 0.85，Lorenz 曲线严重偏向右下角，'
         '说明大陆路由资源高度集中，小 AS 几乎没有独立的路由影响力。',
         'HHI is high, approaching or exceeding the 2,500 concentrated-market '
         'threshold; the top-3 operators hold over 60% of prefixes. Gini ≈ 0.85; '
         'the Lorenz curve bows sharply to the lower-right — routing resources are '
         'heavily concentrated and small ASes have minimal independent routing '
         'influence.'))

_add('/china/step11_part1/', 'IXP 互联生态 · 总量', 'IXP Interconnect · Volume',
     what=(
         '统计中国大陆及中国香港 AS 参与的全球 IXP 数量与分布，'
         '按 IXP 所在地和成员 AS 数量排序，展示中国互联网实体在全球互联网交换点生态中的总体覆盖。',
         'Counts and maps all IXPs globally where mainland China or Hong Kong ASes '
         'are members, ranked by IXP location and member AS count — the total '
         'footprint of Chinese Internet entities in the global exchange-point '
         'ecosystem.'),
     see=(
         '中国大陆 AS 在全球 IXP 的出席数量偏少，全球排名约第 16；'
         '中国香港的 HKIX 在亚太是最重要的 IXP 之一，承接了大量大陆 AS 通过香港出海的流量，'
         '使中国香港成为大陆 IXP 互联的事实跳板。',
         'Mainland China ASes are present at relatively few IXPs globally (ranked '
         '~#16). Hong Kong\'s HKIX is one of Asia-Pacific\'s most important exchanges '
         'and handles a large share of mainland traffic exiting via Hong Kong, making '
         'it the de-facto IXP gateway for the mainland.'))

_add('/china/step11_part2/', 'IXP 互联生态 · 跨境', 'IXP Interconnect · Cross-Border',
     what=(
         '聚焦中国大陆 AS 在境外 IXP 的成员关系，用地图和条形图展示哪些 IXP（如 HKIX、JPIX、'
         'DE-CIX 香港）接入了大陆 AS，以及通过哪些国家/地区进行跨境互联。',
         'Focuses on mainland China ASes\'s memberships at overseas IXPs — a map '
         'and bar chart showing which exchanges (HKIX, JPIX, DE-CIX HK, etc.) '
         'host mainland members, and through which territories cross-border '
         'interconnection flows.'),
     see=(
         '中国大陆的跨境 IXP 互联高度集中于中国香港（HKIX 是最多大陆 AS 参与的境外 IXP），'
         '其次是新加坡和日本；欧美 IXP 的大陆成员数极少，'
         '显示大陆互联网的物理跨境互联路径存在明显的地理集中风险。',
         'Cross-border IXP connectivity is heavily concentrated in Hong Kong (HKIX '
         'hosts the most mainland members of any overseas exchange), followed by '
         'Singapore and Japan. European and US IXP memberships are minimal, '
         'indicating significant geographic concentration risk in physical '
         'cross-border paths.'))

_add('/china/step12/', '机房部署', 'Data-Center Presence',
     what=(
         '统计 PeeringDB 中标记为中国大陆 AS 所在的数据中心（机房）数量和地理分布，'
         '并与境外机房中出现的大陆 AS 相对比，展示物理基础设施的境内-境外分布格局。',
         'Counts data-centre presences (from PeeringDB) of mainland China ASes both '
         'inside the mainland and at overseas facilities, comparing the on-shore '
         'vs. off-shore physical infrastructure footprint.'),
     see=(
         '大陆 AS 在全球机房排名约第 33，境内机房部署集中于北京、上海、广州等几大城市；'
         '境外机房则以中国香港为最大集散地，其次为新加坡，欧美机房出现的大陆 AS 数量极少，'
         '显示物理重心明显境外偏向中国香港/东南亚。',
         'Mainland ASes rank ~#33 globally in data-centre count. On-shore facilities '
         'concentrate in Beijing, Shanghai, and Guangzhou. Overseas presence is '
         'largest in Hong Kong, then Singapore; European and US facilities host very '
         'few mainland ASes — physical weight is skewed toward HK/SEA offshore.'))

_add('/china/step13/', 'IXP × 机房三部图', 'IXP × Facility Tripartite',
     what=(
         '用三部图（AS — IXP — 机房）Sankey 或二分网络图展示中国大陆 AS、它们加入的 IXP、'
         '以及所在机房之间的三重关联关系，揭示"谁在哪儿互联、用哪栋楼"。',
         'A tripartite Sankey or bipartite network linking mainland China ASes, '
         'the IXPs they join, and the facilities where they colocate — revealing '
         'the "who interconnects where, in which building" structure.'),
     see=(
         '中国香港的 HKIX 和 Equinix HK 是最密集的交汇节点，把大陆、香港、东南亚 AS 聚合在一起；'
         '大陆本土三部图则显示 IXP 稀少、机房相对分散的特征，'
         '与中国香港作为跨境枢纽的角色形成鲜明对比。',
         'HKIX and Equinix Hong Kong are the densest intersection points, aggregating '
         'mainland, Hong Kong, and SEA ASes. The mainland-only tripartite shows '
         'sparse IXPs and relatively dispersed facilities — a sharp contrast with '
         'Hong Kong\'s role as cross-border hub.'))

_add('/china/step14/', 'DNS 托管版图', 'DNS Hosting Landscape',
     what=(
         '统计中国大陆注册域名（.cn 及其他 gTLD）的权威 DNS 托管在哪些 AS，'
         '按托管量排名，区分境内 DNS 服务商（阿里云 DNS、DNSPod）和境外服务商（Cloudflare/AWS），'
         '展示大陆 DNS 控制权的分布。',
         'Maps authoritative DNS hosting of mainland Chinese domains (.cn and '
         'other gTLDs) to their hosting ASes, ranked by domain count. Distinguishes '
         'on-shore providers (Alibaba Cloud DNS, DNSPod) from offshore (Cloudflare, '
         'AWS Route 53) — the landscape of DNS control.'),
     see=(
         '境内两大平台（阿里云 DNS 和腾讯 DNSPod）合计托管超过半数大陆注册域名；'
         '但仍有相当比例域名使用境外 DNS（主要是 Cloudflare），'
         '这些域名的解析路径在技术上经过境外节点，形成"内容在国内、解析在国外"的悖论。',
         'Two domestic platforms — Alibaba Cloud DNS and Tencent DNSPod — together '
         'host over half of mainland-registered domains. A significant share still '
         'use offshore DNS (mainly Cloudflare), meaning their resolution paths '
         'technically cross the border — "content on-shore, resolution offshore".'))

_add('/china/step15/', '.cn DNS 主权', '.cn DNS Sovereignty',
     what=(
         '专门分析 .cn 顶级域下的域名，统计其权威名称服务器（NS 记录）所在的 AS 是否注册在'
         '中国大陆，计算" .cn 权威 NS 自持率"，衡量国家顶级域的 DNS 控制权是否真正留在境内。',
         'Focuses exclusively on .cn TLD domains, checking whether each domain\'s '
         'authoritative nameservers (NS records) reside in mainland-registered ASes. '
         'Computes the ".cn authoritative NS self-hosting rate" — is national TLD '
         'DNS control actually kept on-shore?'),
     see=(
         '.cn 权威 NS 的境内自持度较高，多数 .cn 域名使用阿里云或 DNSPod 等境内服务，'
         '主权率高于大陆注册的全部域名的平均水平；但仍有少量 .cn 域名的 NS 位于境外，'
         '属于"国家域名被外资解析"的灰色地带。',
         'The .cn authoritative NS self-hosting rate is high — most .cn domains '
         'use on-shore resolvers (Alibaba, DNSPod). This sovereignty ratio is '
         'above the average for all mainland-registered domains. However, a small '
         'fraction of .cn names still have offshore NS records — a grey zone of '
         '"national domain names resolved by foreign infrastructure".'))

_add('/china/step16/', 'CNAME 跨境链', 'CNAME Cross-Border Chains',
     what=(
         '追踪中国大陆注册域名的 CNAME 链路：从 .cn 或大陆注册域名出发，'
         '逐跳跟随 CNAME 直到 A/AAAA 记录，统计最终落点的 AS 地理归属，'
         '展示"看起来是国内域名、实际指向境外 IP"的跨境依赖链。',
         'Traces CNAME chains starting from mainland-registered domains (.cn and '
         'others), following each alias hop until the final A/AAAA record, then '
         'geolocating the terminating AS. Reveals "looks domestic, terminates '
         'offshore" cross-border dependency chains.'),
     see=(
         '大量中国大陆域名通过一到三层 CNAME 最终落在境外 CDN（Cloudflare、Akamai、Fastly）'
         '的 IP 上；即便顶层域名注册在大陆，实际流量往往经由中国香港或美国 AS 提供服务，'
         '体现"跨境 CNAME 桥接"在内容分发中的普遍性。',
         'Many mainland-registered domains CNAME-chain their way to offshore CDN IPs '
         '(Cloudflare, Akamai, Fastly) within one to three hops. Even when the root '
         'domain is mainland-registered, actual traffic is served from Hong Kong '
         'or US ASes — cross-border CNAME bridging is pervasive in content delivery.'))

_add('/china/step17/', '多排名位置', 'Multi-Ranking Position',
     what=(
         '从 Tranco、CrUX（Chrome UX Report）、APNIC 主动测量三个不同榜单中，'
         '统计中国大陆域名和用户群体的占比与排名位置，对比三种榜单视角下中国大陆的'
         '"互联网存在感"差异。',
         'Cross-references mainland China\'s presence in three distinct ranking '
         'sources — Tranco (traffic-weighted), CrUX (Chrome UX user data), '
         'and APNIC active measurement — comparing the "Internet presence" implied '
         'by each list.'),
     see=(
         'Tranco 和 CrUX 中大陆注册域名比例在全球排前 10，但 APNIC 用户份额排名更高（约前 5），'
         '反映中国大陆是全球重要的互联网消费市场；三个榜单结果差异揭示了"域名可见性"与'
         '"用户访问量"之间的测量偏差。',
         'Mainland-registered domains appear in the Tranco and CrUX top-10 by '
         'country; APNIC user-measurement share ranks even higher (~top-5), '
         'reflecting China as a major internet consumption market. Differences '
         'between the three lists expose measurement biases between "domain '
         'visibility" and "actual user traffic".'))

_add('/china/step18/', '审查拓扑', 'Censorship Topology',
     what=(
         '把 OONI 探针对中国大陆的审查检测结果叠加到 AS 拓扑上：哪些大陆 AS 被探针检测到'
         '"封锁"行为、这些 AS 处于 k-core 的哪一层？用热图呈现审查与网络位置的二维关系。',
         'Overlays OONI probe censorship measurements targeting mainland China onto '
         'the AS topology — which ASes show "blocking" signals, and at what k-core '
         'depth? A heatmap maps censorship intensity to network position.'),
     see=(
         'OONI 检测到大陆审查的 AS 集中在 k-core 浅层（接入网级别），与全球审查拓扑规律一致；'
         '审查网络与非审查网络（如中国香港、国际出口）在 k-core 层次上存在清晰的界线，'
         '暗示审查实施发生在接入层而非骨干层。',
         'OONI-detected censorship in mainland China concentrates in shallow k-core '
         'layers (access-network level), consistent with global censorship topology '
         'patterns. A clear boundary exists between censoring ASes and non-censoring '
         'ASes (HK, international exits) at the k-core layer — censorship is '
         'enforced at the access layer, not the backbone.'))

_add('/china/step19/', 'Atlas 观测点', 'Atlas Probe Coverage',
     what=(
         '统计 RIPE Atlas 中部署在中国大陆境内的探针数量和地理分布，'
         '以及这些探针覆盖了多少大陆 AS；对比探针密度与人口、AS 数量的比例，'
         '评估网络测量基础设施的覆盖盲区。',
         'Counts RIPE Atlas probes located inside mainland China — their number, '
         'geographic spread, and how many mainland ASes they cover. Compares probe '
         'density against population and AS count to assess measurement blind-spots.'),
     see=(
         '中国大陆的 RIPE Atlas 探针数量极少（相对于 6,660 个 AS 而言），'
         '大量 AS 没有任何探针覆盖，导致对大陆网络质量的独立测量能力极为有限；'
         '现有探针主要集中在高校和研究机构，商业 ISP 的覆盖几乎为零。',
         'Mainland China has very few RIPE Atlas probes relative to its 6,660 ASes; '
         'the vast majority of ASes have no probe coverage, severely limiting '
         'independent network-quality measurement. Existing probes concentrate in '
         'universities and research institutes — commercial ISP coverage is '
         'near-zero.'))

_add('/china/step20_part1/', '综合仪表板 · 指数', 'Composite Dashboard · Index',
     what=(
         '把中国大陆在 20 步分析中得出的 5 个子维度（托管、DNS、RPKI、IXP、枢纽比率）'
         '汇总成一个 0-1 主权指数，用仪表盘样式呈现综合得分与各维度分项，'
         '便于与其他国家横向对比。',
         'Aggregates mainland China\'s five sovereignty sub-scores (hosting, DNS, '
         'RPKI, IXP, hub ratio) into a single 0–1 composite index, displayed as a '
         'dashboard gauge with sub-dimension breakdown — formatted for direct '
         'cross-country comparison.'),
     see=(
         '2026-04 综合主权指数 0.269，九国研究中排名最后；托管子维度接近 1.0（境内域名大多'
         '在境内托管），但 DNS、RPKI、IXP、枢纽四项子分都偏低，'
         '共同体现"基础设施高度自建但路由与解析仍依赖境外"的主权悖论。',
         'Composite sovereignty index 0.269 as of 2026-04 — last of 9 countries. '
         'The hosting sub-score approaches 1.0 (most domestic domains hosted '
         'on-shore), but DNS, RPKI, IXP, and hub-ratio sub-scores are all low — '
         'together expressing the sovereignty paradox: infrastructure built '
         'domestically, but routing and resolution still dependent on offshore actors.'))

_add('/china/step20_part2/', '综合仪表板 · 对比', 'Composite Dashboard · Comparison',
     what=(
         '把中国大陆的五维主权指数与九国研究中的其他八个国家（美、日、印、德、英、法、荷、俄）'
         '并排绘成雷达图或条形矩阵，找出中国大陆在哪个维度上相对最强、最弱。',
         'Places mainland China\'s five-dimension sovereignty profile side by side '
         'with the other eight countries (US, JP, IN, DE, GB, FR, NL, RU) as a '
         'radar chart or bar matrix — identifying which dimensions China leads '
         'and lags in relative terms.'),
     see=(
         '雷达图上中国大陆的"托管"角是最突出的，而"RPKI"和"IXP"角明显凹陷；'
         '与俄罗斯的形态相似（高托管-低互联），但中国大陆的 IXP 角更浅，'
         '说明其物理互联参与度是九国中最低的之一。',
         'On the radar, China\'s "hosting" axis juts out while "RPKI" and "IXP" '
         'axes are conspicuously hollow — the profile resembles Russia\'s '
         '(high hosting, low interconnect), but mainland China\'s IXP axis is '
         'even shallower, making it one of the lowest physical interconnect '
         'participants among the nine countries.'))

_add('/china/step20_part3/', '综合仪表板 · 趋势', 'Composite Dashboard · Trend',
     what=(
         '把中国大陆的综合主权指数和各子维度分数在 11 个快照（2024-01 → 2026-04）中的变化'
         '绘制成折线图，让读者看清哪个维度在改善、哪个在退步或停滞。',
         'Plots mainland China\'s composite sovereignty index and each sub-dimension '
         'score across 11 quarterly snapshots (2024-01 → 2026-04) as a line chart — '
         'showing which dimensions are improving, stagnating, or declining.'),
     see=(
         '托管维度在多数快照中稳定高位；DNS 主权分有缓慢上行趋势；'
         'RPKI 分在 2025 年出现阶段性提升后趋于平稳；IXP 分基本持平或微幅波动，'
         '整体主权指数 2026-04 为 0.269，较 2024-01 仅增约 +0.05，进展缓慢。',
         'The hosting dimension holds steady at a high level across snapshots. DNS '
         'sovereignty shows a slow upward drift. RPKI improved in a step around '
         '2025 before levelling off. IXP is essentially flat. The composite '
         'sovereignty index reached 0.269 in 2026-04, only ~+0.05 above the '
         '2024-01 baseline — slow overall progress.'))


# ======================================================================
# COMPLEX NETWORK · 13 analyses
# ======================================================================

_add('/network/step05/', '度分布与幂律拟合', 'Degree Distribution & Power Law',
     what=('"度" = 一个 AS 有多少个邻居。把全网所有 AS 的度值画成分布图，看它是均匀的、钟形的、还是'
           '长尾的。',
           '"Degree" = number of neighbours of an AS. Plot the empirical distribution — uniform? '
           'bell-curve? long-tail?'),
     how=('双对数坐标下若呈直线，说明遵循幂律 P(k) ~ k^-α；拟合斜率 α 越接近 2 表示越严重的长尾。'
          'α < 2 说明极端 hub 占比过高，网络可能不稳定。',
          'On log-log axes, a straight line indicates power-law P(k) ~ k^-α. Smaller α means '
          'heavier tail; α < 2 implies pathological hub dominance.'),
     see=('IYP BGP 层 α ≈ 2.107 —— 典型无标度 (scale-free) 网络。大量 AS 只有几个邻居，但少数超级 '
          'hub (Tier-1/Cloudflare/Google) 连了上千个邻居。',
          'IYP BGP layer α ≈ 2.107 — canonical scale-free. Most ASes have a handful of neighbours, '
          'but a few super-hubs (Tier-1s, Cloudflare, Google) connect to thousands.'),
     keyterm=('无标度网络 · Scale-free',
              '无标度网络是 Barabási-Albert 在 1999 年提出的概念：如果你把整张网络放大或缩小，局部'
              '结构看起来都差不多。互联网、论文引用、航空路线几乎都是无标度。',
              'Scale-free networks (Barabási-Albert 1999) have the property that local structure '
              'looks the same at any zoom level. Internet, citation, and airline networks are all '
              'scale-free.'))

_add('/network/step05_panel01/',
     'BGP 对等度的互补累积分布',
     'BGP Peering Degree · CCDF',
     what=(
         '横轴是单个 AS 拥有的 BGP 对等邻居数 k；纵轴是"拥有 ≥ k 个邻居"的 AS 占比。'
         '在双对数坐标下观察尾部斜率，若呈直线就是幂律尾 P(K≥k) ~ k^−(α−1)。',
         'X-axis is peer-count k per AS; Y-axis is the fraction of ASes with ≥ k '
         'neighbours. On log-log axes, a straight tail indicates power-law '
         'P(K≥k) ~ k^−(α−1).'),
     see=(
         'IYP BGP 层 α ≈ 2.10：99% 的 AS 只有 1–20 个对等邻居，但尾部一小撮超级 '
         'hub (Tier-1 / Cloudflare / Google) 连了数千个。曲线尾部的红色拟合线'
         '就是幂律预测——实际点几乎贴着线下滑，印证无标度结构。',
         'IYP BGP α ≈ 2.10: 99% of ASes have 1–20 peers, but a handful of '
         'super-hubs (Tier-1s, Cloudflare, Google) connect to thousands. The '
         'red fitted tail line is the power-law prediction; observed points '
         'track it almost exactly, confirming the scale-free structure.'))

_add('/network/step05_panel02/',
     'AS 依赖入度的互补累积分布',
     'AS Dependency In-Degree · CCDF',
     what=(
         '把 IHR Hegemony 图的边看作"A 依赖 B 作为上游"，统计每个 AS 被多少个下游 AS '
         '当作关键上游。横轴是入度 k，纵轴是"被 ≥ k 个下游依赖"的 AS 占比，'
         '仍然用双对数坐标。',
         'Treat IHR Hegemony edges as "A depends on B upstream". Count how many '
         'downstream ASes each AS carries. X-axis is in-degree k; Y-axis is the '
         'fraction of ASes with ≥ k downstream dependents. Log-log axes.'),
     see=(
         '依赖入度的长尾比对等度更陡：绝大多数 AS 没有任何下游依赖，只有少数'
         'Tier-1 / 国际云承载了成千上万个下游。这解释了为什么单点故障（一家'
         '运营商）会瞬间影响大片用户——依赖在结构上被高度集中了。',
         'The dependency tail is steeper than peering: most ASes have zero '
         'downstream dependents; only a few Tier-1s and global clouds carry '
         'thousands. This is why a single-operator outage cascades to millions '
         'of users — dependency is structurally concentrated.'))

_add('/network/step05_panel03/',
     'IXP 成员度的互补累积分布',
     'IXP Membership Degree · CCDF',
     what=(
         '一个 AS 可以同时加入多个 Internet Exchange Point (IXP)——越多 IXP，越容易'
         '在全球各地建立本地对等。横轴是该 AS 加入的 IXP 数量，纵轴是"至少加入 k '
         '个 IXP"的 AS 占比。',
         'An AS can join multiple Internet Exchange Points (IXPs) — more IXPs '
         'means easier local peering worldwide. X-axis is the number of IXPs an '
         'AS has joined; Y-axis is the fraction of ASes present at ≥ k IXPs.'),
     see=(
         '极少数 AS（通常是全球 CDN 和大型 Tier-1）进入 50+ IXP，是事实意义上的'
         '"全球对等锚"；大多数 AS 只进入 1–2 个本地 IXP。与 BGP 对等度相比，IXP '
         '度的头部更稀薄，显示 IXP 是头部运营商才消费得起的资源。',
         'A tiny minority (global CDNs, Tier-1s) are present at 50+ IXPs — the '
         'de-facto global peering anchors. Most ASes are at 1–2 local IXPs. '
         'The head is thinner than BGP-peering; IXP presence is a resource only '
         'large operators can afford.'))

_add('/network/step05_panel04/',
     'DNS 托管度的互补累积分布',
     'DNS Hosting Degree · CCDF',
     what=(
         '每个 AS 承载了多少公网可解析的主机名（A/AAAA 终点属于本 AS 的 IP）。'
         '横轴是该 AS 承载的主机名数量，纵轴是"托管 ≥ k 个主机名"的 AS 占比。'
         '若原始数据尚未抽取，此面板会显示"DNS data not yet extracted"。',
         'Counts how many publicly-resolvable hostnames land on each AS (A/AAAA '
         'answers pointing at IPs in that AS). X-axis is hostnames hosted; '
         'Y-axis is the fraction of ASes hosting ≥ k. If upstream data is not '
         'extracted yet, the panel shows a "DNS data not yet extracted" notice.'),
     see=(
         '托管度比任何其他层都更极端地集中：Cloudflare / Google / AWS 单家承载'
         '上千万个主机名，而 99% 的 AS 只承载 < 1K。这是现代内容层"云化"的直接'
         '后果——DNS 层本身就是一个高度不均的经济市场。',
         'Hosting concentration is more extreme than any other layer: '
         'Cloudflare / Google / AWS each host tens of millions of hostnames, '
         'while 99% of ASes host < 1K. This is cloud centralisation made '
         'visible — the DNS layer is already a lopsided economic market.'))

_add('/network/step05_panel05/',
     '三层度分布的对数分箱对比',
     'Three-Layer PDF Comparison · Log-binned',
     what=(
         '不再看"累积"（CCDF），而是直接画概率密度 P(k)——每个度值的概率。'
         '采用对数分箱（log-bins）把稀疏尾部合并成可见的点。BGP / 依赖 / IXP '
         '三条曲线同框放在双对数坐标下对比。',
         'Instead of the cumulative view (CCDF), plot the probability density '
         'P(k) directly — probability of each degree value. Log-binning merges '
         'sparse tail points into visible clusters. Three curves (BGP, '
         'Dependency, IXP) compared on one set of log-log axes.'),
     see=(
         '三条曲线几乎平行下滑——说明它们都服从相似指数的幂律（约 α ≈ 2）。'
         '差异在绝对位置：BGP 最高（最多 AS 参与），IXP 最低（参与门槛高）。'
         '同一套"无标度"结构在完全不同的资源维度上反复出现，是互联网的底层特征。',
         'The three curves decay in near-parallel — they share a similar '
         'power-law exponent (α ≈ 2). They differ only in absolute position: '
         'BGP sits highest (most ASes participate), IXP lowest (higher cost of '
         'entry). The same scale-free structure recurs across different '
         'resource dimensions — a fundamental Internet signature.'))

_add('/network/step05_panel06/',
     '各层拓扑指标汇总',
     'Layer-Level Topology Summary',
     what=(
         '一张速览表：每一层（BGP 对等 / AS 依赖 / IXP 成员 / DNS 托管）的节点数、'
         '边数、平均度 <k>、最大度 k_max、全局聚类系数 C。用等宽字体排版成控制台'
         '风格。',
         'A one-look summary table per layer (BGP Peering, AS Dependency, '
         'IXP Membership, DNS Hosting): node count, edge count, average degree '
         '<k>, maximum degree k_max, global clustering coefficient C. Monospaced '
         'console-style layout.'),
     see=(
         '读者可以直接比较各层规模：BGP 是最大的节点池（~10 万 AS），但聚类系数 '
         'C 偏低（稀疏连接）；AS 依赖的 <k> 更高但节点数少得多；IXP 层节点最少'
         '但 k_max 不算突出。这张表是后续所有中心性 / k-core / 社区分析的"底牌"。',
         'At a glance you can compare layer scales: BGP has the largest node '
         'pool (~100K ASes) but low clustering C (sparse). AS Dependency has '
         'higher <k> but far fewer nodes. IXP has the fewest nodes and a '
         'modest k_max. This table is the baseline all subsequent centrality, '
         'k-core, and community analyses build on.'))

_add('/network/step06/', '小世界特性', 'Small-World Properties',
     what=('"小世界"指两个看似陌生的节点可能只相隔几跳。本图量化互联网的聚类系数 C 与平均最短路径 L，'
           '与随机图作比。',
           'The "small-world" phenomenon — two apparently unrelated nodes are often just a few '
           'hops apart. We compare observed clustering C and mean path length L against a random '
           'baseline.'),
     how=('小世界系数 σ_SW = (C/C_rand) / (L/L_rand)。σ_SW >> 1 说明网络既聚类又短路——典型小世界。',
          'Small-world index σ_SW = (C/C_rand) / (L/L_rand). σ_SW >> 1 = highly clustered yet short-'
          'pathed — hallmark small-world.'),
     see=('IYP 全网 σ_SW = 1,820——聚类系数是随机图的 1,675 倍，而最短路径几乎相同。互联网是"你的'
          '邻居的邻居也是你的邻居"这件事的极端案例。',
          'IYP σ_SW = 1,820 — clustering is 1,675× random, yet path length is basically unchanged. '
          'The Internet is an extreme instance of "my neighbour\'s neighbour is also my neighbour".'))

_add('/network/step07/', '多维中心性', 'Multi-Dimensional Centrality',
     what=('"中心性" = 一个节点在网络中的重要程度。我们同时算四种：度中心性、介数、特征向量、PageRank。'
           '不同指标揭示不同形式的"重要"。',
           '"Centrality" = how important a node is. We compute four simultaneously — degree, '
           'betweenness, eigenvector, PageRank — each highlighting a different "importance".'),
     how=('每张子图上方前 10 名即该维度下的"顶级 AS"。对比四个榜单的重叠：重合越多，说明这些 AS 是'
          '"全能 hub"而非"某一维度 hub"。',
          'The top-10 list atop each sub-panel names that dimension\'s leaders. Overlap across the '
          'four rankings reveals which ASes are "all-round hubs" vs. "specialised hubs".'),
     see=('Cloudflare (AS 13335) 和 Google (AS 15169) 在四个榜单里都前 5——它们是真正的"全能 hub"；'
          '对比之下，Telia (AS 1299) 虽在介数上居首，度数却只排 20 名——它是"桥接型 hub"。',
          'Cloudflare (13335) and Google (15169) appear top-5 on all four — true all-round hubs. '
          'Telia (1299) tops betweenness but is only #20 on degree — a "bridge hub".'))

_add('/network/step08/', 'k-核分解', 'k-Core Decomposition',
     what=('k-core 是 "每个节点至少有 k 个邻居" 的子图。k 值越大代表进入网络越"深处"。'
           '这是剥洋葱的数学版：一层一层剥，直到剩最核心的小核。',
           'The k-core is the maximal subgraph where every node has ≥k neighbours. Bigger k = '
           'deeper in the onion. Mathematical onion-peeling, basically.'),
     how=('X 轴是 k 值、Y 轴是节点数。从右到左看：最外层 k=1 有大量叶节点；内核 k=k_max 只剩核心骨架。',
          'X = k, Y = node count. Read right-to-left — outer k=1 has many leaves; inner k=k_max '
          'keeps only the core backbone.'),
     see=('IYP 全网 k_max = 197——340 个 AS 构成最内核的"骨架"，它们两两几乎全连。Tier-1 (NTT、'
          'Level3、Telia 等) 与超大内容网 (Google、Cloudflare) 同居其中。',
          'IYP k_max = 197 — 340 ASes form the innermost backbone, nearly fully connected. Tier-1s '
          '(NTT, Level3, Telia) and hyperscalers (Google, Cloudflare) live together there.'))

_add('/network/step09/', 'Rich-Club 系数', 'Rich-Club Coefficient',
     what=('"Rich-club" 指有钱人之间更爱连有钱人。把"富"定义为度数高的 AS，问：这些 hub 之间是不是'
           '比随机预期更密集地互连？',
           'Rich-club = rich nodes cluster with rich nodes. Define "rich" as high-degree ASes, then '
           'ask: are these hubs more densely interconnected than random chance predicts?'),
     how=('ρ(k) 是度数 ≥ k 的节点之间的实际边数 / 可能边数；ρ(k)/ρ_rand(k) > 1 说明存在 rich-club '
          '效应。',
          'ρ(k) = edges among nodes with degree ≥ k / maximum possible such edges. '
          'ρ/ρ_rand > 1 confirms rich-club effect.'),
     see=('IYP 高度 hub 的 ρ 显著偏高——Tier-1 彼此几乎两两互联，构成一个"顶层贵族俱乐部"。这也是互联网'
          '能如此鲁棒 (即便边缘挂掉核心仍通) 的结构基础。',
          'IYP high-degree ρ is strongly elevated — Tier-1s are almost pairwise connected, forming '
          'an "aristocratic core". This is structurally why the Internet stays routable even when '
          'edges fail.'))

_add('/network/step10/', '同配性分析', 'Assortativity Analysis',
     what=('"同配性" r 测量度高的节点是否倾向连度高的节点 (同配、r>0) 还是度低的节点 (异配、r<0)。'
           '互联网 r 长期是负值——这是一个有趣的反直觉现象。',
           'Assortativity r — do high-degree nodes connect to high-degree (r>0) or to low-degree '
           '(r<0)? The Internet is persistently disassortative (r<0), a counter-intuitive fact.'),
     how=('散点图的 X 是一条边的一端度数、Y 是另一端。相关系数 r 汇总整体趋势。负斜率线即 r<0 的'
          '视觉表达。',
          'Scatter: X = one endpoint\'s degree, Y = the other\'s. Pearson r summarises the overall '
          'trend. A downward line = r < 0.'),
     see=('IYP r = −0.300：hub 更倾向连接小 AS (eyeball/leaf)，而不是彼此。这保证了信息扩散的效率——'
          '任何小 AS 通过一个 hub 即可触达全网；也使得 "去 hub 化" 攻击特别有效。',
          'IYP r = −0.300 — hubs prefer leaves (eyeballs/edge) to one another. This yields '
          'efficient propagation (any leaf reaches the whole Net in one hub hop) but also explains '
          'why targeted hub attacks hurt disproportionately.'))

_add('/network/step11/', '社区检测', 'Community Detection',
     what=('"社区" = 内部比外部更紧密的子群。Louvain 算法自动地把 AS 分进 108 个社区，然后我们看这些'
           '数学上发现的社区是否对应地理或组织边界。',
           'A "community" = a subgroup denser internally than externally. Louvain algorithm '
           'auto-partitions ASes into 108 communities — we then check whether the mathematically '
           'discovered communities align with geographic or organisational boundaries.'),
     how=('模块度 Q ∈ [0, 1] 衡量社区划分质量：Q > 0.3 即统计显著的社区结构；Q > 0.4 则社区清晰可辨。',
          'Modularity Q ∈ [0,1] scores partition quality. Q > 0.3 = statistically meaningful '
          'communities; Q > 0.4 = sharply defined.'),
     see=('IYP Q = 0.445——极强的社区结构。最大的几个社区对应 "美国内容集群"、"欧洲 Tier-1 俱乐部"、'
          '"中国大陆集群"、"东南亚/大洋洲区域"，说明互联网的数学社区与地缘政治高度吻合。',
          'IYP Q = 0.445 — very strong community structure. The largest communities map to "US '
          'content cluster", "European Tier-1 club", "Mainland China cluster", "SEA/Oceania" — '
          'maths and geopolitics overlap tightly.'))

_add('/network/step13/', '集中度与 HHI', 'Concentration & HHI',
     what=('用三种经济学指标量化互联网资源的 "头部垄断" 程度：Gini 系数、HHI 赫芬达尔-赫希曼指数、'
           'Lorenz 曲线。越偏斜代表资源越向少数实体集中。',
           'Three economics indices quantify how much Internet resources concentrate in a few hands: '
           'Gini, HHI (Herfindahl-Hirschman), Lorenz. More skewed = more concentrated.'),
     how=('Lorenz 曲线越靠右下角越不均；HHI > 2500 即美国反垄断法定义的"高集中"；Gini 1.0 = 完全'
          '垄断、0 = 完全均匀。',
          'Lorenz curves bowed to the bottom-right = more unequal. HHI > 2500 triggers US '
          'anti-trust "high concentration" threshold. Gini 1.0 = total monopoly, 0 = perfectly '
          'uniform.'),
     see=('BGP、DNS、托管、CDN 四个市场的 HHI 都 > 2500，个别 > 5000 (寡头)。头部 5 家在各自领域内'
          '占 60-80%。这份图给 "互联网在技术上分布式、在经济上高度集中" 提供量化证据。',
          'BGP / DNS / hosting / CDN markets all have HHI > 2500; some > 5000 (oligopoly). Top-5 '
          'players capture 60-80% share in each. Quantitative proof that the Internet is '
          'technically distributed but economically concentrated.'))

_add('/network/step15/', '渗流与韧性', 'Percolation & Robustness',
     what=('"渗流" 模拟：按某种规则逐个移除节点，看巨连通分量 (GCC) 什么时候崩溃。'
           '两种规则：随机故障 vs 按度数从大到小的定向攻击。',
           'Percolation simulates progressively removing nodes and watching the giant-connected-'
           'component (GCC). Two rules: random failures vs. targeted attacks on highest-degree '
           'nodes first.'),
     how=('X 轴是移除比例、Y 轴是 GCC 剩余比例。随机曲线应在 80%+ 时仍保持较高 GCC；定向曲线会'
          '"坠崖式" 下降。',
          'X = fraction removed, Y = GCC surviving. Random curve should hold high GCC past 80% '
          'removal; targeted curve collapses precipitously.'),
     see=('IYP 对随机故障极度韧性 (移除 70% 仍保 GCC > 60%)，但对 TOP 1% 的 hub 定向打击极脆弱 '
          '(GCC 掉到 < 10%)。这是"Achilles 互联网"——坚如磐石的长尾 + 阿喀琉斯之踵的 hub。',
          'IYP is extremely robust to random failure (GCC > 60% even after 70% random removal) but '
          'fragile to targeted top-1% hub attacks (GCC drops below 10%). The "Achilles Internet" — '
          'rock-solid tail, heel-weak hubs.'))

_add('/network/step18/', '跨层级联失效', 'Cross-Layer Cascade Failure',
     what=('真实的互联网故障很少只发生在一层。本图模拟：物理层一个机房挂掉 → 托管在那儿的 AS 掉线 → '
          'BGP 重路由 → DNS 解析超时 —— 一个扰动如何在四层之间放大。',
          'Real failures rarely stay in one layer. We simulate: a facility fails → colocated ASes '
          'drop → BGP reconverges → DNS resolution times out. A single perturbation amplified '
          'across four layers.'),
     how=('横轴是时间步，纵轴是"受影响的域名比例"。三条曲线分别对应关掉 US 境内一个大机房、欧洲一个'
          'Tier-1、亚洲一个 CDN 节点。',
          'X = timestep, Y = fraction of domains affected. Three curves correspond to removing a '
          'major US facility, a European Tier-1, and an Asian CDN respectively.'),
     see=('关掉单一 Tier-1 机房时，5 步内影响的域名就能达到 20%+——这远超该机房托管的 AS 直接对应的'
          '域名数，证明跨层放大系数 (cross-layer amplification) 存在且显著。',
          'Removing a single Tier-1 facility propagates to 20%+ affected domains in 5 steps — far '
          'beyond directly-hosted AS footprint, demonstrating a significant cross-layer '
          'amplification factor.'))

_add('/network/step19/', '地理韧性', 'Geographic Resilience',
     what=('假想"如果某国一夜之间从互联网消失 (所有注册在该国的 AS 全部下线)，全球 GCC 会掉多少？"'
          '这张图把这种极端情景的后果量化为一个"可有可无指数"。',
          'Hypothetical: "if country X disappeared overnight (all X-registered ASes offline), how '
          'much does global GCC drop?" This quantifies the "indispensability index" of each '
          'country.'),
     how=('横条图的长度 = 移除该国后 GCC 剩余比例。越短 = 该国越关键；越长 = 越"可替代"。',
          'Bar length = residual GCC after removing that country. Shorter = more critical; longer = '
          'more replaceable.'),
     see=('即便移除美国 (全球 AS 数第一)，全球 GCC 仍保 87%——说明互联网没有单国不可替代；中国、德国、'
          '英国等中等国家的移除影响在 1-3%，基本不伤筋骨。真正可怕的是美+欧同时 (这里不做，'
          '因为脱离现实)。',
          'Even removing the US (largest AS count) leaves 87% GCC — no single country is '
          'irreplaceable. Removing medium powers (CN, DE, GB …) costs 1-3% GCC. The truly '
          'catastrophic scenario is US + EU simultaneously (not simulated — outside plausible '
          'threat model).'))

_add('/network/step22/', '审查拓扑', 'Censorship Topology',
     what=('把 OONI 全球审查检测数据叠加到 IYP 的 AS 拓扑上：哪些 AS 有过"封锁"信号？这些 AS 在网络中'
          '处于什么位置？',
          'Overlay OONI global censorship detections on IYP\'s AS topology: which ASes show '
          '"blocking" signals? Where do these ASes sit in the network?'),
     how=('热图的横轴是 AS 所在国、纵轴是 k-core 层深度 (1 = 叶、200 = 核)。颜色深浅代表该 '
          '(国家, k-core 层) 组合的审查检测量。',
          'Heatmap X = AS country, Y = k-core depth (1 = leaf, 200 = core), colour = censorship '
          'detections at that (country, core-depth) cell.'),
     see=('2,383 个 AS 有 OONI 审查信号，分布远非随机：俄罗斯 (534 AS) 居首、中国第二、伊朗第三；'
          '审查活动主要发生在 k-core 浅层 (eyeball 级)，暗示审查是在接入网层面而非核心骨干。',
          '2,383 ASes have censorship detections, non-randomly distributed — Russia (534) leads, '
          'China 2nd, Iran 3rd. Most activity sits in shallow k-cores (eyeball-level), suggesting '
          'censorship happens at access networks, not backbone.'))

_add('/network/step24/', '零模型对比', 'Null Model Comparison',
     what=('互联网观察到的所有"奇怪"属性 (无标度、小世界、负同配、rich-club) 真的是结构产物，还是随机'
          '碰巧？本图把 IYP 与三种随机图 (Erdős–Rényi / Barabási–Albert / Configuration Model) 并列'
          '对照。',
          'Are all the observed "weird" properties (scale-free, small-world, disassortative, rich-'
          'club) genuinely structural — or random artefacts? We compare IYP against three nulls '
          '(Erdős–Rényi, Barabási–Albert, Configuration Model).'),
     how=('同一张图上并列画四条曲线 (观察 + 三模型)。若观察与某一模型接近，说明那个生成机制可能是'
          '成因；若显著偏离所有零模型，说明存在更深的非随机结构。',
          'Four overlaid curves (observed + three null models) on each subplot. Similarity to a '
          'model hints at the generating mechanism; deviation from all three implies deeper '
          'non-random structure.'),
     see=('IYP 在小世界上接近 BA 模型、在同配性上与所有零模型都不同 (更负)、在 rich-club 上显著偏离——'
          '说明互联网不是单一机制生成的，而是"偏好依附 + 经济利益对齐 + 地缘分区"三重动力的叠加。',
          'IYP matches BA on small-world, differs from all nulls on assortativity (more negative), '
          'deviates strongly on rich-club — the Internet is not driven by a single mechanism but '
          'by "preferential attachment + economic alignment + geographic partitioning" overlaid.'))


def get(url: str) -> dict | None:
    return EXPLAINERS.get(url)
