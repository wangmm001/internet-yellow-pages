# Complex-Network Per-Panel Pilot (step05) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Break step05 (Degree Distribution & Power Law) into 6 separate page-per-panel URLs, each with its own medium-prose bilingual explainer. Validates the pattern for the other 12 complex-network steps.

**Architecture:** Three-layer change — (1) refactor `step05_degree_distribution.py` so each subplot becomes its own figure saved as `step05_panel<NN>_<slug>.png`; (2) extend `analysis/web/nav.py` with a `NETWORK_PANELS` table that registers six child Pages + converts the step-level Page into a `png_index` kind; (3) add `explainers.py` entries and one new Jinja template for the panel-grid landing. No CSS additions (uses existing `.grid-auto`).

**Tech Stack:** Python 3, matplotlib, Jinja2, networkx, powerlaw — all already in use. No new dependencies.

**Reference spec:** `docs/superpowers/specs/2026-04-22-network-per-panel-pilot-design.md`

---

## File Structure

Each file has one clear responsibility:

- **Modify** `analysis/complex_network/step05_degree_distribution.py` — refactor `main()` from one 6-panel figure into six single-panel render functions + a thin orchestrator. Adds: `render_panel01_bgp_ccdf`, `render_panel02_as_dep_ccdf`, `render_panel03_ixp_ccdf`, `render_panel04_dns_hosting_ccdf`, `render_panel05_comparison_pdf`, `render_panel06_summary_stats`.
- **Modify** `analysis/web/nav.py` — add `NETWORK_PANELS` list and extend `_build_network_track()` to emit one `Page` per panel + convert step05's step-level page to `kind='png_index'`.
- **Modify** `analysis/web/explainers.py` — loosen `_add()` signature so `how`/`keyterm` are keyword-only optional; add 6 new `_add()` calls for panel URLs.
- **Modify** `analysis/web/templates/step_png.html` — gate `how`/`keyterm` dialog sections behind `{% if ... %}` so absent fields render nothing.
- **Create** `analysis/web/templates/network_step_index.html` — panel-grid landing (~50 lines, reuses `.grid-auto` + `.chart-card`).
- **Modify** `analysis/web/build.py:264` — route `kind == 'png_index'` to the new template.
- **Delete** `analysis/complex_network_images/step05_degree_distribution.png` (the composite). 6 new panel PNGs land in its place.
- **Regenerate** 7 HTMLs under `analysis/web/site/network/step05*/`.

The project has no pytest. Validation happens via: (a) running the generator and verifying the PNG files exist, (b) running `build.py --dry` and verifying output paths, (c) grepping the generated HTMLs for known explainer strings, (d) browser smoke test.

---

## Task 1: Refactor step05 generator into per-panel functions

**Files:**
- Modify: `analysis/complex_network/step05_degree_distribution.py` — replace the current `main()` body (lines 101–243) with per-panel render functions + a thin orchestrator.
- Delete (produced side-effect): `analysis/complex_network_images/step05_degree_distribution.png`

The existing helpers `load_bgp_graph`, `load_dependency_graph`, `load_ixp_membership`, `load_dns_hosting`, `fit_and_plot` (lines 12–98) are unchanged. Replace everything from line 101 to end of file.

- [ ] **Step 1: Replace the `main()` block**

Replace lines 101–243 of `analysis/complex_network/step05_degree_distribution.py` with:

