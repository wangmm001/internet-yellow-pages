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


# =================== COUNTRIES (dashboards) ===================

_add('/countries/dashboards/new-angles/', '15 个新角度汇总', 'New Angles · Synthesis',
     what=(
         '把 15 个新分析维度的核心结论浓缩成一张汇总页：每个 topic 对应一行摘要，标注数据来源、'
         '样本规模与降级说明。列出三条结构性洞察，跨 topic 印证互相关。',
         'A single-page digest of 15 novel analysis dimensions. Each topic row summarises its '
         'data source, sample size, and any fallback. Three structural insights cross-validate '
         'findings across topics.'),
     see=(
         '三大结构性洞察：① 用户加权后中国大陆互联网曝光度远高于基础设施视角（eyeball 1.0% vs '
         'infra 0.25%，差 23.4×）；② 88% 宣告 AS 不执行 ROV，路由安全存在严重执行落差；③ '
         '.com 占 Tranco Top-10k 的 51.6%，TLD 多样性高但由少数 NS 运营商主导。',
         'Three cross-cutting insights: (1) user-weighted exposure of Chinese mainland Internet '
         'is 23.4× higher than infra view (eyeball 1.0% vs infra 0.25%); (2) 88% of announcing '
         'ASes do not enforce ROV; (3) .com holds 51.6% of Tranco Top-10k despite 350 unique TLDs.'))

_add('/countries/dashboards/scorecards/', '9 国综合 scorecard', '9-Country Scorecard',
     what=(
         '以热力矩阵呈现 9 国 × 15 个新角度指标的综合评分：每行为一个 topic，每列为一个国家。'
         '颜色按列内方向归一化——深绿代表相对强，深红代表相对弱，中性灰表示方向性模糊。',
         'A heatmap of 9 countries × 15 new-angle metrics. Each row is a topic; each column '
         'a country. Colours are direction-normalised within column — dark green = relatively '
         'strong, dark red = relatively weak, neutral grey = ambiguous direction.'),
     see=(
         '美国在路由安全、DNS 托管、IXP 会话真实度上独占强绿；中国大陆在 OONI 审查、ROV 执行率'
         '上深红突出；荷兰 IXP 真实度表现最佳（AMS-IX 主导）；俄罗斯与印度在多数 topic 上评分偏低。',
         'The US leads in routing security, DNS hosting, and IXP session reality. '
         'Chinese mainland shows deep red on OONI censorship and ROV enforcement. '
         'Netherlands tops IXP session reality (AMS-IX dominant). '
         'Russia and India score below median on most topics.'))

_add('/countries/dashboards/evolution-narrative/', '演化叙事', 'Evolution Narrative',
     what=(
         '以叙事文本形式梳理 11 个季度（2024-01 → 2026-04）中 9 国互联网格局的演变轨迹，'
         '重点覆盖 AS 规模、前缀增长、主权指数、IXP 会员等指标的时序变化。',
         'A narrative walkthrough of 11 quarterly snapshots (2024-01 → 2026-04) tracing how '
         '9 countries evolved on AS scale, prefix growth, sovereignty index, and IXP membership. '
         'Each quarter is annotated with the most notable structural shift.'),
     see=(
         '关键发现：若要研究"谁多了一个新 AS"或"谁开了新 IXP peering"须参阅原始时序数据；'
         '总体趋势是美国 AS 数稳增，中国大陆前缀量收缩，荷兰与德国在 IXP 活跃成员数上持续攀升，'
         '俄罗斯主权指数在 2024 年后显著上扬。',
         'Key finding: studying "who added a new AS or IXP peering" requires the raw time-series. '
         'Overall: US AS count grows steadily; Chinese mainland prefix count contracts; '
         'Netherlands and Germany climb on active IXP members; Russia sovereignty index '
         'rises sharply post-2024.'))

_add('/countries/dashboards/correlations/', '跨 Topic 相关性', 'Cross-Topic Correlation Scatters',
     what=(
         '用散点图矩阵展示 15 个新角度指标之间的两两相关关系，样本点为 9 个国家。'
         '每幅散点图的 X/Y 轴对应两个 topic，颜色编码国家，帮助识别结构性共线。',
         'Scatter-plot matrix of pairwise correlations across 15 new-angle metrics. '
         'Each plot places two topics on X/Y axes, with 9 countries as data points, '
         'helping identify structural co-linearity or trade-offs.'),
     see=(
         '路由安全得分与 RPKI 覆盖率高度正相关（r > 0.85）；用户加权主权与基础设施主权的差距'
         '在中国大陆最大，说明人口密度放大了互联网脆弱性；BGP 观测多样性与 IXP 会员数正相关。',
         'Routing security and RPKI coverage correlate strongly (r > 0.85). '
         'The gap between user-weighted and infra-weighted sovereignty is widest for Chinese mainland, '
         'amplifying vulnerability. BGP observation diversity positively correlates with IXP membership.'))

