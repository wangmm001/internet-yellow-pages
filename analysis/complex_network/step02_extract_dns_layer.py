"""Step 2: Extract DNS resolution layer from IYP Neo4j."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.complex_network.utils import run_query, DATA_DIR
import csv
import time

def main():
    t0 = time.time()

    # 2a. AS-level hosting aggregation (HostName → IP → Prefix → AS)
    print('Extracting AS-level DNS hosting stats...')
    hosting = run_query('''
        MATCH (h:HostName)-[:RESOLVES_TO]->(ip:IP)-[:PART_OF]->(pfx:Prefix)
              <-[:ORIGINATE]-(a:AS)
        RETURN a.asn AS asn,
               COUNT(DISTINCT h) AS hostname_count,
               COUNT(DISTINCT ip) AS ip_count
        ORDER BY hostname_count DESC
    ''')
    path = os.path.join(DATA_DIR, 'dns_as_hosting.csv')
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['asn', 'hostname_count', 'ip_count'])
        w.writeheader()
        w.writerows(hosting)
    print(f'  DNS AS hosting: {len(hosting):,} ASes -> {path}')

    # 2b. AuthNS dominance (DomainName → AuthoritativeNameServer)
    print('Extracting DNS authority distribution...')
    auth = run_query('''
        MATCH (d:DomainName)-[:MANAGED_BY]->(ns:AuthoritativeNameServer)
        RETURN ns.name AS ns_name,
               COUNT(DISTINCT d) AS domain_count
        ORDER BY domain_count DESC
        LIMIT 500
    ''')
    path2 = os.path.join(DATA_DIR, 'dns_authority_top500.csv')
    with open(path2, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['ns_name', 'domain_count'])
        w.writeheader()
        w.writerows(auth)
    print(f'  DNS authority: {len(auth):,} top NS -> {path2}')

    # 2c. CNAME alias chains (top platforms)
    print('Extracting CNAME alias distribution...')
    cname = run_query('''
        MATCH (h1:HostName)-[:ALIAS_OF]->(h2:HostName)
        WITH h2.name AS target, COUNT(DISTINCT h1) AS alias_count
        WHERE alias_count > 100
        RETURN target, alias_count
        ORDER BY alias_count DESC
        LIMIT 200
    ''')
    path3 = os.path.join(DATA_DIR, 'cname_top_targets.csv')
    with open(path3, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['target', 'alias_count'])
        w.writeheader()
        w.writerows(cname)
    print(f'  CNAME targets: {len(cname):,} targets -> {path3}')

    # 2d. DNS dependency: which AS hosts the AuthNS for each domain
    print('Extracting AuthNS-to-AS mapping...')
    ns_as = run_query('''
        MATCH (ns:AuthoritativeNameServer)
        WHERE EXISTS { (ns)<-[:MANAGED_BY]-(:DomainName) }
        OPTIONAL MATCH (ns_host:HostName {name: ns.name})-[:RESOLVES_TO]->(ip:IP)
                       -[:PART_OF]->(pfx:Prefix)<-[:ORIGINATE]-(a:AS)
        RETURN ns.name AS ns_name, COLLECT(DISTINCT a.asn) AS hosting_asns
    ''')
    path4 = os.path.join(DATA_DIR, 'ns_to_as.csv')
    with open(path4, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['ns_name', 'hosting_asns'])
        w.writeheader()
        for row in ns_as:
            row['hosting_asns'] = '|'.join(str(x) for x in row['hosting_asns']) if row['hosting_asns'] else ''
            w.writerow(row)
    print(f'  NS-to-AS mapping: {len(ns_as):,} nameservers -> {path4}')

    print(f'\nStep 2 complete in {time.time()-t0:.1f}s')


if __name__ == '__main__':
    main()
