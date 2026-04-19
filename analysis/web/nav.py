'''Navigation metadata for the unified analysis site.

Every page the generator renders is modelled here.  Templates are driven
purely by these structures — no scraping of filenames at render time.

The existing analysis artefacts (china/html, countries/html, complex_network_images)
are not modified; we only iframe / embed them.
'''
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ANALYSIS = REPO_ROOT / 'analysis'

CHINA_HTML = ANALYSIS / 'china' / 'html'
CHINA_DATA = ANALYSIS / 'china' / 'data'
COUNTRIES_HTML = ANALYSIS / 'countries' / 'html'
COUNTRIES_DATA = ANALYSIS / 'countries' / 'data'
NETWORK_IMG = ANALYSIS / 'complex_network_images'
GLOBE_HTML = ANALYSIS / 'as_globe' / 'html'
GLOBE_DATA = ANALYSIS / 'as_globe' / 'data'

SNAPSHOT_LATEST = '2026-04'
SNAPSHOT_PREV = '2025-04'         # retained for 12-month Δ display
SNAPSHOT_BASELINE = '2024-01'     # 27-month baseline for "Δ since launch"
SNAPSHOTS_ALL = ['2024-01', '2024-04', '2024-07', '2024-10',
                 '2025-01', '2025-04', '2025-07', '2025-10',
                 '2026-01', '2026-02', '2026-04']


@dataclass
class Page:
    slug: str
    url: str
    track: str
    title_zh: str
    title_en: str
    kind: str
    src: str | None = None
    phase: str | None = None
    step: int | None = None
    part: int | None = None
    kpis: list[str] = field(default_factory=list)
    subtitle_zh: str | None = None
    subtitle_en: str | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class Phase:
    key: str
    title_zh: str
    title_en: str
    pages: list[Page] = field(default_factory=list)


@dataclass
class Track:
    slug: str
    title_zh: str
    title_en: str
    tagline_zh: str
    tagline_en: str
    accent: str
    phases: list[Phase] = field(default_factory=list)
    hub_url: str = ''

    def all_pages(self) -> list[Page]:
        return [p for phase in self.phases for p in phase.pages]


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}


def _fmt_number(v: float | int) -> str:
    if isinstance(v, float):
        if abs(v) < 1:
            return f'{v:.3f}'
        if abs(v) < 100:
            return f'{v:.2f}'
        return f'{int(round(v))}'
    if isinstance(v, int):
        if abs(v) >= 1000:
            return f'{v:,}'
        return str(v)
    return str(v)


# --- China track ---------------------------------------------------------

