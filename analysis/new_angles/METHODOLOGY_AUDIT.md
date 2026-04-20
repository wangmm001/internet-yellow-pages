# Methodology Audit — IYP Field Drift Across 27 Months
## Silent Rewrites in PeeringDB-sourced Fields

*(Full-time-series scan across 11 quarterly IYP dumps, 2024-01 to 2026-04. Stable join key: `pdb_fac_id` for facilities, `asn` for peeringdb_nets.)*

---

## Motivation

When building `DATACENTERS.md` we observed several eye-catching growth claims that later turned out to be **data-cleaning artifacts**, not real phenomena:

- "Milan +125% (8→18)" → actually **0 growth** (Milano→Milan alias consolidation)
- "Digital Realty +56% catching up to Equinix" → actually **+11% real growth** (45 of 50 are Interxion renames from 2020 M&A that PeeringDB only propagated 2024-2026)
- "Kyiv +183%" → actually **+13%** (Kiev→Kyiv consolidation)

Rather than fix these one-off, we did a **systematic drift audit** on every metadata field of `facilities.csv` and `peeringdb_nets.csv` across the 11-snapshot panel. This document reports the result as a standalone methodology note applicable to any future IYP-based time-series analysis.

---

## 1. Method

For each stable entity (`pdb_fac_id` for facilities, `asn` for peeringdb_nets), we trace every string field across 11 snapshots and count:
- `n_changed`: distinct entities that had ≥1 field-value change across the window
- `churn%` = n_changed / total entities
- Top transitions `"value_A" → "value_B"` with count

The field-drift rate on itself is not enough — the top transitions reveal *what kind* of drift: M&A vs cosmetic vs capacity.

---

## 2. Facility-level fields (6,098 distinct pdb_fac_id tracked)

| Field | Churn% | Top transition | Nature |
|---|---|---|---|
| **operator** | **14.6%** | Interxion → Digital Realty (44) | Mostly M&A/rename lag |
| **name** | 14.3% | Globe Data Center → STT Davao (1) | Mix of renames + formatting |
| state | 7.4% | São Paulo → SP (41) | Standardize to postal code |
| **city** | 6.8% | Kiev → Kyiv (17), Milano → Milan (10), Sao Paulo → São Paulo (11) | Anglicization / accent-ification |
| name_long | 0.4% | various | Mostly new entries |
| cc (country) | 0.1% | SG → ID (2), US → PR (1) | Genuine edge cases |
| clli | 0.1% | code corrections | |
| property | 0.1% | Lessee ↔ Owner | Operator relationship |
| region | 0% | — | Stable |
| status | 0% | — | Stable |

### 2.1 The big operator renames

| Before 2024-01 | After (by 2026-04) | n | Context |
|---|---|---|---|
| Interxion - A Digital Realty Company | Digital Realty | **43** | Digital Realty acquired Interxion in 2020; PeeringDB only propagated the rename 2024-2026 |
| Cyxtera Technologies, Inc. | Centersquare | **28** | Cyxtera filed Chapter 11 in 2023, emerged as Centersquare in 2024 |
| Evoque Data Center Solutions | Centersquare | **10** | Evoque acquired by Brookfield and folded into Centersquare |
| CyrusOne | CyrusOne Inc. | **31** | Cosmetic suffix addition |
| NTT Global Data Centers | NTT DATA's Global Data Centers division | 27 | Rebrand after NTT reorganization |
| NTT Communications (Data Centers) | NTT DOCOMO BUSINESS (Data Centers) | 16 | Rebrand |
| Crown Castle | Crown Castle Inc. | 16 | Cosmetic suffix |
| ST Telemedia Global Data Centres | ST Telemedia Global Data Centres (STT GDC) | 20 | Suffix addition |

### 2.2 Corrected operator growth (2024-01 → 2026-04)

Using `pdb_fac_id` as stable key, we can split each operator's 2026-04 facility count into three buckets:
- **stable**: facility was already assigned to this operator in 2024-01
- **renamed_in**: facility belonged to a different operator in 2024-01, silently moved
- **new**: facility did not exist in 2024-01 at all