```python
PANEL_FILES = [
    'step05_panel01_bgp_ccdf.png',
    'step05_panel02_as_dep_ccdf.png',
    'step05_panel03_ixp_ccdf.png',
    'step05_panel04_dns_hosting_ccdf.png',
    'step05_panel05_comparison_pdf.png',
    'step05_panel06_summary_stats.png',
]


def _new_panel_fig():
    fig = plt.figure(figsize=(10, 7))
    fig.patch.set_facecolor(DARK_BG)
    return fig, fig.add_subplot(1, 1, 1)


def _annotate_fit_box(ax, info):
    ax.text(0.02, 0.02, info, transform=ax.transAxes, fontsize=9,
            color=TEXT_MUTED, va='bottom', family='monospace',
            bbox=dict(boxstyle='round,pad=0.3', facecolor=DARK_BG,
                      edgecolor=DARK_BORDER))


def render_panel01_bgp_ccdf(bgp_degrees):
    fig, ax = _new_panel_fig()
    style_ax(ax, 'BGP Peering Degree (CCDF)', 'Degree k', 'P(K ≥ k)')
    info, *params = fit_and_plot(ax, bgp_degrees, 'BGP Peering', COLORS['red'])
    _annotate_fit_box(ax, info)
    save_fig(fig, 'step05_panel01_bgp_ccdf.png')
    plt.close(fig)
    return ('BGP Peering', *params)


def render_panel02_as_dep_ccdf(dep_in_nonzero):
    fig, ax = _new_panel_fig()
    style_ax(ax, 'AS Dependency In-Degree (CCDF)\n(how many depend on this AS)',
             'In-Degree k', 'P(K ≥ k)')
    info, *params = fit_and_plot(ax, dep_in_nonzero, 'Dependency In-Degree',
                                 COLORS['cyan'])
    _annotate_fit_box(ax, info)
    save_fig(fig, 'step05_panel02_as_dep_ccdf.png')
    plt.close(fig)
    return ('Dependency In-Degree', *params)


def render_panel03_ixp_ccdf(ixp_deg_vals):
    fig, ax = _new_panel_fig()
    style_ax(ax, 'IXP Membership Degree (CCDF)\n(IXPs per AS)',
             'IXP Count k', 'P(K ≥ k)')
    info, *params = fit_and_plot(ax, ixp_deg_vals, 'IXP Membership',
                                 COLORS['orange'])
    _annotate_fit_box(ax, info)
    save_fig(fig, 'step05_panel03_ixp_ccdf.png')
    plt.close(fig)
    return ('IXP Membership', *params)


def render_panel04_dns_hosting_ccdf(dns_degrees):
    fig, ax = _new_panel_fig()
    style_ax(ax, 'DNS Hosting Degree (CCDF)\n(HostNames per AS)',
             'HostName Count k', 'P(K ≥ k)')
    if dns_degrees:
        dns_vals = list(dns_degrees.values())
        info, *params = fit_and_plot(ax, dns_vals, 'DNS Hosting', COLORS['green'])
        _annotate_fit_box(ax, info)
        result = ('DNS Hosting', *params)
    else:
        ax.text(0.5, 0.5, 'DNS data not yet extracted\n(run step02 first)',
                transform=ax.transAxes, ha='center', va='center',
                color=TEXT_SECONDARY, fontsize=14)
        result = None
    save_fig(fig, 'step05_panel04_dns_hosting_ccdf.png')
    plt.close(fig)
    return result


def render_panel05_comparison_pdf(bgp_degrees, dep_in_nonzero, ixp_deg_vals):
    fig, ax = _new_panel_fig()
    style_ax(ax, 'Degree Distribution Comparison\n(PDF, log-binned)',
             'Degree k', 'P(k)')
    for deg_data, label, color in [
        (bgp_degrees, 'BGP Peering', COLORS['red']),
        (dep_in_nonzero, 'Dependency', COLORS['cyan']),
        (ixp_deg_vals, 'IXP Member', COLORS['orange']),
    ]:
        arr = np.array(deg_data)
        arr = arr[arr > 0]
        bins = np.logspace(0, np.log10(max(arr) + 1), 50)
        hist, edges = np.histogram(arr, bins=bins, density=True)
        centers = (edges[:-1] + edges[1:]) / 2
        mask = hist > 0
        ax.loglog(centers[mask], hist[mask], 'o-', color=color, label=label,
                  markersize=4, alpha=0.8, linewidth=1.5)
    ax.legend(fontsize=10, facecolor=DARK_PANEL, edgecolor=DARK_BORDER,
              labelcolor=TEXT_MUTED)
    save_fig(fig, 'step05_panel05_comparison_pdf.png')
    plt.close(fig)


def render_panel06_summary_stats(G_bgp, G_dep, bgp_degrees, dep_in_degrees,
                                 ixp_degrees, ixp_deg_vals, dns_degrees):
    fig, ax = _new_panel_fig()
    ax.set_facecolor(DARK_PANEL)
    ax.axis('off')
    ax.set_title('Summary Statistics', fontsize=16, fontweight='bold',
                 color=TEXT_PRIMARY, pad=12)

    stats_lines = [
        f'{"Layer":<22} {"Nodes":>8} {"Edges":>10} {"<k>":>6} {"k_max":>8} {"C":>6}',
        '─' * 62,
        f'{"BGP Peering":<22} {G_bgp.number_of_nodes():>8,} {G_bgp.number_of_edges():>10,} '
        f'{2*G_bgp.number_of_edges()/G_bgp.number_of_nodes():>6.1f} {max(bgp_degrees):>8,} '
        f'{nx.transitivity(G_bgp):>6.4f}',
        f'{"AS Dependency (dir)":<22} {G_dep.number_of_nodes():>8,} {G_dep.number_of_edges():>10,} '
        f'{G_dep.number_of_edges()/G_dep.number_of_nodes():>6.1f} {max(dep_in_degrees):>8,} {"N/A":>6}',
        f'{"IXP Membership":<22} {len(ixp_degrees):>8,} {"N/A":>10} '
        f'{np.mean(ixp_deg_vals):>6.1f} {max(ixp_deg_vals):>8,} {"N/A":>6}',
    ]
    if dns_degrees:
        dns_vals = list(dns_degrees.values())
        stats_lines.append(
            f'{"DNS Hosting":<22} {len(dns_degrees):>8,} {"N/A":>10} '
            f'{np.mean(dns_vals):>6.0f} {max(dns_vals):>8,} {"N/A":>6}'
        )
    stats_text = '\n'.join(stats_lines)
    ax.text(0.05, 0.85, stats_text, transform=ax.transAxes,
            fontsize=11, color=TEXT_MUTED, va='top', family='monospace',
            bbox=dict(boxstyle='round,pad=0.5', facecolor=DARK_BG,
                      edgecolor=DARK_BORDER))
    save_fig(fig, 'step05_panel06_summary_stats.png')
    plt.close(fig)


def main():
    G_bgp = load_bgp_graph()
    G_dep = load_dependency_graph()
    ixp_degrees = load_ixp_membership()

    dns_path = os.path.join(DATA_DIR, 'dns_as_hosting.csv')
    dns_degrees = load_dns_hosting() if os.path.exists(dns_path) else None

    bgp_degrees = [d for _, d in G_bgp.degree()]
    dep_in_degrees = [d for _, d in G_dep.in_degree()]
    ixp_deg_vals = list(ixp_degrees.values())
    dep_in_nonzero = [d for d in dep_in_degrees if d > 0]

    results = []
    r = render_panel01_bgp_ccdf(bgp_degrees);          results.append(r) if r else None
    r = render_panel02_as_dep_ccdf(dep_in_nonzero);    results.append(r) if r else None
    r = render_panel03_ixp_ccdf(ixp_deg_vals);         results.append(r) if r else None
    r = render_panel04_dns_hosting_ccdf(dns_degrees);  results.append(r) if r else None
    render_panel05_comparison_pdf(bgp_degrees, dep_in_nonzero, ixp_deg_vals)
    render_panel06_summary_stats(G_bgp, G_dep, bgp_degrees, dep_in_degrees,
                                 ixp_degrees, ixp_deg_vals, dns_degrees)

    print('\n── Power-law Fitting Results ──')
    for name, alpha, xmin, R_ln, p_ln, R_exp, p_exp in results:
        print(f'{name}: α={alpha:.3f}, xmin={xmin:.0f}, '
              f'vs_lognorm(R={R_ln:.3f},p={p_ln:.4f}), '
              f'vs_exp(R={R_exp:.3f},p={p_exp:.4f})')

    # Preserve the existing results-CSV side-effect
    results_path = os.path.join(DATA_DIR, 'step05_powerlaw_fits.csv')
    with open(results_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['layer', 'alpha', 'xmin', 'R_vs_lognorm', 'p_vs_lognorm',
                    'R_vs_exp', 'p_vs_exp'])
        for row in results:
            w.writerow(row)
    print(f'Saved fit results to {results_path}')

    # Delete the legacy composite if it still exists
    old_composite = os.path.join(
        os.path.dirname(DATA_DIR), 'complex_network_images',
        'step05_degree_distribution.png')
    if os.path.exists(old_composite):
        os.remove(old_composite)
        print(f'Removed legacy composite: {old_composite}')


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Run the generator**

Run from repo root:
```
python3 -m analysis.complex_network.step05_degree_distribution
```
Expected: prints graph-load lines + a "── Power-law Fitting Results ──" block + "Saved fit results..." + optionally "Removed legacy composite" line. No traceback.

- [ ] **Step 3: Verify the 6 new PNGs exist and the composite is gone**

Run:
```
ls -la analysis/complex_network_images/step05_*.png
```
Expected: exactly 6 PNGs named `step05_panel01_bgp_ccdf.png` through `step05_panel06_summary_stats.png`. No `step05_degree_distribution.png`.

```
test ! -f analysis/complex_network_images/step05_degree_distribution.png && echo "composite removed" || echo "composite STILL PRESENT"
```
Expected: `composite removed`.

- [ ] **Step 4: Spot-check one panel PNG visually**

If a desktop is available:
```
open analysis/complex_network_images/step05_panel01_bgp_ccdf.png
```
Or use `Read` tool on the PNG to visually confirm it renders as a single-panel CCDF with red dots + red fit line + info box (not a 6-panel grid).

If headless, check file size:
```
wc -c analysis/complex_network_images/step05_panel0*.png
```
Expected: each panel in the 50–300 KB range (single-panel figures at 10×7 inch × 180 dpi), all non-zero.

- [ ] **Step 5: Commit**

```bash
git add analysis/complex_network/step05_degree_distribution.py analysis/complex_network_images/
git commit -m "step05: split composite into 6 per-panel PNGs"
```

---

## Task 2: Loosen `explainers._add()` signature

**Files:**
- Modify: `analysis/web/explainers.py:16-27` — change the `_add()` function signature so `how` and `keyterm` are optional.

- [ ] **Step 1: Replace the `_add()` definition**

Find this block near the top of `analysis/web/explainers.py`:

```python
def _add(url: str, title_zh: str, title_en: str, *, what: tuple[str, str],
         how: tuple[str, str], see: tuple[str, str],
         keyterm: tuple[str, str, str] | None = None) -> None:
    EXPLAINERS[url] = {
        'title_zh': title_zh, 'title_en': title_en,
        'what_zh': what[0], 'what_en': what[1],
        'how_zh': how[0], 'how_en': how[1],
        'see_zh': see[0], 'see_en': see[1],
        'keyterm_zh': keyterm[1] if keyterm else None,
        'keyterm_en': keyterm[2] if keyterm else None,
        'keyterm_label': keyterm[0] if keyterm else None,
    }
