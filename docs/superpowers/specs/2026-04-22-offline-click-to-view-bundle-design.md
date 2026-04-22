# Offline Click-to-View Bundle · Design

> Produce a self-contained directory that a user can ship to an offline machine
> and browse by double-clicking an HTML file. Every chart renders, every JS
> library is vendored locally, no internet required.

## Problem

The current `analysis/web/site/` tree depends on:
1. Six external directories (`china/html/`, `countries/html/`,
   `complex_network_images/`, `as_globe/html/`, `as_galaxy/html/`,
   `as_galaxy/data/`) resolved via `../../../../` relative paths.
2. Five CDN-hosted JS libraries loaded via `https://unpkg.com` and
   `https://cdn.jsdelivr.net`.
3. A runtime `fetch('../data/...')` call inside `as_galaxy.html` that
   Chrome blocks over `file://`.
4. Cross-origin `iframe.contentDocument` access (for auto-resize) that
   Chrome blocks over `file://`.

The goal is a single directory that works by pure double-click on any modern
browser, with no internet and no local server.

## Decisions (locked in during brainstorm)

| # | Topic                                 | Chosen |
| - | ------------------------------------- | ------ |
| 1 | Galaxy (127K-AS full view)            | **Dropped.** Needs `fetch()` of binary tiles; `file://` blocks it. Three 5K-AS Globe views remain. |
| 2 | Iframe auto-resize                    | **Replaced with fixed `min-height` CSS.** Chrome `file://` can't read cross-origin iframe `contentDocument`; JS resize fails silently. Each iframe's own page keeps its internal scrolling. |
| 3 | Directory layout                      | **Mirror current structure** under `offline-site/analysis/...`. Keeps existing `../../../../` references working. Adds only a `vendor/` folder for CDN libraries. |
| 4 | Bundle location                       | `offline-site/` at repo root (gitignored, regenerable). Overridable via `--out`. |

## Architecture

One new script: `analysis/web/build_offline.py`.

Pipeline (single command `python3 -m analysis.web.build_offline`):

1. **Clean** target directory (`offline-site/` by default).
2. **Download** vendor libraries into `offline-site/analysis/vendor/`
   (skippable via `--skip-download` after first run).
3. **Run the normal site build** with a Galaxy-suppression flag so
   `analysis/web/site/` emits 89 pages instead of 90 (Globe hub loses the
   Galaxy card; nav drops the route).
4. **Copy** source trees into `offline-site/analysis/`:
   - `analysis/web/site/`
   - `analysis/china/html/`
   - `analysis/countries/html/`
   - `analysis/complex_network_images/`
   - `analysis/as_globe/html/`  (3 files: `as_globe`, `as_force`, `as_strata`)
   - `analysis/web/static/` as part of the site build output
