# IYP new_angles · Research Trail Index
## Session Output · 2026-04-19 → 2026-04-20

Entry-point map for the ROV time-series + international data center + methodology-audit research body produced this session. Reading order if starting from zero: **FINDINGS → DATACENTERS → METHODOLOGY_AUDIT**.

---

## 1. Narrative documents

| Doc | Lines | Core content | Headline findings |
|---|---|---|---|
| **`FINDINGS.md`** | 320 | 11-quarter ROV + IXP + hegemony time-series | **F** 6 findings A-F · **A** IXP 72-77% stable ghost ratio · **B** 2025-Q2 ROV jump: 68% measurement-artifact + **panel method** · **B-addendum** Italy 100% step-synced 52 ISPs · **F** industry capacity-growth panel (novel) |
| **`DATACENTERS.md`** | 450 | 11-quarter DC layer analysis (5,858 facilities, 59K AS-DC edges, 4.4K IXP-DC) | **A** +18% DC monotonic · **B** operator "growth" dominated by rename propagation (Digital Realty +56% → actual zero) · **C** city ghost growth corrected · **Italy causal chain falsified** (DC unchanged, MIX-IT route-server suspected) · **Indonesia deep-dive** (PT Telkom batch registration + real build-out) · **France anomaly** (14.6% upgrade rate) · **Cogent +15 batch registration** |
| **`METHODOLOGY_AUDIT.md`** | 215 | PeeringDB field drift across 27 months | 14.6% operator rename churn · 13.5% traffic-bucket upgrade (real) · 6.8% city alias consolidation · info_type "(empty)" share 15% → 27% (quality degradation) · **7-item checklist** for future IYP time-series work |

**Total narrative**: 985 lines, 3 docs.

---

## 2. HTML visualization output

All under `analysis/new_angles/html/` with mirrors in `analysis/countries/html/`.

### 2.1 ROV time-series series (4 HTMLs)

| HTML | Content |
|---|---|
| `evolution_timeseries.html` | 8 panels · 11-quarter evolution (hegemony / IXP / BGP / RPKI / archetype / ...) |
| `rov_jump_2025q2.html` | 4 panels · 2025-Q2 jump attribution (68% measurement artifact) |
| `rov_panel_adoption.html` | 4 panels · Panel-based unbiased re-estimate (30,340-AS stable panel) |
| `rov_two_peaks.html` | 4 panels · 2025-Q2 vs 2026-Q1 cohort comparison (11 overlap / 1.4%) |

### 2.2 DC series (3 HTMLs + pyvis)

| HTML | Content |
|---|---|
| `datacenters.html` | 12 panels · geography + ownership + temporal + routing |
| `dc_routing_pyvis.html` | 878-node interactive graph (top-30 DCs × 848 multi-DC ASes × 4,152 edges) |
| `capacity_growth.html` | 6 panels · industry capacity-upgrade signal (21.6% up / 1% down / 21:1 ratio) |

### 2.3 Supporting

| HTML | Updated? |
|---|---|
| `schema_gaps.html` | Yes (G5/G7/G8/G11/G12/G14 corrected + G15/G16 added) |
| plus 9 per-topic HTMLs (topic1-21) from prior session | Yes (warnings collapsed) |

---

## 3. Data artifacts

**CSVs** (11 snapshots × N tables):

```
data_cache/new_angles/<YYYY-MM-DD>/  (11 snapshot dirs)
  ├─ as_country.csv                 27 existing + 4 new
  ├─ ihr_hegemony_incoming.csv
  ├─ rovista.csv
  ├─ ... (23 others)
  ├─ facilities.csv                 ← new Phase 2
  ├─ facility_members.csv           ← new Phase 2
  ├─ facility_ixps.csv              ← new Phase 2
  └─ peeringdb_nets.csv             ← new Phase 2
```

**Metrics JSON** (provenance):
- `analysis/new_angles/data/evolution_timeseries_metrics.json`
- `analysis/new_angles/data/datacenters_metrics.json`
- `analysis/new_angles/data/capacity_growth_metrics.json`

---

## 4. Driver scripts + extractors

