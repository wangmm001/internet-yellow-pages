"""analysis/china/build_site.py

Post-process analysis/china/html/*.html into a modern static site.

What it does:
  1. Parses each of the 20 existing step HTMLs (Plotly multi-chart or Pyvis single-network).
  2. Extracts Plotly.js bundle once, writes to html/plotly.min.js so all pages share it.
  3. Rebuilds every step HTML using a new template (chart-card + <dialog> caption).
  4. Splits over-stuffed steps into ≤3-chart sub-pages (step03/04/11/20).
  5. Regenerates html/index.html as a professional navigation hub.
  6. Copies site_assets/site.css + site.js into html/.

Idempotent: overwrites html/ in place. Before the first run it snapshots the
directory as html_legacy_YYYYMMDD.tar.gz for safety.

Usage:
  python3 -m analysis.china.build_site
  python3 -m analysis.china.build_site --no-backup   (skip tarball)
"""
from __future__ import annotations

import argparse
import datetime
import html as _html
import json
import os
import re
import shutil
import sys
import tarfile
from pathlib import Path

BASE = Path(__file__).resolve().parent          # analysis/china/
HTML_DIR = BASE / 'html'
DATA_DIR = BASE / 'data'
ASSETS = BASE / 'site_assets'

# ─── step inventory ─────────────────────────────────────────────────────────

STEP_FILES = {
    1:  'step01_scope.html',
    2:  'step02_top_as.html',
    3:  'step03_global_ranks.html',
    4:  'step04_prefixes.html',
    5:  'step05_peering_graph.html',
    6:  'step06_centrality.html',
    7:  'step07_kcore.html',
    8:  'step08_depends_on_world.html',
    9:  'step09_dependents.html',
    10: 'step10_concentration.html',
    11: 'step11_ixp_landscape.html',
    12: 'step12_facilities.html',
    13: 'step13_ixp_fac_bridge.html',
    14: 'step14_dns_hosting.html',
    15: 'step15_dns_authority.html',
    16: 'step16_cname_chains.html',
    17: 'step17_rankings.html',
    18: 'step18_censorship.html',
    19: 'step19_atlas.html',
    20: 'step20_synthesis.html',
}

PYVIS_STEPS = {5, 9, 13, 16}

PHASES = [
    ('A', '范围与身份',           'Scope & Identity',                     [1, 2, 3]),
    ('B', 'BGP 拓扑位置',         'BGP Topology',                         [4, 5, 6, 7]),
    ('C', '依赖与 Hegemony',      'Dependency & Hegemony',                [8, 9, 10]),
    ('D', '物理基础设施',         'Physical Infrastructure',              [11, 12, 13]),
    ('E', 'DNS / 内容 / 排名',    'DNS · Content · Ranking',              [14, 15, 16, 17]),
    ('F', '安全 / 测量 / 综合',   'Security · Measurement · Synthesis',   [18, 19, 20]),
]

STEP_TITLES = {
    1:  ('中国自治系统清册',      'AS Inventory & Scope'),
    2:  ('头部自治系统身份档案',  'Top-20 Chinese ASes · Identity'),
    3:  ('全球规模排名',          'China vs World at a Glance'),
    4:  ('BGP 前缀与 RPKI',       'CN BGP Prefix Footprint'),
    5:  ('对等互联子图',          'CN AS Peering Subgraph'),
    6:  ('全球中心性位置',        'CN in Global Centrality'),
    7:  ('k-core 层级位置',       'CN in Global k-Core'),
    8:  ('出向 Hegemony',         'Who Does China Depend On'),
    9:  ('入向 Hegemony',         'Who Depends on China'),
    10: ('集中度与 HHI',          'China Concentration & HHI'),
    11: ('IXP 互联生态',          'Chinese IXP Landscape'),
    12: ('机房部署',              'CN AS Facility Co-location'),
    13: ('IXP × 机房三部图',      'IXP + Facility Tripartite'),
    14: ('DNS 托管版图',          'CN DNS Hosting Footprint'),
    15: ('.cn DNS 主权',          '.cn DNS Sovereignty'),
    16: ('CNAME 跨境链',          'Cross-Border CNAME Chains'),
    17: ('多排名位置',            'CN in Global Rankings'),
    18: ('审查拓扑',              'Censorship Topology in CN'),
    19: ('Atlas 观测点',          'RIPE Atlas Presence in CN'),
    20: ('综合仪表板',            'Synthesis Dashboard'),
}