| Operator | 2024-01 | 2026-04 | stable | renamed_in | **new** | % raw growth | **% real growth** |
|---|---|---|---|---|---|---|---|
| Equinix, Inc. | 200 | 222 | 190 | 3 | **29** | +11% | **+15%** ⭐ |
| **Digital Realty** | 90 | 140 | 85 | **45** | **10** | +56% | **+11%** |
| Cogent Communications | 36 | 55 | 36 | 0 | 19 | +53% | **+53%** ⭐ |
| Cologix | 35 | 44 | 34 | 0 | 10 | +26% | +29% ⭐ |
| Lumen Technologies | 64 | 49 | 38 | 0 | 11 | −23% | Actually added 11 new, shed 26 old (portfolio rotation, not pure contraction) |
| EXA Infrastructure | 66 | 54 | 49 | 0 | 5 | −18% | Same pattern — 5 new vs −17 old |
| Centersquare | 0 | **38** | 0 | **38** | **0** | ∞ | **0** — entirely rebrand |
| STT GDC (new full name) | 0 | 35 | 0 | 20 | 15 | ∞ | +15 real new |
| nLighten | 0 | 34 | 0 | 26 | 8 | ∞ | +8 real new |
| CyrusOne Inc. | 0 | 33 | 0 | 31 | 2 | ∞ | +2 real new |

**Corrected ranking of real 2-year new builds** (top 5):
1. Equinix **+29**
2. Cogent **+19**
3. STT GDC **+15**  
4. Lumen **+11** (despite net contraction due to portfolio rotation)
5. Digital Realty **+10** (real organic growth; 45 others are Interxion absorption)

**Lesson**: Raw operator-count deltas are **dominated by rename propagation** in PeeringDB. Any M&A-era report must use `pdb_fac_id` stable-key tracking.

### 2.3 City-name normalization (417 facilities, 6.8% churn)

All transitions are cosmetic (language / accent / hyphenation). Top patterns:

| From | To | n | Pattern |
|---|---|---|---|
| Kiev | Kyiv | 17 | Ukrainian romanization (post-2022 transliteration update) |
| Sao Paulo | São Paulo | 11 | ASCII → accented |
| Milano | Milan | 10 | Italian → English |
| Poznań | Poznan | 8 | Polish → ASCII |
| Roma | Rome | 7 | Italian → English |
| Bengaluru | Bangalore | 7 | Local → English (reverse direction!) |
| Hortolândia | Hortolandia | 6 | ASCII-ification |
| Cluj-Napoca | Cluj Napoca | 6 | De-hyphenation |
| Praha | Prague | 5 | Czech → English |
| Wien | Vienna | 5 | German → English |
| Saint-Petersburg | St. Petersburg | 5 | Formatting |
| Bogotá | Bogota | 5 | Accent removal |
| Nürnberg | Nuremberg | 4 | German → English |
| CABA | Buenos Aires | 4 | Abbreviation expansion |
| İstanbul | Istanbul | 4 | Turkish → ASCII |

No single transition explains most of the churn — this was a **systematic multi-pass cleanup** done by PeeringDB around 2025-10. Likely triggered by a data-quality review, not organic user edits.

**Lesson**: Any "top city by growth" analysis must apply an alias dictionary covering:
- ASCII ⇄ accented characters
- Local language ⇄ English transliteration
- Abbreviation ⇄ full form
- Hyphenation variants
- "City, SubLocation" combining rules

The `norm_city()` function in `analysis/new_angles/datacenters.py` implements the above for the most common cases. More aliases should be added as discovered.

---

## 3. AS-level PeeringDB fields (23,114 distinct AS tracked)

| Field | Churn% | Top transition | Nature |
|---|---|---|---|
| **info_traffic** | **13.5%** | 10-20Gbps → 20-50Gbps (409) | **Real capacity upgrades** — all monotonically increasing |
| info_ratio | 4.1% | Balanced ↔ Mostly Inbound | Real traffic-shape shifts |
| info_type | 3.6% | Cable/DSL/ISP ↔ NSP | Reclassification; bidirectional |
| info_scope | 2.6% | Not Disclosed → Regional/Asia Pacific | Disclosure improvements |
| **policy_general** | **2.5%** | **Open → Selective (342), Selective → Open (181)** | Real policy drift |
| policy_contracts | 0.7% | Not Required → Required/Private Only | |
| policy_ratio | 0.3% | True ↔ False | Small churn |

### 3.1 The hidden "capacity upgrade" signal (info_traffic)

13.5% of AS had their declared traffic bucket change — and **ALL** of the top 15 transitions are **one-bucket up** (5-10→10-20, 10-20→20-50, 20-50→50-100, 50-100→100-200, 100-200→200-300, 200-300→300-500, 300-500→500-1000, 500-1000→1-5Tbps).

This is an **unexploited panel signal for tracking network capacity growth** — 3,109 AS upgraded their declared traffic capacity over 27 months. Aggregated, this could produce a "industry-level throughput growth curve" that's independent of vendor reports.