| Script | Purpose |
|---|---|
| `analysis/new_angles/extract_data.py` | Full extraction + 4 DC extractors + `IYP_SNAPSHOT` env-var support |
| `analysis/new_angles/run_timeseries.sh` | 11-snapshot time-series driver (all 27 CSVs, ~1h22min) |
| `analysis/new_angles/run_dc_timeseries.sh` | Incremental 4-CSV DC-only driver (~47min) |
| `analysis/new_angles/evolution_timeseries.py` | Aggregator: panel metrics → 8-panel HTML |
| `analysis/new_angles/rov_jump_2025q2.py` | 2025-Q2 attribution analysis |
| `analysis/new_angles/rov_panel_adoption.py` | Panel method re-estimate |
| `analysis/new_angles/rov_two_peaks_comparison.py` | Cohort comparison |
| `analysis/new_angles/datacenters.py` | DC layer 12 panels + CITY_ALIASES + OPERATOR_ALIASES |
| `analysis/new_angles/datacenters_pyvis.py` | Interactive DC↔AS graph |
| `analysis/new_angles/capacity_growth.py` | Capacity upgrade panel (novel) |
| `analysis/new_angles/schema_gaps.py` | Updated with G15/G16 + resolved G5/G7/G8/G11/G12/G14 |

---

## 5. Headline findings — publishable quality

Listed by "single-finding publishability" (subjective):

### 5.1 Panel-method corrects measurement-artifact inflation in ROV adoption narrative

Raw PeeringDB stats show ROV adoption jumping 4,315 → 7,247 AS (+68%) between 2025-Q1 and 2025-Q2. Panel-based re-analysis (same AS self-compared across 30,340-AS stable panel) reveals **66-68% of the jump is ROVISTA measurement-set expansion** (new sample biased to already-enforcing US AS at 2.4× baseline rate). True adoption rate per quarter is 3.28% (10× baseline noise) with a **previously-unnoticed 1.32% secondary peak in 2026-Q1**. **Any ROV adoption paper citing post-2025-Q1 numbers must cite the panel method.**

### 5.2 Italy 2026-Q1 ROV flip is a synchronized IXP-policy event, not infrastructure investment

52 Italian ISPs (Telecom Italia Sparkle, Fastweb, Wind, Tiscali, BT Italia, ...) flipped ROV enforcement in the same quarter with 100% (0,0,1,1) step-trajectory. DC-side investigation falsified the "new DC build → new equipment → ROV" hypothesis (Milan DC count 0 change in 2 years after alias normalization). 32/52 flippers registered at MIX DC CALDERA (operator: MIX s.r.l. = Milano Internet Exchange). **Most plausible mechanism: MIX-IT route server enabled RPKI-invalid drop in Q1 2026**, following the AMS-IX/DE-CIX/LINX template from 2019-2022.

### 5.3 PeeringDB has 14.6% silent operator renames over 27 months — invalidating naive operator-growth claims

Using `pdb_fac_id` as stable key, we find that across the 5,858 facility panel:
- **Digital Realty's apparent +56% DC growth is almost entirely Interxion brand consolidation** (2020 M&A that PeeringDB propagated 2024-2026). Real organic growth: 139 → 140.
- **Centersquare is not a "new entrant" with 38 DCs**; it's the Cyxtera+Evoque merger post-bankruptcy that **lost 35 DCs** during reorg.
- **Lumen's −23% "decline" was a sudden 2025-Q3 drop** of 15 DCs as Colt's 2023 EMEA acquisition propagated through PeeringDB.
- **Top-5 operator total fell 512 → 504** (−8 net DCs) — the "operator market expansion" narrative is virtually entirely artifact.

Practical tool: `OPERATOR_ALIASES` dict in `datacenters.py` consolidating 60+ known rebrands.

### 5.4 Industry capacity-upgrade panel (novel signal, independent of vendor reports)