# per-step KPI strip rendered in the step hero (and as preview on index cards)
STEP_KPIS = {
    1:  [('6,660', 'CN 大陆 AS'),    ('1,468', 'HK AS'),       ('474', 'TW AS')],
    2:  [('#1 电信', '骨干'),         ('47,744', '前 20 前缀数'),('44%', '占全国前缀')],
    3:  [('#3', 'AS 数排名'),         ('#3', '前缀排名'),        ('#16', 'IXP 排名')],
    4:  [('109,409', '中国总前缀'),   ('v4 主导', '双栈率低'),   ('中等', 'RPKI 覆盖')],
    5:  [('400', '子图节点'),         ('2,450', '对等互联边'),   ('77', '外部国家数')],
    6:  [('Top 1%', '度数'),          ('Top 2%', 'PageRank'),    ('弱于规模', '中心性')],
    7:  [('k-core', '分层结构'),      ('少数 CN', '入深核'),     ('依附 Tier-1', '')],
    8:  [('70%+', '出向依赖境外'),    ('US 第一', '上游国家'),   ('低自持', '')],
    9:  [('有限', '外国依赖 CN'),     ('区域性', '主要影响圈'),  ('', '')],
    10: [('高', 'HHI 集中度'),        ('偏不均衡', 'Gini'),      ('头部少数', '主导')],
    11: [('#16', 'IXP 排名'),         ('密度低', '本地互联'),    ('多通过境外', '')],
    12: [('#33', '机房排名'),         ('重心境外', 'CN AS 部署'),('托管美欧', '')],
    13: [('三部图', 'IXP×Fac×AS'),    ('中介枢纽', 'HK 为主'),   ('', '')],
    14: [('高外包', 'DNS 托管'),      ('Cloud 主导', '市场结构'),('', '')],
    15: [('低', '.cn 境外权威'),      ('自持高', '国家域'),      ('', '')],
    16: [('跨境链', 'CNAME 桥接'),    ('外部 CDN', '大量使用'),  ('', '')],
    17: [('Tranco/CrUX', '多榜单'),   ('CN 头部入榜', '前列'),    ('', '')],
    18: [('审查拓扑', 'OONI / GFW'),  ('特征与非审查', '有别'),   ('', '')],
    19: [('少量', 'CN Atlas 探针'),   ('测量盲区', '多'),         ('', '')],
    20: [('0.256', '主权指数'),       ('全球第 9', '九国对比'),   ('五大维度', '综合')],
}

