#!/usr/bin/env python3
"""One-shot patch: add AS→Org labels and country-based coloring to
step13_ixp_fac_bridge.html (pyvis output). Idempotent.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from analysis.china.common import country_color
from analysis.web.enrich_as_labels import load_as_org_map, DEFAULT_MAP_CSV

HTML_PATH = Path(__file__).resolve().parents[2] / 'analysis' / 'china' / 'html' / 'step13_ixp_fac_bridge.html'


def main():
    as_org_map = load_as_org_map(DEFAULT_MAP_CSV)
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
        elif nid.startswith('ixp:') or nid.startswith('fac:'):
            cm = cc_re.search(title)
            if cm:
                cc = cm.group(1)
                node['color'] = country_color(cc)
                changed_ixp_fac += 1

    new_array = json.dumps(nodes, ensure_ascii=False, separators=(', ', ': '))
    new_html = html[:m.start(2)] + new_array + html[m.end(2):]
    HTML_PATH.write_text(new_html, encoding='utf-8')
    print(f'patched: {changed_as} AS labels, {changed_ixp_fac} IXP/Fac colors')


if __name__ == '__main__':
    main()
