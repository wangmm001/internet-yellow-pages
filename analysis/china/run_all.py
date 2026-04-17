"""Orchestrator for China-in-Global-Internet-Hierarchy 20-step analysis.

Usage:
  python3 -m analysis.china.run_all            # run all 20 steps sequentially
  python3 -m analysis.china.run_all --step 7   # rerun a single step
  python3 -m analysis.china.run_all --verify   # verification report only
  python3 -m analysis.china.run_all --report   # regenerate README + index.html
"""
import argparse
import importlib
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.china.common import (  # noqa: E402
    DATA_DIR, HTML_DIR, BANNER_CSS, DARK_BG, DARK_PANEL, DARK_BORDER,
    TEXT_PRIMARY, TEXT_SECONDARY, COLORS, read_step_metrics,
)

STEPS = [
    (1, 'step01_scope_identity', 'China AS Inventory & Scope', '中国自治系统清册'),
    (2, 'step02_top_as', 'Top-20 Chinese ASes · Identity', '头部自治系统身份档案'),
    (3, 'step03_global_ranks', 'China vs World at a Glance', '全球规模排名'),
    (4, 'step04_prefixes', 'CN BGP Prefix Footprint', 'BGP 前缀与 RPKI'),
    (5, 'step05_peering_graph', 'CN AS Peering Subgraph', '对等互联子图'),
    (6, 'step06_centrality', 'CN in Global Centrality', '全球中心性位置'),
    (7, 'step07_kcore', 'CN in Global k-Core', 'k-core 层级位置'),
    (8, 'step08_depends_on_world', 'Who Does China Depend On', '出向 Hegemony'),
    (9, 'step09_dependents', 'Who Depends on China', '入向 Hegemony'),
    (10, 'step10_concentration', 'China Concentration & HHI', '集中度与 HHI'),
    (11, 'step11_ixp_landscape', 'Chinese IXP Landscape', 'IXP 互联生态'),
    (12, 'step12_facilities', 'CN AS Facility Co-location', '机房部署'),
    (13, 'step13_ixp_fac_bridge', 'IXP+Facility Tripartite', 'IXP×机房三部图'),
    (14, 'step14_dns_hosting', 'CN DNS Hosting Footprint', 'DNS 托管版图'),
    (15, 'step15_dns_authority', '.cn DNS Sovereignty', '.cn DNS 主权'),
    (16, 'step16_cname_chains', 'Cross-Border CNAME Chains', 'CNAME 跨境链'),
    (17, 'step17_rankings', 'CN in Global Rankings', '多排名位置'),
    (18, 'step18_censorship', 'Censorship Topology in CN', '审查拓扑'),
    (19, 'step19_atlas', 'RIPE Atlas Presence in CN', 'Atlas 观测点'),
    (20, 'step20_synthesis', 'Synthesis Dashboard', '综合仪表板'),
]


def run_step(step_num):
    info = next(s for s in STEPS if s[0] == step_num)
    mod_name = info[1]
    print(f'\n{"=" * 60}\nStep {step_num:02d} · {info[3]} / {info[2]}\n{"=" * 60}')
    try:
        mod = importlib.import_module(f'analysis.china.{mod_name}')
        mod.main()
        return True
    except Exception as e:
        traceback.print_exc()
        print(f'[FAIL] Step {step_num}: {e}')
        return False


def verify():
    """Print a verification table of all outputs."""
    print(f'{"Step":<5} {"Title":<32} {"HTML":<12} {"Size":>8} {"CSV":<10} {"Metrics":<10}')
    print('-' * 90)
    for sn, mod, ten, tzh in STEPS:
        # find html file
        hits = [f for f in os.listdir(HTML_DIR)
                if f.startswith(f'step{sn:02d}') and f.endswith('.html')]
        if hits:
            html_path = os.path.join(HTML_DIR, hits[0])
            size = os.path.getsize(html_path)
            html_flag = 'OK'
        else:
            size = 0
            html_flag = 'MISS'
        metrics = read_step_metrics(sn)
        metrics_flag = 'OK' if metrics else 'MISS'
        csv_hits = [f for f in os.listdir(DATA_DIR)
                    if f.startswith('cn_') or f.startswith('global_')]
        csv_flag = f'{len(csv_hits)} tot' if csv_hits else 'MISS'
        print(f'{sn:<5} {tzh[:30]:<32} {html_flag:<12} {size // 1024:>5} KB '
              f'{csv_flag:<10} {metrics_flag:<10}')