CHINA_PHASES: list[tuple[str, str, str, list[tuple[int, str, str, int | None, list[str]]]]] = [
    ('A', '范围与身份', 'Scope & Identity', [
        (1, 'step01_scope', 'AS 清册与范围', None, ['6,660 大陆 · 1,468 港 · 474 台']),
        (2, 'step02_top_as', '头部 AS 身份档案', None, ['Top-20 持 44% 前缀']),
        (3, 'step03_part1', '全球排名 · 规模', 1, ['#3 AS · #3 前缀 · #16 IXP']),
        (3, 'step03_part2', '全球排名 · 连通度', 2, []),
        (3, 'step03_part3', '全球排名 · 内容', 3, []),
        (3, 'step03_part4', '全球排名 · 综合', 4, []),
    ]),
    ('B', 'BGP 拓扑位置', 'BGP Topology', [
        (4, 'step04_part1', 'BGP 前缀与 RPKI · 分布', 1, ['109,409 前缀 · RPKI 中等']),
        (4, 'step04_part2', 'BGP 前缀与 RPKI · 采纳', 2, []),
        (5, 'step05_peering_graph', 'AS 对等子图', None, ['400 节点 · 2,450 边']),
        (6, 'step06_centrality', '全球中心性位置', None, ['PageRank 中等 · 度数偏高']),
        (7, 'step07_kcore', 'k-core 层级位置', None, ['少数 AS 进入深层核心']),
    ]),
    ('C', '依赖与 Hegemony', 'Dependency & Hegemony', [
        (8, 'step08_depends_on_world', '出向 Hegemony', None, ['70%+ 依赖境外上游']),
        (9, 'step09_dependents', '入向 Hegemony', None, ['外国依赖 CN 程度有限']),
        (10, 'step10_concentration', '集中度与 HHI', None, ['HHI 偏高 · 头部集中']),
    ]),
    ('D', '物理基础设施', 'Physical Infrastructure', [
        (11, 'step11_part1', 'IXP 互联生态 · 总量', 1, ['IXP #16 · 密度低']),
        (11, 'step11_part2', 'IXP 互联生态 · 跨境', 2, []),
        (12, 'step12_facilities', '机房部署', None, ['机房 #33 · 重心境外']),
        (13, 'step13_ixp_fac_bridge', 'IXP × 机房三部图', None, ['HK 为主要跨境枢纽']),
    ]),
    ('E', 'DNS · 内容 · 排名', 'DNS · Content · Ranking', [
        (14, 'step14_dns_hosting', 'DNS 托管版图', None, ['云厂商 + 海外 ISP 主导']),
        (15, 'step15_dns_authority', '.cn DNS 主权', None, ['.cn 权威自持度高']),
        (16, 'step16_cname_chains', 'CNAME 跨境链', None, ['大量跨境 CNAME 桥接']),
        (17, 'step17_rankings', '多排名位置', None, ['Tranco / CrUX / APNIC']),
    ]),
    ('F', '安全 · 测量 · 综合', 'Security · Measurement · Synthesis', [
        (18, 'step18_censorship', '审查拓扑', None, ['审查网络与非审查网络有别']),
        (19, 'step19_atlas', 'Atlas 观测点', None, ['少量 CN Atlas 探针']),
        (20, 'step20_part1', '综合仪表板 · 指数', 1, ['主权指数 0.269 · 全球第 9']),
        (20, 'step20_part2', '综合仪表板 · 对比', 2, []),
        (20, 'step20_part3', '综合仪表板 · 趋势', 3, []),
    ]),
]


def _build_china_track() -> Track:
    phases: list[Phase] = []
    for key, title_zh, title_en, rows in CHINA_PHASES:
        pages: list[Page] = []
        for step, src_stem, title_zh_step, part, kpis in rows:
            metrics = _load_json(CHINA_DATA / f'step{step:02d}_metrics.json')
            title_en_step = metrics.get('title_en', title_zh_step)
            url_slug = f'step{step:02d}' + (f'_part{part}' if part else '')
            pages.append(Page(
                slug=url_slug,
                url=f'/china/{url_slug}/',
                track='china',
                title_zh=title_zh_step,
                title_en=title_en_step,
                kind='plotly',
                src=f'../../../../china/html/{src_stem}.html',
                phase=key,
                step=step,
                part=part,
                kpis=kpis,
            ))
        phases.append(Phase(key, title_zh, title_en, pages))

    # Prepend a Dashboards phase with the cross-snapshot evolution page
    dash_pages = [Page(
        slug='evolution',
        url='/china/evolution/',
        track='china',
        title_zh='时序演化',
        title_en='Time-Series Evolution',
        kind='plotly',
        src='../../../../china/html/evolution.html',
        phase='dashboards',
        kpis=['10 季度', 'CN 深度'],
    )]
    phases.insert(0, Phase('dashboards', '综合仪表板', 'Dashboards', dash_pages))

    return Track(
        slug='china',
        title_zh='中国互联网全球位置',
        title_en='China in the Global Internet Hierarchy',
        tagline_zh='20 步系统性考察中国在全球互联网分层中的位置与依赖',
        tagline_en='20 analytical steps examining China across BGP · DNS · IXP · content · sovereignty.',
        accent='#ff453a',
        phases=phases,
        hub_url='/china/',
    )


# --- Countries track -----------------------------------------------------

COUNTRY_NAMES: list[tuple[str, str, str]] = [
    ('US', '美国', 'United States'),
    ('CN', '中国', 'China'),
    ('JP', '日本', 'Japan'),
    ('IN', '印度', 'India'),
    ('DE', '德国', 'Germany'),
    ('GB', '英国', 'United Kingdom'),
    ('FR', '法国', 'France'),
    ('NL', '荷兰', 'Netherlands'),
    ('RU', '俄罗斯', 'Russia'),
]