### 3.2 info_type disclosure degrading (data quality warning)

| Snapshot | (empty) info_type | % of total |
|---|---|---|
| 2024-01 | 2,445 | 15.0% |
| 2025-01 | 5,135 | 26.5% |
| 2026-04 | 5,601 | 27.0% |

**The fraction of AS with undisclosed `info_type` nearly doubled** from 15% to 27%. Any study using `info_type` to stratify AS must disclose this — the "representative" sample for any category is narrowing as new AS join PeeringDB without filling the field.

Also notable: **Government category appeared at 2025-01** (75 AS, now 87). PeeringDB's own ontology is still evolving.

### 3.3 Peering policy drift (policy_general)

Top transitions:
- 342 AS: Open → Selective (becoming more exclusive)
- 181 AS: Selective → Open (opening up)
- 32 AS: Open → No (shutting down peering disclosure)

**Net drift toward more Selective**: +161 (342 − 181) over 27 months. Real signal of increased peering curation / gatekeeping.

---

## 4. Implications for Previous Findings

### 4.1 `DATACENTERS.md` Finding B (operator growth) — CORRECTED

The "Digital Realty +56% vs Lumen −23%" framing is **substantively wrong** when using raw operator counts. Corrected picture in section 2.2 of this document.

### 4.2 `DATACENTERS.md` Finding C (top cities) — CORRECTED

Every single claim involving "+>50% single-city growth" needs alias normalization. Corrected top-15 list is in `DATACENTERS.md` section 2.3.

### 4.3 `FINDINGS.md` Finding B (ROV 2025-Q2 + 2026-Q1 peaks) — NOT AFFECTED

These findings were built on `rovista.csv` which has no field-drift issue (only numeric `ratio` and binary `label`). The cohort profiles (Italian ISPs etc.) used `peeringdb_nets.csv` `info_type` field, but only as a descriptor — no quantitative claim depended on category stability.

### 4.4 `FINDINGS.md` 2.2.2 Italy causal chain — REINFORCED

The Italy ROV-flip causal chain actually becomes **cleaner** after this audit:
- Milan DC growth is 0 (alias artifact), so the "DC build → ROV deploy" hypothesis is conclusively falsified
- The true mechanism must be non-infrastructural — MIX-IT route-server policy is the remaining high-likelihood candidate

---

## 5. Quick-reference checklist for future IYP time-series analysis

Before publishing any "field X changed by Y%" claim on IYP data:

- [ ] **Use stable entity IDs as join key** (`pdb_fac_id`, `asn`, `pdb_ix_id`, `pdb_org_id`) — never string names
- [ ] **Compute field churn rate** for every string field touched, against a known stable panel
- [ ] **List top transitions** per field: if top-3 transitions are "A → A-variant-of-A", it's cosmetic; otherwise investigate
- [ ] **Apply alias dictionaries** for: city names, operator names, country codes edge cases
- [ ] **Disclose empty-value drift**: does the field become more or less populated over time?
- [ ] **Separate real vs renamed in new-entry counts**: operator `new` count must exclude facilities inherited via rename
- [ ] **Verify ontology stability**: did the category set itself change (new category added / removed)?

---

## 6. Artifacts

| Path | Content |
|---|---|
| `analysis/new_angles/METHODOLOGY_AUDIT.md` | This document |
| `analysis/new_angles/datacenters.py` | Already patched with `norm_city()` + `CITY_ALIASES` |
| `analysis/new_angles/DATACENTERS.md` § 2.2 / § 2.3 / § 2.3.1 | Corrected Finding B and Finding C |

---

## 7. Next candidates (methodology follow-ups)

1. **Operator alias dictionary** (similar to `CITY_ALIASES`): build `OPERATOR_ALIASES` from the rename table in § 2.1, use in `datacenters.py` so a consistent "canonical operator" name is shown
2. **info_traffic capacity growth panel**: the 3,109 AS that upgraded their declared traffic bucket could be visualized as a "industry-wide Mbps→Tbps advance" curve — novel signal
3. **Full field audit across all 26 IYP CSVs**: extend this drift scan to `as_categorized.csv`, `rovista.csv`, `ixp_live_members.csv` — some may have similar silent rewrites we haven't noticed
4. **Disclose audit results upstream to PeeringDB / IYP**: the fact that Digital Realty/Interxion M&A propagated to PeeringDB 4 years after the deal is a data-freshness issue worth reporting