_add('/countries/dashboards/ixp-reality/', 'IXP 会话真伪', 'IXP Session Reality Check',
     what=(
         '对比 PeeringDB 自报成员数与 Alice-LG 实时 route-server 抓取的 BGP session 状态，'
         '量化"声称成员"与"活跃会话"之间的落差。数据覆盖 13 个 IXP、15,524 条 MEMBER_OF 边。',
         'Compares PeeringDB self-reported membership against Alice-LG real-time route-server '
         'session state across 13 IXPs and 15,524 MEMBER_OF edges, quantifying the gap between '
         'claimed and established sessions.'),
     see=(
         '74%（11,433/15,524）的成员边当前 state=Established；PeeringDB 在同一 IXP 子集声称 17,153 '
         '个成员，差集约 1,629 个"声称但不活跃"。AMS-IX 和 DE-CIX 的真实活跃率最高，亚太 IXP '
         '的落差率偏大，说明 PeeringDB 数据新鲜度在该区域较差。',
         '74% (11,433/15,524) of member edges have state=Established. PeeringDB claims 17,153 '
         'members for the same IXP subset, leaving ~1,629 "claimed but inactive." AMS-IX and '
         'DE-CIX show highest real-session rates; APAC IXPs show larger gaps, indicating stale '
         'PeeringDB data in that region.'))

_add('/countries/dashboards/collector-consensus/', 'BGP 观测冗余度', 'Multi-Source Peering Visibility',
     what=(
         '交叉比对 bgpkit as2rel_v4 与 as2rel_v6 两个 BGP 观测源，统计每个 AS 在多少个源中可见。'
         '共观察到 14,488 个 AS；双栈可见（v4+v6 同时出现）的 AS 占 46.9%。',
         'Cross-references bgpkit as2rel_v4 and as2rel_v6 BGP observation sources, counting how '
         'many sources each AS appears in. Of 14,488 observed ASes, 46.9% (6,797) are visible '
         'in both v4 and v6 datasets — the "dual-stack visible" fraction.'),
     see=(
         '7,023 个 AS 仅在 v4 可见，668 个仅在 v6 可见；v4/v6 可见度差异直接反映 IPv6 部署真实度'
         '（登记 ≠ 被多源观测到）。中国大陆 AS 的双栈可见率显著低于美国和欧洲，暗示 IPv6 路由'
         '通告仍以单一观测源为主。',
         '7,023 ASes appear only in v4; 668 only in v6. The v4/v6 visibility gap reflects '
         'real IPv6 deployment (registration ≠ multi-source observation). '
         'Chinese mainland ASes show significantly lower dual-stack visibility than US or European peers, '
         'suggesting IPv6 announcements are dominated by single-source collection.'))

_add('/countries/dashboards/real-traffic/', '反 eyeball 对照', 'Counter-Eyeball Demand Signal',
     what=(
         '以 Google CrUX Top-100 万为主信号，对比 APNIC Eyeball（基于 Google Ads + DNS 测量）'
         '揭示"真实用户需求"与"基础设施视角 AS 权重"之间的结构差。数据覆盖 200,000 行 CrUX 记录。',
         'Uses Google CrUX Top-1M as the demand signal to contrast with APNIC Eyeball '
         '(Google Ads + DNS measurement), exposing the structural gap between real user demand '
         'and infrastructure-view AS weights. Covers 200,000 CrUX records.'),
     see=(
         '用户视角（仅 71 个 eyeball AS）下中国大陆互联网曝光度达 5.9%，而基础设施视角（6,660 个 AS）'
         '仅 0.25%，差距 23.4 倍。CrUX 与 APNIC eyeball 两源对比显示：高 Eyeball 份额国家（IN/BR）'
         '在 CrUX 内容侧排名偏低，说明用户规模 ≠ 内容生产能力。',
         'User-view (71 eyeball ASes) puts Chinese mainland Internet exposure at 5.9%; infra-view '
         '(6,660 ASes) gives only 0.25% — a 23.4× gap. Cross-referencing CrUX and APNIC eyeball '
         'shows high-eyeball countries (IN/BR) rank lower in content supply, confirming user scale '
         'does not equal content production.'))

_add('/countries/dashboards/app-censorship/', '应用级封锁矩阵', 'App-Level Censorship Matrix',
     what=(
         '基于 OONI 12 个应用专用探针（共 18,788 条 CENSORED 边，横跨 10 个 app、165 个国家），'
         '展示各国对 WhatsApp/Telegram/Signal/Psiphon 等应用的封锁矩阵。',
         'Built from OONI 12 app-specific probes (18,788 CENSORED edges across 10 apps and 165 '
         'countries), this dashboard displays a country × application censorship matrix for '
         'WhatsApp, Telegram, Signal, Psiphon, and others.'),
     see=(
         '中国大陆对全部 10 个测试应用均有严重阻断记录（179 个严重阻断 pair）；俄罗斯封锁 Telegram '
         '历史记录仍留存；印度与巴基斯坦在 VoIP/通讯应用上有局部阻断；规避工具（Tor/Psiphon/'
         'RiseupVPN）在五国阻断率 > 60%。',
         'Chinese mainland records severe blocks across all 10 tested apps (179 critical pairs). '
         'Russia retains historical Telegram blocks. India and Pakistan show partial VoIP/messaging '
         'blocks. Circumvention tools (Tor/Psiphon/RiseupVPN) face > 60% block rates in five countries.'))