COUNTRY_DASHBOARDS: list[tuple[str, str, str, str]] = [
    ('new-angles', 'new_angles_synthesis.html', '15 个新角度汇总', 'New Angles Synthesis'),
    ('scorecards', 'scorecards.html', '9 国综合 scorecard', '9-Country Scorecard'),
    ('cross-country', 'cross_country.html', '跨国对比', 'Cross-Country Dashboard'),
    ('evolution', 'evolution.html', '时序演化', 'Time-Series Evolution'),
    ('evolution-narrative', 'evolution_narrative.html', '演化叙事', 'Evolution Narrative'),
    ('correlations', 'correlations.html', '跨 Topic 相关性', 'Cross-Topic Correlation Scatters'),
    ('ixp-reality', 'topic16_ixp_reality.html', 'IXP 会话真伪', 'IXP Session Reality Check'),
    ('collector-consensus', 'topic17_collector_consensus.html', '多 collector 一致性', 'Multi-Collector Consensus'),
    ('real-traffic', 'topic18_real_traffic.html', '反 eyeball 对照', 'Counter-Eyeball Demand Signal'),
    ('app-censorship', 'topic19_app_censorship.html', '应用级封锁矩阵', 'App-Level Censorship Matrix'),
    ('anycast-census', 'topic20_anycast_census.html', 'Anycast 地理普查', 'Anycast Geographic Census'),
    ('dns-authority-deep', 'topic21_dns_authority_deep.html', 'DNS 权威深度图', 'DNS Authority Consolidation'),
    ('schema-gaps', 'schema_gaps.html', 'Schema 缺口清单', 'Upstream Schema Gap Report'),
    ('matrix', 'dependency_matrix.html', '跨国依赖矩阵', 'Cross-Country Dependency Matrix'),
    ('geography', 'content_geography.html', '内容地理', 'Content Geography'),
    ('eyeball', 'eyeball_weighted.html', '用户加权视角', 'User-weighted Sovereignty'),
    ('routing-security', 'routing_security.html', '路由安全真身', 'Routing Security Reality'),
    ('toplist', 'toplist.html', 'Tranco Top-10k 深度', 'Tranco Top-10k Deep-dive'),
    ('asdb', 'asdb_category.html', 'AS 业务类型图谱', 'ASDB Category Map'),
    ('archetype', 'as_archetype.html', 'AS 业务原型', 'AS Business Archetype'),
    ('bgp-tags', 'bgp_tags.html', 'AS 行为标签地图', 'BGP-tools AS Tags'),
    ('ooni', 'ooni_tests.html', 'OONI 审查测试图谱', 'OONI Censorship Tests'),
    ('rovista-country', 'rovista_by_country.html', 'ROV 执行国别地图', 'ROV Enforcement by Country'),
    ('atlas', 'atlas_probes.html', 'Atlas 探针全球覆盖', 'RIPE Atlas Probes'),
    ('bgp-obs', 'bgp_observation.html', 'BGP 观测多样性', 'BGP Observation Diversity'),
    ('org-concentration', 'org_concentration.html', 'AS 所有权集中度', 'AS Ownership Concentration'),
    ('ihr-hegemony', 'ihr_hegemony.html', '全球依赖中心性', 'Global IHR Hegemony'),
    ('multinational', 'multinational.html', '跨国组织 AS 足迹', 'Multinational Org Footprint'),
    ('dns-authority', 'dns_authority.html', '全球 DNS 权威集中度', 'Global DNS Authority'),
    ('country-dep', 'country_dep_matrix.html', '9×9 国家依赖矩阵', 'Country Dependency Matrix'),
]


def _country_sov(cc: str, snapshot: str) -> float | None:
    data = _load_json(COUNTRIES_DATA / snapshot / cc / 'step20_metrics.json')
    return data.get('metrics', {}).get('composite_sovereignty_index')


def _country_total_ases(cc: str, snapshot: str) -> int | None:
    data = _load_json(COUNTRIES_DATA / snapshot / cc / 'step01_metrics.json')
    return data.get('metrics', {}).get('total_ases')


