#!/usr/bin/env python3
"""One-shot patch for step16_cname_chains.html: cluster by cloud family.

Reads analysis/china/data/cn_cname_chains.csv, recomputes the bipartite
aggregation (TLD -> cloud-family), and rewrites the pyvis-generated
HTML's nodes/edges arrays.  Idempotent on its own output.
"""
import csv
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from analysis.china.common import COLORS, country_color
from analysis.china.step16_cname_chains import classify_target

HTML = Path('analysis/china/html/step16_cname_chains.html')
CSV = Path('analysis/china/data/cn_cname_chains.csv')

FAMILY_COLOR = {
    'Aliyun': COLORS['orange'], 'Aliyun CDN': COLORS['orange'],
    'Tencent': COLORS['blue'], 'Tencent Cloud': COLORS['blue'],
    'Tencent DNSPod': COLORS['blue'], 'Tencent DNS': COLORS['blue'],
    'Huawei': COLORS['red'], 'Huawei Cloud': COLORS['red'], 'Huawei CDN': COLORS['red'],
    'Baidu': COLORS['purple'],
    'NetEase': COLORS['pink'],
    'JD': COLORS['amber'], 'JD Cloud': COLORS['amber'],
    'ChinaCache': COLORS['green'], 'ChinaNetCenter': COLORS['green'],
    'Wangsu': COLORS['cyan'], 'Wangsu CDN': COLORS['cyan'],
    'Other CN': COLORS['teal'],
}


def main():
    if not CSV.exists():
        sys.exit(f'missing {CSV}')
    if not HTML.exists():
        sys.exit(f'missing {HTML}')

    # Aggregate
    fam_target_count = Counter()
    tld_to_fam = Counter()
    with CSV.open() as f:
        for row in csv.DictReader(f):
            dst = row['dst']
            src = row['src']
            fam = classify_target(dst) or 'Other CN'
            tld = src.rsplit('.', 1)[-1].lower() if '.' in src else 'none'
            fam_target_count[fam] += 1
            tld_to_fam[(tld, fam)] += 1

    # Tld bucketing
    tld_edge_count = Counter()
    for (t, _), c in tld_to_fam.items():
        tld_edge_count[t] += c
    TOP_TLDS = 12
    main_tlds = {t for t, _ in tld_edge_count.most_common(TOP_TLDS)}

    tld_edges = Counter()
    tld_fam_edges = Counter()
    with CSV.open() as f:
        for row in csv.DictReader(f):
            src = row['src']
            dst = row['dst']
            fam = classify_target(dst) or 'Other CN'
            tld_raw = src.rsplit('.', 1)[-1].lower() if '.' in src else 'none'
            tld = tld_raw if tld_raw in main_tlds else 'other'
            tld_edges[tld] += 1
            tld_fam_edges[(tld, fam)] += 1

    def scaled(count, base=22, k=7.5, cap=70):
        return min(round(base + math.log(max(count, 1) + 1) * k), cap)

    left_tlds = sorted(tld_edges.items(), key=lambda x: -x[1])
    right_fams = sorted(fam_target_count.items(), key=lambda x: -x[1])

    nodes = []
    n_left = len(left_tlds)
    for i, (tld, count) in enumerate(left_tlds):
        label = f'.{tld}' if tld not in ('other', 'none') else tld
        cc = tld.upper() if len(tld) == 2 else ''
        color = country_color(cc) if cc else COLORS['cyan']
        nodes.append({
            'id': f'tld:{tld}',
            'label': f'{label} ({count})',
            'title': f'TLD {label} — {count} CNAME edges',
            'color': color,
            'size': scaled(count),
            'x': -900,
            'y': float(i - n_left / 2) * 90,
        })
    n_right = len(right_fams)
    for i, (fam, count) in enumerate(right_fams):
        color = FAMILY_COLOR.get(fam, COLORS['teal'])
        nodes.append({
            'id': f'fam:{fam}',
            'label': f'{fam} ({count})',
            'title': f'{fam} — {count} distinct target hosts',
            'color': color,
            'size': scaled(count),
            'x': 900,
            'y': float(i - n_right / 2) * 90,
        })

    edges = []
    for (tld, fam), count in tld_fam_edges.items():
        width = min(1 + math.log(count + 1), 8.0)
        edges.append({
            'from': f'tld:{tld}',
            'to': f'fam:{fam}',
            'value': count,
            'width': round(width, 2),
            'title': f'{count} edges',
            'arrows': {'to': {'enabled': True, 'scaleFactor': 0.4}},
        })

    html = HTML.read_text(encoding='utf-8')
    # Replace nodes DataSet
    m_n = re.search(r'(nodes\s*=\s*new\s+vis\.DataSet\()(\[.*?\])(\s*\);)',
                    html, flags=re.DOTALL)
    if not m_n:
        sys.exit('could not locate nodes DataSet')
    html = html[:m_n.start(2)] + json.dumps(nodes, ensure_ascii=False, separators=(', ', ': ')) + html[m_n.end(2):]

    # Replace edges DataSet
    m_e = re.search(r'(edges\s*=\s*new\s+vis\.DataSet\()(\[.*?\])(\s*\);)',
                    html, flags=re.DOTALL)
    if not m_e:
        sys.exit('could not locate edges DataSet')
    html = html[:m_e.start(2)] + json.dumps(edges, ensure_ascii=False, separators=(', ', ': ')) + html[m_e.end(2):]

    HTML.write_text(html, encoding='utf-8')
    print(f'patched: {len(nodes)} nodes ({n_left} TLDs + {n_right} families), {len(edges)} edges')


if __name__ == '__main__':
    main()
