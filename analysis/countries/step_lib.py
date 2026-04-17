"""Country-parameterized step extractors.

Each step_NN(country, snapshot) returns a metrics dict and optionally writes a
small per-country CSV. All 20 steps from analysis/china/ generalized.

Heavy cached CSVs (bgp_peering, as_dependency, as_metadata, ...) are loaded ONCE
per process via lru_cache; subsequent country calls reuse them.

Steps needing live Neo4j fail gracefully and return a minimal metrics dict marked
{'_error': '...'} so cross-country comparison remains possible.
"""
import csv
import os
import sys
from collections import Counter, defaultdict
from functools import lru_cache

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.countries.common import (  # noqa: E402
    COLORS, COUNTRY_NAME, DATA_DIR, bilingual, load_all_target_country_ases,
    load_as_country_map, load_as_metadata, load_country_as_map, load_country_ases,
    neo4j_available, snapshot_country_dir, write_country_csv, write_country_metrics, zh,
)
from analysis.complex_network.utils import DATA_DIR as CACHE_DIR, run_query


# ─────────────────────────────────────────────────────────────
# Lazy-loaded cached CSVs (shared across all countries)
# ─────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def _as_metadata():
    return load_as_metadata()


@lru_cache(maxsize=1)
def _country_as_map():
    return load_country_as_map()


@lru_cache(maxsize=1)
def _peering_edges():
    """Return list of (a, b) AS peering edges (a < b)."""
    path = os.path.join(CACHE_DIR, 'bgp_peering.csv')
    edges = []
    if not os.path.exists(path):
        return edges
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                s, d = int(r['src']), int(r['dst'])
            except Exception:
                continue
            if s == d:
                continue
            if s > d:
                s, d = d, s
            edges.append((s, d))
    return edges


@lru_cache(maxsize=1)
def _centrality():
    """Return dict[asn] -> {degree, betweenness, eigenvector, pagerank}."""
    path = os.path.join(CACHE_DIR, 'step07_centrality_full.csv')
    mp = {}
    if not os.path.exists(path):
        return mp
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                mp[int(r['asn'])] = {
                    'degree': float(r['degree']),
                    'betweenness': float(r['betweenness']),
                    'eigenvector': float(r['eigenvector']),
                    'pagerank': float(r['pagerank']),
                }
            except Exception:
                continue
    return mp


@lru_cache(maxsize=1)
def _coreness():
    path = os.path.join(CACHE_DIR, 'step08_coreness.csv')
    mp = {}
    if not os.path.exists(path):
        return mp
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                mp[int(r['asn'])] = int(r['coreness'])
            except Exception:
                continue
    return mp


@lru_cache(maxsize=1)
def _as_prefix_count():
    mp = {}
    path = os.path.join(CACHE_DIR, 'as_prefix_count.csv')
    if not os.path.exists(path):
        return mp
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                mp[int(r['asn'])] = int(r['prefix_count'])
            except Exception:
                continue
    return mp


@lru_cache(maxsize=1)
def _dependency_edges():
    """(src, dst, hege) list."""
    path = os.path.join(CACHE_DIR, 'as_dependency.csv')
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                s = int(r['src'])
                d = int(r['dst'])
                h = float(r['hege'])
            except Exception:
                continue
            if s != d:
                out.append((s, d, h))
    return out


@lru_cache(maxsize=1)
def _ixp_membership():
    """dict: ixp_name -> {'asns': set, 'country': cc}."""
    path = os.path.join(CACHE_DIR, 'as_ixp_membership.csv')
    mp = {}
    if not os.path.exists(path):
        return mp
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                asn = int(r['asn'])
            except Exception:
                continue
            ixp = r['ixp_name']
            ccs = (r.get('ixp_countries') or '').split('|')
            entry = mp.setdefault(ixp, {'asns': set(), 'country': (ccs[0] if ccs else 'ZZ')})
            entry['asns'].add(asn)
    return mp


@lru_cache(maxsize=1)
def _facility_membership():
    """dict: (asn, facility) -> country_code."""
    path = os.path.join(CACHE_DIR, 'as_facility.csv')
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                asn = int(r['asn'])
            except Exception:
                continue
            fac = r['facility_name']
            ccs = (r.get('fac_countries') or '').split('|')
            out.append((asn, fac, ccs[0] if ccs else 'ZZ'))
    return out