# Chart plain-language titles keyed by step → [{plain, sub, part}]
# Order matches the existing <h3> subtitle order in each HTML.
CHART_META = {
    1: [
        {'plain': '中国区都有哪些“互联网行政区”？',    'sub': '① 中国区 AS 分层 · Sunburst',        'part': 1},
        {'plain': '大陆 / 香港 / 台湾 / 澳门各有多少 AS？',  'sub': '② 区域 AS 规模对比 · Bar',       'part': 1},
        {'plain': '这些 AS 各自在经营什么业务？',       'sub': '③ 区域 × 标签类别 · Table',           'part': 1},
    ],
    2: [
        {'plain': '谁是中国互联网真正的“国家队”？',     'sub': '① Top-20 身份表 · Identity',          'part': 1},
        {'plain': '前 20 家呈现怎样的“头部集中”？',     'sub': '② 前缀数排名 · Log-scale Bar',        'part': 1},
    ],
    3: [
        {'plain': '全球每个国家有多少 AS？',            'sub': '① 世界地图 · AS Count by Country',    'part': 1},
        {'plain': 'AS 数量最多的 15 个国家是谁？',       'sub': '② Top-15 · AS Count',                 'part': 1},
        {'plain': '全球每个国家拥有多少 BGP 前缀？',    'sub': '③ 世界地图 · BGP Prefixes',           'part': 2},
        {'plain': '前缀数 Top-15 的国家排行',           'sub': '④ Top-15 · BGP Prefixes',             'part': 2},
        {'plain': '全球每个国家有多少 IXP？',           'sub': '⑤ 世界地图 · IXP Count',              'part': 3},
        {'plain': 'IXP 数 Top-15 的国家排行',           'sub': '⑥ Top-15 · IXP Count',                'part': 3},
        {'plain': '全球每个国家有多少数据中心/机房？',   'sub': '⑦ 世界地图 · Facility Count',        'part': 4},
        {'plain': '机房数 Top-15 的国家排行',           'sub': '⑧ Top-15 · Facility Count',           'part': 4},
    ],
    4: [
        {'plain': '中国前 20 大 AS 各控制多少 IP 地址？','sub': '① 起源前缀 · Treemap',                'part': 1},
        {'plain': 'IPv4 与 IPv6 前缀如何分配？',          'sub': '② v4 vs v6 Split · Log-scale',       'part': 1},
        {'plain': '中国 AS 的 RPKI 数字签名覆盖率多高？','sub': '③ RPKI ROA 覆盖',                     'part': 2},
        {'plain': '中国 AS 使用多少 Anycast 前缀？',     'sub': '④ Anycast 前缀比例',                  'part': 2},
    ],
    5: [
        {'plain': '中国前 30 大 AS 彼此是如何互联的？',  'sub': '对等互联子图 · 400 节点 · 2,450 条边', 'part': 1},
    ],
    6: [
        {'plain': '中国 AS 在全球中心性榜上处于什么位置？','sub': '① 四维中心性散点矩阵',             'part': 1},
        {'plain': '“度数大”与“影响力大”是同一回事吗？',    'sub': '② Degree × PageRank 散点',         'part': 1},
        {'plain': '中国 Top-30 AS 的全球 PageRank 排名',  'sub': '③ CN Top-30 PageRank 排名',         'part': 1},
    ],
    7: [
        {'plain': '各区域 AS 的 k-core 层级分布',         'sub': '① 各区域 coreness 分布',             'part': 1},
        {'plain': '哪些中国 AS 进入了全球深层核心？',    'sub': '② CN 进入深层核心 AS 列表',          'part': 1},
        {'plain': 'k-core 层级与度数之间的关系是什么？',  'sub': '③ Coreness × Degree',                'part': 1},
    ],
    8: [
        {'plain': '中国 AS 主要依赖哪些境外运营商？',     'sub': '① CN→Foreign Sankey (top-20×top-15)', 'part': 1},
        {'plain': '外部上游依赖度排行榜',                'sub': '② 外部上游 Hegemony 排名',           'part': 1},
        {'plain': '中国的依赖流向了哪些国家？',           'sub': '③ 目的国家聚合分布',                 'part': 1},
    ],
    9: [
        {'plain': '哪些外国 AS 反过来依赖中国 AS？',      'sub': '入向依赖子图 · Network',             'part': 1},
    ],
    10: [
        {'plain': '资源分布的“贫富差距”有多悬殊？',      'sub': '① Lorenz 曲线 · 4 维度',              'part': 1},
        {'plain': 'HHI 集中度指数对比',                  'sub': '② HHI 对比 · CN vs World',           'part': 1},
        {'plain': 'Gini 系数对比',                       'sub': '③ Gini 系数对比 · CN vs World',       'part': 1},
    ],
    11: [
        {'plain': '中国 AS 的 IXP 会员遍布全球哪里？',    'sub': '① CN 会员全球分布',                  'part': 1},
        {'plain': '哪些 IXP 吸引最多中国 AS？',          'sub': '② Top-25 IXP · CN 会员数',           'part': 1},
        {'plain': '境内 IXP 排行榜',                     'sub': '③ 境内 IXP 榜',                       'part': 2},
        {'plain': '中国 AS 在境内 vs 境外 IXP 如何分布？','sub': '④ 境内 vs 境外 分布',                 'part': 2},
    ],
    12: [
        {'plain': '中国 AS 的机房部署分布在哪些国家？',   'sub': '① 国家 → 机房 Treemap',              'part': 1},
        {'plain': '各机房运营商的部署热力图',             'sub': '② 机房部署热力图',                    'part': 1},
        {'plain': '中国 AS 占位最多的 Top-20 机房',       'sub': '③ Top-20 机房',                       'part': 1},
    ],
    13: [
        {'plain': 'IXP × 机房 × AS 三者如何连成一体？',   'sub': '三部图 · IXP+Facility+AS',           'part': 1},
    ],
    14: [
        {'plain': '全球 DNS 托管的全景分布',             'sub': '① 全球托管 Sunburst',                 'part': 1},
        {'plain': '托管中国域名的 Top-20 AS',             'sub': '② Top-20 CN 托管 AS',                 'part': 1},
        {'plain': '云厂商 vs 传统 ISP 的托管份额对比',    'sub': '③ Cloud vs ISP 分布',                'part': 1},
    ],
    15: [
        {'plain': '.cn 域名权威 DNS 由谁提供？',           'sub': '① Top-20 .cn 权威 NS 提供商',        'part': 1},
        {'plain': '提供商 → 国家 的权威 DNS 桥接关系',     'sub': '② 提供商 → 国家 Sankey',             'part': 1},
        {'plain': '.cn 权威 DNS 的国籍占比',                'sub': '③ 国籍占比',                         'part': 1},
    ],
    16: [
        {'plain': '.cn 域名的 CNAME 链跨境指向谁？',       'sub': 'CNAME 跨境链路图',                   'part': 1},
    ],
    17: [
        {'plain': '中国 AS 在 Tranco / CAIDA / APNIC 等多榜单上的位置', 'sub': '① 多排名平行坐标图', 'part': 1},
        {'plain': '中国 AS 的排名数分布（对数轴）',         'sub': '② CN AS 排名分布 · Log',            'part': 1},
        {'plain': '中国 Top-20 AS 在主榜单的位置',           'sub': '③ Top-20 CN in primary ranking',   'part': 1},
    ],
    18: [
        {'plain': 'AS 与审查测试的关联热图',                'sub': '① AS × 测试 热图',                   'part': 1},
        {'plain': '审查 / 非审查 / 全球网络的拓扑差异',    'sub': '② 拓扑特征对比',                      'part': 1},
        {'plain': '审查测试按类型如何分布？',                'sub': '③ 测试类型分布',                     'part': 1},
    ],
    19: [
        {'plain': 'RIPE Atlas 探针在中国的地理分布',        'sub': '① CN 探针地理分布',                  'part': 1},
        {'plain': '全球 Atlas 探针数 Top-20 国家（中国高亮）','sub': '② Top-20 国家 · CN 突出',          'part': 1},
        {'plain': 'Atlas 主动测量中命中的中国目标',         'sub': '③ Atlas 测量的 CN 目标',              'part': 1},
    ],
    20: [
        {'plain': '① 规模与全球排名',                       'sub': '综合面板 · Scale & Ranking',        'part': 1},
        {'plain': '② 拓扑位置与对等互联伙伴',                'sub': '综合面板 · Topology & Peers',       'part': 1},
        {'plain': '③ 依赖与 Hegemony 占比',                 'sub': '综合面板 · Dependency & Hegemony',  'part': 1},
        {'plain': '④ 资源集中度 (HHI / Gini)',               'sub': '综合面板 · Concentration',          'part': 2},
        {'plain': '⑤ 物理基础设施 (IXP / 机房)',             'sub': '综合面板 · Physical Infrastructure','part': 2},
        {'plain': '⑥ DNS / 内容 / 排名',                     'sub': '综合面板 · DNS · Content',          'part': 2},
        {'plain': '⑦ 审查与可观测性',                        'sub': '综合面板 · Censorship & Measurement','part': 3},
        {'plain': '⑧ 中国互联网主权综合指数',                 'sub': '综合面板 · Sovereignty Index',      'part': 3},
    ],
}

# Part labels used in the part-tab switcher for split steps
PART_LABELS = {
    3:  [('AS 数量',       'AS Count'),
         ('BGP 前缀',      'BGP Prefixes'),
         ('IXP 数量',      'IXP Count'),
         ('机房数量',      'Facility Count')],
    4:  [('前缀构成',      'Prefix Composition'),
         ('安全与广播',    'Security & Anycast')],
    11: [('会员地理',      'Member Geography'),
         ('境内 vs 境外',   'Domestic vs Overseas')],
    20: [('规模与拓扑',    'Scale & Topology'),
         ('集中度与基础设施', 'Concentration & Infra'),
         ('主权综合',      'Sovereignty')],
}