_add('/countries/dashboards/anycast-census/', 'Anycast 地理普查', 'Anycast Geographic Census',
     what=(
         '基于 UTwente LACES v4/v6 数据集（7,814 独立前缀，500,000 条 PoP 定位记录）绘制 anycast '
         '前缀的地理落点分布，揭示 CDN、DNS 根服务器的实际 PoP 部署格局。',
         'Maps anycast prefix geographic distribution using UTwente LACES v4/v6 '
         '(7,814 prefixes, 500,000 PoP records), revealing where CDN and DNS root-server '
         'Points-of-Presence actually land.'),
     see=(
         '7,807/7,814 前缀被标记为 anycast；PoP 分布高度集中于美国、荷兰和德国三国；中国大陆境内'
         'anycast PoP 覆盖率偏低，DNS 根服务器镜像节点主要由 Anycast 路由承载。亚洲 PoP 密度低于'
         '欧美，是互联网测量偏差的隐性来源。',
         '7,807 of 7,814 prefixes are anycast-tagged. PoPs concentrate heavily in the US, '
         'Netherlands, and Germany. Chinese mainland has below-average anycast PoP coverage; '
         'DNS root-server mirrors rely predominantly on anycast routing. Lower PoP density '
         'in Asia is a latent source of measurement bias.'))

_add('/countries/dashboards/dns-authority-deep/', 'DNS 权威深度图', 'DNS Authority Consolidation',
     what=(
         '从三类 MANAGED_BY 关系（正向 NS 100 万行、反向 RDNS 50 万行、根区 iana.root_zone 5000 行）'
         '出发，按 NS 主机名的 2LD 聚合运营商，绘制 DNS 权威托管的深度集中度图谱。',
         'Builds on three MANAGED_BY relation types — forward NS (1M rows), reverse RDNS (500K), '
         'root zone (5K) — and aggregates operators by NS 2LD to chart deep consolidation '
         'in DNS authoritative hosting.'),
     see=(
         'Cloudflare、AWS Route53、Google 占据正向 NS 集中度前三；HHI ≈ 326（500 NS 范围内），'
         '属于分散市场，但 top-3 合计份额仍超 30%。根区运营商（Verisign/ICANN 授权）高度集中；'
         '中国大陆域名的 NS 大量落在国内自建 DNS，自持度高于平均。',
         'Cloudflare, AWS Route53, and Google lead forward-NS concentration. '
         'HHI ≈ 326 (across 500 NS) signals a dispersed market, yet the top-3 combined share '
         'exceeds 30%. Root-zone operators (Verisign/ICANN) are highly concentrated. '
         'Chinese mainland domains use predominantly domestic DNS, above-average self-hosting ratio.'))

_add('/countries/dashboards/schema-gaps/', 'Schema 缺口清单', 'Upstream Schema Gap Report',
     what=(
         '记录 IYP 2024-01 → 2026-04 跨度 15 个 topic + evolution 分析中发现的所有上游 schema '
         '不一致与缺失：每条列出具体 Cypher 路径、受影响的 topic 与快照、以及本研究采用的 workaround。',
         'Documents all upstream schema inconsistencies and gaps discovered across 15 topics '
         'and the evolution analysis over 11 IYP snapshots. Each entry shows the Cypher path, '
         'affected topics/snapshots, and the workaround adopted.'),
     see=(
         '共 16 个 gap（High 2 · Medium 7 · Low 7）。High 级别：① MANRS crawler 可能失败导致节点'
         '缺失；② Cloudflare DNS QUERIED_FROM 关系名变更致 topic18 降级。静态 fallback dict 覆盖'
         '9 国；crawler 文档未声明属性名建议标准化后提 PR。',
         '16 gaps total (High 2 · Medium 7 · Low 7). High-severity: (1) MANRS crawler failure '
         'can leave nodes missing; (2) Cloudflare DNS QUERIED_FROM relation rename caused '
         'topic18 fallback. Static fallback dicts cover all 9 countries. '
         'Attribute naming conventions are inconsistent — standardisation PRs recommended.'))

_add('/countries/dashboards/eyeball/', '用户加权视角', 'User-weighted Sovereignty',
     what=(
         '引入 APNIC Eyeball（每个 AS 在所在国的用户份额）× Worldbank 人口数据作为新权重，'
         '重新计算主权指数与集中度指标。X 轴为基础设施视角，Y 轴为用户视角，散点偏离对角线说明差距。',
         'Re-weights sovereignty and concentration metrics by APNIC Eyeball (per-AS user share '
         'in-country) × Worldbank population. Scatter plots compare infra-view (X) vs user-view '
         '(Y) — departure from the diagonal marks the eyeball gap.'),
     see=(
         '中国大陆在深层 k-core 上基础设施视角约 0.25%、用户视角约 5.9%，差距 23.4 倍，是九国中最大。'
         '荷兰 AS 密度最高（93 AS/百万人口 vs 中国大陆 4.7），说明荷兰的互联网资源分配极度人均领先。',
         'Chinese mainland k-core infrastructure view ≈ 0.25%, user view ≈ 5.9% — a 23.4× gap, '
         'the largest of the nine. Netherlands has the highest AS density (93 ASes per million '
         'population vs Chinese mainland 4.7), indicating far superior per-capita Internet '
         'resource allocation.'))