@lru_cache(maxsize=1)
def _as_organization():
    """dict: asn -> (org_name, countries)."""
    path = os.path.join(CACHE_DIR, 'as_organization.csv')
    mp = {}
    if not os.path.exists(path):
        return mp
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                mp[int(r['asn'])] = (r.get('org_name', ''),
                                     (r.get('org_countries') or '').split('|'))
            except Exception:
                continue
    return mp


@lru_cache(maxsize=1)
def _dns_as_hosting():
    """dict: asn -> hostname_count."""
    path = os.path.join(CACHE_DIR, 'dns_as_hosting.csv')
    mp = {}
    if not os.path.exists(path):
        return mp
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                mp[int(r['asn'])] = int(r['hostname_count'])
            except Exception:
                continue
    return mp


@lru_cache(maxsize=1)
def _censorship():
    """list of (asn, test_name, count)."""
    path = os.path.join(CACHE_DIR, 'censorship.csv')
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                out.append((int(r['asn']), r['test_name'], int(r['detection_count'])))
            except Exception:
                continue
    return out


@lru_cache(maxsize=1)
def _global_country_stats():
    """Load global_country_stats.csv — prefers snapshot-local cache."""
    candidates = [
        os.path.join(CACHE_DIR, 'global_country_stats.csv'),
        os.path.join(os.path.dirname(__file__), '..', 'china', 'data',
                     'global_country_stats.csv'),
    ]
    out = {}
    for path in candidates:
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                for r in csv.DictReader(f):
                    out[r['country_code']] = {
                        'as_count': int(r.get('as_count') or 0),
                        'prefix_count': int(r.get('prefix_count') or 0),
                        'ixp_count': int(r.get('ixp_count') or 0),
                        'facility_count': int(r.get('facility_count') or 0),
                    }
            return out
    return out


# ─────────────────────────────────────────────────────────────
# Step functions — country parameterized
# ─────────────────────────────────────────────────────────────

TAG_CATS = [
    ('ISP', ['Internet Service Provider', 'Home ISP', 'Carrier']),
    ('Eyeball', ['Eyeball', 'Mobile Data', 'Business Broadband']),
    ('Content/CDN', ['Content Delivery Network', 'Cloud', 'Hosting', 'CDN']),
    ('Academic/Edu', ['Academic', 'Education', 'Universities']),
    ('Government', ['Government', 'Defense', 'Military']),
    ('Enterprise', ['Enterprise', 'Business']),
]


def _primary_tag(tags):
    if not tags:
        return 'Unknown'
    blob = '|'.join(tags)
    for cat, kws in TAG_CATS:
        for kw in kws:
            if kw in blob:
                return cat
    return 'Other'


def step01_scope(country, snapshot):
    """AS inventory with tag breakdown."""
    asns = load_country_ases(country)
    md = _as_metadata()
    tag_counter = Counter()
    rows = []
    for a in asns:
        meta = md.get(a, {'tags': []})
        cat = _primary_tag(meta['tags'])
        tag_counter[cat] += 1
        rows.append({'asn': a, 'category': cat,
                     'tags': '|'.join(meta['tags'][:4])})
    write_country_csv(snapshot, country, 'ases.csv', rows,
                      fieldnames=['asn', 'category', 'tags'])
    metrics = {
        'total_ases': len(asns),
        'tag_distribution': dict(tag_counter),
    }
    return metrics


def step02_top_as(country, snapshot):
    """Top-10 ASes by CAIDA ASRank within this country."""
    if not neo4j_available():
        return {'_error': 'neo4j-unavailable'}
    try:
        recs = run_query("""
            MATCH (a:AS)-[:COUNTRY]->(:Country {country_code:$cc})
            MATCH (a)-[r:RANK]->(rk:Ranking {name:'CAIDA ASRank'})
            OPTIONAL MATCH (a)-[:NAME]->(n:Name)
            RETURN a.asn AS asn, r.rank AS rank, head(collect(n.name)) AS name
            ORDER BY r.rank LIMIT 10
        """, {'cc': country})
    except Exception as e:
        return {'_error': str(e)[:100]}
    rows = [{'asn': r['asn'], 'name': r.get('name') or '', 'rank': r['rank']}
            for r in recs]
    write_country_csv(snapshot, country, 'top10_caida.csv', rows,
                      fieldnames=['asn', 'rank', 'name'])
    metrics = {
        'top10_caida_rank': [(r['asn'], r['rank']) for r in rows],
        'best_caida_rank': rows[0]['rank'] if rows else None,
    }
    return metrics