# Steps that split: {step_num: num_parts}
SPLIT_STEPS = {s: len({c['part'] for c in CHART_META[s]}) for s in CHART_META}
SPLIT_STEPS = {s: p for s, p in SPLIT_STEPS.items() if p > 1}   # only those with >1 part

# ─── parsing helpers ────────────────────────────────────────────────────────

SUBTITLE_RE  = re.compile(r'<h3 style="color:#E6EDF3;margin:24px 0 6px 0">([^<]+)</h3>')
CAPTION_RE   = re.compile(r'<div class="chart-caption">(.+?)</div>', re.DOTALL)
CHART_BLK_RE = re.compile(
    r'<div id="([a-f0-9-]+)" class="plotly-graph-div"[^>]*></div>\s*'
    r'<script[^>]*>(.+?)</script>',
    re.DOTALL,
)
PLOTLY_JS_RE = re.compile(
    r'<script>\s*(/\*\*\s*\n\*\s*plotly\.js\s+v.*?)</script>',
    re.DOTALL,
)


def parse_plotly_html(text: str) -> dict:
    """Return {'type': 'plotly', 'charts': [...], 'plotly_js': str|None}."""
    subs = SUBTITLE_RE.findall(text)
    caps = CAPTION_RE.findall(text)
    blocks = CHART_BLK_RE.findall(text)
    if not (len(subs) == len(caps) == len(blocks)):
        raise RuntimeError(
            f'chart-block mismatch: subtitles={len(subs)}, captions={len(caps)}, '
            f'chart blocks={len(blocks)}'
        )
    charts = []
    for sub, cap, (cid, cscript) in zip(subs, caps, blocks):
        charts.append({
            'subtitle': sub,
            'chart_id': cid,
            'chart_script': cscript,
            'caption_html': cap,
        })
    pjs = PLOTLY_JS_RE.search(text)
    return {'type': 'plotly', 'charts': charts, 'plotly_js': pjs.group(1) if pjs else None}


def parse_pyvis_html(text: str) -> dict:
    cap_m = CAPTION_RE.search(text)
    caption = cap_m.group(1) if cap_m else ''
    # head extras we want to preserve (vis-network CSS + JS, bootstrap CSS)
    head_m = re.search(r'<head>(.*?)</head>', text, re.DOTALL)
    head_inner = head_m.group(1) if head_m else ''
    extras = []
    for m in re.finditer(r'<link[^>]*(?:vis-network|bootstrap)[^>]*/?>', head_inner):
        extras.append(m.group(0))
    for m in re.finditer(r'<script[^>]*(?:vis-network|bootstrap)[^>]*></script>', head_inner):
        extras.append(m.group(0))
    # pyvis local bindings reference
    if 'lib/bindings/utils.js' in head_inner:
        extras.append('<script src="lib/bindings/utils.js"></script>')
    # grab the <style> that sets #mynetwork dimensions
    sty_m = re.search(r'<style[^>]*>\s*#mynetwork\s*\{.*?</style>', head_inner, re.DOTALL)
    if sty_m:
        extras.append(sty_m.group(0))

    # body content between <div class="content"> and the <div class="chart-caption">
    body_m = re.search(r'<div class="content">(.*?)<div class="chart-caption">', text, re.DOTALL)
    content = body_m.group(1) if body_m else ''
    # strip legacy sidebar-note (writeup) — captions carry the explanation now
    content = re.sub(r'<div class="sidebar-note">.*?</div>', '', content, flags=re.DOTALL)
    return {
        'type': 'pyvis',
        'caption_html': caption,
        'head_extras': '\n'.join(extras),
        'body_content': content.strip(),
    }


def parse_step(step: int) -> dict:
    path = HTML_DIR / STEP_FILES[step]
    if not path.exists():
        raise FileNotFoundError(path)
    text = path.read_text(encoding='utf-8')
    if step in PYVIS_STEPS:
        return parse_pyvis_html(text)
    return parse_plotly_html(text)


# ─── metrics loader ─────────────────────────────────────────────────────────

def load_metrics() -> dict:
    out = {}
    for step in range(1, 21):
        p = DATA_DIR / f'step{step:02d}_metrics.json'
        if p.exists():
            try:
                out[step] = json.loads(p.read_text(encoding='utf-8'))
            except Exception as e:
                print(f'[warn] failed to parse {p}: {e}')
                out[step] = {}
        else:
            out[step] = {}
    return out


# ─── output file-name helpers ───────────────────────────────────────────────

def step_page_name(step: int, part: int = 1, total_parts: int = 1) -> str:
    if total_parts > 1:
        return f'step{step:02d}_part{part}.html'
    return STEP_FILES[step]


def step_parts_count(step: int) -> int:
    return SPLIT_STEPS.get(step, 1)


def iter_site_pages():
    """Yield (step, part_idx, total_parts) in global linear order."""
    for step in range(1, 21):
        n = step_parts_count(step)
        for p in range(1, n + 1):
            yield step, p, n


def build_nav_order():
    """Return list of tuples (filename, step, part, total_parts, step_title_zh, plain_ids_on_page)."""
    out = []
    for step, part, total in iter_site_pages():
        fname = step_page_name(step, part, total)
        title_zh, _ = STEP_TITLES[step]
        out.append((fname, step, part, total, title_zh))
    return out


# ─── HTML template helpers ──────────────────────────────────────────────────

def esc(s: str) -> str:
    return _html.escape(s, quote=True)