_add('/countries/dashboards/routing-security/', '路由安全真身', 'Routing Security Reality',
     what=(
         '将路由安全拆为三层：宣告层（RPKI ROA 签名率）、实行层（ROVISTA 实测 drop 无效路由）、'
         '承诺层（MANRS 声明）。范围：29,778 个交叉 AS，2024-10 快照。',
         'Decomposes routing security into three tiers: announcement (RPKI ROA signing rate), '
         'enforcement (ROVISTA measured invalid-prefix drop), and commitment (MANRS declaration). '
         'Scope: 29,778 cross-referenced ASes, 2024-10 snapshot.'),
     see=(
         '88% 的宣告 AS 不执行 ROV（ROVISTA drop 率 < 50%）；签名率高 ≠ 真正过滤无效路由；'
         '美国和荷兰的实行率最高；中国大陆 ROV 实行 AS 占比仅约 3%；MANRS 承诺数量与实际执行'
         '相关性低，说明"承诺"层存在大量空洞声明。',
         '88% of announcing ASes do not enforce ROV (ROVISTA drop rate < 50%). '
         'High RPKI signing rate does not imply filtering. US and Netherlands have the highest '
         'enforcement rates. Chinese mainland ROV-enforcing ASes account for only ~3%. '
         'MANRS commitments show weak correlation with actual enforcement.'))

_add('/countries/dashboards/toplist/', 'Tranco Top-10k 深度', 'Tranco Top-10k Deep-dive',
     what=(
         '以 Tranco Top-10k（2024-10 快照）为分析单元，解剖 Top 域名的 TLD 构成、托管 AS 分布、'
         'NS 运营商集中度与各国域名占比。共 333 个 TLD，.com 占 50%。',
         'Dissects Tranco Top-10k (2024-10 snapshot) by TLD composition, hosting-AS distribution, '
         'NS operator concentration, and per-country domain share. Covers 333 TLDs; '
         '.com holds 50% of the top-10k.'),
     see=(
         '.com 占 51.6%（降级自四源对比），350 个独立 TLD 显示 ccTLD 碎片化；托管 AS 高度集中'
         '于 Cloudflare/AWS/Google；中国大陆 ccTLD .cn 在 Top-10k 中仅约 0.3%，与其网民规模'
         '极不匹配；.de/.nl 在 Top-10k 的代表度相对人口最高。',
         '.com accounts for 51.6% (single-source fallback). 350 unique TLDs show ccTLD '
         'fragmentation. Hosting ASes concentrate on Cloudflare/AWS/Google. '
         'Chinese mainland .cn holds only ~0.3% of Top-10k — far below its Internet population share. '
         '.de/.nl have the highest per-capita Top-10k representation.'))

_add('/countries/dashboards/asdb/', 'AS 业务类型图谱', 'ASDB Category Map',
     what=(
         '以 Stanford ASDB 数据集（layer=1 顶级业务分类）切分 9 国 AS 组成，主要类别包括 '
         'Computer & IT、Manufacturing、Service、Government、Construction 等。',
         'Uses the Stanford ASDB dataset (layer-1 top-level categories) to decompose each '
         'country\'s AS population by business sector: Computer & IT, Manufacturing, Service, '
         'Government, Construction, and others.'),
     see=(
         'Computer & IT 占全局 57%，是最大单一类别（16K Service AS 排第二）；美国该类别 AS '
         '数远超其他国家；中国大陆 Government 类别 AS 占比相对高于欧洲，反映国家主导的网络格局；'
         '荷兰与德国的 Manufacturing/Service AS 比例高，与工业互联网布局一致。',
         'Computer & IT accounts for 57% globally — the single largest category (Service 16K '
         'is second). The US dominates this category by count. Chinese mainland shows a higher '
         'Government-category share than European peers, reflecting state-led network governance. '
         'Netherlands and Germany have elevated Manufacturing/Service shares.'))

_add('/countries/dashboards/archetype/', 'AS 业务原型', 'AS Business Archetype',
     what=(
         '基于 bgptools.as_names 的 Carrier / Content / Eyeball / T1 四分法，描绘 9 国 AS 组合'
         '的"业务原型"：每国 AS 偏用户端（Eyeball）还是内容端（Content），或运营商（Carrier）？',
         'Uses bgptools.as_names Carrier/Content/Eyeball/T1 four-way taxonomy to draw each '
         'country\'s AS "business archetype" — is its AS population user-oriented (Eyeball), '
         'content-oriented (Content), carrier, or Tier-1?'),
     see=(
         'Eyeball AS 8,332 / Content 1,173 / Carrier 557 / T1 15（降级自 AWS IP-range 方案）；'
         '美国在 Content 与 T1 两类绝对领先；中国大陆 Eyeball 类别数量庞大但 Content 稀少，'
         '反映"消费端重、生产端轻"的结构；荷兰 Carrier+T1 密度全球最高。',
         'Eyeball 8,332 / Content 1,173 / Carrier 557 / T1 15 (fallback from AWS IP-range plan). '
         'US leads absolutely in Content and T1. Chinese mainland has many Eyeball ASes but few '
         'Content ASes — a "heavy consumer, light producer" structure. '
         'Netherlands has the highest Carrier+T1 density globally.'))

_add('/countries/dashboards/bgp-tags/', 'AS 行为标签地图', 'BGP-tools AS Tags',
     what=(
         '展示 bgp.tools 手工维护的 18 个 AS 行为标签在 9 国的分布。标签涵盖角色（Home ISP、'
         'Academic、Government）、安全（ToR、VPN、DDoS Mitigation、Anycast）与关键基础设施。'
         '数据：15,350 条标签记录，2024-10 快照。',
         'Shows the distribution of bgp.tools 18 hand-curated AS behavioral tags across 9 '
         'countries. Tags cover role (Home ISP, Academic, Government), security (ToR, VPN, '
         'DDoS Mitigation, Anycast), and critical infrastructure. Data: 15,350 tag records, '
         '2024-10 snapshot.'),
     see=(
         'Home ISP 2,424 是最大标签类；ToR 974、VPN 751、关键基础设施 448；荷兰与美国的 ToR/VPN '
         'AS 密度远超其他国家；中国大陆几乎没有 ToR 标签 AS，但 Government 标签 AS 比例最高；'
         '德国 Academic AS 比例领先欧洲。',
         'Home ISP 2,424 is the largest tag. ToR 974, VPN 751, critical infrastructure 448. '
         'Netherlands and the US have far higher ToR/VPN AS density than others. '
         'Chinese mainland has almost no ToR-tagged ASes but the highest Government-tagged share. '
         'Germany leads Europe in Academic-tagged ASes.'))