def step03_global_ranks(country, snapshot):
    """Country's global rank in scale metrics."""
    stats = _global_country_stats()
    if not stats:
        return {'_error': 'no-global-stats'}
    result = {}
    own = stats.get(country, {})
    for metric in ('as_count', 'prefix_count', 'ixp_count', 'facility_count'):
        sr = sorted([(cc, s[metric]) for cc, s in stats.items() if cc != 'ZZ'],
                    key=lambda t: -t[1])
        rank = next((i + 1 for i, (cc, _) in enumerate(sr) if cc == country), None)
        result[metric] = {'rank': rank, 'value': own.get(metric, 0)}
    return result


def step04_prefix(country, snapshot):
    """BGP prefix footprint via live Neo4j (RPKI + anycast tags)."""
    asns = load_country_ases(country)
    if not neo4j_available():
        pfx = _as_prefix_count()
        total = sum(pfx.get(a, 0) for a in asns)
        return {
            'v4_prefixes': total, 'v6_prefixes': 0,
            'rpki_rate_pct': None, 'anycast_prefixes': None,
            '_source': 'cache-only',
        }
    try:
        recs = run_query("""
            MATCH (a:AS)-[:COUNTRY]->(:Country {country_code:$cc})
            MATCH (a)-[:ORIGINATE]->(pfx:BGPPrefix)
            OPTIONAL MATCH (pfx)-[:CATEGORIZED]->(t:Tag)
            WITH pfx, collect(DISTINCT t.label) AS tags
            RETURN pfx.af AS af, tags
        """, {'cc': country})
    except Exception as e:
        return {'_error': str(e)[:100]}
    v4 = v6 = roa = any_tagged = 0
    for r in recs:
        if r.get('af') == 6:
            v6 += 1
        else:
            v4 += 1
        tags = r.get('tags') or []
        if 'RPKI Valid' in tags:
            roa += 1
        if any('Anycast' in (t or '') for t in tags):
            any_tagged += 1
    total = v4 + v6
    return {
        'v4_prefixes': v4,
        'v6_prefixes': v6,
        'total_prefixes': total,
        'rpki_rate_pct': round(roa / max(total, 1) * 100, 2),
        'anycast_prefixes': any_tagged,
    }


def step05_peering(country, snapshot):
    """Peering neighbor countries — who does this country peer with most?"""
    asns = load_country_ases(country)
    cmap = _country_as_map()
    edges = _peering_edges()
    foreign_cc = Counter()
    cn_cn = 0
    cn_foreign = 0
    for a, b in edges:
        a_in = a in asns
        b_in = b in asns
        if not (a_in or b_in):
            continue
        if a_in and b_in:
            cn_cn += 1
        else:
            cn_foreign += 1
            other = b if a_in else a
            ccs = cmap_of_as(other, cmap)
            for cc in ccs:
                if cc != country:
                    foreign_cc[cc] += 1
    return {
        'internal_edges': cn_cn,
        'cross_border_edges': cn_foreign,
        'top_peer_countries': dict(foreign_cc.most_common(10)),
    }


@lru_cache(maxsize=1)
def _as_to_countries():
    """Reverse lookup: asn -> frozenset(country_codes)."""
    mp = defaultdict(set)
    for cc, asns in _country_as_map().items():
        for a in asns:
            mp[a].add(cc)
    return {a: frozenset(s) for a, s in mp.items()}


def cmap_of_as(asn, cmap=None):
    """Return set of country codes for an ASN (frozenset)."""
    return _as_to_countries().get(asn, frozenset({'ZZ'}))


def step06_centrality(country, snapshot):
    """CN positions in global centrality."""
    asns = load_country_ases(country)
    c = _centrality()
    if not c:
        return {'_error': 'no-centrality-cache'}
    own = [(a, c[a]) for a in asns if a in c]
    if not own:
        return {'cn_count': 0}
    # Global ranks
    ranks = {}
    for metric in ('degree', 'betweenness', 'eigenvector', 'pagerank'):
        srt = sorted(c.items(), key=lambda kv: -kv[1][metric])
        for i, (asn, _) in enumerate(srt):
            ranks.setdefault(asn, {})[metric] = i + 1
    best = {m: None for m in ('degree', 'betweenness', 'eigenvector', 'pagerank')}
    for a, _ in own:
        if a in ranks:
            for m in best:
                r = ranks[a].get(m)
                if r and (best[m] is None or r < best[m]):
                    best[m] = r
    return {
        'count_with_centrality': len(own),
        'best_ranks': best,
    }


