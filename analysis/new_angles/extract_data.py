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


# ---- Topic 7/8/9 extract: OONI, PeeringDB, Atlas ----

def extract_ooni():
    """OONI per-test censorship measurements.

    Schema: (AS)-[:CENSORED {country_code, percentage_*, count_*, total_count}]
            ->(Tag {label: 'OONI <TestName> Test'})
    """
    print('[ooni] per-test measurements', flush=True)
    q = """
        MATCH (a:AS)-[r:CENSORED]->(t:Tag)
        WHERE t.label STARTS WITH 'OONI'
        RETURN a.asn AS asn, t.label AS test,
               r.country_code AS cc,
               r.total_count AS total,
               r.percentage_dns_blocking AS pct_dns,
               r.percentage_tcp_blocking AS pct_tcp,
               r.percentage_both_blocked AS pct_both,
               r.percentage_unblocked AS pct_ok
    """
    rows = [dict(r) for r in run_query(q, {})]
    write_csv('ooni_censored.csv', rows,
              ['asn', 'test', 'cc', 'total',
               'pct_dns', 'pct_tcp', 'pct_both', 'pct_ok'])


def extract_peeringdb_orgs():
    """PeeringDB org full-record view.

    Crawler stores the flattened org json as props on :EXTERNAL_ID edge.
    """
    print('[peeringdb] org records', flush=True)
    q = """
        MATCH (org:Organization)-[r:EXTERNAL_ID]->(o:OpaqueID)
        WHERE r.reference_name = 'peeringdb.org'
        RETURN o.id AS pdb_id,
               r.name AS name,
               r.info_type AS info_type,
               r.info_ratio AS info_ratio,
               r.info_traffic AS info_traffic,
               r.info_scope AS info_scope,
               r.policy_general AS policy_general,
               r.policy_locations AS policy_locations,
               r.policy_ratio AS policy_ratio,
               r.policy_contracts AS policy_contracts,
               r.country AS country
    """
    try:
        rows = [dict(r) for r in run_query(q, {})]
    except Exception as e:
        print(f'  peeringdb query failed: {e}', flush=True)
        rows = []
    write_csv('peeringdb_orgs.csv', rows,
              ['pdb_id', 'name', 'info_type', 'info_ratio', 'info_traffic',
               'info_scope', 'policy_general', 'policy_locations',
               'policy_ratio', 'policy_contracts', 'country'])


def extract_atlas_probes():
    """RIPE Atlas probe distribution + capability tags."""
    print('[atlas] probes + tags', flush=True)
    q = """
        MATCH (p:AtlasProbe)
        OPTIONAL MATCH (p)-[:COUNTRY]->(c:Country)
        OPTIONAL MATCH (p)-[:ASSIGNED]->(t:Tag)
        RETURN p.id AS id, c.country_code AS cc,
               p.status AS status,
               collect(DISTINCT t.label) AS tags
    """
    try:
        recs = run_query(q, {})
    except Exception as e:
        print(f'  atlas query failed: {e}', flush=True)
        write_csv('atlas_probes.csv', [], ['id', 'cc', 'status', 'tags'])
        return
    rows = []
    for r in recs:
        d = dict(r)
        d['tags'] = '|'.join(sorted(d.get('tags') or []))
        rows.append(d)
    write_csv('atlas_probes.csv', rows, ['id', 'cc', 'status', 'tags'])


# ---- Topic 10/11/12: BGP collector / IANA allocation / IHR hegemony ----

def extract_bgp_collector():
    """BGP collector observations: how many collectors see each AS.

    PCH + BGPKit snapshots should provide per-collector AS visibility.
    Schema assumption: (BGPCollector)-[:PART_OF|...]->? or tag-based.
    Probe label existence first.
    """
    print('[bgp_collector] collector → AS visibility', flush=True)
    try:
        label_chk = run_query(
            'MATCH (c:BGPCollector) RETURN count(c) AS c', {})
        n = list(label_chk[0].values())[0] if label_chk else 0
        print(f'  BGPCollector nodes: {n}', flush=True)
    except Exception as e:
        print(f'  BGPCollector label missing: {e}', flush=True)
        n = 0
    if n == 0:
        write_csv('bgp_collectors.csv', [], ['collector', 'n_asns'])
        write_csv('collector_per_as.csv', [], ['asn', 'n_collectors'])
        return

    q = """
        MATCH (a:AS)-[r:PEERS_WITH]->(b:AS)
        WITH a.asn AS asn, r.reference_name AS src, count(*) AS peer_count
        WHERE src CONTAINS 'pch' OR src CONTAINS 'bgpkit'
        RETURN asn, src, peer_count
    """
    try:
        rows = [dict(r) for r in run_query(q, {})]
    except Exception as e:
        print(f'  collector query failed: {e}', flush=True)
        rows = []
    write_csv('collector_observations.csv', rows,
              ['asn', 'src', 'peer_count'])