_add('/countries/dashboards/ooni/', 'OONI 审查测试图谱', 'OONI Censorship Tests',
     what=(
         '以 OONI 10 个测试类型 × 165 国的 CENSORED 边（共 18,788 条）绘制审查矩阵，测试包括'
         'Web Connectivity、WhatsApp、Telegram 等；country_code 缺失时从 AS→Country 映射回退。',
         'Charts a censorship matrix from 18,788 CENSORED edges across 10 OONI test types and '
         '165 countries. Tests include Web Connectivity, WhatsApp, and Telegram. '
         'Missing country_code falls back to AS→Country mapping.'),
     see=(
         '179 对严重阻断 pair 中中国大陆位居首位；俄罗斯在 Telegram 与 VoIP 测试上有历史阻断记录；'
         '规避工具（Tor/Psiphon/RiseupVPN/TorSF）在强审查国家被阻断率 > 60%；美国、荷兰、'
         '德国在全部 10 个测试中无严重阻断记录。',
         '179 severe block pairs; Chinese mainland ranks first. Russia retains historical '
         'blocks on Telegram and VoIP tests. Circumvention tools (Tor/Psiphon/RiseupVPN/TorSF) '
         'face > 60% blocking in heavy-censorship countries. US, Netherlands, and Germany '
         'record zero severe blocks across all 10 tests.'))

_add('/countries/dashboards/rovista-country/', 'ROV 执行国别地图', 'ROV Enforcement by Country',
     what=(
         '将 ROVISTA 实测 drop 率（无效前缀被过滤的比例）按国家聚合，补充 Topic 2 全球散点图的'
         '国家粒度视角。范围：有 ROVISTA 数据的 AS，2024-10 快照；PeeringDB 字段缺失时回退。',
         'Aggregates ROVISTA measured drop rates (fraction of invalid prefixes actually filtered) '
         'by country, adding a country-level view to the Topic 2 global scatter. '
         'Covers all ASes with ROVISTA data, 2024-10 snapshot, with PeeringDB fallback.'),
     see=(
         'BT（英国）以 63% drop 率居国别榜首；五国 ROV 执行率为 0%（包括多个亚洲国家）；中国大陆'
         'AS 平均 drop 率 < 3%；欧洲整体优于亚洲；全球仍有 > 80% 的宣告 AS 不执行 ROV，'
         '路由劫持风险依然系统性存在。',
         'BT (UK) tops the country ranking at 63% drop rate. Five countries record 0% ROV '
         'enforcement, including several Asian nations. Chinese mainland AS average drop rate '
         'is under 3%. Europe outperforms Asia overall. More than 80% of announcing ASes '
         'globally still do not enforce ROV.'))

_add('/countries/dashboards/atlas/', 'Atlas 探针全球覆盖', 'RIPE Atlas Probes',
     what=(
         '以 RIPE Atlas 39,502 个探针在 222 国的地理分布，揭示主动 Internet 测量能力的地理不平等。'
         '探针密度决定路由/DNS/拥塞研究的测量精度；低密度区域的分析结论存在系统性偏差。',
         'Maps 39,502 RIPE Atlas probes across 222 countries, exposing geographic inequality '
         'in active Internet measurement capacity. Probe density determines the precision of '
         'routing/DNS/congestion studies — low-density regions introduce systematic bias.'),
     see=(
         'Top-5 国合计占全球探针 40%（德国、荷兰、法国、美国、英国领先）；中国大陆探针数量显著偏低，'
         '约 50 个，与其网络规模严重不匹配；9,681 个探针 country 字段未知（已排除）；探针密度与'
         '主权指数正相关，说明高主权国家在测量基础设施上也更有优势。',
         'Top-5 countries account for 40% of all probes (Germany, Netherlands, France, US, UK '
         'lead). Chinese mainland has only ~50 probes — severely under-represented relative to '
         'network scale. 9,681 probes have unknown country (excluded). Probe density correlates '
         'positively with sovereignty index.'))

_add('/countries/dashboards/bgp-obs/', 'BGP 观测多样性', 'BGP Observation Diversity',
     what=(
         '基于 bgpkit.as2rel 的 v4 与 v6 两个 peering 观测源，量化 AS 的"多源可见度"——一个 AS '
         '在几个独立观测源中被看到，反映路由宣告的真实传播范围。',
         'Uses bgpkit.as2rel v4 and v6 peering sources to quantify AS multi-source visibility — '
         'how many independent collectors observe each AS, reflecting the true propagation '
         'scope of its route announcements.'),
     see=(
         '14,488 AS 在至少一源可见；13K 有 v4 记录，6.8K 有 v6 记录，6.2K 同时被两源观测（降级自'
         'PCH 三源方案）；v4/v6 双栈可见率 46.9%；中国大陆 AS 的 v6 单源可见比例偏高，说明 IPv6'
         '路由宣告分散度不足，测量质量低于欧美。',
         '14,488 ASes visible in at least one source; 13K have v4, 6.8K have v6, '
         '6.2K are observed by both (fallback from a three-source PCH plan). '
         'Dual-stack visibility rate: 46.9%. Chinese mainland ASes show higher v6 single-source '
         'visibility, indicating insufficient IPv6 route propagation diversity.'))