def generate_index_html():
    """Build index.html with sidebar navigation to all step HTMLs."""
    items_html = ''
    for sn, mod, ten, tzh in STEPS:
        hits = sorted(f for f in os.listdir(HTML_DIR)
                      if f.startswith(f'step{sn:02d}') and f.endswith('.html'))
        href = hits[0] if hits else '#'
        metrics = read_step_metrics(sn)
        m_short = ''
        if metrics and metrics.get('metrics'):
            first = next(iter(metrics['metrics'].items()), None)
            if first:
                k, v = first
                if isinstance(v, (int, float)):
                    m_short = f' · {k}={v:,}' if isinstance(v, int) else f' · {k}={v}'
        items_html += (
            f'<li><a href="{href}"><b>Step {sn:02d}</b> · {tzh}'
            f'<br><span class="en">{ten}{m_short}</span></a></li>'
        )

    phase_labels = [
        ('A', '范围与身份 Scope & Identity', [1, 2, 3]),
        ('B', 'BGP 拓扑位置 BGP Topology', [4, 5, 6, 7]),
        ('C', '依赖与 Hegemony', [8, 9, 10]),
        ('D', '物理基础设施 Physical', [11, 12, 13]),
        ('E', 'DNS / 内容 / 排名 DNS/Content', [14, 15, 16, 17]),
        ('F', '安全 / 测量 / 综合 Security & Synthesis', [18, 19, 20]),
    ]

    phase_nav = ''
    for letter, title, steps_in_phase in phase_labels:
        phase_nav += f'<h3 class="phase"><span class="ph-letter">{letter}</span> {title}</h3><ol>'
        for sn in steps_in_phase:
            info = next(s for s in STEPS if s[0] == sn)
            hits = sorted(f for f in os.listdir(HTML_DIR)
                          if f.startswith(f'step{sn:02d}') and f.endswith('.html'))
            href = hits[0] if hits else '#'
            phase_nav += (
                f'<li><a href="{href}"><span class="snum">{sn:02d}</span> '
                f'{info[3]}<br><span class="en">{info[2]}</span></a></li>'
            )
        phase_nav += '</ol>'

    # Summary metrics from Step 3 + 20
    s3 = read_step_metrics(3) or {}
    s20 = read_step_metrics(20) or {}
    ranks = (s3.get('metrics') or {}).get('cn_ranks_by_metric', {}) or {}
    sovereignty = (s20.get('metrics') or {}).get('composite_sovereignty_index', None)

    headline = f'''
    <div class="headline">
      <h1>中国互联网全球位置全景分析</h1>
      <h2>China's Position in the Global Internet Hierarchy · 20-Step IYP Analysis</h2>
      <div class="stats">
        <div class="stat"><div class="stat-v">#{ranks.get('as_count', {}).get('rank', '?')}</div>
             <div class="stat-l">AS 数<br>AS Count Rank</div></div>
        <div class="stat"><div class="stat-v">#{ranks.get('prefix_count', {}).get('rank', '?')}</div>
             <div class="stat-l">前缀数<br>Prefix Rank</div></div>
        <div class="stat"><div class="stat-v">#{ranks.get('ixp_count', {}).get('rank', '?')}</div>
             <div class="stat-l">IXP 数<br>IXP Rank</div></div>
        <div class="stat"><div class="stat-v">#{ranks.get('facility_count', {}).get('rank', '?')}</div>
             <div class="stat-l">机房数<br>Facility Rank</div></div>
        <div class="stat hi"><div class="stat-v">{sovereignty:.3f}</div>
             <div class="stat-l">主权指数<br>Sovereignty Index</div></div>
      </div>
    </div>
    '''

    html = f'''<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>中国互联网全球位置全景分析</title>
{BANNER_CSS}
<style>
  .headline {{ background:{DARK_PANEL}; padding:32px 28px 20px;
               border-bottom:2px solid {COLORS['red']}; }}
  .headline h1 {{ margin:0 0 4px 0; color:{TEXT_PRIMARY}; font-size:28px; }}
  .headline h2 {{ margin:0 0 18px 0; color:{TEXT_SECONDARY}; font-size:16px;
                  font-weight:400; }}
  .stats {{ display:flex; gap:14px; flex-wrap:wrap; }}
  .stat {{ background:{DARK_BG}; border:1px solid {DARK_BORDER}; padding:12px 20px;
           border-radius:8px; min-width:110px; text-align:center; }}
  .stat.hi {{ border-color:{COLORS['red']}; background:rgba(255,107,107,0.08); }}
  .stat-v {{ font-size:24px; color:{COLORS['red']}; font-weight:700; }}
  .stat-l {{ font-size:11px; color:{TEXT_SECONDARY}; margin-top:4px; line-height:1.3; }}
  .phase {{ color:{COLORS['cyan']}; margin-top:26px; padding-bottom:4px;
            border-bottom:1px solid {DARK_BORDER}; font-size:16px; }}
  .ph-letter {{ background:{COLORS['cyan']}; color:{DARK_BG};
                padding:2px 8px; border-radius:4px; font-size:14px; margin-right:8px; }}
  ol {{ list-style:none; padding:0; margin:6px 0 14px 0; }}
  ol li {{ margin:6px 0; }}
  ol li a {{ display:block; background:{DARK_PANEL}; border:1px solid {DARK_BORDER};
             border-left:4px solid {COLORS['red']};
             padding:10px 14px; border-radius:6px;
             color:{TEXT_PRIMARY}; text-decoration:none; font-size:14px; }}
  ol li a:hover {{ border-left-color:{COLORS['cyan']}; background:#1a2028; }}
  ol li a .snum {{ color:{COLORS['cyan']}; font-weight:700; margin-right:8px; }}
  ol li a .en {{ color:{TEXT_SECONDARY}; font-size:12px; }}
</style></head><body>
{headline}
<div class="content">
<p style="color:{TEXT_SECONDARY};font-size:14px;">
本分析基于 Internet Yellow Pages (IYP) Neo4j 知识图谱（快照 2026-04），沿用
<b>复杂网络科学 · 互联网主权 · 测量拓扑</b>的学术视角，按 20 个分析步骤考察中国
在全球互联网体系中的分层位置与依赖关系。<br>
This analysis uses the IYP Neo4j knowledge graph (snapshot 2026-04) to examine China's
position in the global Internet hierarchy across 20 steps, framed by complex-network science,
Internet sovereignty, and measurement-topology lenses.
</p>
{phase_nav}
<div class="step-footer">
  产出：20 个交互式 HTML 图表 · 20 个 CSV 数据文件 · 20 个 metrics JSON · 1 个综合仪表板<br>
  Artifacts: 20 interactive HTMLs, 20 CSVs, 20 metrics JSONs, 1 synthesis dashboard.
  <br>Data source: IYP snapshot 2026-04 · Generated by analysis/china/run_all.py
</div>
</div>
</body></html>'''
    out = os.path.join(HTML_DIR, 'index.html')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'[index] wrote {out} ({os.path.getsize(out) // 1024} KB)')


