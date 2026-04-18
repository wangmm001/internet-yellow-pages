"""One-shot RPKI backfill for snapshots whose extract returned 0%.

Root cause: step_lib step04 hard-codes `Tag.label == 'RPKI Valid'`. Some
older IYP dumps expose the RPKI-valid tag under a different label. This
script probes the live Neo4j session for all plausible RPKI-Valid tag
labels, then re-computes rpki_rate_pct for each of the 9 target countries
and patches the already-written step04 JSON.

Usage (after docker compose load of a single dump):
    python3 -m analysis.countries.fix_rpki_gaps --snapshot 2024-07
"""
import argparse
import json
import sys
from pathlib import Path

from neo4j import GraphDatabase

REPO = Path(__file__).resolve().parent.parent.parent
DATA = REPO / 'analysis' / 'countries' / 'data'
COUNTRIES = ['US', 'CN', 'DE', 'GB', 'JP', 'FR', 'NL', 'IN', 'RU']


def _driver():
    return GraphDatabase.driver('bolt://localhost:7687')


def probe_tag_labels(sess):
    rec = list(sess.run(
        'MATCH (t:Tag) RETURN DISTINCT t.label AS lbl LIMIT 200'))
    return [r['lbl'] for r in rec if r['lbl']]


def probe_prefix_tags(sess):
    """Which tag labels are actually connected to Prefix nodes?"""
    rec = list(sess.run(
        'MATCH (p:Prefix)-[:CATEGORIZED]->(t:Tag) '
        'RETURN DISTINCT t.label AS lbl, count(*) AS c '
        'ORDER BY c DESC LIMIT 100'))
    return [(r['lbl'], r['c']) for r in rec if r['lbl']]


def probe_rpki_via_node_label(sess):
    """Check if RPKI status is via a distinct node label (not Tag)."""
    rec = list(sess.run(
        'CALL db.labels() YIELD label '
        'WHERE label CONTAINS "RPKI" OR label CONTAINS "Rpki" OR '
        '      label CONTAINS "ROA" '
        'RETURN label'))
    return [r['label'] for r in rec]


def pick_rpki_label(labels):
    # Prefer exact matches, fall back to substring
    exact = [l for l in labels if l == 'RPKI Valid']
    if exact:
        return exact[0]
    candidates = [l for l in labels
                  if 'rpki' in l.lower() and 'valid' in l.lower()
                  and 'invalid' not in l.lower()]
    return candidates[0] if candidates else None


def count_rpki_for_country(sess, cc, rpki_label):
    q = """
    MATCH (a:AS)-[:COUNTRY]->(:Country {country_code:$cc})
    MATCH (a)-[:ORIGINATE]->(pfx)
    WHERE pfx:BGPPrefix OR pfx:Prefix
    WITH collect(DISTINCT pfx) AS pfxs
    UNWIND pfxs AS pfx
    OPTIONAL MATCH (pfx)-[:CATEGORIZED]->(t:Tag {label:$lbl})
    RETURN count(DISTINCT pfx) AS total,
           count(DISTINCT CASE WHEN t IS NOT NULL THEN pfx END) AS roa
    """
    r = sess.run(q, {'cc': cc, 'lbl': rpki_label}).single()
    return r['total'], r['roa']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--snapshot', required=True, help='YYYY-MM')
    args = ap.parse_args()
    snap = args.snapshot
    snap_dir = DATA / snap
    if not snap_dir.exists():
        print(f'FATAL: {snap_dir} not found')
        sys.exit(1)

    drv = _driver()
    with drv.session() as sess:
        labels = probe_tag_labels(sess)
        pfx_tags = probe_prefix_tags(sess)
        rpki_nodes = probe_rpki_via_node_label(sess)
        print(f'[{snap}] found {len(labels)} Tag labels; '
              f'RPKI-like: {[l for l in labels if "rpki" in l.lower()]}')
        print(f'[{snap}] Prefix→Tag connections (top 20):')
        for lbl, c in pfx_tags[:20]:
            print(f'    {c:>10}  {lbl}')
        print(f'[{snap}] RPKI/ROA node labels: {rpki_nodes}')
        # If any prefix tag looks RPKI-valid, use it; else bail
        candidates = [l for l, _ in pfx_tags
                      if 'rpki' in l.lower() and 'valid' in l.lower()
                      and 'invalid' not in l.lower()]
        rpki_label = candidates[0] if candidates else None
        if not rpki_label:
            print(f'[{snap}] → no per-Prefix RPKI-Valid tag in this dump; '
                  f'this schema predates IYP prefix-level ROA tagging. '
                  f'Leaving metrics JSONs unchanged.')
            return
        print(f'[{snap}] using tag label: "{rpki_label}"')

        for cc in COUNTRIES:
            total, roa = count_rpki_for_country(sess, cc, rpki_label)
            if total == 0:
                print(f'  {cc}: skip (no prefixes)')
                continue
            pct = round(roa / total * 100, 2)
            mf = snap_dir / cc / 'step04_metrics.json'
            if not mf.exists():
                print(f'  {cc}: no step04 JSON')
                continue
            doc = json.loads(mf.read_text(encoding='utf-8'))
            old = doc['metrics'].get('rpki_rate_pct')
            doc['metrics']['rpki_rate_pct'] = pct
            doc.setdefault('patch', {})['rpki_backfill'] = {
                'probe_label': rpki_label, 'total': total, 'roa': roa,
                'old_value': old,
            }
            mf.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                          encoding='utf-8')
            print(f'  {cc}: {old} → {pct}%  (roa={roa}/total={total})')
    drv.close()


if __name__ == '__main__':
    main()