def extract_iana_nro():
    """Country-level IANA + NRO address allocation.

    Schema probe: IANAPrefix / RIRPrefix labels, ASSIGNED/RESERVED relations.
    """
    print('[iana_nro] registry-level allocations', flush=True)
    for label in ('IANAPrefix', 'RIRPrefix'):
        try:
            r = run_query(
                f'MATCH (p:{label}) RETURN count(p) AS c', {})
            n = list(r[0].values())[0] if r else 0
            print(f'  {label} nodes: {n}', flush=True)
        except Exception as e:
            print(f'  {label} missing: {e}', flush=True)

    # Country-level RIR allocations via NRO delegated stats
    q = """
        MATCH (p:RIRPrefix)-[r:ASSIGNED]->(c:Country)
        RETURN c.country_code AS cc, p.prefix AS prefix,
               r.reference_name AS src
        LIMIT 100000
    """
    try:
        rows = [dict(r) for r in run_query(q, {})]
    except Exception as e:
        print(f'  NRO query failed: {e}', flush=True)
        rows = []
    write_csv('nro_country_prefixes.csv', rows, ['cc', 'prefix', 'src'])


def extract_ihr_hegemony():
    """IHR local hegemony scores per AS.

    Schema: (AS)-[:DEPENDS_ON {hege}]->(AS) — already used indirectly.
    Here we aggregate to per-AS hegemony centrality.
    """
    print('[ihr] AS-level hegemony detail', flush=True)
    # Each dependency edge has a hege score. We aggregate:
    #   incoming_hege = sum of hege on edges ending at AS (how much others
    #     depend on this AS)
    #   outgoing_hege = sum of hege on edges starting from AS
    q = """
        MATCH (a:AS)-[r:DEPENDS_ON]->(b:AS)
        WHERE r.hege IS NOT NULL
        WITH b.asn AS dep_on, sum(r.hege) AS incoming,
             count(a) AS n_deps
        RETURN dep_on AS asn, incoming, n_deps
        ORDER BY incoming DESC LIMIT 5000
    """
    try:
        rows = [dict(r) for r in run_query(q, {})]
    except Exception as e:
        print(f'  hegemony query failed: {e}', flush=True)
        rows = []
    write_csv('ihr_hegemony_incoming.csv', rows,
              ['asn', 'incoming', 'n_deps'])


# ---- T16: Alice-LG live IXP members (13 IXPs) ----

def extract_alice_lg_members():
    """13 alice_lg crawlers produce MEMBER_OF edges with live session state.

    Reference-name filter picks out alice_lg-sourced records specifically
    (vs peeringdb-sourced MEMBER_OF which lacks the live props).
    """
    print('[alice_lg] live IXP member sessions', flush=True)
    q = """
        MATCH (a:AS)-[m:MEMBER_OF]->(i:IXP)
        WHERE m.reference_name STARTS WITH 'alice_lg.'
        RETURN a.asn AS asn, i.name AS ixp_name,
               m.reference_name AS source,
               m.state AS state,
               m.uptime AS uptime,
               m.routes_received AS routes_received,
               m.description AS description,
               m.address AS address
    """
    try:
        rows = [dict(r) for r in run_query(q, {})]
    except Exception as e:
        print(f'  alice_lg query failed: {e}', flush=True)
        rows = []
    write_csv('ixp_live_members.csv', rows,
              ['asn', 'ixp_name', 'source', 'state',
               'uptime', 'routes_received', 'description', 'address'])


# ---- T17: PCH multi-collector consensus ----

