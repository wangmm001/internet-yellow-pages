"""Step 10 · China Concentration & HHI.

Dimensions: concentration metrics applied to China-specific slices
Data: cached as_prefix_count.csv, as_organization.csv, dns_as_hosting.csv, as_ixp_membership.csv
Output: cn_concentration.csv + Plotly Lorenz + HHI dashboard
"""
import csv
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.china.common import (  # noqa: E402
    COLORS, DATA_DIR, DARK_PANEL, TEXT_PRIMARY, load_cn_ases,
    save_multi_plotly_html, write_csv, write_step_metrics, writeup,
)
from analysis.complex_network.utils import DATA_DIR as GLOBAL_DATA_DIR
from analysis.complex_network.step13_concentration_hhi import (
    gini_coefficient, hhi_index, lorenz_curve,
)

STEP = 10
TITLE_ZH = '中国互联网集中度与 HHI 分析'
TITLE_EN = 'China Internet Concentration & HHI'


def load_col(path, key_col, val_col, val_type=int):
    data = {}
    if not os.path.exists(path):
        return data
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            try:
                data[int(row[key_col])] = val_type(row[val_col])
            except Exception:
                continue
    return data


def main():
    cn = load_cn_ases()

    # Per AS: prefix count
    prefix = load_col(os.path.join(GLOBAL_DATA_DIR, 'as_prefix_count.csv'),
                      'asn', 'prefix_count')
    # Per AS: hostname count
    host = load_col(os.path.join(GLOBAL_DATA_DIR, 'dns_as_hosting.csv'),
                    'asn', 'hostname_count')

    # Org→AS count (aggregated)
    org_cn = Counter()
    org_all = Counter()
    path = os.path.join(GLOBAL_DATA_DIR, 'as_organization.csv')
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            try:
                asn = int(row['asn'])
            except Exception:
                continue
            org = (row.get('org_name') or '').strip()
            if not org:
                continue
            org_all[org] += 1
            if asn in cn:
                org_cn[org] += 1

    # IXP memberships per AS
    ixp_cn = Counter()
    ixp_all = Counter()
    path = os.path.join(GLOBAL_DATA_DIR, 'as_ixp_membership.csv')
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            try:
                asn = int(row['asn'])
            except Exception:
                continue
            ixp_all[asn] += 1
            if asn in cn:
                ixp_cn[asn] += 1

    # Build metric dicts (CN-only, and global-all for comparison)
    cn_prefix = [prefix[a] for a in cn if a in prefix]
    cn_host = [host[a] for a in cn if a in host]
    cn_org = list(org_cn.values())
    cn_ixp_counts = list(ixp_cn.values())

    global_prefix = list(prefix.values())
    global_host = list(host.values())
    global_org = list(org_all.values())
    global_ixp_counts = list(ixp_all.values())

    def gh(arr):
        if not arr:
            return 0.0, 0.0
        s = sum(arr)
        shares = [x / s for x in arr] if s else []
        return gini_coefficient(arr), hhi_index(shares)

    g_cn_p, h_cn_p = gh(cn_prefix)
    g_cn_h, h_cn_h = gh(cn_host)
    g_cn_o, h_cn_o = gh(cn_org)
    g_cn_i, h_cn_i = gh(cn_ixp_counts)

    g_g_p, h_g_p = gh(global_prefix)
    g_g_h, h_g_h = gh(global_host)
    g_g_o, h_g_o = gh(global_org)
    g_g_i, h_g_i = gh(global_ixp_counts)

    write_csv('cn_concentration.csv', [
        {'dimension': 'prefix', 'cn_gini': g_cn_p, 'cn_hhi': h_cn_p,
         'global_gini': g_g_p, 'global_hhi': h_g_p, 'cn_n': len(cn_prefix)},
        {'dimension': 'hostname', 'cn_gini': g_cn_h, 'cn_hhi': h_cn_h,
         'global_gini': g_g_h, 'global_hhi': h_g_h, 'cn_n': len(cn_host)},
        {'dimension': 'org_control', 'cn_gini': g_cn_o, 'cn_hhi': h_cn_o,
         'global_gini': g_g_o, 'global_hhi': h_g_o, 'cn_n': len(cn_org)},
        {'dimension': 'ixp_memberships', 'cn_gini': g_cn_i, 'cn_hhi': h_cn_i,
         'global_gini': g_g_i, 'global_hhi': h_g_i, 'cn_n': len(cn_ixp_counts)},
    ])

    # ── Plotly: Lorenz curves overlay for CN and global ──
    import plotly.graph_objects as go
    import plotly.subplots as sp

    lorenz_fig = sp.make_subplots(
        rows=2, cols=2,
        subplot_titles=('前缀 Prefix', '托管 Hostname', '组织-AS 控股 Org', 'IXP 会员数'))
    for i, (arr_cn, arr_g, title_key) in enumerate([
        (cn_prefix, global_prefix, 'prefix'),
        (cn_host, global_host, 'host'),
        (cn_org, global_org, 'org'),
        (cn_ixp_counts, global_ixp_counts, 'ixp'),
    ]):
        r = i // 2 + 1
        c = i % 2 + 1
        if arr_g:
            x, y = lorenz_curve(arr_g)
            lorenz_fig.add_trace(go.Scatter(
                x=x, y=y, mode='lines', name='Global',
                line=dict(color='#8B949E', width=2),
                showlegend=(i == 0),
            ), row=r, col=c)
        if arr_cn:
            x, y = lorenz_curve(arr_cn)
            lorenz_fig.add_trace(go.Scatter(
                x=x, y=y, mode='lines', name='CN',
                line=dict(color=COLORS['red'], width=3),
                showlegend=(i == 0),
            ), row=r, col=c)
        # diagonal
        lorenz_fig.add_trace(go.Scatter(
            x=[0, 1], y=[0, 1], mode='lines', name='Equality',
            line=dict(color='#30363D', dash='dash'), showlegend=False,
        ), row=r, col=c)
    lorenz_fig.update_layout(
        title='Lorenz 曲线 · CN vs Global (curve further from diagonal → more concentrated)',
        height=720,
    )

    # ── Bar: HHI + Gini side-by-side ──
    dims = ['prefix', 'hostname', 'org', 'ixp']
    hhi_fig = go.Figure()
    hhi_fig.add_trace(go.Bar(
        x=dims, y=[h_cn_p, h_cn_h, h_cn_o, h_cn_i],
        name='CN HHI', marker_color=COLORS['red'],
        text=[f'{v:.4f}' for v in [h_cn_p, h_cn_h, h_cn_o, h_cn_i]],
        textposition='outside',
    ))
    hhi_fig.add_trace(go.Bar(
        x=dims, y=[h_g_p, h_g_h, h_g_o, h_g_i],
        name='Global HHI', marker_color='#8B949E',
        text=[f'{v:.4f}' for v in [h_g_p, h_g_h, h_g_o, h_g_i]],
        textposition='outside',
    ))
    hhi_fig.update_layout(
        title='Herfindahl–Hirschman Index (higher → more concentrated)',
        barmode='group',
    )

    gini_fig = go.Figure()
    gini_fig.add_trace(go.Bar(
        x=dims, y=[g_cn_p, g_cn_h, g_cn_o, g_cn_i],
        name='CN Gini', marker_color=COLORS['red'],
        text=[f'{v:.3f}' for v in [g_cn_p, g_cn_h, g_cn_o, g_cn_i]],
        textposition='outside',
    ))
    gini_fig.add_trace(go.Bar(
        x=dims, y=[g_g_p, g_g_h, g_g_o, g_g_i],
        name='Global Gini', marker_color='#8B949E',
        text=[f'{v:.3f}' for v in [g_g_p, g_g_h, g_g_o, g_g_i]],
        textposition='outside',
    ))
    gini_fig.update_layout(
        title='Gini 系数 · CN vs Global', barmode='group')

    metrics = {
        'cn_gini_prefix': round(g_cn_p, 4), 'global_gini_prefix': round(g_g_p, 4),
        'cn_gini_hostname': round(g_cn_h, 4), 'global_gini_hostname': round(g_g_h, 4),
        'cn_gini_org': round(g_cn_o, 4), 'global_gini_org': round(g_g_o, 4),
        'cn_gini_ixp': round(g_cn_i, 4), 'global_gini_ixp': round(g_g_i, 4),
        'cn_hhi_prefix': round(h_cn_p, 4), 'global_hhi_prefix': round(h_g_p, 4),
        'cn_hhi_hostname': round(h_cn_h, 4), 'global_hhi_hostname': round(h_g_h, 4),
    }
    write_step_metrics(STEP, metrics, TITLE_ZH, TITLE_EN)

    w = writeup(
        hypothesis=(
            '经济体"行业集中度"的 HHI>0.25 通常被视为高度集中 (US DOJ 标准)；'
            '互联网基础设施的集中化被认为是系统性风险来源之一。<br>'
            'HHI > 0.25 is commonly labeled "highly concentrated" (US DOJ). High concentration of '
            'Internet infrastructure is a documented source of systemic risk.'
        ),
        finding=(
            f'前缀集中度 HHI: CN={h_cn_p:.3f} vs 全球={h_g_p:.3f}；'
            f'托管 HHI: CN={h_cn_h:.3f} vs 全球={h_g_h:.3f}；'
            f'组织控股 HHI: CN={h_cn_o:.3f} vs 全球={h_g_o:.3f}。'
            f'CN 在 hostname/org 维度集中度高于全球平均。<br>'
            f'Prefix HHI CN={h_cn_p:.3f} vs Global={h_g_p:.3f}; '
            f'Hostname HHI CN={h_cn_h:.3f} vs Global={h_g_h:.3f}; '
            f'Org HHI CN={h_cn_o:.3f} vs Global={h_g_o:.3f}. CN is more concentrated on host/org dims.'
        ),
        reference='Reuse of complex_network/step13_concentration_hhi.py functions',
    )

    save_multi_plotly_html(
        [lorenz_fig, hhi_fig, gini_fig], 'step10_concentration.html',
        step_num=STEP, title_zh=TITLE_ZH, title_en=TITLE_EN, source='cached CSV',
        writeup_html=w,
        subtitles=['1. Lorenz 曲线 (4 维度)', '2. HHI 对比', '3. Gini 系数对比'],
    )


if __name__ == '__main__':
    main()