```

Replace with:

```python
def _add(url: str, title_zh: str, title_en: str, *, what: tuple[str, str],
         how: tuple[str, str] | None = None,
         see: tuple[str, str],
         keyterm: tuple[str, str, str] | None = None) -> None:
    EXPLAINERS[url] = {
        'title_zh': title_zh, 'title_en': title_en,
        'what_zh': what[0], 'what_en': what[1],
        'how_zh': how[0] if how else None,
        'how_en': how[1] if how else None,
        'see_zh': see[0], 'see_en': see[1],
        'keyterm_zh': keyterm[1] if keyterm else None,
        'keyterm_en': keyterm[2] if keyterm else None,
        'keyterm_label': keyterm[0] if keyterm else None,
    }
```

All existing call sites pass `how=` and `keyterm=` as keyword arguments, so none break.

- [ ] **Step 2: Verify existing explainers still register**

Run:
```
python3 -c "from analysis.web import explainers; print(len(explainers.EXPLAINERS), 'entries'); print(sorted(k for k in explainers.EXPLAINERS if k.startswith('/network/'))[:3])"
```
Expected: a count > 20 and three sample URLs from `/network/`. No `TypeError`.

- [ ] **Step 3: Commit**

```bash
git add analysis/web/explainers.py
git commit -m "explainers: make how/keyterm optional in _add()"
```

---

## Task 3: Gate `how`/`keyterm` in `step_png.html`

**Files:**
- Modify: `analysis/web/templates/step_png.html` — wrap the `how` and `keyterm` dialog sections in `{% if %}` conditionals.

First verify the current template's dialog content. The file currently ends at line 73 and does NOT include the dialog body (per Read result: line 73 is `{% endblock %}`). The dialog block actually lives elsewhere.

- [ ] **Step 1: Locate the dialog template**

Run:
```
grep -rn "cap-dialog\|what_zh\|how_zh" analysis/web/templates/
```
Expected output: finds the file(s) containing the `<dialog id="cap-dialog">` with `{{ explainer.what_zh }}` / `{{ explainer.how_zh }}` / `{{ explainer.see_zh }}` bindings. Likely `base.html` or a partial included from it.

Based on what you find, open that file.

- [ ] **Step 2: Wrap the `how_zh`/`how_en` paragraphs and the keyterm block**

Find the two `<p>` lines that render `{{ explainer.how_zh }}` and `{{ explainer.how_en }}`, plus their surrounding `<h4>` header. Wrap the whole `how` section (from its `<h4>` to the closing `</p>` of the English paragraph) with:

```jinja
{% if explainer.how_zh %}
…existing <h4> + two <p> lines…
{% endif %}
```

Similarly find the `keyterm` block (uses `{{ explainer.keyterm_label }}`, `keyterm_zh`, `keyterm_en`) and wrap it:

```jinja
{% if explainer.keyterm_label %}
…existing keyterm block…
{% endif %}
```

Do NOT wrap `what` or `see` — those remain mandatory.

- [ ] **Step 3: Smoke-test the build with an existing page**

```
python3 -m analysis.web.build --dry
```
Expected: no traceback. Prints a count of intended outputs.

- [ ] **Step 4: Verify an existing step05 page still renders its `how` section (since step05's existing explainer has `how`)**

Run:
```
python3 -m analysis.web.build
grep -c '如何读\|怎么读' analysis/web/site/network/step05/index.html || echo "NO CURRENT step05 content yet"
```
(step05 index page still exists at this task point — it'll be replaced in Task 6.) If grep returns ≥ 1, the existing `how` section still renders. If it's 0 because step05 is no longer on disk (unlikely at this point), just verify another network page that has an explainer, e.g. `network/step06`:
```
grep -c '怎么读\|如何读\|How to read' analysis/web/site/network/step06/index.html
```
Expected: ≥ 1.

- [ ] **Step 5: Commit**

```bash
git add analysis/web/templates/
git commit -m "templates: gate how/keyterm blocks on presence"
```

---

## Task 4: Register panel Pages in `nav.py`

**Files:**
- Modify: `analysis/web/nav.py` — add `NETWORK_PANELS` data structure above `_build_network_track()`, and extend `_build_network_track()` to emit panel Pages and convert step05's step-level page to `kind='png_index'`.

- [ ] **Step 1: Add `NETWORK_PANELS` declaration**

Find the existing `NETWORK_GROUPS` declaration (currently at line 369–373) and immediately BELOW it (above the `def _build_network_track()` line at ~376), insert:

```python
# Panel-level pages for step05 pilot.  Other steps still use the single
# composite PNG from NETWORK_STEPS until they are migrated.
# Tuple shape: (parent_step, panel_id, png_file, slug, title_zh, title_en, subtitle_zh, kpis)
NETWORK_PANELS: list[tuple[int, int, str, str, str, str, str, list[str]]] = [
    (5, 1, 'step05_panel01_bgp_ccdf.png', 'step05_panel01',
     'BGP 对等度的互补累积分布',
     'BGP Peering Degree · CCDF',
     '每个 AS 的对等邻居数如何分布 · Scale-free heavy tail',
     ['α ≈ 2.10', '幂律长尾']),
    (5, 2, 'step05_panel02_as_dep_ccdf.png', 'step05_panel02',
     'AS 依赖入度的互补累积分布',
     'AS Dependency In-Degree · CCDF',
     '有多少 AS 在依赖这个 AS 作为上游',
     ['依赖集中于头部']),
    (5, 3, 'step05_panel03_ixp_ccdf.png', 'step05_panel03',
     'IXP 成员度的互补累积分布',
     'IXP Membership Degree · CCDF',
     '每个 AS 加入了多少个交换中心',
     ['少数 AS · 数十 IXP']),
    (5, 4, 'step05_panel04_dns_hosting_ccdf.png', 'step05_panel04',
     'DNS 托管度的互补累积分布',
     'DNS Hosting Degree · CCDF',
     '每个 AS 承载的权威 / 托管域名数',
     ['超级托管 AS 偏头部']),
    (5, 5, 'step05_panel05_comparison_pdf.png', 'step05_panel05',
     '三层度分布的对数分箱对比',
     'Three-Layer PDF Comparison · Log-binned',
     'BGP / 依赖 / IXP 三层的 P(k) 同框',
     ['三层同构 · 尾部一致']),
    (5, 6, 'step05_panel06_summary_stats.png', 'step05_panel06',
     '各层拓扑指标汇总',
     'Layer-Level Topology Summary',
     '节点 / 边 / 平均度 / k_max / 聚类系数',
     ['单表速览']),
]
```

- [ ] **Step 2: Rewrite the step05 branch in `_build_network_track()`**

Locate `_build_network_track()` (line 376). Inside the `for step in steps:` loop, currently it produces one `Page` per step with `kind='png'`. Replace the whole `for step in steps:` block so step05 takes a different branch:

```python
def _build_network_track() -> Track:
    rows_by_step = {row[0]: row for row in NETWORK_STEPS}
    panels_by_step: dict[int, list[tuple]] = {}
    for p in NETWORK_PANELS:
        panels_by_step.setdefault(p[0], []).append(p)

    phases: list[Phase] = []
    for key, title_zh, title_en, steps in NETWORK_GROUPS:
        pages: list[Page] = []
        for step in steps:
            step_n, src_file, zh, en, subtitle, kpis = rows_by_step[step]
            if step in panels_by_step:
                # Step-level page becomes an index of its panels
                step_panels = sorted(panels_by_step[step], key=lambda r: r[1])
                pages.append(Page(
                    slug=f'step{step:02d}',
                    url=f'/network/step{step:02d}/',
                    track='network',
                    title_zh=zh,
                    title_en=en,
                    kind='png_index',
                    src=None,
                    phase=key,
                    step=step_n,
                    kpis=kpis,
                    subtitle_zh=subtitle,
                    extra={'panels': [
                        {
                            'url': f'/network/{slug}/',
                            'src': f'../../../../complex_network_images/{png}',
                            'title_zh': ptz,
                            'title_en': pte,
                            'subtitle_zh': psub,
                            'kpis': pkpis,
                            'panel_id': pid,
                        }
                        for (_s, pid, png, slug, ptz, pte, psub, pkpis) in step_panels
                    ]},
                ))
                # One Page per panel
                for (_s, pid, png, slug, ptz, pte, psub, pkpis) in step_panels:
                    pages.append(Page(
                        slug=slug,
                        url=f'/network/{slug}/',
                        track='network',
                        title_zh=ptz,
                        title_en=pte,
                        kind='png',
                        src=f'../../../../complex_network_images/{png}',
                        phase=key,
                        step=step_n,
                        part=pid,
                        kpis=pkpis,
                        subtitle_zh=psub,
                    ))
            else:
                pages.append(Page(
                    slug=f'step{step:02d}',
                    url=f'/network/step{step:02d}/',
                    track='network',
                    title_zh=zh,
                    title_en=en,
                    kind='png',
                    src=f'../../../../complex_network_images/{src_file}',
                    phase=key,
                    step=step_n,
                    kpis=kpis,
                    subtitle_zh=subtitle,
                ))
        phases.append(Phase(key, title_zh, title_en, pages))
    # (rest of function unchanged — dash_pages, phases.insert, return Track)
