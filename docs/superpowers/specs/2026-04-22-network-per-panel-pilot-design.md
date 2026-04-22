# Complex-Network Per-Panel Presentation · Design (Pilot: step05)

> Break each multi-panel composite PNG in the complex-network track into one
> page per subplot, each with its own medium-prose explainer. Pilot on step05,
> validate end-to-end, then bulk-apply the pattern to the other 12 steps in a
> follow-up.

## Problem

Today each complex-network step (13 total) renders as ONE composite PNG
containing 4–6 subplots, presented on a single page with one "图解" dialog
covering the whole composite. Readers cannot focus on a single panel or get
a tailored explanation of just that subplot.

## Scope of this spec

Pilot only — step05 `度分布与幂律拟合 · Degree Distribution & Power Law`.
Six panels: BGP CCDF, AS-Dependency In-Degree CCDF, IXP Membership CCDF,
DNS Hosting CCDF, Degree Distribution Comparison, Summary Statistics table.

Out of scope: steps 06, 07, 08, 09, 10, 11, 13, 15, 18, 19, 22, 24.
Those get their own plan after the pilot lands and is reviewed in-browser.

## Decisions (all locked in during brainstorm)

| # | Decision                                                  | Chosen |
| - | --------------------------------------------------------- | ------ |
| 1 | Presentation layout — page-per-panel vs multi-card page   | **page-per-panel** (one URL per panel) |
| 2 | Image generation — modify generator vs crop composite     | **modify generator** |
| 3 | Explainer depth — full prose / medium / short caption     | **medium** (2 sections: `what` + `see`) |
| 4 | Rollout — pilot one step / all 13 / phased by complexity  | **pilot step05 first** |
| 5 | Legacy composite PNG — delete vs keep                     | **delete** |

## Architecture

Three layers, each with a clear responsibility:

### 1. Generator · `analysis/complex_network/step05_degree_distribution.py`

Refactor the current 6-panel `plt.figure(figsize=(30, 18)) + gridspec(2,3)`
into six independent single-panel functions plus a thin `main()` that calls
them. Each writes one PNG at ~10×7 inches (~1000×700 px at 100 DPI):

```
step05_panel01_bgp_ccdf.png
step05_panel02_as_dep_ccdf.png
step05_panel03_ixp_ccdf.png
step05_panel04_dns_hosting_ccdf.png
step05_panel05_comparison_pdf.png
step05_panel06_summary_stats.png
```

Naming scheme: `step<NN>_panel<MM>_<slug>.png` — stable, sortable, encodes
parent step. Same dark-theme palette and `style_ax()` helper as today.

The composite `step05_degree_distribution.png` is deleted.

### 2. Navigation · `analysis/web/nav.py`

Add a `NETWORK_PANELS` table alongside the existing `NETWORK_STEPS`:

```python
NETWORK_PANELS: list[tuple[int, int, str, str, str, str, list[str]]] = [
    # (parent_step, panel_id, png_file, title_zh, title_en, subtitle, kpis)
    (5, 1, 'step05_panel01_bgp_ccdf.png',
     'BGP 对等度的互补累积分布',
     'BGP Peering Degree · CCDF',
     '每个 AS 的对等邻居数如何分布',
     ['α ≈ 2.10', '幂律长尾']),
    ...
]
```

`_build_network_track()` emits one `Page` per panel with
`url=f'/network/step{step:02d}_panel{n:02d}/'` and `kind='png'`.

The step-level page `/network/step05/` switches from `kind='png'` to a new
`kind='png_index'` that renders a panel-grid landing (6 thumbnail cards,
each linking to its panel URL). Prev/next navigation among step index pages
is unchanged — panel pages link prev/next within their own step.

### 3. Explainers · `analysis/web/explainers.py`

Loosen `_add()` signature so `how` and `keyterm` are optional:

```python
def _add(url, title_zh, title_en, *, what, how=None, see, keyterm=None):
    ...
```

The existing ~25 call sites already pass all four positionally — no breakage.

Add 6 new `_add('/network/step05_panel01/', …)` entries with only `what` +
`see` (bilingual prose, ~150 words each section).

### 4. Template · `analysis/web/templates/`