_add('/countries/dashboards/org-concentration/', 'AS 所有权集中度', 'AS Ownership Concentration',
     what=(
         '以 caida.as2org 数据集派生各国 AS 的组织归属，计算 HHI 市场集中度指数，判断 9 国'
         '互联网 AS 资源是否存在寡头垄断（HHI > 2,500）或高度分散（HHI < 100）。',
         'Derives AS ownership from caida.as2org, computes HHI concentration index per country, '
         'and tests whether each country\'s AS pool shows oligopoly (HHI > 2,500) '
         'or dispersion (HHI < 100).'),
     see=(
         '9 国 HHI 均 < 200（组织级高度分散）；但按用户数加权后，中国大陆的三大运营商（中国电信/'
         '中国联通/中国移动）合计控制 > 90% 用户，说明 AS 层面分散不等于市场层面分散；'
         '美国在 AS 组织数量上最多，但 Comcast/AT&T 的用户份额仍高度集中。',
         'All 9 countries have HHI < 200 at the AS-organisation level (highly dispersed). '
         'However, weighting by user base, Chinese mainland\'s top-3 operators (Telecom/Unicom/Mobile) '
         'control > 90% of users — AS dispersion ≠ market dispersion. '
         'The US has the most AS organisations but Comcast/AT&T still dominate user share.'))

_add('/countries/dashboards/ihr-hegemony/', '全球依赖中心性', 'Global IHR Hegemony',
     what=(
         '以 IHR local-hegemony-v4 量化全球 AS 依赖图：对每个 AS 聚合其入向依赖权重（多少个 AS '
         '将它当作必经路径），识别全球互联网的依赖中心节点。范围：top-5,000 AS 按入向权重排序。',
         'Aggregates IHR local-hegemony-v4 to compute global dependency centrality: '
         'for each AS, sum the incoming hegemony weights (how many ASes route through it). '
         'Scope: top-5,000 ASes by incoming hegemony.'),
     see=(
         'No.1 = AS6939 Hurricane Electric（美国，入向权重 27,500+）；Lumen/CenturyLink 排第二（10,900）；'
         '中国大陆 CERNET2 全球第 5，是前 10 中唯一非美国实体；中国大陆中国电信/联通排名 50-100；'
         '荷兰 AMS-IX 相关 AS 集中在前 20。',
         'No.1 = AS6939 Hurricane Electric (US, incoming weight 27,500+). '
         'Lumen/CenturyLink ranks second (10,900). Chinese mainland CERNET2 is global #5 — '
         'the only non-US entity in the top 10. China Telecom/Unicom rank 50–100. '
         'Netherlands AMS-IX-related ASes cluster in the top 20.'))

_add('/countries/dashboards/multinational/', '跨国组织 AS 足迹', 'Multinational Org Footprint',
     what=(
         '交叉 caida.as2org 的 as_organization.csv 与 as_country.csv，找出 AS 跨多国的 814 个'
         '跨国组织（占 97,759 个组织的 0.8%），分析其 AS 足迹的国家广度与 AS 密度。',
         'Cross-references caida.as2org organization and country tables to identify 814 '
         'multinational organisations (0.8% of 97,759) whose ASes span multiple countries, '
         'then analyses their country breadth and AS density.'),
     see=(
         'Top-3：Internet Systems Consortium（ISC，18 国，56 AS）、ISC, Inc.（16 国，71 AS）、'
         'AT&T Japan（12 国）；美国主导跨国 AS 足迹；中国大陆跨国组织较少但中国移动在 10+ 国'
         '均有 AS；荷兰 AMS-IX 相关组织足迹覆盖 50+ 国，是欧洲最广的跨国互联网实体。',
         'Top-3: Internet Systems Consortium (18 countries, 56 ASes), ISC Inc. (16 countries, '
         '71 ASes), AT&T Japan (12 countries). The US dominates multinational AS footprints. '
         'Chinese mainland multinationals are fewer, though China Mobile spans 10+ countries. '
         'Netherlands AMS-IX-related orgs cover 50+ countries — the widest European footprint.'))

_add('/countries/dashboards/dns-authority/', '全球 DNS 权威集中度', 'Global DNS Authority',
     what=(
         '基于 OpenINTEL Top-500 权威 NS 服务器（按托管域名数排序）交叉 ns_to_as 映射，'
         '计算 DNS 权威托管的运营商集中度（HHI）与国家分布。覆盖 158 个独立运营商。',
         'Uses OpenINTEL Top-500 authoritative NS servers (ranked by hosted domain count), '
         'cross-referenced with ns_to_as, to compute DNS authority operator concentration (HHI) '
         'and country distribution across 158 operators.'),
     see=(
         '最大运营商 GoDaddy (domaincontrol.com) 托管 130 万域名；dns-parking 728K；Google 652K；'
         'HHI (top-500 内) ≈ 326，属分散市场但 top-3 合计 > 30%；中国大陆域名 NS 主要落在国内'
         '运营商，中国域名注册局/阿里云/腾讯云合计占中国大陆域名权威比例约 60%。',
         'Largest operator: GoDaddy (domaincontrol.com) hosts 1.3M domains; dns-parking 728K; '
         'Google 652K. HHI ≈ 326 across top-500 — dispersed but top-3 combined share exceeds 30%. '
         'Chinese mainland domains rely predominantly on domestic operators (CNNIC/Alibaba Cloud/'
         'Tencent Cloud ≈ 60% combined domestic-domain authority).'))