5. **Rewrite HTML `src`/`href`/`import`** references from CDN URLs to the
   vendored paths. Per-file regex pass:
   - `https://unpkg.com/3d-force-graph@1.77/dist/3d-force-graph.min.js`
     → `../../vendor/3d-force-graph@1.77/dist/3d-force-graph.min.js`
     (exact relative prefix computed from the HTML file's depth).
   - `https://unpkg.com/globe.gl@2.32/dist/globe.gl.min.js` → vendored.
   - `https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/vis-network.min.{css,js}`
     → vendored (note: the original URL contains a `dist/dist/` oddity
     in countries pyvis HTMLs — preserve faithful rewrite).
   - `https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/{css/bootstrap.min.css,js/bootstrap.bundle.min.js}`
     → vendored.
   - `https://unpkg.com/three@0.165.0/...` → should not appear (only in
     as_galaxy, which is excluded).
6. **Patch** `offline-site/analysis/web/site/assets/site.css` (or
   whichever CSS file holds the `.chart-iframe` rule — verify at build time)
   to add `min-height: 700px` (or equivalent). Patch `site.js` to wrap the
   iframe-autosize `contentDocument` access in a `try { … } catch {}` so
   Chrome `file://` failures don't break the global `load` listener.
7. **Verify** no unexpected external HTTP references remain. Grep the
   output tree for `https?://[^"'\s]+` and compare against an allowlist
   (license links: creativecommons.org, openstreetmap.org, plotly.com,
   maplibre.org, stamen.com, mapbox.com, carto.com, and the unpkg maki
   icon URL which is used as an image source inside folium maps — that
   one warrants follow-up but is low-risk because folium's maki icons are
   optional tile markers).
8. **Emit** `offline-site/README.txt` with a one-paragraph usage guide
   ("open `analysis/web/site/index.html` by double-clicking").

### Vendor inventory

URLs downloaded once into `offline-site/analysis/vendor/`:

| Library             | URL(s)                                                              | Local path                                                |
| ------------------- | ------------------------------------------------------------------- | --------------------------------------------------------- |
| 3d-force-graph 1.77 | `unpkg.com/3d-force-graph@1.77/dist/3d-force-graph.min.js`          | `vendor/3d-force-graph@1.77/dist/3d-force-graph.min.js`   |
| globe.gl 2.32       | `unpkg.com/globe.gl@2.32/dist/globe.gl.min.js`                      | `vendor/globe.gl@2.32/dist/globe.gl.min.js`               |
| vis-network 9.1.2   | `cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/vis-network.min.{css,js}` | `vendor/vis-network@9.1.2/dist/vis-network.min.{css,js}` |
| Bootstrap 5.0.0-b3  | `cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/{css/bootstrap.min.css,js/bootstrap.bundle.min.js}` | `vendor/bootstrap@5.0.0-beta3/dist/...`      |

Note: `3d-force-graph` and `globe.gl` each bundle their own three.js
inline, so we do not need a separate `three@0.165.0/` vendor entry.

## CLI

```
python3 -m analysis.web.build_offline                    # build offline-site/
python3 -m analysis.web.build_offline --out /tmp/foo     # custom target
python3 -m analysis.web.build_offline --skip-download    # reuse vendor/
python3 -m analysis.web.build_offline --verify-only      # scan existing output, exit 0 if no external URLs
```

## Directory shape (final)

```
offline-site/
├── README.txt
└── analysis/
    ├── web/site/                  (89 HTMLs; Galaxy nav entry removed)
    ├── china/html/                (31 Plotly pages)
    ├── countries/html/            (47 pages, incl. pyvis)
    ├── complex_network_images/    (13 PNGs + evolution.html)
    ├── as_globe/html/             (as_globe + as_force + as_strata)
    └── vendor/
        ├── 3d-force-graph@1.77/dist/3d-force-graph.min.js
        ├── globe.gl@2.32/dist/globe.gl.min.js
        ├── vis-network@9.1.2/dist/{vis-network.min.css, vis-network.min.js}
        └── bootstrap@5.0.0-beta3/dist/{css/bootstrap.min.css, js/bootstrap.bundle.min.js}
```

Total size ≈ 260 MB (vs 317 MB if Galaxy were included).

## Galaxy suppression mechanism

The existing `analysis/web/nav.py` `_build_globe_track()` hard-codes Galaxy
into `GLOBE_VIEWS`. To suppress Galaxy for the offline build without
affecting the normal site build:

- Add an env var `IYP_EXCLUDE_GALAXY=1` that, when set, makes
  `_build_globe_track()` filter Galaxy out of `GLOBE_VIEWS`.
- `build_offline.py` sets this env var before invoking `analysis.web.build`
  as a subprocess (or clears it afterwards).

No changes to the production site build unless the env var is set.

## Verify pass & allowlist

After rewrite, grep the output tree for `https?://`. Allowed external URLs
(license/attribution links — safe to leave as dead links offline):

- `plotly.com` — "view source" link in Plotly toolbar
- `carto.com`, `stamen.com`, `mapbox.com`, `maplibre.org` — tile provider
  attribution in folium maps
- `openstreetmap.org`, `creativecommons.org` — license footers

Anything else must be either vendored or explicitly skipped.

If the verify pass finds a `unpkg.com`, `cdnjs.cloudflare.com`, or
`cdn.jsdelivr.net` reference that was missed, the build fails with the
unresolved list.

## Re-run durability

Script is idempotent. Re-running:
- Overwrites `offline-site/analysis/` each time (clean copy).
- `--skip-download` reuses `vendor/` (saves time if network is slow).
- Each rebuild starts from the current `analysis/web/site/` etc. state,
  so regenerating an underlying analysis (e.g. step05 panel refresh)
  flows into the next offline build.

## Out of scope

- Galaxy 127K-AS view (dropped).
- Flat URL restructuring (rejected).
- Service-worker PWA packaging.
- `.zip` container (user can tar/zip themselves).
- Launcher scripts (`.sh`/`.bat`). Pure file:// only.
- Windows-specific path tweaks. All paths are POSIX-relative; Windows
  handles them transparently on any modern browser.