ICON_CAP = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
ICON_LINK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>'
ICON_CLOSE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>'
ICON_SEARCH = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>'
ICON_SUN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>'
ICON_HOME = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9.5L12 2l9 7.5V21a1 1 0 0 1-1 1h-5v-7h-6v7H4a1 1 0 0 1-1-1z"/></svg>'
ICON_ARROW_LEFT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>'
ICON_ARROW_RIGHT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>'


def render_top_nav(current_step: int | None) -> str:
    tabs = []
    for letter, zh, en, steps in PHASES:
        active = ''
        if current_step is not None and current_step in steps:
            active = ' active'
        href = f'index.html#phase-{letter}'
        tabs.append(f'<a class="nav-tab{active}" href="{href}">{esc(letter)} · {esc(zh)}</a>')
    return f'''<header class="top-nav">
  <a class="nav-brand" href="index.html">
    <span class="logo">中</span>
    <span>
      <div class="brand-title">CN in Global Internet</div>
      <div class="brand-sub">中国互联网全球位置 · 20-Step IYP Analysis</div>
    </span>
  </a>
  <span class="nav-spacer"></span>
  <nav class="nav-tabs">{''.join(tabs)}</nav>
  <div class="nav-actions">
    <button class="icon-btn" data-action="toggle-theme" aria-label="切换主题 / Toggle theme" title="切换主题 · toggle theme">{ICON_SUN}</button>
    <a class="icon-btn" href="index.html" aria-label="返回首页 / Home" title="首页 · home">{ICON_HOME}</a>
  </div>
</header>'''


def render_side_toc(current_step: int, current_part: int | None) -> str:
    """Side TOC with phases + steps, highlighting current step."""
    groups = []
    for letter, zh, en, steps in PHASES:
        items = []
        for s in steps:
            n = step_parts_count(s)
            href = step_page_name(s, 1, n)
            cur = 'true' if s == current_step else 'false'
            title_zh, title_en = STEP_TITLES[s]
            parts_badge = f' <span style="font-size:10px;color:#8B949E;">×{n}</span>' if n > 1 else ''
            items.append(
                f'<li><a href="{href}" data-current="{cur}"><span class="sn">{s:02d}</span>'
                f'<span>{esc(title_zh)}{parts_badge}</span></a></li>'
            )
        groups.append(
            f'<h4>{esc(letter)} · {esc(zh)}</h4><ul>{"".join(items)}</ul>'
        )
    return f'<aside class="side-toc">{"".join(groups)}</aside>'


def render_breadcrumb(step: int, part: int, total_parts: int) -> str:
    # Phase
    phase_info = next((p for p in PHASES if step in p[3]), None)
    if phase_info:
        letter, zh_p, _, _ = phase_info
        phase_crumb = f'<a href="index.html#phase-{letter}">{esc(letter)} · {esc(zh_p)}</a>'
    else:
        phase_crumb = ''
    step_zh, _ = STEP_TITLES[step]
    part_crumb = ''
    if total_parts > 1:
        part_name = PART_LABELS.get(step, [(f'Part {i+1}', '') for i in range(total_parts)])[part - 1][0]
        part_crumb = f'<span class="sep">›</span><span class="current">Part {part} · {esc(part_name)}</span>'
        step_crumb = f'<span>Step {step:02d} · {esc(step_zh)}</span>'
    else:
        step_crumb = f'<span class="current">Step {step:02d} · {esc(step_zh)}</span>'
    return (f'<nav class="breadcrumb"><a href="index.html">首页 Home</a>'
            f'<span class="sep">›</span>{phase_crumb}'
            f'<span class="sep">›</span>{step_crumb}{part_crumb}</nav>')


def render_step_hero(step: int, part: int, total_parts: int, metrics_payload: dict) -> str:
    title_zh, title_en = STEP_TITLES[step]
    suffix = ''
    if total_parts > 1:
        part_zh, part_en = PART_LABELS.get(step, [('', '')] * total_parts)[part - 1]
        suffix = f' · Part {part}: {esc(part_zh)}'
    kpis_html = ''
    for val, key in STEP_KPIS.get(step, []):
        if not val and not key:
            continue
        kpis_html += f'<div class="kpi"><div class="v">{esc(val)}</div><div class="k">{esc(key)}</div></div>'
    # Phase badge
    phase_info = next((p for p in PHASES if step in p[3]), None)
    eyebrow = ''
    if phase_info:
        letter, zh_p, en_p, _ = phase_info
        eyebrow = f'<div class="eyebrow">Phase {letter} · {esc(zh_p)}</div>'
    return f'''<section class="step-hero">
  {eyebrow}
  <h1>Step {step:02d} · {esc(title_zh)}{suffix}</h1>
  <p class="en-sub">{esc(title_en)}</p>
  <div class="kpi-strip">{kpis_html}</div>
</section>'''


def render_part_tabs(step: int, active_part: int, total_parts: int) -> str:
    if total_parts <= 1:
        return ''
    tabs = []
    labels = PART_LABELS.get(step, [(f'Part {i+1}', '') for i in range(total_parts)])
    for i in range(1, total_parts + 1):
        zh, en = labels[i - 1]
        href = step_page_name(step, i, total_parts)
        cls = 'part-tab active' if i == active_part else 'part-tab'
        tabs.append(f'<a class="{cls}" href="{href}"><span class="pn">{i:02d}</span><span>{esc(zh)}</span></a>')
    return f'<div class="part-tabs">{"".join(tabs)}</div>'


