#!/usr/bin/env python3
"""One-shot patch: add AS→Org labels, country-based coloring, and log-scaled
sizes to step13_ixp_fac_bridge.html (pyvis output). Idempotent.
"""
import csv
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from analysis.china.common import country_color
from analysis.web.enrich_as_labels import load_as_org_map, DEFAULT_MAP_CSV

HTML_PATH = Path(__file__).resolve().parents[2] / 'analysis' / 'china' / 'html' / 'step13_ixp_fac_bridge.html'
TRI_CSV = Path(__file__).resolve().parents[2] / 'analysis' / 'china' / 'data' / 'cn_ixp_fac_tripartite.csv'


def _scaled(metric):
    return min(round(18 + math.log(max(metric, 1) + 1) * 6.5), 54)


def _load_metrics():
    """Build as_metric, ixp_metric, fac_metric from the committed tripartite CSV."""
    as_ixps = {}
    ixp_ases = {}
    fac_ases = {}
    with TRI_CSV.open(encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            asn = row.get('asn', '').strip()
            ixp = row.get('ixp', '').strip()
            fac = row.get('fac', '').strip()
            if asn and ixp:
                as_ixps.setdefault(asn, set()).add(ixp)
                ixp_ases.setdefault(ixp, set()).add(asn)
            if asn and fac:
                fac_ases.setdefault(fac, set()).add(asn)
    as_metric = {a: len(s) for a, s in as_ixps.items()}
    ixp_metric = {i: len(s) for i, s in ixp_ases.items()}
    fac_metric = {f: len(s) for f, s in fac_ases.items()}
    return as_metric, ixp_metric, fac_metric


def main():
    as_org_map = load_as_org_map(DEFAULT_MAP_CSV)
    as_metric, ixp_metric, fac_metric = _load_metrics()
    html = HTML_PATH.read_text(encoding='utf-8')

    # Find: nodes = new vis.DataSet([ … ]);
    m = re.search(r'(nodes\s*=\s*new\s+vis\.DataSet\()(\[.*?\])(\s*\);)',
                  html, flags=re.DOTALL)
    if not m:
        sys.exit('ERROR: could not locate "nodes = new vis.DataSet(...)" in HTML')

    # Parse the JSON-ish array.  pyvis emits valid JSON inside the argument.
    raw_array = m.group(2)
    nodes = json.loads(raw_array)

    changed_as = 0
    changed_ixp_fac = 0
    changed_sizes = 0
    cc_re = re.compile(r'\[([A-Z]{2})\]')
    for node in nodes:
        nid = str(node.get('id', ''))
        title = node.get('title', '') or ''
        if nid.startswith('as:'):
            try:
                asn = int(nid[3:])
            except ValueError:
                continue
            org = as_org_map.get(asn)
            if org:
                disp_org = (org[:20].rstrip() + '…') if len(org) > 22 else org
                node['label'] = f'AS{asn} · {disp_org}'
                node['title'] = f'AS{asn} · {org} (CN)'
                changed_as += 1
            # Size by distinct IXPs this AS participates in
            metric = as_metric.get(str(asn), 1)
            new_size = _scaled(metric)
            if node.get('size') != new_size:
                node['size'] = new_size
                changed_sizes += 1
        elif nid.startswith('ixp:') or nid.startswith('fac:'):
            cm = cc_re.search(title)
            if cm:
                cc = cm.group(1)
                node['color'] = country_color(cc)
                changed_ixp_fac += 1
            # Size by distinct ASes at this IXP / facility
            raw_key = nid.split(':', 1)[1]
            if nid.startswith('ixp:'):
                metric = ixp_metric.get(raw_key, 1)
            else:
                metric = fac_metric.get(raw_key, 1)
            new_size = _scaled(metric)
            if node.get('size') != new_size:
                node['size'] = new_size
                changed_sizes += 1

    new_array = json.dumps(nodes, ensure_ascii=False, separators=(', ', ': '))
    new_html = html[:m.start(2)] + new_array + html[m.end(2):]
    HTML_PATH.write_text(new_html, encoding='utf-8')
    print(f'patched: {changed_as} AS labels, {changed_ixp_fac} IXP/Fac colors, {changed_sizes} sizes')


if __name__ == '__main__':
    main()