_add('/countries/dashboards/country-dep/', '9×9 国家依赖矩阵', 'Country Dependency Matrix',
     what=(
         '将 IHR local-hegemony-v4 的 AS 级依赖关系按国家聚合成 9×9 矩阵，每格为起源国 AS 对'
         '目标国 AS 的 hege 加权依赖总量；对角线为国内自依赖，行净和揭示净出口 / 净进口方向。',
         'Aggregates IHR local-hegemony-v4 into a 9×9 country matrix. Each cell is the total '
         'hegemony-weighted dependency of source-country ASes on target-country ASes. '
         'The diagonal is domestic self-dependency; row net-sum reveals net exporter/importer.'),
     see=(
         '美国是唯一净出口国（net = +13,604），即全球其他 AS 对美国 AS 的依赖显著大于美国对外依赖；'
         '中国大陆是最大净进口国（net = −5,018），净进口/净出口比约 253:1；荷兰对美国的依赖排名'
         '九国第二低，说明欧洲互联网具备较强的横向互联自主性。',
         'The US is the sole net exporter (net = +13,604): the global Internet depends on US '
         'ASes far more than US ASes depend on others. Chinese mainland is the largest net '
         'importer (net = −5,018), net-import/export ratio ≈ 253:1. '
         'Netherlands has the second-lowest US dependence among the nine, confirming '
         'strong European lateral interconnection autonomy.'))

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


# =================== GLOBE & NETWORK-EVOLUTION ===================

_add('/network/evolution/', '时序演化', 'Network Time-Series',
     what=(
         '数据源为 `data_cache/complex_network/`，覆盖 2024-01 → 2026-04 共 10 个季度快照。'
         '每个快照计算 10 项拓扑指标：节点数、边数、平均度、最大度、聚类系数、同配性、k-max、'
         'rich-club 系数、Louvain 模块度、渗流阈值，绘制成折线时序图。鼠标悬停可读取每季度精确值。',
         'Source: `data_cache/complex_network/` across 10 quarterly snapshots '
         '(2024-01 → 2026-04). Ten topology metrics are computed per snapshot: '
         'node/edge count, mean/max degree, clustering coefficient, assortativity, '
         'k-max, rich-club coefficient, Louvain modularity, and percolation threshold. '
         'Hover any point to read the exact quarterly value.'),
     see=(
         '2025-Q1 至 2025-Q2 区间 BGP peering 图边数出现显著跃升（+约 8%），推测与骨干路由'
         '重组有关；Louvain 模块度自 2024 年起持续上升，说明社群结构在加剧分化；聚类系数与'
         '同配性长期稳定，验证互联网核心拓扑对增量扰动具有鲁棒性。渗流阈值维持在 0.07-0.09，'
         '意味着移除约 8% 的 hub 节点即可令网络碎裂。',
         'A notable edge-count spike (~+8%) appears between 2025-Q1 and 2025-Q2, likely tied '
         'to backbone route re-organisation. Louvain modularity has risen steadily since 2024, '
         'indicating deepening community fragmentation. Clustering coefficient and assortativity '
         'remain stable, confirming the Internet core is robust to incremental perturbation. '
         'Percolation threshold holds at 0.07–0.09 — removing ~8% of hub nodes suffices to '
         'fragment the network.'))

_add('/globe/strata/', '分层占比图', 'AS Strata · Country Canopy',
     what=(
         '基于 three.js + OrbitControls + CSS2DRenderer 的 3D 伞盖状结构。94 个国家映射为扇区：'
         '扇角 = 该国 AS 占全球比例，柱高 = 该国 IPv4 地址总量，国家之间的丝带粗细 = '
         'Top-5K AS 对等量（成对 peering 流量代理）。拖拽旋转、滚轮缩放；点击扇区显示国家摘要。',
         'A canopy-shaped 3D structure built with three.js, OrbitControls, and CSS2DRenderer. '
         '94 countries map to sectors: sector angle = country AS share of global total, '
         'column height = IPv4 address space, ribbon width = pairwise peering volume (Top-5K AS). '
         'Drag to rotate, scroll to zoom, click a sector for a country summary.'),
     see=(
         '中国大陆扇区约 8,624 AS（约 7% 全球份额），宽度位居全球第 3，次于美国 (~34%) 和欧盟聚合；'
         '美国扇区高度远超其他（IPv4 地址总量约 15 亿），折射出历史分配不均；北美丝带最粗，'
         '说明跨大西洋 peering 是全球最密集的对等轴；亚太内部丝带偏细，暗示区域内 peering 仍不足。',
         'Chinese mainland sector: ~8,624 ASes (~7% global share), width ranks 3rd after US (~34%) '
         'and aggregated EU. US column dwarfs all others (IPv4 ~1.5 B addresses), reflecting '
         'historical allocation inequity. Trans-Atlantic ribbons are the thickest globally — '
         'intra-APAC ribbons remain comparatively thin, indicating under-developed regional peering.'))