def step07_kcore(country, snapshot):
    """k-core positions."""
    asns = load_country_ases(country)
    core = _coreness()
    if not core:
        return {'_error': 'no-coreness-cache'}
    own = [core[a] for a in asns if a in core]
    if not own:
        return {'deepest_k': None}
    max_k_all = max(core.values())
    return {
        'global_max_k': max_k_all,
        'deepest_k_in_country': max(own),
        'count_k_ge_30': sum(1 for k in own if k >= 30),
        'count_k_ge_100': sum(1 for k in own if k >= 100),
    }


def step08_outbound_dep(country, snapshot):
    """Outbound hegemony."""
    asns = load_country_ases(country)
    cmap = _country_as_map()
    edges = _dependency_edges()
    out_edges = 0
    dest_cc = Counter()
    upstream_count = Counter()
    for s, d, h in edges:
        if h < 0.05:
            continue
        if s in asns and d not in asns:
            out_edges += 1
            upstream_count[d] += 1
            for cc in cmap_of_as(d, cmap):
                if cc != country:
                    dest_cc[cc] += 1
                    break
    top5 = [(a, upstream_count[a]) for a, _ in upstream_count.most_common(5)]
    return {
        'outbound_edges': out_edges,
        'top_destination_countries': dict(dest_cc.most_common(10)),
        'top5_upstream_ases': top5,
    }


def step09_inbound_dep(country, snapshot):
    """Inbound hegemony."""
    asns = load_country_ases(country)
    cmap = _country_as_map()
    edges = _dependency_edges()
    in_edges = 0
    src_cc = Counter()
    cn_upstream_count = Counter()
    for s, d, h in edges:
        if h < 0.03:
            continue
        if d in asns and s not in asns:
            in_edges += 1
            cn_upstream_count[d] += 1
            for cc in cmap_of_as(s, cmap):
                if cc != country:
                    src_cc[cc] += 1
                    break
    top5 = [(a, cnt) for a, cnt in cn_upstream_count.most_common(5)]
    return {
        'inbound_edges': in_edges,
        'top_source_countries': dict(src_cc.most_common(10)),
        'top5_country_upstream_ases': top5,
    }


def step10_concentration(country, snapshot):
    """HHI + Gini for prefix/hostname/org within country."""
    from analysis.complex_network.step13_concentration_hhi import (
        gini_coefficient, hhi_index,
    )
    asns = load_country_ases(country)
    pfx = _as_prefix_count()
    host = _dns_as_hosting()
    orgs = _as_organization()
    pfx_vals = [pfx[a] for a in asns if a in pfx]
    host_vals = [host[a] for a in asns if a in host]
    org_counter = Counter()
    for a in asns:
        if a in orgs:
            org_counter[orgs[a][0]] += 1
    org_vals = list(org_counter.values())

    def gh(arr):
        if not arr:
            return 0.0, 0.0
        s = sum(arr)
        return gini_coefficient(arr), hhi_index([x / s for x in arr] if s else [])
    g_p, h_p = gh(pfx_vals)
    g_h, h_h = gh(host_vals)
    g_o, h_o = gh(org_vals)
    return {
        'gini_prefix': round(g_p, 4),
        'hhi_prefix': round(h_p, 4),
        'gini_hostname': round(g_h, 4),
        'hhi_hostname': round(h_h, 4),
        'gini_org': round(g_o, 4),
        'hhi_org': round(h_o, 4),
    }


def step11_ixp(country, snapshot):
    """IXP landscape — domestic vs foreign participation."""
    asns = load_country_ases(country)
    ixps = _ixp_membership()
    domestic = 0
    foreign = 0
    ccs_hit = Counter()
    for ixp, entry in ixps.items():
        present = entry['asns'] & asns
        if not present:
            continue
        if entry['country'] == country:
            domestic += len(present)
        else:
            foreign += len(present)
        ccs_hit[entry['country']] += len(present)
    return {
        'ixp_memberships_domestic': domestic,
        'ixp_memberships_foreign': foreign,
        'top_ixp_host_countries': dict(ccs_hit.most_common(10)),
    }