```

Keep the rest of `_build_network_track()` (the `dash_pages = [...]` block, `phases.insert(0, ...)`, and `return Track(...)`) exactly as it is today.

- [ ] **Step 3: Smoke-test the nav enumeration**

Run:
```
python3 -c "from analysis.web import nav; m = nav.build_site_model(); urls = [p.url for p in next(t for t in m['tracks'] if t.slug=='network').all_pages()]; print('step05-related:'); [print('  ', u) for u in urls if 'step05' in u]"
```
Expected output (7 URLs, index first then 6 panels in order):
```
step05-related:
   /network/step05/
   /network/step05_panel01/
   /network/step05_panel02/
   /network/step05_panel03/
   /network/step05_panel04/
   /network/step05_panel05/
   /network/step05_panel06/
```

- [ ] **Step 4: Commit**

```bash
git add analysis/web/nav.py
git commit -m "nav: register step05 panel Pages + png_index landing"
```

---

## Task 5: Create `network_step_index.html` template

**Files:**
- Create: `analysis/web/templates/network_step_index.html` — ~50-line panel-grid landing.

- [ ] **Step 1: Write the template file**

Create `analysis/web/templates/network_step_index.html` with:

```jinja
{% extends 'base.html' %}
{% block body %}
<article class="page">
  <nav class="breadcrumb">
    <a href="{{ assets_prefix }}index.html">首页 · Home</a>
    <span class="sep">›</span>
    <a href="{{ assets_prefix }}{{ track.slug }}/index.html">{{ track.title_zh }}</a>
    <span class="sep">›</span>
    <span class="cur">{{ page.title_zh }}</span>
  </nav>

  <header class="page-head">
    <div class="row-1">
      <span class="tier-badge is-green">N</span>
      <p class="eyebrow" style="margin:0;">
        {{ track.title_en }}
        {% if page.phase %}· Phase {{ page.phase }}{% endif %}
        {% if page.step %}· Step {{ '%02d'|format(page.step) }}{% endif %}
        · {{ page.extra.panels|length }} 个面板 · {{ page.extra.panels|length }} panels
      </p>
    </div>
    <h1>{{ page.title_zh }}</h1>
    <p class="en">{{ page.title_en }}</p>
    {% if page.subtitle_zh %}<p class="sub">{{ page.subtitle_zh }}</p>{% endif %}
    {% if page.kpis %}
    <div class="chart-caption" style="margin-top:12px;">
      {% for k in page.kpis %}<span class="chip" style="margin-right:6px;">{{ k }}</span>{% endfor %}
    </div>
    {% endif %}
  </header>

  <section class="grid-auto" style="margin-top:18px;">
    {% for panel in page.extra.panels %}
    <a class="chart-card" href="{{ assets_prefix }}{{ panel.url.lstrip('/') }}index.html"
       style="display:block; text-decoration:none; color:inherit;">
      <div class="chart-head">
        <div>
          <h3 style="font-size:14px; margin:0;">Panel {{ '%02d'|format(panel.panel_id) }} · {{ panel.title_zh }}</h3>
          <span class="en" style="font-size:11px;">{{ panel.title_en }}</span>
        </div>
      </div>
      <div class="chart-png-wrap" style="max-height:220px; overflow:hidden;">
        <img class="chart-png" src="{{ panel.src }}" alt="{{ panel.title_en }}"
             loading="lazy" decoding="async"
             style="width:100%; height:auto; display:block;">
      </div>
      {% if panel.subtitle_zh %}
      <div class="chart-caption" style="padding:8px 12px; font-size:12px;">
        {{ panel.subtitle_zh }}
      </div>
      {% endif %}
    </a>
    {% endfor %}
  </section>

  <nav class="nav-foot">
    {% if prev_page %}
    <a class="nav-link-card" data-nav="prev" href="{{ assets_prefix }}{{ prev_page.url.lstrip('/') }}index.html">
      <div class="lab">← 上一页 · Prev</div>
      <div class="title">{{ prev_page.title_zh }}</div>
      <div class="en">{{ prev_page.title_en }}</div>
    </a>
    {% else %}<span class="nav-link-card is-pad"></span>{% endif %}

    {% if next_page %}
    <a class="nav-link-card is-next" data-nav="next" href="{{ assets_prefix }}{{ next_page.url.lstrip('/') }}index.html">
      <div class="lab">下一页 · Next →</div>
      <div class="title">{{ next_page.title_zh }}</div>
      <div class="en">{{ next_page.title_en }}</div>
    </a>
    {% else %}<span class="nav-link-card is-pad"></span>{% endif %}
  </nav>