def extract_pch_collectors():
    """PCH ORIGINATE edges carry collector count + collector list.

    Compares to BGPKit/RIS coverage via separate datasets.
    """
    print('[pch] per-prefix collector consensus', flush=True)
    q = """
        MATCH (a:AS)-[o:ORIGINATE]->(p:Prefix)
        WHERE o.reference_name STARTS WITH 'pch.'
        RETURN a.asn AS asn, p.prefix AS prefix, p.af AS af,
               o.count AS n_collectors,
               o.seen_by_collectors AS seen_by,
               o.reference_name AS source
        LIMIT 500000
    """
    try:
        rows = [dict(r) for r in run_query(q, {})]
    except Exception as e:
        print(f'  pch query failed: {e}', flush=True)
        rows = []
    write_csv('pch_prefix_collectors.csv', rows,
              ['asn', 'prefix', 'af', 'n_collectors', 'seen_by', 'source'])


# ---- T18a/b: Cloudflare DNS traffic ----

def extract_cf_dns_countries():
    """Cloudflare 1.1.1.1 DNS query origins per country.

    Schema: (DomainName)-[:DNS_ACTIVITY {value, clientCountryAlpha2}]->...
    """
    print('[cf_dns_country] Cloudflare DNS by country', flush=True)
    q = """
        MATCH (d:DomainName)-[r:DNS_ACTIVITY]->(c:Country)
        WHERE r.reference_name = 'cloudflare.dns_top_locations'
        RETURN d.name AS domain, c.country_code AS cc,
               r.value AS value_pct
        ORDER BY value_pct DESC
        LIMIT 50000
    """
    try:
        rows = [dict(r) for r in run_query(q, {})]
    except Exception as e:
        print(f'  cf_dns_country query failed: {e}', flush=True)
        rows = []
    write_csv('cf_dns_top_countries.csv', rows,
              ['domain', 'cc', 'value_pct'])


def extract_cf_dns_ases():
    """Cloudflare 1.1.1.1 DNS query origins per AS."""
    print('[cf_dns_as] Cloudflare DNS by AS', flush=True)
    q = """
        MATCH (d:DomainName)-[r:DNS_ACTIVITY]->(a:AS)
        WHERE r.reference_name = 'cloudflare.dns_top_ases'
        RETURN d.name AS domain, a.asn AS asn,
               r.value AS value_pct
        ORDER BY value_pct DESC
        LIMIT 100000
    """
    try:
        rows = [dict(r) for r in run_query(q, {})]
    except Exception as e:
        print(f'  cf_dns_as query failed: {e}', flush=True)
        rows = []
    write_csv('cf_dns_top_ases.csv', rows, ['domain', 'asn', 'value_pct'])


# ---- T18c: Google CRUX per country ----

def extract_crux_by_country():
    """Google CRUX top 1M hostnames per country — real browser data."""
    print('[crux] Google CRUX top by country', flush=True)
    q = """
        MATCH (h:HostName)-[rk:RANK]->(r:Ranking)
        WHERE rk.reference_name = 'google.crux_top1m_country'
        RETURN h.name AS hostname, r.name AS ranking,
               rk.rank AS rank, rk.country_code AS cc
        ORDER BY rank ASC
        LIMIT 200000
    """
    try:
        rows = [dict(r) for r in run_query(q, {})]
    except Exception as e:
        print(f'  crux query failed: {e}', flush=True)
        rows = []
    write_csv('crux_top_by_country.csv', rows,
              ['hostname', 'ranking', 'rank', 'cc'])


# ---- T19: OONI 12-app censorship ----

def extract_ooni_apps():
    """All OONI app-specific tests (non-webconnectivity).

    Each app crawler produces CENSORED edges with Tag labels like
    "OONI Telegram Test" etc. We union everything, per-AS per-country.
    """
    print('[ooni_apps] 12 app-specific tests', flush=True)
    q = """
        MATCH (a:AS)-[r:CENSORED]->(t:Tag)
        WHERE t.label STARTS WITH 'OONI '
          AND t.label <> 'OONI Web Connectivity Test'
        RETURN a.asn AS asn, t.label AS app_tag,
               r.country_code AS cc,
               r.total_count AS total,
               r.percentage_total_blocked AS pct_blocked,
               r.percentage_total_ok AS pct_ok,
               r.percentage_dns_blocking AS pct_dns,
               r.percentage_tcp_blocking AS pct_tcp
    """
    try:
        rows = [dict(r) for r in run_query(q, {})]
    except Exception as e:
        print(f'  ooni apps query failed: {e}', flush=True)
        rows = []
    write_csv('ooni_apps_matrix.csv', rows,
              ['asn', 'app_tag', 'cc', 'total',
               'pct_blocked', 'pct_ok', 'pct_dns', 'pct_tcp'])