def _build_countries_track() -> Track:
    profile_pages: list[Page] = []
    for cc, zh, en in COUNTRY_NAMES:
        sov_now = _country_sov(cc, SNAPSHOT_LATEST)
        sov_prev = _country_sov(cc, SNAPSHOT_PREV)
        tot_now = _country_total_ases(cc, SNAPSHOT_LATEST)
        tot_prev = _country_total_ases(cc, SNAPSHOT_PREV)
        kpis = []
        if sov_now is not None:
            kpis.append(f'主权指数 {sov_now:.3f}')
        if tot_now is not None:
            kpis.append(f'{tot_now:,} ASes')
        profile_pages.append(Page(
            slug=cc,
            url=f'/countries/{cc}/',
            track='countries',
            title_zh=f'{zh}互联网分层',
            title_en=f'{en} · Internet Hierarchy',
            kind='plotly',
            src=f'../../../../countries/html/profile_{cc}.html',
            phase='profiles',
            kpis=kpis,
            extra={
                'cc': cc,
                'country_zh': zh,
                'country_en': en,
                'sov_now': sov_now,
                'sov_prev': sov_prev,
                'tot_now': tot_now,
                'tot_prev': tot_prev,
            },
        ))

    dashboard_pages: list[Page] = []
    for slug, src_file, title_zh, title_en in COUNTRY_DASHBOARDS:
        dashboard_pages.append(Page(
            slug=slug,
            url=f'/countries/dashboards/{slug}/',
            track='countries',
            title_zh=title_zh,
            title_en=title_en,
            kind='plotly',
            src=f'../../../../../countries/html/{src_file}',
            phase='dashboards',
            kpis=[],
        ))

    phases = [
        Phase('profiles', '九国画像', 'Country Profiles', profile_pages),
        Phase('dashboards', '综合仪表板', 'Synthesis Dashboards', dashboard_pages),
    ]
    return Track(
        slug='countries',
        title_zh='九国互联网分层',
        title_en='Nine-Country Internet Hierarchy',
        tagline_zh='US · CN · JP · IN · DE · GB · FR · NL · RU 九国 × 20 指标 × 2 快照',
        tagline_en='Nine peer economies × 20 metrics × 2 snapshots (2025-04 → 2026-04).',
        accent='#0071e3',
        phases=phases,
        hub_url='/countries/',
    )


# --- Complex-network track ----------------------------------------------

NETWORK_STEPS: list[tuple[int, str, str, str, str, list[str]]] = [
    (5, 'step05_degree_distribution.png', '度分布与幂律拟合',
     'Degree Distribution & Power Law',
     '各层节点度分布的幂律指数与拟合拖尾',
     ['α ≈ 2.107', '无标度网络']),
    (6, 'step06_small_world.png', '小世界特性',
     'Small-World Properties',
     '聚类系数与平均最短路径 vs 随机基线',
     ['σ_SW = 1,820', 'C 为随机图 1,675×']),
    (7, 'step07_centrality_analysis.png', '多维中心性',
     'Multi-Dimensional Centrality',
     'Degree / Betweenness / Eigenvector / PageRank',
     ['识别系统性枢纽 AS']),
    (8, 'step08_kcore.png', 'k-核分解',
     'k-Core Decomposition',
     '最内核层厚度与节点归属',
     ['k_max = 197', '340 AS 组成核心骨架']),
    (9, 'step09_rich_club.png', 'Rich-Club 系数',
     'Rich-Club Coefficient',
     'hub 之间的互联程度 vs 随机模型',
     ['ρ(k) 显著偏高']),
    (10, 'step10_assortativity.png', '同配性分析',
     'Assortativity Analysis',
     '节点度之间的关联模式',
     ['r = −0.300', '负同配 · hub 连 leaf']),
    (11, 'step11_community_detection.png', '社区检测',
     'Community Detection (Louvain)',
     '模块度优化与社区地理/组织相关性',
     ['108 个社区', 'Q = 0.445']),
    (13, 'step13_concentration_hhi.png', '集中度与 HHI',
     'Concentration & HHI',
     'Gini 系数 / HHI / Lorenz 曲线多维度集中度',
     ['头部集中 · 多层共振']),
    (15, 'step15_percolation.png', '渗流与韧性',
     'Percolation & Robustness',
     '随机故障 vs 定向攻击下的巨连通分量',
     ['随机鲁棒', '定向脆弱']),
    (18, 'step18_cross_layer_cascade.png', '跨层级联失效',
     'Cross-Layer Cascade Failure',
     'BGP × DNS × 物理层的级联放大',
     ['单点失效向下放大']),
    (19, 'step19_geo_resilience.png', '地理韧性',
     'Geographic Resilience',
     '按国家逐个移除 AS 后的 GCC 大小',
     ['移除 US 仍保 87% GCC']),
    (22, 'step22_censorship_topology.png', '审查拓扑',
     'Censorship Topology',
     'OONI 检测 × AS 拓扑位置相关性',
     ['2,383 AS 有检测信号', 'RU 居首 (534)']),
    (24, 'step24_null_model_comparison.png', '零模型对比',
     'Null Model Comparison',
     'ER / BA / Configuration Model 对照',
     ['IYP 显著偏离随机']),
]

