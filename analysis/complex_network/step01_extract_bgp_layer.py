"""Step 1: Extract AS-BGP topology layer from IYP Neo4j."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.complex_network.utils import run_query, DATA_DIR
import csv
import time

def main():
    t0 = time.time()

    # 1a. AS peering graph (deduplicated, undirected)
    print('Extracting AS peering edges...')
    peering = run_query('''
        MATCH (a:AS)-[r:PEERS_WITH]-(b:AS)
        WHERE a.asn < b.asn
        RETURN DISTINCT a.asn AS src, b.asn AS dst
    ''')
    path = os.path.join(DATA_DIR, 'bgp_peering.csv')
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['src', 'dst'])
        w.writeheader()
        w.writerows(peering)
    print(f'  BGP peering: {len(peering):,} unique edges -> {path}')

    # 1b. AS dependency graph (directed, with hegemony weight)
    print('Extracting AS dependency edges...')
    deps = run_query('''
        MATCH (a:AS)-[r:DEPENDS_ON]->(b:AS)
        RETURN a.asn AS src, b.asn AS dst, r.hege AS hege
    ''')
    path2 = os.path.join(DATA_DIR, 'as_dependency.csv')
    with open(path2, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['src', 'dst', 'hege'])
        w.writeheader()
        w.writerows(deps)
    print(f'  AS dependency: {len(deps):,} edges -> {path2}')

    # 1c. AS originate prefixes (for prefix count per AS)
    print('Extracting AS prefix origination...')
    orig = run_query('''
        MATCH (pfx:BGPPrefix)<-[r:ORIGINATE]-(a:AS)
        RETURN a.asn AS asn, COUNT(DISTINCT pfx) AS prefix_count
        ORDER BY prefix_count DESC
    ''')
    path3 = os.path.join(DATA_DIR, 'as_prefix_count.csv')
    with open(path3, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['asn', 'prefix_count'])
        w.writeheader()
        w.writerows(orig)
    print(f'  AS prefix origination: {len(orig):,} ASes -> {path3}')

    # 1d. AS metadata (country, tags)
    print('Extracting AS metadata...')
    meta = run_query('''
        MATCH (a:AS)
        OPTIONAL MATCH (a)-[:COUNTRY]->(c:Country)
        WITH a, COLLECT(DISTINCT c.country_code) AS countries
        OPTIONAL MATCH (a)-[:CATEGORIZED]->(t:Tag)
        RETURN a.asn AS asn,
               countries,
               COLLECT(DISTINCT t.label) AS tags
    ''')
    path4 = os.path.join(DATA_DIR, 'as_metadata.csv')
    with open(path4, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['asn', 'countries', 'tags'])
        w.writeheader()
        for row in meta:
            row['countries'] = '|'.join(row['countries']) if row['countries'] else ''
            row['tags'] = '|'.join(row['tags']) if row['tags'] else ''
            w.writerow(row)
    print(f'  AS metadata: {len(meta):,} ASes -> {path4}')

    print(f'\nStep 1 complete in {time.time()-t0:.1f}s')


if __name__ == '__main__':
    main()