def step12_facilities(country, snapshot):
    """Facility distribution."""
    asns = load_country_ases(country)
    facs = _facility_membership()
    cc_count = Counter()
    fac_count = Counter()
    for asn, fac, cc in facs:
        if asn in asns:
            cc_count[cc] += 1
            fac_count[fac] += 1
    return {
        'total_facility_records': sum(cc_count.values()),
        'distinct_facilities_with_country': len(fac_count),
        'top_countries_by_facility_presence': dict(cc_count.most_common(5)),
        'top_facilities': fac_count.most_common(5),
    }


def step13_bridge(country, snapshot):
    """IXP × Facility bridge count via Neo4j (fallback: skip)."""
    if not neo4j_available():
        return {'_error': 'neo4j-unavailable'}
    try:
        rec = run_query("""
            MATCH (a:AS)-[:COUNTRY]->(:Country {country_code:$cc})
            MATCH (a)-[:MEMBER_OF]->(ix:IXP)-[:LOCATED_IN]->(f:Facility)
            RETURN count(DISTINCT ix) AS ixps, count(DISTINCT f) AS facs,
                   count(*) AS rows
        """, {'cc': country})
    except Exception as e:
        return {'_error': str(e)[:100]}
    if rec:
        return {
            'distinct_ixps': rec[0]['ixps'],
            'distinct_facilities': rec[0]['facs'],
            'tripartite_rows': rec[0]['rows'],
        }
    return {}


def step14_dns_hosting(country, snapshot):
    """Hostnames hosted on country's ASes."""
    asns = load_country_ases(country)
    host = _dns_as_hosting()
    md = _as_metadata()
    total = 0
    top5 = []
    for a in asns:
        if a in host:
            total += host[a]
    sorted_ases = sorted([(a, host[a]) for a in asns if a in host],
                         key=lambda t: -t[1])[:5]
    cloud = isp = other = 0
    for a in asns:
        if a not in host:
            continue
        hc = host[a]
        tags = md.get(a, {}).get('tags', [])
        blob = '|'.join(tags)
        if any(k in blob for k in ('Cloud', 'Hosting', 'Content Delivery')):
            cloud += hc
        elif any(k in blob for k in ('ISP', 'Carrier', 'Home ISP')):
            isp += hc
        else:
            other += hc
    return {
        'total_hosted_hostnames': total,
        'hosting_ases': sum(1 for a in asns if a in host),
        'top5_hosting_ases': sorted_ases,
        'cloud_hostnames': cloud,
        'isp_hostnames': isp,
        'other_hostnames': other,
    }


def step15_dns_sovereignty(country, snapshot):
    """DNS authority sovereignty for country's ccTLD.

    Neo4j live: top-500 NS of <cc> zone with inferred provider country.
    """
    if not neo4j_available():
        return {'_error': 'neo4j-unavailable'}
    cc_lower = country.lower()
    try:
        recs = run_query(f"""
            MATCH (d:DomainName)-[:MANAGED_BY]->(ns:AuthoritativeNameServer)
            WHERE d.name ENDS WITH '.{cc_lower}'
            RETURN ns.name AS ns, count(DISTINCT d) AS c
            ORDER BY c DESC LIMIT 300
        """)
    except Exception as e:
        return {'_error': str(e)[:100]}
    total = sum(r['c'] for r in recs)
    if not total:
        return {'total_domains': 0, 'domestic_pct': 0.0}
    # Infer provider country via keyword heuristics
    CN_KW = ['aliyun', 'dnspod', 'huawei', 'baidu', 'cnnic', 'cernet', 'xinnet', 'alidns']
    US_KW = ['cloudflare', 'awsdns', 'amazonaws', 'google', 'godaddy', 'domaincontrol',
             'verisign', 'nstld']
    DE_KW = ['domainendirekt', 'ispgateway', '1und1', 'strato', 'heinlein', 'denic']
    GB_KW = ['nominet', 'easydns', 'ctd']
    JP_KW = ['jpnap', 'jprs', 'iij']
    RU_KW = ['nic.ru', 'ripn', 'ru-center']
    FR_KW = ['afnic', 'ovh', 'online.net', 'gandi']
    NL_KW = ['sidn', 'xs4all', 'transip']
    IN_KW = ['in.ac', 'ernet']
    region_kw = {'CN': CN_KW, 'US': US_KW, 'DE': DE_KW, 'GB': GB_KW, 'JP': JP_KW,
                 'RU': RU_KW, 'FR': FR_KW, 'NL': NL_KW, 'IN': IN_KW}
    by_country = Counter()
    for r in recs:
        n = r['ns'].lower()
        matched = False
        for cc, kws in region_kw.items():
            if any(k in n for k in kws):
                by_country[cc] += r['c']
                matched = True
                break
        if not matched:
            tld = n.rsplit('.', 1)[-1] if '.' in n else ''
            by_country[f'tld:{tld}'] += r['c']
    domestic = by_country.get(country, 0)
    return {
        'total_domains': total,
        'ns_sampled': len(recs),
        'domestic_pct': round(domestic / total * 100, 2),
        'operator_country_distribution': dict(by_country.most_common(10)),
    }


