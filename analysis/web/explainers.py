'''Plain-language chart explainers (图解) for every non-China page.

Follows the tone & structure of the existing China pages:
  这是什么图 / 怎么读 / 能看出什么 — accessible, not academic.

Keyed by canonical page URL (matches ``nav.Page.url``).  Missing entries
render the wrapper without a 图解 button.
'''
from __future__ import annotations

EXPLAINERS: dict[str, dict] = {}


def _add(url: str, title_zh: str, title_en: str, *, what: tuple[str, str],
         how: tuple[str, str], see: tuple[str, str],
         keyterm: tuple[str, str, str] | None = None) -> None:
    EXPLAINERS[url] = {
        'title_zh': title_zh, 'title_en': title_en,
        'what_zh': what[0], 'what_en': what[1],
        'how_zh': how[0], 'how_en': how[1],
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
