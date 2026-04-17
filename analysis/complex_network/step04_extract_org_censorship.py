"""Step 4: Extract organization-governance and censorship layers from IYP Neo4j."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.complex_network.utils import run_query, DATA_DIR
import csv
import time

def main():
    t0 = time.time()

    # 4a. AS → Organization ownership
    print('Extracting AS-Organization ownership...')
    org = run_query('''
        MATCH (a:AS)-[:MANAGED_BY]->(o:Organization)
        OPTIONAL MATCH (o)-[:COUNTRY]->(c:Country)
        RETURN a.asn AS asn, o.name AS org_name,
               COLLECT(DISTINCT c.country_code) AS org_countries
    ''')
    path = os.path.join(DATA_DIR, 'as_organization.csv')
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['asn', 'org_name', 'org_countries'])
        w.writeheader()
        for row in org:
            row['org_countries'] = '|'.join(row['org_countries']) if row['org_countries'] else ''
            w.writerow(row)
    print(f'  AS-Organization: {len(org):,} edges -> {path}')

    # 4b. AS sibling groups
    print('Extracting AS sibling relationships...')
    siblings = run_query('''
        MATCH (a:AS)-[:SIBLING_OF]-(b:AS)
        WHERE a.asn < b.asn
        RETURN DISTINCT a.asn AS src, b.asn AS dst
    ''')
    path2 = os.path.join(DATA_DIR, 'as_siblings.csv')
    with open(path2, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['src', 'dst'])
        w.writeheader()
        w.writerows(siblings)
    print(f'  AS siblings: {len(siblings):,} pairs -> {path2}')

    # 4c. Censorship detections
    print('Extracting censorship detections...')
    censor = run_query('''
        MATCH (a:AS)-[c:CENSORED]->(t)
        RETURN a.asn AS asn,
               labels(t)[0] AS target_type,
               c.reference_name AS test_name,
               COUNT(*) AS detection_count
    ''')
    path3 = os.path.join(DATA_DIR, 'censorship.csv')
    with open(path3, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['asn', 'target_type', 'test_name', 'detection_count'])
        w.writeheader()
        w.writerows(censor)
    print(f'  Censorship: {len(censor):,} detections -> {path3}')

    # 4d. Organization power index (ASes + prefixes per org)
    print('Extracting organization power index...')
    org_power = run_query('''
        MATCH (o:Organization)<-[:MANAGED_BY]-(a:AS)
        WITH o, COLLECT(DISTINCT a.asn) AS asns, COUNT(DISTINCT a) AS as_count
        OPTIONAL MATCH (o)-[:COUNTRY]->(c:Country)
        RETURN o.name AS org_name,
               as_count,
               COLLECT(DISTINCT c.country_code) AS countries
        ORDER BY as_count DESC
        LIMIT 500
    ''')
    path4 = os.path.join(DATA_DIR, 'org_power_top500.csv')
    with open(path4, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['org_name', 'as_count', 'countries'])
        w.writeheader()
        for row in org_power:
            row['countries'] = '|'.join(row['countries']) if row['countries'] else ''
            w.writerow(row)
    print(f'  Organization power: {len(org_power):,} orgs -> {path4}')

    # 4e. AS country assignment
    print('Extracting AS-Country assignments...')
    as_country = run_query('''
        MATCH (a:AS)-[:COUNTRY]->(c:Country)
        RETURN a.asn AS asn, c.country_code AS country
    ''')
    path5 = os.path.join(DATA_DIR, 'as_country.csv')
    with open(path5, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['asn', 'country'])
        w.writeheader()
        w.writerows(as_country)
    print(f'  AS-Country: {len(as_country):,} assignments -> {path5}')

    print(f'\nStep 4 complete in {time.time()-t0:.1f}s')


if __name__ == '__main__':
    main()