# ---- T20: UTwente LACES anycast geographic census ----

def extract_laces_geoprefix():
    """LACES v4/v6 GeoPrefixes with location points."""
    print('[laces] GeoPrefix locations', flush=True)
    q = """
        MATCH (g:GeoPrefix)-[:LOCATED_IN]->(p:Point)
        OPTIONAL MATCH (g)-[:COUNTRY]->(c:Country)
        OPTIONAL MATCH (g)-[:CATEGORIZED]->(t:Tag {label:'Anycast'})
        RETURN g.prefix AS prefix, g.af AS af,
               c.country_code AS cc,
               p.lat AS lat, p.lng AS lng,
               CASE WHEN t IS NOT NULL THEN 1 ELSE 0 END AS is_anycast
        LIMIT 500000
    """
    try:
        rows = [dict(r) for r in run_query(q, {})]
    except Exception as e:
        print(f'  laces query failed: {e}', flush=True)
        rows = []
    write_csv('laces_geoprefix_countries.csv', rows,
              ['prefix', 'af', 'cc', 'lat', 'lng', 'is_anycast'])


# ---- T21: DNS authority (forward + reverse + root) ----

def extract_ns_authority_forward():
    """openintel.infra_ns MANAGED_BY — forward DNS authority."""
    print('[ns_forward] infra_ns forward authority', flush=True)
    q = """
        MATCH (d:DomainName)-[m:MANAGED_BY]->(n)
        WHERE m.reference_name = 'openintel.infra_ns'
          AND (n:HostName OR n:AuthoritativeNameServer)
        RETURN d.name AS domain, n.name AS ns_host
        LIMIT 1000000
    """
    try:
        rows = [dict(r) for r in run_query(q, {})]
    except Exception as e:
        print(f'  ns_forward query failed: {e}', flush=True)
        rows = []
    write_csv('ns_authority_forward.csv', rows, ['domain', 'ns_host'])


def extract_ns_authority_rdns():
    """simulamet.rirdata_rdns MANAGED_BY — reverse DNS authority per prefix."""
    print('[ns_reverse] rirdata_rdns reverse authority', flush=True)
    q = """
        MATCH (p)-[m:MANAGED_BY]->(n)
        WHERE m.reference_name = 'simulamet.rirdata_rdns'
          AND (p:RDNSPrefix OR p:Prefix)
          AND (n:HostName OR n:AuthoritativeNameServer)
        RETURN p.prefix AS prefix, n.name AS ns_host,
               m.source AS rir_source
        LIMIT 500000
    """
    try:
        rows = [dict(r) for r in run_query(q, {})]
    except Exception as e:
        print(f'  ns_reverse query failed: {e}', flush=True)
        rows = []
    write_csv('rdns_authority.csv', rows, ['prefix', 'ns_host', 'rir_source'])


def extract_root_zone_ns():
    """iana.root_zone — who manages each TLD."""
    print('[root_ns] IANA root zone NS', flush=True)
    q = """
        MATCH (d:DomainName)-[m:MANAGED_BY]->(n)
        WHERE m.reference_name = 'iana.root_zone'
          AND (n:HostName OR n:AuthoritativeNameServer)
        RETURN d.name AS tld, n.name AS ns_host
    """
    try:
        rows = [dict(r) for r in run_query(q, {})]
    except Exception as e:
        print(f'  root_ns query failed: {e}', flush=True)
        rows = []
    write_csv('root_zone_ns.csv', rows, ['tld', 'ns_host'])


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
    extract_ooni()
    extract_peeringdb_orgs()
    extract_atlas_probes()
    extract_bgp_collector()
    extract_iana_nro()
    extract_ihr_hegemony()
    # T16-T21 new extractions
    extract_alice_lg_members()
    extract_pch_collectors()
    extract_cf_dns_countries()
    extract_cf_dns_ases()
    extract_crux_by_country()
    extract_ooni_apps()
    extract_laces_geoprefix()
    extract_ns_authority_forward()
    extract_ns_authority_rdns()
    extract_root_zone_ns()
    print('done', flush=True)


if __name__ == '__main__':
    main()