def render_chart_card(step: int, chart_idx: int, chart: dict, chart_meta: dict, page_slug: str) -> str:
    """Render one chart-card with title/subtitle/plotly-div/caption-dialog."""
    anchor = f'chart-{chart_idx + 1}'
    cap_id = f'cap-{step:02d}-{chart_idx + 1}'
    plain = chart_meta.get('plain', f'图 {chart_idx + 1}')
    sub = chart_meta.get('sub', chart.get('subtitle', ''))
    cap_html = chart['caption_html']
    # The caption prefix contains a redundant "图解" <span class="label">...</span> from add_captions.py;
    # dialog's own header already carries the label, so we strip it.
    cap_body = re.sub(r'<span class="label">[^<]*</span>', '', cap_html).strip()
    chart_html = (
        f'<div id="{esc(chart["chart_id"])}" class="plotly-graph-div" '
        f'style="height:560px; width:100%;"></div>'
        f'<script>{chart["chart_script"]}</script>'
    )
    return f'''<article class="chart-card" id="{anchor}">
  <header class="chart-head">
    <h2 class="plain-title">{esc(plain)}</h2>
    <p class="analyst-sub">{esc(sub)}</p>
    <div class="chart-meta">
      <button class="copy-btn" data-target="{anchor}" title="复制图表链接" aria-label="Copy chart link">{ICON_LINK}</button>
      <button class="cap-btn" data-cap="{cap_id}" aria-controls="{cap_id}">{ICON_CAP}<span>图解</span></button>
    </div>
  </header>
  <div class="chart-mount">{chart_html}</div>
  <dialog id="{cap_id}" class="cap-dialog" aria-labelledby="{cap_id}-t">
    <header class="cap-head">
      <span class="cap-label">图解</span>
      <span class="cap-title" id="{cap_id}-t">{esc(plain)}</span>
      <button class="cap-close" aria-label="关闭 / close">{ICON_CLOSE}</button>
    </header>
    <div class="cap-body">{cap_body}</div>
  </dialog>
</article>'''


def render_pyvis_card(step: int, parsed: dict, chart_meta: dict) -> str:
    cap_id = f'cap-{step:02d}-1'
    plain = chart_meta['plain']
    sub = chart_meta['sub']
    cap_body = re.sub(r'<span class="label">[^<]*</span>', '', parsed['caption_html']).strip()
    return f'''<article class="chart-card" id="chart-1">
  <header class="chart-head">
    <h2 class="plain-title">{esc(plain)}</h2>
    <p class="analyst-sub">{esc(sub)}</p>
    <div class="chart-meta">
      <button class="copy-btn" data-target="chart-1" title="复制图表链接" aria-label="Copy chart link">{ICON_LINK}</button>
      <button class="cap-btn" data-cap="{cap_id}" aria-controls="{cap_id}">{ICON_CAP}<span>图解</span></button>
    </div>
  </header>
  <div class="chart-mount pyvis-mount">{parsed['body_content']}</div>
  <dialog id="{cap_id}" class="cap-dialog" aria-labelledby="{cap_id}-t">
    <header class="cap-head">
      <span class="cap-label">图解</span>
      <span class="cap-title" id="{cap_id}-t">{esc(plain)}</span>
      <button class="cap-close" aria-label="关闭 / close">{ICON_CLOSE}</button>
    </header>
    <div class="cap-body">{cap_body}</div>
  </dialog>
</article>'''


def render_step_foot(cur_idx: int, nav_order: list) -> str:
    def cell(label, side):
        return f'''<a class="{side} disabled"><span class="label">{label}</span></a>'''
    prev = ''
    nxt = ''
    if cur_idx == 0:
        prev = cell('已是首页', 'prev')
    else:
        f, s, p, t, title = nav_order[cur_idx - 1]
        part_suf = f' · Part {p}' if t > 1 else ''
        prev = (f'<a class="prev" href="{f}"><span class="label">← 上一步</span>'
                f'<span class="title">Step {s:02d} · {esc(title)}{esc(part_suf)}</span></a>')
    if cur_idx == len(nav_order) - 1:
        nxt = cell('已到末页', 'next')
    else:
        f, s, p, t, title = nav_order[cur_idx + 1]
        part_suf = f' · Part {p}' if t > 1 else ''
        nxt = (f'<a class="next" href="{f}"><span class="label">下一步 →</span>'
               f'<span class="title">Step {s:02d} · {esc(title)}{esc(part_suf)}</span></a>')
    return f'<footer class="step-foot">{prev}{nxt}</footer>'


def render_step_page(step: int, part: int, total_parts: int,
                     parsed: dict, nav_order: list, cur_idx: int,
                     metrics_payload: dict, is_first_plotly_page: bool) -> str:
    title_zh, title_en = STEP_TITLES[step]
    part_suffix = ''
    if total_parts > 1:
        part_zh, _ = PART_LABELS.get(step, [('', '')] * total_parts)[part - 1]
        part_suffix = f' · Part {part}: {part_zh}'
    page_title = f'Step {step:02d} · {title_zh}{part_suffix} · 中国互联网全球位置'

    # For pyvis pages, embed extras; plotly pages share plotly.min.js
    head_extras = ''
    chart_section = ''

    if parsed['type'] == 'pyvis':
        # pyvis: use the parsed head extras (vis-network CDN)
        head_extras = parsed['head_extras']
        chart_section = render_pyvis_card(step, parsed, CHART_META[step][0])
    else:
        # plotly: determine which charts belong to THIS part
        charts_on_page = []
        for i, meta in enumerate(CHART_META[step]):
            if meta['part'] == part:
                charts_on_page.append((i, meta, parsed['charts'][i]))
        cards = []
        for idx, meta, ch in charts_on_page:
            cards.append(render_chart_card(step, idx, ch, meta, step_page_name(step, part, total_parts)))
        chart_section = '\n'.join(cards)
        # Plotly config shim (small, safe to include on each page)
        head_extras = '<script>window.PlotlyConfig = {MathJaxConfig: "local"};</script>'
        head_extras += '<script src="plotly.min.js"></script>'

    breadcrumb = render_breadcrumb(step, part, total_parts)
    hero = render_step_hero(step, part, total_parts, metrics_payload)
    part_tabs = render_part_tabs(step, part, total_parts)
    side_toc = render_side_toc(step, part)
    top_nav = render_top_nav(step)
    step_foot = render_step_foot(cur_idx, nav_order)

    return f'''<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(page_title)}</title>
<link rel="stylesheet" href="site.css">
{head_extras}
</head>
<body>
{top_nav}
<div class="shell">
{side_toc}
<main class="step-page">
{breadcrumb}
{hero}
{part_tabs}
{chart_section}
{step_foot}
</main>
</div>
<script src="site.js" defer></script>
</body>
</html>
'''