</article>
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add analysis/web/templates/network_step_index.html
git commit -m "templates: add network_step_index for panel-grid landing"
```

---

## Task 6: Route `png_index` in `build.py`

**Files:**
- Modify: `analysis/web/build.py:264` — add a third branch in the template selection.

- [ ] **Step 1: Replace the template selection line**

Find line 264 (inside the `for page in track.all_pages():` loop):

```python
            template_name = 'step_plotly.html' if page.kind == 'plotly' else 'step_png.html'
```

Replace with:

```python
            if page.kind == 'plotly':
                template_name = 'step_plotly.html'
            elif page.kind == 'png_index':
                template_name = 'network_step_index.html'
            else:
                template_name = 'step_png.html'
```

- [ ] **Step 2: Smoke-test the dry build**

Run:
```
python3 -m analysis.web.build --dry 2>&1 | tail -10
```
Expected: "wrote N pages in X.Ys" — no tracebacks. Missing-source report should NOT flag the 6 panel PNGs (they were produced in Task 1).

- [ ] **Step 3: Commit**

```bash
git add analysis/web/build.py
git commit -m "build: route png_index kind to network_step_index template"
```

---

## Task 7: Author 6 panel explainers

**Files:**
- Modify: `analysis/web/explainers.py` — add 6 new `_add()` calls for the step05 panels, placed in the `/network/` section alongside the existing step05 entry.

- [ ] **Step 1: Find the existing step05 explainer block**

Run:
```
grep -n "'/network/step05" analysis/web/explainers.py
```
Expected: a line number where the existing step05 explainer is declared. Let this line be `L`.

- [ ] **Step 2: Insert the 6 panel explainers**

Immediately AFTER the closing paren + blank line of the existing step05 `_add('/network/step05/', ...)` call, insert these six new calls. Each uses only `what=` + `see=` (medium-prose form) — `how` and `keyterm` are omitted.

```python
_add('/network/step05_panel01/',
     'BGP 对等度的互补累积分布',
     'BGP Peering Degree · CCDF',
     what=(
         '横轴是单个 AS 拥有的 BGP 对等邻居数 k；纵轴是"拥有 ≥ k 个邻居"的 AS 占比。'
         '在双对数坐标下观察尾部斜率，若呈直线就是幂律尾 P(K≥k) ~ k^−(α−1)。',
         'X-axis is peer-count k per AS; Y-axis is the fraction of ASes with ≥ k '
         'neighbours. On log-log axes, a straight tail indicates power-law '
         'P(K≥k) ~ k^−(α−1).'),
     see=(
         'IYP BGP 层 α ≈ 2.10：99% 的 AS 只有 1–20 个对等邻居，但尾部一小撮超级 '
         'hub (Tier-1 / Cloudflare / Google) 连了数千个。曲线尾部的红色拟合线'
         '就是幂律预测——实际点几乎贴着线下滑，印证无标度结构。',
         'IYP BGP α ≈ 2.10: 99% of ASes have 1–20 peers, but a handful of '
         'super-hubs (Tier-1s, Cloudflare, Google) connect to thousands. The '
         'red fitted tail line is the power-law prediction; observed points '
         'track it almost exactly, confirming the scale-free structure.'))

