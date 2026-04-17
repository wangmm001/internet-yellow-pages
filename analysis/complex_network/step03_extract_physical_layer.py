"""Step 3: Extract physical infrastructure layer from IYP Neo4j."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.complex_network.utils import run_query, DATA_DIR
import csv
import time

def main():
    t0 = time.time()

    # 3a. AS-IXP membership bipartite graph
    print('Extracting AS-IXP membership...')
    ixp = run_query('''
        MATCH (a:AS)-[:MEMBER_OF]->(ix:IXP)
        OPTIONAL MATCH (ix)-[:COUNTRY]->(c:Country)
        RETURN a.asn AS asn, ix.name AS ixp_name,
               COLLECT(DISTINCT c.country_code) AS ixp_countries
    ''')
    path = os.path.join(DATA_DIR, 'as_ixp_membership.csv')
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['asn', 'ixp_name', 'ixp_countries'])
        w.writeheader()
        for row in ixp:
            row['ixp_countries'] = '|'.join(row['ixp_countries']) if row['ixp_countries'] else ''
            w.writerow(row)
    print(f'  AS-IXP membership: {len(ixp):,} edges -> {path}')

    # 3b. AS-Facility co-location
    print('Extracting AS-Facility co-location...')
    fac = run_query('''
        MATCH (a:AS)-[:LOCATED_IN]->(f:Facility)
        OPTIONAL MATCH (f)-[:COUNTRY]->(c:Country)
        RETURN a.asn AS asn, f.name AS facility_name,
               COLLECT(DISTINCT c.country_code) AS fac_countries
    ''')
    path2 = os.path.join(DATA_DIR, 'as_facility.csv')
    with open(path2, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['asn', 'facility_name', 'fac_countries'])
        w.writeheader()
        for row in fac:
            row['fac_countries'] = '|'.join(row['fac_countries']) if row['fac_countries'] else ''
            w.writerow(row)
    print(f'  AS-Facility: {len(fac):,} edges -> {path2}')

    # 3c. IXP co-location network (ASes sharing IXPs)
    print('Extracting IXP-based AS co-location (top IXPs)...')
    coloc = run_query('''
        MATCH (a:AS)-[:MEMBER_OF]->(ix:IXP)<-[:MEMBER_OF]-(b:AS)
        WHERE a.asn < b.asn
        WITH a.asn AS src, b.asn AS dst, COUNT(DISTINCT ix) AS shared_ixps
        WHERE shared_ixps >= 3
        RETURN src, dst, shared_ixps
        ORDER BY shared_ixps DESC
        LIMIT 50000
    ''')
    path3 = os.path.join(DATA_DIR, 'as_shared_ixps.csv')
    with open(path3, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['src', 'dst', 'shared_ixps'])
        w.writeheader()
        w.writerows(coloc)
    print(f'  AS shared IXPs (>=3): {len(coloc):,} pairs -> {path3}')

    # 3d. IXP stats
    print('Extracting IXP membership counts...')
    ixp_stats = run_query('''
        MATCH (ix:IXP)<-[:MEMBER_OF]-(a:AS)
        OPTIONAL MATCH (ix)-[:COUNTRY]->(c:Country)
        RETURN ix.name AS ixp_name,
               COLLECT(DISTINCT c.country_code) AS countries,
               COUNT(DISTINCT a) AS member_count
        ORDER BY member_count DESC
    ''')
    path4 = os.path.join(DATA_DIR, 'ixp_stats.csv')
    with open(path4, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['ixp_name', 'countries', 'member_count'])
        w.writeheader()
        for row in ixp_stats:
            row['countries'] = '|'.join(row['countries']) if row['countries'] else ''
            w.writerow(row)
    print(f'  IXP stats: {len(ixp_stats):,} IXPs -> {path4}')

    print(f'\nStep 3 complete in {time.time()-t0:.1f}s')


if __name__ == '__main__':
    main()