def generate_readme():
    """Regenerate bilingual README.md from per-step metrics."""
    lines = [
        '# 中国在全球互联网分层中的位置 · 20 步分析报告',
        '## China in the Global Internet Hierarchy · 20-Step IYP Analysis',
        '',
        '> 基于 Internet Yellow Pages (IYP) Neo4j 知识图谱 · 快照 2026-04 · 分析日期 2026-04-16',
        '> Based on IYP Neo4j knowledge graph (snapshot 2026-04, generated 2026-04-16)',
        '',
        '## 概览 · Overview',
        '',
    ]
    s3 = read_step_metrics(3) or {}
    ranks = (s3.get('metrics') or {}).get('cn_ranks_by_metric', {}) or {}
    s20 = read_step_metrics(20) or {}
    sovereignty = (s20.get('metrics') or {}).get('composite_sovereignty_index')
    comps = (s20.get('metrics') or {}).get('components') or {}

    lines += [
        '| 指标 Metric | 数值 Value | 解读 Interpretation |',
        '|---|---|---|',
        f'| AS 数量 全球排名 / AS count rank | #{ranks.get("as_count", {}).get("rank", "?")} '
        f'({ranks.get("as_count", {}).get("value", "?"):,}) | 接近头部 (US/BR/IN 之后) |',
        f'| BGP 前缀数 全球排名 / Prefix rank | #{ranks.get("prefix_count", {}).get("rank", "?")} '
        f'({ranks.get("prefix_count", {}).get("value", "?"):,}) | 规模靠前 |',
        f'| IXP 数 全球排名 / IXP rank | #{ranks.get("ixp_count", {}).get("rank", "?")} '
        f'({ranks.get("ixp_count", {}).get("value", "?"):,}) | 互联基础设施相对薄弱 |',
        f'| Facility 数 全球排名 / Facility rank | #{ranks.get("facility_count", {}).get("rank", "?")} '
        f'({ranks.get("facility_count", {}).get("value", "?"):,}) | 机房密度明显偏低 |',
    ]
    if sovereignty is not None:
        lines.append(f'| 主权综合指数 / Sovereignty Index | **{sovereignty:.3f}** | 五维加权平均 |')
    lines += ['', '### 主权指数分项 Sovereignty Components', '']
    for k, v in comps.items():
        short = k.replace('\n', ' / ')
        lines.append(f'- {short}: **{v:.3f}**')
    lines += ['', '## 六阶段结构 · Six Phases', '']

    phase_labels = [
        ('A · 范围与身份 Scope & Identity', [1, 2, 3]),
        ('B · BGP 拓扑位置 BGP Topology', [4, 5, 6, 7]),
        ('C · 依赖与 Hegemony', [8, 9, 10]),
        ('D · 物理基础设施 Physical Infrastructure', [11, 12, 13]),
        ('E · DNS / 内容 / 排名 DNS / Content / Rankings', [14, 15, 16, 17]),
        ('F · 安全 / 测量 / 综合 Security / Measurement / Synthesis', [18, 19, 20]),
    ]
    for pname, steps in phase_labels:
        lines += [f'### Phase {pname}', '']
        for sn in steps:
            info = next(s for s in STEPS if s[0] == sn)
            metrics = read_step_metrics(sn)
            hits = sorted(f for f in os.listdir(HTML_DIR)
                          if f.startswith(f'step{sn:02d}') and f.endswith('.html'))
            href = hits[0] if hits else ''
            lines += [
                f'#### Step {sn:02d} · {info[3]} / {info[2]}',
                '',
                f'- 本体维度 / Ontology: _(see script docstring)_',
                f'- HTML: [`html/{href}`](html/{href})',
            ]
            if metrics:
                for k, v in (metrics.get('metrics') or {}).items():
                    if isinstance(v, (dict, list)):
                        v_str = json.dumps(v, ensure_ascii=False)
                        if len(v_str) > 180:
                            v_str = v_str[:180] + '…'
                        lines.append(f'- {k}: `{v_str}`')
                    else:
                        lines.append(f'- {k}: **{v}**')
            lines.append('')

    lines += [
        '## 复现 · Reproduction',
        '',
        '```bash',
        '# 依赖 Dependencies',
        'pip install plotly pyvis kaleido networkx matplotlib neo4j pandas numpy',
        '',
        '# 运行全部 20 步 Run all 20 steps',
        'python3 -m analysis.china.run_all',
        '',
        '# 只运行一步 Run a single step',
        'python3 -m analysis.china.run_all --step 7',
        '',
        '# 生成报告与索引 Regenerate report & index',
        'python3 -m analysis.china.run_all --report',
        '',
        '# 验证 Verify',
        'python3 -m analysis.china.run_all --verify',
        '```',
        '',
        '## 数据源 · Data Sources',
        '',
        '- IYP Neo4j 知识图谱 · 40+ node types · 34 relationship types',
        '- 复用全局缓存 CSV: `analysis/complex_network/data/`',
        '- 主要数据提供方 (via IYP): BGPKIT, CAIDA, PeeringDB, OpenINTEL, IHR, APNIC, Tranco, '
        'RIPE NCC, OONI, RIPE Atlas',
        '',
        '## 科学视角 · Scientific Lenses',
        '',
        '- 复杂网络: Barabási, Newman (度分布 / k-core / 中心性)',
        '- 互联网 Hegemony: Pelsser/IHR',
        '- 关键基础设施: Labovitz, Feamster',
        '- 互联网主权: Milton Mueller, Niels ten Oever',
        '- 测量方法: CAIDA, RIPE Atlas',
    ]

    path = os.path.join(os.path.dirname(__file__), 'README.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'[readme] wrote {path} ({os.path.getsize(path) // 1024} KB)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--step', type=int, help='run only one step')
    ap.add_argument('--verify', action='store_true', help='verification only')
    ap.add_argument('--report', action='store_true', help='regenerate README + index')
    args = ap.parse_args()

    if args.verify:
        verify()
        return
    if args.report:
        generate_index_html()
        generate_readme()
        return
    if args.step:
        run_step(args.step)
        generate_index_html()
        generate_readme()
        return

    # Full pipeline
    results = {}
    for sn, mod, ten, tzh in STEPS:
        results[sn] = run_step(sn)
    generate_index_html()
    generate_readme()
    print('\n=== Summary ===')
    ok = sum(1 for v in results.values() if v)
    print(f'{ok}/{len(STEPS)} steps succeeded')
    verify()


if __name__ == '__main__':
    main()
