"""One-shot extraction for 3 new-angle analyses.

Expects a live Neo4j with a loaded IYP dump at bolt://localhost:7687.
Writes CSVs under data_cache/new_angles/ for downstream offline builds.
"""
import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from analysis.complex_network.utils import run_query  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent.parent.parent / 'data_cache' / 'new_angles'
OUT_DIR.mkdir(parents=True, exist_ok=True)


def write_csv(name, rows, fieldnames):
    path = OUT_DIR / name
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f'  wrote {path} ({len(rows)} rows)', flush=True)


# ---- Topic 1: APNIC eyeball + Worldbank pop ----

def extract_eyeball():
    print('[eyeball] per-AS user-share per country', flush=True)
    q = """
        MATCH (a:AS)-[p:POPULATION]->(c:Country)
        RETURN a.asn AS asn, c.country_code AS cc,
               p.percent AS pct_users, p.samples AS samples
        ORDER BY cc, pct_users DESC
    """
    rows = [dict(r) for r in run_query(q, {})]
    write_csv('eyeball_as_country.csv', rows,
              ['asn', 'cc', 'pct_users', 'samples'])


def extract_worldbank_pop():
    print('[pop] country populations', flush=True)
    # The worldbank crawler stores the count on edge property `value`
    # (see iyp/crawlers/worldbank/country_pop.py).
    q = """
        MATCH (c:Country)-[p:POPULATION]->(:Estimate)
        RETURN c.country_code AS cc, p.value AS population
    """
    rows = [dict(r) for r in run_query(q, {})]
    write_csv('country_population.csv', rows, ['cc', 'population'])


# ---- Topic 2: RPKI × ROVISTA × MANRS ----

def extract_rovista():
    print('[rovista] per-AS ROV enforcement ratio', flush=True)
    q = """
        MATCH (a:AS)-[r:CATEGORIZED]->(t:Tag)
        WHERE t.label IN ['Validating RPKI ROV', 'Not Validating RPKI ROV']
        RETURN a.asn AS asn, t.label AS label, r.ratio AS ratio
    """
    rows = [dict(r) for r in run_query(q, {})]
    write_csv('rovista.csv', rows, ['asn', 'label', 'ratio'])


def extract_manrs():
    print('[manrs] per-AS MANRS action implementation', flush=True)
    q = """
        MATCH (a:AS)-[:IMPLEMENT]->(t:Tag)
        WHERE t.label STARTS WITH 'MANRS Action'
        RETURN a.asn AS asn, t.label AS action
    """
    rows = [dict(r) for r in run_query(q, {})]
    write_csv('manrs.csv', rows, ['asn', 'action'])


def extract_rpki_per_as():
    print('[rpki] per-AS prefix RPKI coverage', flush=True)
    q = """
        MATCH (a:AS)-[:ORIGINATE]->(pfx:Prefix)
        OPTIONAL MATCH (pfx)-[:CATEGORIZED]->(t:Tag {label:'RPKI Valid'})
        WITH a.asn AS asn, count(DISTINCT pfx) AS total,
             count(DISTINCT t) AS rpki
        RETURN asn, total, rpki
    """
    rows = [dict(r) for r in run_query(q, {})]
    write_csv('rpki_per_as.csv', rows, ['asn', 'total', 'rpki'])


def extract_as_country():
    """AS → Country mapping for cross-joins in topics 2 and 1."""
    print('[as_country] AS → Country', flush=True)
    q = """
        MATCH (a:AS)-[:COUNTRY]->(c:Country)
        RETURN a.asn AS asn, c.country_code AS cc
    """
    rows = [dict(r) for r in run_query(q, {})]
    write_csv('as_country.csv', rows, ['asn', 'cc'])


# ---- Topic 3: top-list cross-comparison ----