# ─── index page ────────────────────────────────────────────────────────────

HUB_PREVIEW_KPIS = {
    1:  '6,660 大陆 · 1,468 港 · 474 台',
    2:  'Top-20 持 44% 前缀',
    3:  '全球 #3 AS · #3 前缀 · #16 IXP',
    4:  '109,409 前缀 · RPKI 中等',
    5:  '400 节点 · 2,450 对等边',
    6:  'PageRank 中等 · 度数偏高',
    7:  '少数 CN AS 入深层核心',
    8:  '70%+ 依赖境外上游',
    9:  '外国依赖 CN 的程度有限',
    10: 'HHI 偏高 · 头部集中',
    11: 'IXP #16 · 密度低',
    12: '机房 #33 · 重心在境外',
    13: 'HK 为主要跨境枢纽',
    14: '云厂商 + 海外 ISP 主导',
    15: '.cn 权威自持度高',
    16: '大量跨境 CNAME 桥接',
    17: 'Tranco / CrUX / APNIC',
    18: '审查网络与非审查网络有别',
    19: '少量 CN Atlas 探针',
    20: '主权指数 0.256 · 全球第 9',
}


def render_index(metrics: dict) -> str:
    # Hero KPIs (based on user-supplied stats from old index.html)
    hero_stats = [
        ('#3',    'AS 数',        'AS Count Rank'),
        ('#3',    '前缀数',       'Prefix Rank'),
        ('#16',   'IXP 数',       'IXP Rank'),
        ('#33',   '机房数',       'Facility Rank'),
        ('0.256', '主权指数',     'Sovereignty Index'),
    ]
    rail = ''.join(
        f'<div class="stat{" hi" if i == 4 else ""}">'
        f'<div class="big">{esc(v)}</div>'
        f'<div class="k">{esc(zh)}</div>'
        f'<div class="en">{esc(en)}</div>'
        '</div>'
        for i, (v, zh, en) in enumerate(hero_stats)
    )
    # Filter chips (by phase)
    chips = ['<button class="filter-chip active" data-filter="all">全部</button>']
    for letter, zh, en, _ in PHASES:
        chips.append(f'<button class="filter-chip" data-filter="{letter}">{esc(letter)} · {esc(zh)}</button>')

    # Phase sections
    phase_html = ''
    for letter, zh, en, steps in PHASES:
        cards = []
        for s in steps:
            n = step_parts_count(s)
            href = step_page_name(s, 1, n)
            t_zh, t_en = STEP_TITLES[s]
            kpi_line = HUB_PREVIEW_KPIS.get(s, '')
            badge = f'<span class="parts-badge">{n} subpages</span>' if n > 1 else ''
            cards.append(
                f'<a class="step-card" href="{href}" data-phase="{letter}">'
                f'{badge}'
                f'<div class="num">Step {s:02d}</div>'
                f'<h3>{esc(t_zh)}</h3>'
                f'<div class="en-sub">{esc(t_en)}</div>'
                f'<div class="kpi-row"><span>{esc(kpi_line)}</span></div>'
                f'</a>'
            )
        phase_html += (
            f'<section class="phase" id="phase-{letter}" data-phase="{letter}">'
            f'<header class="phase-head">'
            f'<span class="letter">{esc(letter)}</span>'
            f'<div><h2>{esc(zh)}</h2><div class="en">{esc(en)}</div></div>'
            f'</header>'
            f'<div class="step-grid">{"".join(cards)}</div>'
            f'</section>'
        )

    # Build site
    top_nav = render_top_nav(None)
    search_box = (
        '<div class="search-box">' + ICON_SEARCH +
        '<input type="text" placeholder="搜索步骤 / Search steps…" aria-label="search">'
        '<span class="search-kbd">/</span></div>'
    )
    today = datetime.date.today().strftime('%Y-%m-%d')
    return f'''<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>中国互联网全球位置全景 · China in Global Internet Hierarchy</title>
<link rel="stylesheet" href="site.css">
</head>
<body>
{top_nav}
<main class="hub">
  <section class="hub-hero">
    <div class="eyebrow"><span class="dot"></span> IYP Snapshot 2026-04 · 20-Step Analysis</div>
    <h1>中国互联网全球位置全景分析</h1>
    <p class="en-title">China's Position in the Global Internet Hierarchy · built on the Internet Yellow Pages (IYP) Neo4j knowledge graph</p>
    <p class="lede">
      本分析以复杂网络科学、互联网主权与测量拓扑三重视角，系统考察中国在全球互联网 20 个维度上的分层位置与依赖关系。
      每一张图附“图解”按钮，点击可查看 ~300 字的通俗解读，专业而不晦涩。
      <br>
      <span style="color:var(--muted);font-size:13px;">
        This study examines China across 20 dimensions of the global Internet using complex-network science,
        Internet sovereignty, and measurement topology. Click the "图解" badge on any chart for a plain-language explanation.
      </span>
    </p>
    <div class="stat-rail">{rail}</div>
    <div class="hub-actions">
      {search_box}
      <div class="filter-row">{"".join(chips)}</div>
    </div>
  </section>

  <div class="phase-board">
    {phase_html}
  </div>

  <footer class="site-foot">
    产出：27 个子页面 · 63 张交互图表 · 20 个 metrics JSON · 1 个主导航<br>
    Artifacts: 27 subpages · 63 charts · 20 metrics files · 1 hub index<br>
    Data: IYP snapshot 2026-04 · generated {esc(today)} by <code>analysis/china/build_site.py</code>
  </footer>
</main>
<script src="site.js" defer></script>
</body>
</html>
'''