NETWORK_GROUPS: list[tuple[str, str, str, list[int]]] = [
    ('α', '单层拓扑', 'Single-Layer Topology', [5, 6, 7, 8, 9, 10, 11]),
    ('β', '集中度与韧性', 'Concentration & Resilience', [13, 15, 18, 19]),
    ('γ', '地缘与基线', 'Geopolitics & Baselines', [22, 24]),
]


def _build_network_track() -> Track:
    rows_by_step = {row[0]: row for row in NETWORK_STEPS}
    phases: list[Phase] = []
    for key, title_zh, title_en, steps in NETWORK_GROUPS:
        pages: list[Page] = []
        for step in steps:
            step_n, src_file, zh, en, subtitle, kpis = rows_by_step[step]
            pages.append(Page(
                slug=f'step{step:02d}',
                url=f'/network/step{step:02d}/',
                track='network',
                title_zh=zh,
                title_en=en,
                kind='png',
                src=f'../../../../complex_network_images/{src_file}',
                phase=key,
                step=step_n,
                kpis=kpis,
                subtitle_zh=subtitle,
            ))
        phases.append(Phase(key, title_zh, title_en, pages))

    # Prepend a Dashboards phase with the global network time-series page
    dash_pages = [Page(
        slug='evolution',
        url='/network/evolution/',
        track='network',
        title_zh='时序演化',
        title_en='Network Time-Series',
        kind='plotly',
        src='../../../../complex_network_images/evolution.html',
        phase='dashboards',
        kpis=['10 季度', '10 指标'],
    )]
    phases.insert(0, Phase('dashboards', '综合仪表板', 'Dashboards', dash_pages))

    return Track(
        slug='network',
        title_zh='全球复杂网络分析',
        title_en='Global Complex-Network Analysis',
        tagline_zh='把互联网视为 BGP × DNS × 物理 × 组织 四层多重网络的全栈拓扑体检',
        tagline_en='The Internet as a four-layer multiplex — a full-stack complex-network audit.',
        accent='#30d158',
        phases=phases,
        hub_url='/network/',
    )


# --- Globe (3D AS interconnect) track -----------------------------------

GLOBE_VIEWS: list[tuple[str, str, str, str, str, list[str]]] = [
    ('strata', 'as_strata.html', '分层占比图', 'AS Strata · Country Canopy',
     '扇区面积=占比 · 柱高=国家 IPv4 · 丝带粗细=对等量',
     ['94 国扇区', '1.8K 对等丝带', 'Three.js']),
    ('globe', 'as_globe.html', '地球视图', 'Geographic Globe',
     'globe.gl · 真实坐标 + 国家质心抖动 + 对等弧',
     ['5,000 AS', '地理坐标', 'globe.gl']),
    ('force', 'as_force.html', '拓扑力图', 'Force Topology',
     '3d-force-graph · 力导布局暴露对等社群',
     ['5,000 AS', '拓扑布局', '3d-force-graph']),
]