def step16_cname(country, snapshot):
    """Cross-border CNAME chains into country's cloud operators (CN-style)."""
    if not neo4j_available():
        return {'_error': 'neo4j-unavailable'}
    # Country-specific keywords
    PATTERNS = {
        'CN': ['aliyuncs', 'alicdn', 'myqcloud', 'hwclouds', 'cdnhwc',
               'wscloudcdn', 'bdstatic', 'chinacache', 'chinanetcenter'],
        'US': ['cloudfront.net', 'amazonaws.com', 'akamaiedge', 'akamai.net',
               'azureedge', 'fastly.net', 'cloudflare.com'],
        'JP': ['akamai.jp', 'linedevdns', 'cdn-jp'],
        'DE': ['myracloud', 'dogado'],
        'FR': ['ovh.net', 'gandi.net'],
        'GB': ['cloudflare', 'edgio'],
        'NL': ['leaseweb', 'transip.net'],
        'IN': [],
        'RU': ['selectel', 'yandexcloud'],
    }
    kws = PATTERNS.get(country, [])
    if not kws:
        return {'alias_edges': 0, '_note': 'no-keywords-for-country'}
    cond = ' OR '.join([f"h2.name CONTAINS '{k}'" for k in kws])
    try:
        recs = run_query(f"""
            MATCH (h1:HostName)-[:ALIAS_OF]->(h2:HostName)
            WHERE {cond}
            RETURN count(DISTINCT h1) AS n, count(DISTINCT h2) AS t
            LIMIT 1
        """)
    except Exception as e:
        return {'_error': str(e)[:100]}
    if recs:
        return {
            'alias_sources': recs[0].get('n', 0),
            'alias_targets': recs[0].get('t', 0),
        }
    return {}


def step17_rankings(country, snapshot):
    """Country's ASes in multi-ranking systems."""
    if not neo4j_available():
        return {'_error': 'neo4j-unavailable'}
    try:
        recs = run_query("""
            MATCH (a:AS)-[:COUNTRY]->(:Country {country_code:$cc})
            MATCH (a)-[r:RANK]->(rk:Ranking)
            WITH rk.name AS rname, min(r.rank) AS best
            RETURN rname, best ORDER BY best LIMIT 30
        """, {'cc': country})
    except Exception as e:
        return {'_error': str(e)[:100]}
    rk_summary = {r['rname']: r['best'] for r in recs}
    return {
        'rankings_count': len(rk_summary),
        'best_caida_rank': rk_summary.get('CAIDA ASRank'),
        'best_ranks_per_system': dict(list(rk_summary.items())[:10]),
    }


def step18_censorship(country, snapshot):
    """Censorship signal detection on country's ASes."""
    asns = load_country_ases(country)
    cens = _censorship()
    per_as = Counter()
    per_test = Counter()
    for asn, test, cnt in cens:
        if asn in asns:
            per_as[asn] += cnt
            per_test[test] += cnt
    return {
        'censoring_ases': len(per_as),
        'total_detections': sum(per_as.values()),
        'top5_tests': per_test.most_common(5),
        'top5_censoring_ases': per_as.most_common(5),
    }


def step19_atlas(country, snapshot):
    """RIPE Atlas probes in country."""
    if not neo4j_available():
        return {'_error': 'neo4j-unavailable'}
    try:
        rec = run_query("""
            MATCH (p:AtlasProbe)-[:LOCATED_IN]->(:Country {country_code:$cc})
            RETURN count(p) AS cnt
        """, {'cc': country})
    except Exception as e:
        return {'_error': str(e)[:100]}
    return {'probes_count': rec[0]['cnt'] if rec else 0}