def extract_top_lists():
    print('[toplists] scanning Ranking nodes', flush=True)
    q = """
        MATCH (r:Ranking)
        WHERE r.name IN [
            'Tranco top 1M',
            'Cisco Umbrella top 1M',
            'OpenINTEL Tranco top 1M'
        ]
        RETURN r.name AS source
    """
    try:
        sources = sorted({r['source'] for r in run_query(q, {})})
        print(f'  found top-1M sources: {sources}', flush=True)
    except Exception as e:
        sources = []
        print(f'  enumerate failed: {e}', flush=True)

    # Also discover CrUX per-country
    q_crux = """
        MATCH (r:Ranking)
        WHERE r.name STARTS WITH 'CrUX top'
        RETURN r.name AS source LIMIT 20
    """
    try:
        crux = sorted({r['source'] for r in run_query(q_crux, {})})
        print(f'  CrUX variants: {len(crux)}', flush=True)
    except Exception as e:
        crux = []

    # Per-source top-N (N=10000) domains to keep CSVs small
    for src in sources:
        q_rank = """
            MATCH (d:DomainName)-[r:RANK]->(rk:Ranking {name:$name})
            RETURN d.name AS domain, r.rank AS rank
            ORDER BY r.rank ASC LIMIT 10000
        """
        rows = [dict(r) for r in run_query(q_rank, {'name': src})]
        slug = (src.lower().replace(' ', '_').replace('top_1m', 'top')
                     .replace("'", ''))
        write_csv(f'toplist_{slug}.csv', rows, ['domain', 'rank'])


# ---- Topic 4/5/6 extract (AS categories / hyperscaler / bgptools tags) ----

def extract_as_categorized():
    """All (AS)-[:CATEGORIZED]->(Tag) with source discriminator.

    Stanford ASDB + bgptools.tags + RPKI + anycast + ... all land on
    the same relation; we keep r.reference_name to separate sources.
    """
    print('[as_categorized] all AS→Tag links with source', flush=True)
    q = """
        MATCH (a:AS)-[r:CATEGORIZED]->(t:Tag)
        RETURN a.asn AS asn, t.label AS tag,
               r.reference_name AS source, r.layer AS layer
    """
    rows = [dict(r) for r in run_query(q, {})]
    write_csv('as_categorized.csv', rows,
              ['asn', 'tag', 'source', 'layer'])


def extract_aws_prefixes():
    """Amazon AWS GeoPrefix → service + country.

    crawler writes (GeoPrefix)-[:CATEGORIZED]->(Tag {label:'<service>'}),
    (GeoPrefix)-[:COUNTRY]->(Country).
    """
    print('[aws] AWS GeoPrefix → service + country', flush=True)
    q = """
        MATCH (p:GeoPrefix)-[r:CATEGORIZED]->(t:Tag)
        WHERE r.reference_name CONTAINS 'amazon'
        OPTIONAL MATCH (p)-[:COUNTRY]->(c:Country)
        RETURN p.prefix AS prefix, t.label AS service,
               c.country_code AS cc
    """
    rows = [dict(r) for r in run_query(q, {})]
    write_csv('aws_prefixes.csv', rows, ['prefix', 'service', 'cc'])


def extract_hyperscaler_origin():
    """ASes that originate AWS/hyperscaler prefixes."""
    print('[hyperscaler] ASes originating AWS/cloud prefixes', flush=True)
    q = """
        MATCH (a:AS)-[:ORIGINATE]->(p:Prefix)<-[r:CATEGORIZED]-(:AS {asn:0})
        RETURN a.asn AS asn LIMIT 0
    """
    # Fallback: look at ASes managing AWS-tagged prefixes
    q2 = """
        MATCH (a:AS)-[:ORIGINATE]->(p:GeoPrefix)-[r:CATEGORIZED]->(t:Tag)
        WHERE r.reference_name CONTAINS 'amazon'
        RETURN DISTINCT a.asn AS asn, t.label AS service
        LIMIT 5000
    """
    try:
        rows = [dict(r) for r in run_query(q2, {})]
    except Exception as e:
        print(f'  hyperscaler query failed: {e}', flush=True)
        rows = []
    write_csv('hyperscaler_originators.csv', rows, ['asn', 'service'])


def main():
    print(f'output dir: {OUT_DIR}', flush=True)
    extract_as_country()
    extract_eyeball()
    extract_worldbank_pop()
    extract_rovista()
    extract_manrs()
    extract_rpki_per_as()
    extract_top_lists()
    extract_as_categorized()
    extract_aws_prefixes()
    extract_hyperscaler_origin()
    print('done', flush=True)


if __name__ == '__main__':
    main()