def _build_globe_track() -> Track:
    pages: list[Page] = []
    for slug, src_file, title_zh, title_en, subtitle_zh, kpis in GLOBE_VIEWS:
        pages.append(Page(
            slug=slug,
            url=f'/globe/{slug}/',
            track='globe',
            title_zh=title_zh,
            title_en=title_en,
            kind='plotly',  # reuses step_plotly.html iframe wrapper
            src=f'../../../../as_globe/html/{src_file}',
            phase='views',
            kpis=kpis,
            subtitle_zh=subtitle_zh,
        ))
    return Track(
        slug='globe',
        title_zh='全球 AS 互联立体图',
        title_en='Global AS Interconnect · 3D',
        tagline_zh='把 5,000 头部 AS 与其对等关系搬到三维地球与拓扑空间，一眼看全球互联架构',
        tagline_en='Top 5K ASes × WebGL 3D — geographic globe + force topology, region-colored, IPv4-sized.',
        accent='#5E5CE6',
        phases=[Phase('views', '三维视图', '3D Views', pages)],
        hub_url='/globe/',
    )


# --- Unified structure --------------------------------------------------

def build_site_model() -> dict:
    china = _build_china_track()
    countries = _build_countries_track()
    network = _build_network_track()
    globe = _build_globe_track()
    tracks = [china, countries, network, globe]

    flat: list[Page] = []
    for t in tracks:
        flat.extend(t.all_pages())

    prev_next: dict[str, tuple[Page | None, Page | None]] = {}
    for idx, page in enumerate(flat):
        prev_p = flat[idx - 1] if idx > 0 else None
        next_p = flat[idx + 1] if idx < len(flat) - 1 else None
        prev_next[page.url] = (prev_p, next_p)

    # Sovereignty leaderboard for home-page footer
    leaderboard: list[dict] = []
    for cc, zh, en in COUNTRY_NAMES:
        sov_now = _country_sov(cc, SNAPSHOT_LATEST)
        sov_prev = _country_sov(cc, SNAPSHOT_PREV)
        sov_base = _country_sov(cc, SNAPSHOT_BASELINE)
        if sov_now is None:
            continue
        leaderboard.append({
            'cc': cc,
            'zh': zh,
            'en': en,
            'sov_now': sov_now,
            'sov_prev': sov_prev,
            'sov_base': sov_base,
            'delta': (sov_now - sov_prev) if sov_prev is not None else None,
            'delta_baseline': (sov_now - sov_base) if sov_base is not None else None,
            'url': f'/countries/{cc}/',
        })
    leaderboard.sort(key=lambda r: r['sov_now'], reverse=True)

    return {
        'tracks': {t.slug: t for t in tracks},
        'tracks_list': tracks,
        'flat_pages': flat,
        'prev_next': prev_next,
        'leaderboard': leaderboard,
        'snapshot_latest': SNAPSHOT_LATEST,
        'snapshot_prev': SNAPSHOT_PREV,
        'snapshot_baseline': SNAPSHOT_BASELINE,
        'snapshots_all': SNAPSHOTS_ALL,
        'totals': {
            'china_steps': len({p.step for p in china.all_pages()}),
            'china_pages': len(china.all_pages()),
            'countries_profiles': len([p for p in countries.all_pages() if p.phase == 'profiles']),
            'countries_dashboards': len([p for p in countries.all_pages() if p.phase == 'dashboards']),
            'network_steps': len(network.all_pages()),
            'globe_views': len(globe.all_pages()),
            'all_pages': len(flat),
        },
    }


def iter_pages(tracks: Iterable[Track]) -> Iterable[Page]:
    for t in tracks:
        for p in t.all_pages():
            yield p


if __name__ == '__main__':
    model = build_site_model()
    print('Tracks:')
    for t in model['tracks_list']:
        print(f'  · {t.slug}: {len(t.all_pages())} pages across {len(t.phases)} phase(s)')
    print(f"Total flat pages: {model['totals']['all_pages']}")
    print('Leaderboard:')
    for row in model['leaderboard']:
        delta = row['delta']
        delta_s = f"{delta:+.3f}" if delta is not None else '—'
        print(f"  {row['cc']}  sov={row['sov_now']:.3f}  Δ{delta_s}")