# ─── build pipeline ────────────────────────────────────────────────────────

def backup_existing(html_dir: Path) -> Path | None:
    if not html_dir.exists() or not any(html_dir.iterdir()):
        return None
    ts = datetime.date.today().strftime('%Y%m%d')
    out = BASE / f'html_legacy_{ts}.tar.gz'
    if out.exists():
        print(f'[backup] {out} already exists, skipping')
        return out
    print(f'[backup] archiving {html_dir} → {out}')
    with tarfile.open(out, 'w:gz') as tf:
        tf.add(html_dir, arcname=html_dir.name)
    size_mb = out.stat().st_size / (1024 * 1024)
    print(f'[backup] wrote {size_mb:.1f} MB archive')
    return out


def write_plotly_js(parsed_steps: dict) -> Path:
    """Extract plotly.js once and write to html/plotly.min.js."""
    for step in range(1, 21):
        if step in PYVIS_STEPS:
            continue
        p = parsed_steps.get(step)
        if p and p.get('plotly_js'):
            out = HTML_DIR / 'plotly.min.js'
            out.write_text(p['plotly_js'], encoding='utf-8')
            size_mb = out.stat().st_size / (1024 * 1024)
            print(f'[assets] wrote plotly.min.js ({size_mb:.2f} MB) from step {step:02d}')
            return out
    raise RuntimeError('could not extract plotly.js from any step')


def copy_static_assets():
    for name in ('site.css', 'site.js'):
        src = ASSETS / name
        if not src.exists():
            raise FileNotFoundError(src)
        shutil.copy2(src, HTML_DIR / name)
        print(f'[assets] copied {name} ({src.stat().st_size // 1024} KB)')


def build(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-backup', action='store_true')
    args = ap.parse_args(argv)

    if not HTML_DIR.exists():
        sys.exit(f'[error] html directory not found: {HTML_DIR}')

    if not args.no_backup:
        backup_existing(HTML_DIR)

    print('[parse] reading 20 step HTMLs...')
    parsed_steps = {s: parse_step(s) for s in range(1, 21)}
    for s, p in parsed_steps.items():
        nc = len(p.get('charts', [])) if p['type'] == 'plotly' else 1
        print(f'  step{s:02d}: {p["type"]:6s} charts={nc}')

    print('[assets] writing plotly.min.js + site.css + site.js...')
    write_plotly_js(parsed_steps)
    copy_static_assets()

    metrics = load_metrics()
    nav_order = build_nav_order()
    print(f'[nav] {len(nav_order)} sub-pages in linear order')

    # Render step pages
    sizes = []
    for idx, (fname, step, part, total, _) in enumerate(nav_order):
        parsed = parsed_steps[step]
        metrics_payload = metrics.get(step, {})
        is_first = (step in (s for s in range(1, 21) if s not in PYVIS_STEPS)) and idx == 0
        html = render_step_page(step, part, total, parsed, nav_order, idx, metrics_payload, is_first)
        out = HTML_DIR / fname
        out.write_text(html, encoding='utf-8')
        sizes.append((fname, out.stat().st_size))
    for f, sz in sizes:
        print(f'  {f:35s} {sz//1024:5d} KB')

    # Render index.html
    idx_html = render_index(metrics)
    (HTML_DIR / 'index.html').write_text(idx_html, encoding='utf-8')
    print(f'  index.html                          {(HTML_DIR/"index.html").stat().st_size//1024:5d} KB')

    # Delete legacy split-step originals (now superseded by _partN pages)
    legacy_deletes = [STEP_FILES[s] for s in SPLIT_STEPS]
    for lg in legacy_deletes:
        p = HTML_DIR / lg
        if p.exists() and not any(p.name == step_page_name(s, pt, step_parts_count(s))
                                  for s in range(1, 21) for pt in range(1, step_parts_count(s) + 1)):
            p.unlink()
            print(f'[cleanup] removed legacy {lg}')

    total_mb = sum(sz for _, sz in sizes) / (1024 * 1024)
    plotly_mb = (HTML_DIR / 'plotly.min.js').stat().st_size / (1024 * 1024)
    print(f'\n[done] pages: {len(sizes)} ({total_mb:.1f} MB) + plotly.min.js ({plotly_mb:.1f} MB)')
    # Post-verify
    cap_total = 0
    for f, _ in sizes:
        cap_total += (HTML_DIR / f).read_text().count('class="cap-dialog"')
    print(f'[verify] {cap_total} caption dialogs across sub-pages (expected 63)')


if __name__ == '__main__':
    build()