One new template: `network_step_index.html` (~40 lines) — renders the
step-level landing as a 3-column grid of panel thumbnails. Reuses existing
`chart-card` CSS from `site.css`.

Tiny edit to `step_png.html`: gate the `how` and `keyterm` dialog sections
on presence (`{% if explainer.how_zh %}…{% endif %}`) so medium-prose
explainers don't render empty `<h4>` blocks. (If the template already handles
missing fields, zero edits — verify first.)

### 5. Site build · `analysis/web/build.py`

Existing `build.py` iterates `nav.tracks`, emitting one file per `Page`. With
the new panel pages registered, it emits `/network/step05/index.html` (via
`network_step_index.html`) plus `/network/step05_panel01..06/index.html`
(via existing `step_png.html`). Tiny extension: route `kind='png_index'` to
the new template.

## Data flow

1. Regenerate: `python3 -m analysis.complex_network.step05_degree_distribution`
   reads `data_cache/complex_network/*.csv`, writes 6 panel PNGs to
   `analysis/complex_network_images/`, removes the old composite.
2. Rebuild site: `python3 -m analysis.web.build` picks up new panel URLs,
   emits 7 HTMLs under `analysis/web/site/network/` (1 index + 6 panels).

## Deliverables

1. `analysis/complex_network/step05_degree_distribution.py` — refactored into
   6 panel functions + `main()`.
2. 6 new panel PNGs, old composite deleted.
3. `analysis/web/nav.py` — `NETWORK_PANELS` table, `_build_network_track`
   emits panel Pages, step-level Page switches to `png_index` kind.
4. `analysis/web/explainers.py` — `_add()` signature loosened, 6 new entries.
5. `analysis/web/templates/network_step_index.html` — new panel-grid template.
6. `analysis/web/templates/step_png.html` — optional gate on `how`/`keyterm`.
7. `analysis/web/build.py` — route `png_index` kind to new template.
8. Regenerated `analysis/web/site/network/step05*/*.html` (7 files).

## Explainer content — sample for panel 01 (BGP CCDF)

```python
_add('/network/step05_panel01/',
     'BGP 对等度的互补累积分布',
     'BGP Peering Degree · CCDF',
     what=(
         '横轴是单个 AS 拥有的 BGP 对等邻居数 k；纵轴是"拥有 ≥ k 个邻居"的 '
         'AS 占比。在双对数坐标下观察尾部斜率，若呈直线就是幂律尾 '
         'P(K≥k) ~ k^−(α−1)。',
         'X-axis is peer-count k per AS; Y-axis is the fraction of ASes with '
         '≥ k neighbours. On log-log axes, a straight tail indicates power-law '
         'P(K≥k) ~ k^−(α−1).'),
     see=(
         'IYP BGP 层 α ≈ 2.10：99% 的 AS 只有 1–20 个邻居，但尾部一小撮超级 '
         'hub (Tier-1 / Cloudflare / Google) 连了数千个。曲线尾部的红色拟合线'
         '就是幂律预测——实际点几乎贴着线下滑，印证无标度结构。',
         'IYP BGP α ≈ 2.10: 99% of ASes have 1–20 peers, but a handful of '
         'super-hubs (Tier-1s, Cloudflare, Google) connect to thousands. The '
         'red fitted tail line is the power-law prediction; observed points '
         'track it almost exactly, confirming the scale-free structure.'))
```

5 more similar entries for panels 02–06.

## Re-run durability

Re-running `step05_degree_distribution.py` regenerates the 6 panel PNGs
idempotently (same filenames, overwrites). Re-running `build.py` regenerates
the 7 HTMLs idempotently. No state accumulation.

## Out of scope (for this spec)

- Steps 06, 07, 08, 09, 10, 11, 13, 15, 18, 19, 22, 24.
- Thumbnail generation for the index grid — we'll rely on the panel PNGs
  themselves displayed at CSS-constrained sizes. If file sizes make this
  slow, a follow-up adds `step<NN>_panel<MM>_thumb.png` outputs.
- Changes to `analysis/web/site.css` beyond whatever the new index template
  needs. Reuse existing `chart-card` / `tile` styles.