Among 13,650 AS observed in ≥2 PeeringDB snapshots, **21.6% upgraded info_traffic bucket vs 1.0% downgraded** (21:1 ratio). NSP (26.8%) and Cable/DSL/ISP (25.1%) lead; Enterprise / Non-Profit / Education lag at ~10%. **Indonesia 31.4%** is the upgrade-rate champion; **France 14.6%** is the European anomaly. This is the first panel-method measurement of operator-declared capacity growth — independent of Cisco Annual Internet Report or vendor telemetry.

### 5.5 Indonesia 2024-2026 infrastructure expansion is real and multi-layered

- DC count +50% (134 → 201) — 35% driven by PT Telekomunikasi Indonesia batch-registering 23 PoPs in 2024-Q3
- Jakarta metro + Bekasi (satellite) +24 DCs; secondary cities (Surabaya, Medan, Denpasar, Makassar, Yogyakarta) +12
- AS capacity upgrade rate 31.4% (#1 globally)
- AS-DC presence edges +163% (1,234 → 3,242)

**Two independent data layers strongly reinforce**: capacity + DC-presence + operator expansion all moving together. Not a metadata artifact.

---

## 6. Next candidates (unexplored)

From the accumulated "next candidate" lists across FINDINGS.md (10), DATACENTERS.md (8), METHODOLOGY_AUDIT.md (4), the most actionable:

1. **AS49915** outlier: 1 → 356 DCs in 2 years, still unexplained (whois lookup required)
2. **France capex vs PeeringDB reconciliation** — which hypothesis explains the 14.6% anomaly
3. **Extend drift audit to other IYP CSVs** (as_categorized, rovista, ixp_live_members)
4. **Submarine cable layer integration** (TeleGeography / PCH) — IYP Facility nodes could join to physical links
5. **External validation**: MIX-IT public statements Q1 2026; ARIN/LACNIC ROA automation releases 2025 Q1
6. **Per-country ROV panel** — who contributed most to 2025-Q2 vs 2026-Q1 peaks at AS level
7. **Hegemony top-20 internal reshuffling** despite stable total share

---

## 7. Reproduce

```bash
# Re-extract all 27+4 CSVs from any dump in dumps_archive/
bash analysis/new_angles/run_timeseries.sh       # ~1h22min for 10 dumps
bash analysis/new_angles/run_dc_timeseries.sh    # ~47min if only DC needed

# Rebuild HTMLs from cached CSVs (no Neo4j needed)
python3 -m analysis.new_angles.evolution_timeseries
python3 -m analysis.new_angles.rov_jump_2025q2
python3 -m analysis.new_angles.rov_panel_adoption
python3 -m analysis.new_angles.rov_two_peaks_comparison
python3 -m analysis.new_angles.datacenters
python3 -m analysis.new_angles.datacenters_pyvis
python3 -m analysis.new_angles.capacity_growth
python3 -m analysis.new_angles.schema_gaps
```

To add a new quarterly dump (e.g. 2026-07-01):
```bash
# 1. Download to dumps_archive/iyp-2026-07-01.dump
# 2. Extract that single snapshot
DUMPS="2026-07-01" bash analysis/new_angles/run_timeseries.sh
DUMPS="2026-07-01" bash analysis/new_angles/run_dc_timeseries.sh
# 3. Re-run aggregators
python3 -m analysis.new_angles.evolution_timeseries
python3 -m analysis.new_angles.datacenters
python3 -m analysis.new_angles.capacity_growth
```

---

## 8. Session statistics

- **Duration**: ~24 hours elapsed (with 2 long-running extractions: ROV timeseries 1h22, DC timeseries 47min)
- **Commits to narrative**: 3 docs (FINDINGS + DATACENTERS + METHODOLOGY_AUDIT) + INDEX
- **Python scripts authored**: 7 new (+ extract_data.py extended)
- **HTMLs generated**: 7 new + 4 mirror
- **Data produced**: 11 snapshots × 31 CSVs = 341 CSVs, ~9 GB on disk
- **Findings classified as "publishable": 5** (panel method, Italy causal chain, operator rename audit, capacity-upgrade panel, Indonesia deep-dive)
- **Subsequent sessions can resume from**: this INDEX; all outputs are reproducible from `dumps_archive/` without further Neo4j extraction.