def step20_sovereignty(country, snapshot, prior=None):
    """Composite sovereignty index from prior steps."""
    prior = prior or {}
    s4 = prior.get(4, {})
    s8 = prior.get(8, {})
    s9 = prior.get(9, {})
    s11 = prior.get(11, {})
    s14 = prior.get(14, {})
    s15 = prior.get(15, {})

    # 5 components, each 0-1
    host_total = s14.get('total_hosted_hostnames', 0) or 0
    hosting_sov = min(host_total / 300000, 1.0)
    dns_sov = (s15.get('domestic_pct') or 0) / 100.0
    rpki = (s4.get('rpki_rate_pct') or 0) / 100.0
    ixp_dom = s11.get('ixp_memberships_domestic', 0) or 0
    ixp_frn = s11.get('ixp_memberships_foreign', 0) or 0
    ixp_domes = ixp_dom / max(ixp_dom + ixp_frn, 1)
    inbound = s9.get('inbound_edges', 0) or 1
    outbound = s8.get('outbound_edges', 0) or 1
    hub_ratio = min(inbound / max(outbound, 1), 1.0)

    components = {
        'hosting_sovereignty': round(hosting_sov, 4),
        'dns_sovereignty': round(dns_sov, 4),
        'rpki_adoption': round(rpki, 4),
        'ixp_domesticization': round(ixp_domes, 4),
        'hub_ratio': round(hub_ratio, 4),
    }
    composite = sum(components.values()) / len(components)
    return {
        'composite_sovereignty_index': round(composite, 4),
        'components': components,
    }


STEP_FUNCS = {
    1: step01_scope,
    2: step02_top_as,
    3: step03_global_ranks,
    4: step04_prefix,
    5: step05_peering,
    6: step06_centrality,
    7: step07_kcore,
    8: step08_outbound_dep,
    9: step09_inbound_dep,
    10: step10_concentration,
    11: step11_ixp,
    12: step12_facilities,
    13: step13_bridge,
    14: step14_dns_hosting,
    15: step15_dns_sovereignty,
    16: step16_cname,
    17: step17_rankings,
    18: step18_censorship,
    19: step19_atlas,
    20: step20_sovereignty,
}

STEP_TITLES = {
    1: ('AS 清册与标签分布', 'AS inventory & tag breakdown'),
    2: ('头部 AS (CAIDA)', 'Top ASes (CAIDA ASRank)'),
    3: ('全球规模排名', 'Global scale rank'),
    4: ('BGP 前缀与 RPKI', 'BGP prefixes & RPKI'),
    5: ('对等互联伙伴', 'Peering partners'),
    6: ('全球中心性位置', 'Global centrality ranks'),
    7: ('k-core 层级位置', 'k-core depth'),
    8: ('出向 Hegemony', 'Outbound hegemony'),
    9: ('入向 Hegemony', 'Inbound hegemony'),
    10: ('集中度 Gini/HHI', 'Concentration'),
    11: ('IXP 会员分布', 'IXP landscape'),
    12: ('机房分布', 'Facility distribution'),
    13: ('IXP × 机房 桥梁', 'IXP × Facility bridge'),
    14: ('DNS 托管版图', 'DNS hosting'),
    15: ('DNS 主权率', 'DNS sovereignty'),
    16: ('跨境 CNAME 链', 'Cross-border CNAME'),
    17: ('多排名位置', 'Multi-ranking positions'),
    18: ('审查拓扑', 'Censorship topology'),
    19: ('Atlas 探针', 'Atlas probes'),
    20: ('综合主权指数', 'Composite sovereignty index'),
}


def run_all_for_country(country, snapshot='2026-04'):
    """Execute all 20 step extractors for one country. Write metrics JSONs.

    Returns: dict[step_num] -> metrics dict.
    """
    results = {}
    for n in range(1, 21):
        fn = STEP_FUNCS[n]
        try:
            if n == 20:
                metrics = fn(country, snapshot, prior=results)
            else:
                metrics = fn(country, snapshot)
        except Exception as e:
            metrics = {'_error': f'exception: {e!r}'[:200]}
        title_zh, title_en = STEP_TITLES[n]
        write_country_metrics(snapshot, country, n, metrics, title_zh, title_en)
        results[n] = metrics
    return results