_add('/network/step05_panel02/',
     'AS 依赖入度的互补累积分布',
     'AS Dependency In-Degree · CCDF',
     what=(
         '把 IHR Hegemony 图的边看作"A 依赖 B 作为上游"，统计每个 AS 被多少个下游 AS '
         '当作关键上游。横轴是入度 k，纵轴是"被 ≥ k 个下游依赖"的 AS 占比，'
         '仍然用双对数坐标。',
         'Treat IHR Hegemony edges as "A depends on B upstream". Count how many '
         'downstream ASes each AS carries. X-axis is in-degree k; Y-axis is the '
         'fraction of ASes with ≥ k downstream dependents. Log-log axes.'),
     see=(
         '依赖入度的长尾比对等度更陡：绝大多数 AS 没有任何下游依赖，只有少数'
         'Tier-1 / 国际云承载了成千上万个下游。这解释了为什么单点故障（一家 '
         '运营商）会瞬间影响大片用户——依赖在结构上被高度集中了。',
         'The dependency tail is steeper than peering: most ASes have zero '
         'downstream dependents; only a few Tier-1s and global clouds carry '
         'thousands. This is why a single-operator outage cascades to millions '
         'of users — dependency is structurally concentrated.'))

_add('/network/step05_panel03/',
     'IXP 成员度的互补累积分布',
     'IXP Membership Degree · CCDF',
     what=(
         '一个 AS 可以同时加入多个 Internet Exchange Point (IXP)——越多 IXP，越容易'
         '在全球各地建立本地对等。横轴是该 AS 加入的 IXP 数量，纵轴是"至少加入 k '
         '个 IXP"的 AS 占比。',
         'An AS can join multiple Internet Exchange Points (IXPs) — more IXPs '
         'means easier local peering worldwide. X-axis is the number of IXPs an '
         'AS has joined; Y-axis is the fraction of ASes present at ≥ k IXPs.'),
     see=(
         '极少数 AS（通常是全球 CDN 和大型 Tier-1）进入 50+ IXP，是事实意义上的'
         '"全球对等锚"；大多数 AS 只进入 1–2 个本地 IXP。与 BGP 对等度相比，IXP '
         '度的头部更稀薄，显示 IXP 是头部运营商才消费得起的资源。',
         'A tiny minority (global CDNs, Tier-1s) are present at 50+ IXPs — the '
         'de-facto global peering anchors. Most ASes are at 1–2 local IXPs. '
         'The head is thinner than BGP-peering; IXP presence is a resource only '
         'large operators can afford.'))