_add('/globe/globe/', '地球视图', 'Geographic Globe',
     what=(
         '基于 globe.gl（three.js 后端），将 5,000 个头部 AS 按真实地理坐标投影到 earth-dark '
         '纹理地球表面。点颜色按区域分组（CN / NA / EA / EU / 其他），点大小对应 IPv4 地址空间；'
         '对等弧连接 AS 间的 BGP peering 关系。拖拽旋转；点击 AS 点可查看 ASN、名称与地址量。',
         'Built with globe.gl (three.js backend). 5,000 top ASes are projected onto an earth-dark '
         'texture globe at their real geographic coordinates. Point colour encodes region '
         '(CN / NA / EA / EU / other); size encodes IPv4 address space. '
         'Arcs connect BGP peering pairs. Drag to rotate; click a point to see ASN, name, and prefix count.'),
     see=(
         '美国 AS 高度聚集在东西海岸（Virginia/California 两极）与芝加哥枢纽；中国大陆 AS 则集中于'
         '北京/上海/广州三地；欧洲节点在法兰克福/阿姆斯特丹/伦敦密度最高。对等弧显示跨太平洋连接'
         '显著少于跨大西洋，验证"数字鸿沟"的地理根源。西非与中亚地区节点极稀，说明这些区域依赖'
         '少数门户 AS 连接全球。',
         'US ASes cluster on the east coast (Virginia) and west coast (California) with Chicago '
         'as the interior hub. Chinese mainland ASes concentrate in Beijing, Shanghai, and Guangzhou. '
         'European density peaks at Frankfurt, Amsterdam, and London. '
         'Trans-Pacific arcs are visibly sparser than trans-Atlantic ones — the geographic root '
         'of the digital divide. West Africa and Central Asia show very few nodes, '
         'relying on a handful of gateway ASes for global connectivity.'))

_add('/globe/force/', '拓扑力图', 'Force Topology',
     what=(
         '基于 3d-force-graph（three.js），同样以 5,000 个头部 AS 为节点，但改用 force-directed '
         '布局替代真实地理坐标——拓扑相近的 AS 在引力作用下聚拢，与地理无关。'
         '节点颜色按社群检测结果着色，边为 BGP peering；拖拽/滚轮交互，点击节点可高亮邻居。',
         'Same 5,000 top ASes as the geographic globe, but rendered with 3d-force-graph '
         '(three.js) using force-directed layout rather than real coordinates. '
         'Topologically similar ASes gravitate together regardless of geography. '
         'Node colour encodes community; edges are BGP peering pairs. '
         'Drag/scroll to navigate; click a node to highlight its neighbours.'),
     see=(
         'Tier-1 骨干（AT&T、Lumen、NTT 等）聚居图中心，形成致密的高度数核；'
         'CDN/云巨头（Cloudflare、Google、Amazon）占据围绕核心的第二层；'
         '中国大陆 AS 群在图右下方形成独立子簇，与全球骨干仅有少数桥接边相连，'
         '视觉上印证了"半封闭式"互联网拓扑的结构特征。eyeball ISP 散落图外缘。',
         'Tier-1 backbones (AT&T, Lumen, NTT, etc.) occupy the dense centre hub. '
         'CDN/cloud giants (Cloudflare, Google, Amazon) form a second shell around the core. '
         'Chinese mainland ASes cluster into an isolated sub-cloud at the periphery, '
         'connected to the global backbone by only a few bridge edges — visually confirming '
         'the semi-closed topology. Eyeball ISPs scatter along the outer fringe.'))

_add('/globe/galaxy/', '全景星图', 'Full Galaxy · 127K AS',
     what=(
         '基于 three.js InstancedMesh（4 级 LOD + 八叉树流式加载），将全部 127,000+ 个 AS '
         '渲染为粒子星图。支持 3 种评分预设布局切换：reach（覆盖面）/ economy（经济价值）/ '
         'structure（拓扑结构重要性）。注意：离线版本受浏览器 file:// 限制暂不支持；'
         '在线访问或启用本地 HTTP 服务器后可正常加载。',
         'Renders all 127,000+ ASes as a particle starfield using three.js InstancedMesh with '
         '4-level LOD and octree streaming. Three scoring preset layouts are switchable: '
         'reach (address coverage), economy (economic value), and structure (topological importance). '
         'Note: offline file:// mode is not supported due to browser CORS restrictions; '
         'use a local HTTP server or the online version to load the full dataset.'),
     see=(
         '127K 个粒子在任意 preset 下都呈现幂律分布：极少数 AS 聚集于高分核心（对应少数 Tier-1 '
         '和超大型 CDN），而绝大多数 AS 漂散在低分外围。切换 reach→structure preset 可见'
         'Cloudflare（覆盖率极高）和 AT&T（结构重要性极高）在两种坐标系下位置截然不同，'
         '说明"覆盖大 ≠ 拓扑核心"——两个维度彼此补充而非替代。',
         'Under any preset, 127K particles display a power-law distribution: a tiny elite '
         'cluster at the high-score core (Tier-1s and mega-CDNs) while the vast majority '
         'drift in the low-score periphery. Switching reach→structure reveals that Cloudflare '
         '(top-ranked by reach) and AT&T (top-ranked by structure) occupy very different '
         'positions — confirming that "large footprint ≠ topological centrality."'))


def get(url: str) -> dict | None:
    return EXPLAINERS.get(url)