_add('/network/step05_panel04/',
     'DNS 托管度的互补累积分布',
     'DNS Hosting Degree · CCDF',
     what=(
         '每个 AS 承载了多少公网可解析的主机名（A/AAAA 终点属于本 AS 的 IP）。'
         '横轴是该 AS 承载的主机名数量，纵轴是"托管 ≥ k 个主机名"的 AS 占比。'
         '若原始数据尚未抽取，此面板会显示"DNS data not yet extracted"。',
         'Counts how many publicly-resolvable hostnames land on each AS (A/AAAA '
         'answers pointing at IPs in that AS). X-axis is hostnames hosted; '
         'Y-axis is the fraction of ASes hosting ≥ k. If upstream data is not '
         'extracted yet, the panel shows a "DNS data not yet extracted" notice.'),
     see=(
         '托管度比任何其他层都更极端地集中：Cloudflare / Google / AWS 单家承载'
         '上千万个主机名，而 99% 的 AS 只承载 < 1K。这是现代内容层"云化"的直接'
         '后果——DNS 层本身就是一个高度不均的经济市场。',
         'Hosting concentration is more extreme than any other layer: '
         'Cloudflare / Google / AWS each host tens of millions of hostnames, '
         'while 99% of ASes host < 1K. This is cloud centralisation made '
         'visible — the DNS layer is already a lopsided economic market.'))

_add('/network/step05_panel05/',
     '三层度分布的对数分箱对比',
     'Three-Layer PDF Comparison · Log-binned',
     what=(
         '不再看"累积"（CCDF），而是直接画概率密度 P(k)——每个度值的概率。'
         '采用对数分箱（log-bins）把稀疏尾部合并成可见的点。BGP / 依赖 / IXP '
         '三条曲线同框放在双对数坐标下对比。',
         'Instead of the cumulative view (CCDF), plot the probability density '
         'P(k) directly — probability of each degree value. Log-binning merges '
         'sparse tail points into visible clusters. Three curves (BGP, '
         'Dependency, IXP) compared on one set of log-log axes.'),
     see=(
         '三条曲线几乎平行下滑——说明它们都服从相似指数的幂律（约 α ≈ 2）。'
         '差异在绝对位置：BGP 最高（最多 AS 参与），IXP 最低（参与门槛高）。'
         '同一套"无标度"结构在完全不同的资源维度上反复出现，是互联网的底层特征。',
         'The three curves decay in near-parallel — they share a similar '
         'power-law exponent (α ≈ 2). They differ only in absolute position: '
         'BGP sits highest (most ASes participate), IXP lowest (higher cost of '
         'entry). The same scale-free structure recurs across different '
         'resource dimensions — a fundamental Internet signature.'))

_add('/network/step05_panel06/',
     '各层拓扑指标汇总',
     'Layer-Level Topology Summary',
     what=(
         '一张速览表：每一层（BGP 对等 / AS 依赖 / IXP 成员 / DNS 托管）的节点数、'
         '边数、平均度 <k>、最大度 k_max、全局聚类系数 C。用等宽字体排版成控制台'
         '风格。',
         'A one-look summary table per layer (BGP Peering, AS Dependency, '
         'IXP Membership, DNS Hosting): node count, edge count, average degree '
         '<k>, maximum degree k_max, global clustering coefficient C. Monospaced '
         'console-style layout.'),
     see=(
         '读者可以直接比较各层规模：BGP 是最大的节点池（~10 万 AS），但聚类系数 '
         'C 偏低（稀疏连接）；AS 依赖的 <k> 更高但节点数少得多；IXP 层节点最少'
         '但 k_max 不算突出。这张表是后续所有中心性 / k-core / 社区分析的"底牌"。',
         'At a glance you can compare layer scales: BGP has the largest node '
         'pool (~100K ASes) but low clustering C (sparse). AS Dependency has '
         'higher <k> but far fewer nodes. IXP has the fewest nodes and a '
         'modest k_max. This table is the baseline all subsequent centrality, '
         'k-core, and community analyses build on.'))
```

- [ ] **Step 3: Verify all 7 entries are registered**

Run:
```
python3 -c "from analysis.web import explainers; urls = sorted(k for k in explainers.EXPLAINERS if k.startswith('/network/step05')); print(len(urls)); [print(u) for u in urls]"
```
Expected:
```
7
/network/step05/
/network/step05_panel01/
/network/step05_panel02/
/network/step05_panel03/
/network/step05_panel04/
/network/step05_panel05/
/network/step05_panel06/
```

- [ ] **Step 4: Commit**

```bash
git add analysis/web/explainers.py
git commit -m "explainers: add 6 step05 panel explainers (medium prose)"
```

---

## Task 8: Build the site and verify end-to-end

**Files:**
- Modified (by build): `analysis/web/site/network/step05*/index.html` (7 new/rewritten files)
- Modified (by build): `analysis/web/build_manifest.json`

- [ ] **Step 1: Full rebuild**

```
python3 -m analysis.web.build
```
Expected: "wrote N pages in X.Ys" — no missing-source warnings, no broken links. Page count grows by 6 vs previous build (step05 composite URL kept, 6 new panel URLs added).

- [ ] **Step 2: Verify the 7 output HTMLs exist**

```
ls analysis/web/site/network/step05*/index.html
```
Expected output:
```
analysis/web/site/network/step05/index.html
analysis/web/site/network/step05_panel01/index.html
analysis/web/site/network/step05_panel02/index.html
analysis/web/site/network/step05_panel03/index.html
analysis/web/site/network/step05_panel04/index.html
analysis/web/site/network/step05_panel05/index.html
analysis/web/site/network/step05_panel06/index.html
```

- [ ] **Step 3: Confirm the step05 index renders 6 thumbnail cards**

```
grep -c 'step05_panel0' analysis/web/site/network/step05/index.html
```
Expected: ≥ 6 (each panel referenced at least once: one link href + one img src per card).

```
grep -c 'Panel 0' analysis/web/site/network/step05/index.html
```
Expected: 6 (one `Panel 0N · …` heading per card).

- [ ] **Step 4: Confirm a panel page renders the explainer**

```
grep -c 'α ≈ 2.10\|99% 的 AS' analysis/web/site/network/step05_panel01/index.html
```
Expected: ≥ 1 — the panel01 explainer prose is present.

```
grep -c '怎么读\|How to read' analysis/web/site/network/step05_panel01/index.html
```
Expected: 0 — medium prose has no `how` section, so no "怎么读" heading renders.

- [ ] **Step 5: Visual smoke test**

From repo root:
```
python3 -m http.server 8765 &
sleep 2
open 'http://localhost:8765/analysis/web/site/network/step05/index.html' 2>/dev/null || curl -s 'http://localhost:8765/analysis/web/site/network/step05/index.html' | grep -c 'step05_panel'
```

Manual checks (if browser available):
- step05 landing shows a grid of 6 thumbnail cards
- Clicking a thumbnail navigates to `/network/step05_panelNN/`
- Panel page shows one large PNG + "图解 · Explainer" button
- Clicking the button opens a dialog with only "这是什么图" + "能看出什么" sections (no "怎么读", no keyterm block)
- Prev/next navigation works across panels and back to other step pages

Kill the server:
```
pkill -f "http.server 8765" || true
```

- [ ] **Step 6: Commit the regenerated site**

```bash
git add analysis/web/site/network/ analysis/web/build_manifest.json
git commit -m "site: regenerate step05 as panel-index + 6 panel pages"
```

---

## Self-Review

1. **Spec coverage:**
   - "Refactor generator, emit 6 PNGs, delete composite" → Task 1 ✓
   - "Loosen `_add()` signature" → Task 2 ✓
   - "Gate `how`/`keyterm` in template" → Task 3 ✓
   - "Add `NETWORK_PANELS` + panel Pages + `png_index` kind" → Task 4 ✓
   - "New `network_step_index.html` template" → Task 5 ✓
   - "Route `png_index` in build.py" → Task 6 ✓
   - "Author 6 medium-prose explainers" → Task 7 ✓
   - "Regenerate 7 HTMLs" → Task 8 ✓
   - "Re-run durability (idempotent)" → Task 1 re-run overwrites PNGs; Task 8 re-run overwrites HTMLs. Confirmed by design.

2. **Placeholder scan:** No TBD / TODO / "add appropriate error handling". Every code block is complete.

3. **Type consistency:** `NETWORK_PANELS` tuple shape (8 fields) matches consumer in `_build_network_track()`. Panel URL/slug/path scheme (`step05_panelNN`) used consistently across nav.py, explainers.py, and templates. Template contract (`page.extra.panels` list of dicts with `url`/`src`/`title_*`/`subtitle_zh`/`kpis`/`panel_id`) matches producer in nav.py.

4. **One ambiguity resolved inline:** Task 3 requires locating the dialog template because `step_png.html` itself only shows the image + chip + Full-res link — the dialog body lives in a parent/partial. Step 1 of Task 3 does a grep to locate it rather than guessing.

5. **Ordering:** Task 1 produces PNGs that Task 8's build consumes. Task 2 (loosen `_add`) must precede Task 7 (use the loosened signature). Task 4 (register Pages) must precede Tasks 5/6 (template + build routing consume the `png_index` kind). Task 8 depends on all previous tasks.
