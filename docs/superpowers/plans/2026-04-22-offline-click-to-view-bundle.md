# Offline Click-to-View Bundle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce `offline-site/` — a self-contained directory that works by double-clicking an HTML file on any offline machine, with every chart, JS library, and asset fully local.

**Architecture:** One orchestrator script `analysis/web/build_offline.py` that (1) fetches CDN libraries once into `offline-site/analysis/vendor/`, (2) runs the normal site build with `IYP_EXCLUDE_GALAXY=1` so Galaxy (which needs `fetch()` and is blocked by Chrome `file://`) is dropped, (3) copies the site + its external-artifact directories into `offline-site/analysis/`, (4) single-pass regex rewrite of CDN URLs → vendored paths in all HTMLs, (5) verifies no unexpected external URLs remain.

**Tech Stack:** Python stdlib (`urllib.request`, `shutil`, `re`, `subprocess`, `pathlib`). No new dependencies. Good news found during scoping: `.chart-frame` already has `min-height: 720px` in `site.css`, and `site.js:88-98` already wraps `contentDocument` access in `try/catch`, so neither CSS nor JS needs patching — Chrome `file://` silently falls back to the fixed 720px iframe height, which is the intended behavior.

**Reference spec:** `docs/superpowers/specs/2026-04-22-offline-click-to-view-bundle-design.md`

---

## File Structure

- **Create** `analysis/web/build_offline.py` — orchestrator with CLI (`--out`, `--skip-download`, `--verify-only`).
- **Modify** `analysis/web/nav.py` — honor `IYP_EXCLUDE_GALAXY` env var in `_build_globe_track()` so Galaxy view is filterable without touching the production build.
- **Modify** `.gitignore` — add `offline-site/` so the output directory is regenerable but not committed.
- **Output** (generated, gitignored): `offline-site/` with mirror layout.

Single orchestrator script; each pipeline step is a module-level function so we can test/verify them in isolation.

No tests directory (project doesn't use pytest). Validation via an inline `--self-test` flag that exercises pure functions with small fixtures (URL rewrite, vendor path calculation, allowlist check).

---

## Task 1: Scaffold `build_offline.py` with CLI skeleton

**Files:**
- Create: `analysis/web/build_offline.py`
- Modify: `.gitignore` (add `offline-site/`)

- [ ] **Step 1: Write the initial script**

Create `analysis/web/build_offline.py` with:

```python
"""Build an offline, click-to-view bundle of the IYP analysis site.

Produces <out>/ (default: offline-site/) containing:
  analysis/web/site/                  — 89 HTMLs (Galaxy excluded)
  analysis/china/html/                — 31 Plotly pages
  analysis/countries/html/            — 47 pages
  analysis/complex_network_images/    — 13 PNGs + evolution.html
  analysis/as_globe/html/             — 3 WebGL views
  analysis/vendor/                    — vendored CDN JS/CSS

Every external CDN URL is rewritten to point at the vendored copy.
Runs idempotently; re-runs overwrite the target cleanly.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / 'offline-site'

# Source trees copied into the offline bundle.  Paths are relative to REPO_ROOT.
SOURCE_TREES = [
    'analysis/web/site',
    'analysis/china/html',
    'analysis/countries/html',
    'analysis/complex_network_images',
    'analysis/as_globe/html',
]

# CDN URLs → local vendor paths (relative to <out>/analysis/vendor/).
VENDOR_MAP = {
    'https://unpkg.com/3d-force-graph@1.77/dist/3d-force-graph.min.js':
        '3d-force-graph@1.77/dist/3d-force-graph.min.js',
    'https://unpkg.com/globe.gl@2.32/dist/globe.gl.min.js':
        'globe.gl@2.32/dist/globe.gl.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/vis-network.min.css':
        'vis-network@9.1.2/dist/vis-network.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/vis-network.min.js':
        'vis-network@9.1.2/dist/vis-network.min.js',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/css/bootstrap.min.css':
        'bootstrap@5.0.0-beta3/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/js/bootstrap.bundle.min.js':
        'bootstrap@5.0.0-beta3/dist/js/bootstrap.bundle.min.js',
}

# External URLs we accept staying as dead links in the offline bundle
# (license/attribution links, optional decorative icons).
EXTERNAL_ALLOWLIST_PREFIXES = (
    'https://plotly.com',
    'https://carto.com',
    'https://stamen.com',
    'https://www.mapbox.com',
    'https://maplibre.org',
    'https://openstreetmap.org',
    'https://www.openstreetmap.org',
    'https://creativecommons.org',
    'https://unpkg.com/maki@2.1.0/icons/',  # folium map-marker icons (optional)
    'https://github.com/zloirock/core-js',  # core-js LICENSE reference inside pyvis bundle
)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', type=Path, default=DEFAULT_OUT,
                    help='Target directory (default: offline-site/ at repo root)')
    ap.add_argument('--skip-download', action='store_true',
                    help='Reuse existing vendor/ (skip network fetch)')
    ap.add_argument('--verify-only', action='store_true',
                    help='Scan <out> for external URLs, exit 0 if none (minus allowlist)')
    ap.add_argument('--self-test', action='store_true',
                    help='Run built-in assertion tests and exit')
    args = ap.parse_args()

    if args.self_test:
        self_test()
        print('self-test OK')
        return

    raise NotImplementedError('pipeline not yet implemented')


def self_test():
    pass


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Add `.gitignore` entry**

Append `offline-site/` to `.gitignore`. Verify:

```
grep -n '^offline-site' .gitignore
```

Expected: the line exists. If it's not there, add it with `echo 'offline-site/' >> .gitignore`.

- [ ] **Step 3: Smoke-test the CLI**

```
python3 -m analysis.web.build_offline --self-test
```
Expected: `self-test OK`.

```
python3 -m analysis.web.build_offline --help
```
Expected: usage text with `--out`, `--skip-download`, `--verify-only`, `--self-test`.

- [ ] **Step 4: Commit**

```bash
git add analysis/web/build_offline.py .gitignore
git commit -m "build_offline: CLI skeleton + gitignore offline-site/"
```

---

## Task 2: Implement `download_vendor()`

**Files:**
- Modify: `analysis/web/build_offline.py` — add `download_vendor()` + self-test case.

- [ ] **Step 1: Add a failing self-test case**

Append to `self_test()`:

```python
    # --- vendor_local_path helper ---
    assert vendor_local_path(
        'https://unpkg.com/globe.gl@2.32/dist/globe.gl.min.js'
    ) == 'globe.gl@2.32/dist/globe.gl.min.js'
    assert vendor_local_path(
        'https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/vis-network.min.css'
    ) == 'vis-network@9.1.2/dist/vis-network.min.css'
    try:
        vendor_local_path('https://example.com/foo.js')
    except KeyError:
        pass
    else:
        raise AssertionError('expected KeyError for unmapped URL')
```

- [ ] **Step 2: Run the self-test — expect failure**

```
python3 -m analysis.web.build_offline --self-test
```
Expected: `NameError: name 'vendor_local_path' is not defined`.

- [ ] **Step 3: Add `vendor_local_path()` and `download_vendor()`**

Insert above `main()`:

```python
def vendor_local_path(url: str) -> str:
    """Return the vendor-local path for a CDN URL (relative to vendor/)."""
    return VENDOR_MAP[url]


def download_vendor(vendor_dir: Path, skip: bool = False) -> None:
    """Download every URL in VENDOR_MAP into <vendor_dir>/<local_path>.

    Skips any file that already exists when ``skip`` is True.
    """
    vendor_dir.mkdir(parents=True, exist_ok=True)
    for url, rel in VENDOR_MAP.items():
        dst = vendor_dir / rel
        if skip and dst.exists() and dst.stat().st_size > 0:
            print(f'  reuse  {rel}')
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        print(f'  fetch  {url}')
        req = urllib.request.Request(url, headers={'User-Agent': 'iyp-offline-build'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            dst.write_bytes(resp.read())
```

- [ ] **Step 4: Run the self-test — expect pass**

```
python3 -m analysis.web.build_offline --self-test
```
Expected: `self-test OK`.

- [ ] **Step 5: Smoke-test `download_vendor()` against the network**

```
python3 -c "
from pathlib import Path
from analysis.web.build_offline import download_vendor
download_vendor(Path('/tmp/iyp-vendor-test'))
"
ls -la /tmp/iyp-vendor-test/*/dist/
```
Expected: six files under `/tmp/iyp-vendor-test/<lib>@<ver>/dist/`, all non-zero. Roughly:
```
3d-force-graph@1.77/dist/3d-force-graph.min.js    (~1.4 MB)
globe.gl@2.32/dist/globe.gl.min.js                 (~1.4 MB)
vis-network@9.1.2/dist/vis-network.min.css         (~50 KB)
vis-network@9.1.2/dist/vis-network.min.js          (~2 MB)
bootstrap@5.0.0-beta3/dist/css/bootstrap.min.css   (~160 KB)
bootstrap@5.0.0-beta3/dist/js/bootstrap.bundle.min.js  (~80 KB)
```

Clean up: `rm -rf /tmp/iyp-vendor-test`.

- [ ] **Step 6: Commit**

```bash
git add analysis/web/build_offline.py
git commit -m "build_offline: download_vendor + vendor_local_path"
```

---

## Task 3: Galaxy suppression via `IYP_EXCLUDE_GALAXY` env var

**Files:**
- Modify: `analysis/web/nav.py` — `GLOBE_VIEWS` or `_build_globe_track()` to filter Galaxy when env var set.

- [ ] **Step 1: Locate the Galaxy entry**

```
grep -n "galaxy\|as_galaxy" analysis/web/nav.py | head
```

The Galaxy view is defined in `GLOBE_VIEWS` (a list of 4 tuples, one per view) — look for the tuple whose first element is `'galaxy'`.

- [ ] **Step 2: Modify `_build_globe_track()` to filter Galaxy**

Find `_build_globe_track()` (approximately line 445). The current body begins:

```python
def _build_globe_track() -> Track:
    pages: list[Page] = []
    for slug, src_dir, src_file, title_zh, title_en, subtitle_zh, kpis in GLOBE_VIEWS:
        pages.append(Page(
```

Replace the `for` line + its iterable with an env-var-aware filter:

```python
def _build_globe_track() -> Track:
    pages: list[Page] = []
    exclude = set()
    if os.environ.get('IYP_EXCLUDE_GALAXY'):
        exclude.add('galaxy')
    views = [v for v in GLOBE_VIEWS if v[0] not in exclude]
    for slug, src_dir, src_file, title_zh, title_en, subtitle_zh, kpis in views:
        pages.append(Page(
```

Add `import os` to the top of `nav.py` if not already present — run:
```
grep -n "^import os" analysis/web/nav.py
```
If no line, add `import os` near the other top-level imports (around line 9-14).

- [ ] **Step 3: Verify the filter works**

```
python3 -c "import os; os.environ['IYP_EXCLUDE_GALAXY']='1'; from analysis.web import nav; m = nav.build_site_model(); globe = m['tracks']['globe']; print([p.slug for p in globe.all_pages()])"
```
Expected: `['strata', 'globe', 'force']` — Galaxy dropped.

```
python3 -c "from analysis.web import nav; m = nav.build_site_model(); globe = m['tracks']['globe']; print([p.slug for p in globe.all_pages()])"
```
Expected: `['strata', 'globe', 'force', 'galaxy']` — default behavior unchanged when env var absent.

- [ ] **Step 4: Commit**

```bash
git add analysis/web/nav.py
git commit -m "nav: honor IYP_EXCLUDE_GALAXY to filter Galaxy from globe track"
```

---

## Task 4: Implement `run_site_build()` + `copy_sources()`

**Files:**
- Modify: `analysis/web/build_offline.py` — add both functions.

- [ ] **Step 1: Add the functions above `main()`**

```python
def run_site_build() -> None:
    """Invoke analysis.web.build as a subprocess with Galaxy suppressed."""
    env = os.environ.copy()
    env['IYP_EXCLUDE_GALAXY'] = '1'
    result = subprocess.run(
        [sys.executable, '-m', 'analysis.web.build'],
        env=env, cwd=REPO_ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise RuntimeError(f'site build failed (exit {result.returncode})')
    print(result.stdout.strip().splitlines()[-1] if result.stdout else 'site built')


def copy_sources(out: Path) -> None:
    """Copy all SOURCE_TREES into <out>/<tree>/, preserving structure."""
    for rel in SOURCE_TREES:
        src = REPO_ROOT / rel
        dst = out / rel
        if dst.exists():
            shutil.rmtree(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst, symlinks=False)
        size_mb = sum(f.stat().st_size for f in dst.rglob('*') if f.is_file()) / (1024 * 1024)
        print(f'  copy   {rel} ({size_mb:.1f} MB)')
```

- [ ] **Step 2: Verify both functions import cleanly**

```
python3 -c "from analysis.web.build_offline import run_site_build, copy_sources; print('OK')"
```
Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add analysis/web/build_offline.py
git commit -m "build_offline: run_site_build + copy_sources"
```

---

## Task 5: Implement `rewrite_cdn_refs()`

**Files:**
- Modify: `analysis/web/build_offline.py` — add CDN-rewrite function + self-test case.

- [ ] **Step 1: Add a failing self-test case**

Append to `self_test()`:

```python
    # --- rewrite_cdn_refs core ---
    # Case 1: file in analysis/countries/html/ → vendor/ is 2 levels up
    html = '<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/js/bootstrap.bundle.min.js"></script>'
    out = rewrite_cdn_refs(html, depth_from_vendor=2)
    assert out == '<script src="../../vendor/bootstrap@5.0.0-beta3/dist/js/bootstrap.bundle.min.js"></script>', repr(out)

    # Case 2: file at root of offline-site/ (0 levels from vendor/) — unrealistic but handles the edge
    out = rewrite_cdn_refs(
        '<link href="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/vis-network.min.css">',
        depth_from_vendor=0)
    assert out == '<link href="vendor/vis-network@9.1.2/dist/vis-network.min.css">', repr(out)

    # Case 3: unmapped URL stays untouched
    out = rewrite_cdn_refs('<a href="https://plotly.com/">plotly</a>', depth_from_vendor=2)
    assert out == '<a href="https://plotly.com/">plotly</a>'
```

- [ ] **Step 2: Run the self-test — expect failure**

```
python3 -m analysis.web.build_offline --self-test
```
Expected: `NameError: name 'rewrite_cdn_refs' is not defined`.

- [ ] **Step 3: Implement `rewrite_cdn_refs()` and `rewrite_file()`**

Insert above `main()`:

```python
def rewrite_cdn_refs(html: str, depth_from_vendor: int) -> str:
    """Replace every CDN URL in VENDOR_MAP with its vendor-relative path.

    ``depth_from_vendor`` is the number of directory levels the HTML file
    sits above <out>/analysis/vendor/.  E.g. a file at
    <out>/analysis/countries/html/foo.html is 2 levels below
    <out>/analysis/, so depth_from_vendor=2 and the vendor prefix becomes
    ``../../vendor/``.
    """
    prefix = '../' * depth_from_vendor + 'vendor/'
    for url, local in VENDOR_MAP.items():
        html = html.replace(url, prefix + local)
    return html


def _depth_from_vendor(html_path: Path, out: Path) -> int:
    """How many directory levels does html_path sit below out/analysis/?"""
    rel = html_path.relative_to(out / 'analysis')
    # rel.parts[:-1] is the directory chain (excluding the filename);
    # vendor/ lives at the same level as rel.parts[0], so depth is:
    return len(rel.parts) - 1


def rewrite_file(html_path: Path, out: Path) -> int:
    """Rewrite CDN refs in one HTML file.  Returns number of substitutions."""
    original = html_path.read_text(encoding='utf-8')
    depth = _depth_from_vendor(html_path, out)
    new = rewrite_cdn_refs(original, depth_from_vendor=depth)
    if new != original:
        html_path.write_text(new, encoding='utf-8')
    # Count substitutions by counting how many VENDOR_MAP URLs no longer appear
    count = sum(1 for url in VENDOR_MAP if url in original and url not in new)
    return count
```

- [ ] **Step 4: Run the self-test — expect pass**

```
python3 -m analysis.web.build_offline --self-test
```
Expected: `self-test OK`.

- [ ] **Step 5: Commit**

```bash
git add analysis/web/build_offline.py
git commit -m "build_offline: rewrite_cdn_refs + per-file substitution"
```

---

## Task 6: Implement `verify_no_external_urls()`

**Files:**
- Modify: `analysis/web/build_offline.py` — add verify function + self-test case.

- [ ] **Step 1: Add a failing self-test case**

Append to `self_test()`:

```python
    # --- is_allowlisted ---
    assert is_allowlisted('https://plotly.com/python/')
    assert is_allowlisted('https://openstreetmap.org/copyright')
    assert is_allowlisted('https://unpkg.com/maki@2.1.0/icons/circle-15.svg')
    assert not is_allowlisted('https://unpkg.com/3d-force-graph@1.77/dist/3d-force-graph.min.js')
    assert not is_allowlisted('https://example.com/evil.js')
```

- [ ] **Step 2: Run the self-test — expect failure**

```
python3 -m analysis.web.build_offline --self-test
```
Expected: `NameError: name 'is_allowlisted' is not defined`.

- [ ] **Step 3: Implement verification**

Insert above `main()`:

```python
_EXTERNAL_URL_RE = re.compile(rb'https?://[^\s"\'<>()]+')


def is_allowlisted(url: str) -> bool:
    return any(url.startswith(prefix) for prefix in EXTERNAL_ALLOWLIST_PREFIXES)


def verify_no_external_urls(out: Path) -> list[tuple[Path, str]]:
    """Scan every HTML/JS/CSS under <out> for un-allowlisted external URLs.

    Returns a list of (file, url) findings.  Empty list = clean.
    """
    findings: list[tuple[Path, str]] = []
    for path in out.rglob('*'):
        if not path.is_file():
            continue
        if path.suffix not in {'.html', '.htm', '.css', '.js'}:
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        for m in _EXTERNAL_URL_RE.finditer(data):
            url = m.group(0).decode('utf-8', errors='replace').rstrip('.,;:')
            if is_allowlisted(url):
                continue
            findings.append((path, url))
    return findings
```

- [ ] **Step 4: Run the self-test — expect pass**

```
python3 -m analysis.web.build_offline --self-test
```
Expected: `self-test OK`.

- [ ] **Step 5: Commit**

```bash
git add analysis/web/build_offline.py
git commit -m "build_offline: verify_no_external_urls + allowlist"
```

---

## Task 7: Wire up `main()` — full pipeline + `--verify-only`

**Files:**
- Modify: `analysis/web/build_offline.py` — replace `NotImplementedError` with real pipeline.

- [ ] **Step 1: Replace the `raise NotImplementedError` in `main()`**

Replace the `raise NotImplementedError(...)` line with:

```python
    out: Path = args.out.resolve()
    vendor_dir = out / 'analysis' / 'vendor'

    if args.verify_only:
        if not out.exists():
            sys.stderr.write(f'{out} does not exist\n')
            return 1
        findings = verify_no_external_urls(out)
        if findings:
            print(f'{len(findings)} un-allowlisted external URL(s):')
            for path, url in findings[:20]:
                print(f'  {path.relative_to(out)}: {url}')
            if len(findings) > 20:
                print(f'  … and {len(findings) - 20} more')
            return 1
        print('verify-only: clean (no external URLs outside allowlist).')
        return 0

    print(f'Building offline bundle at {out}')
    out.mkdir(parents=True, exist_ok=True)

    print('→ fetching vendor libraries …')
    download_vendor(vendor_dir, skip=args.skip_download)

    print('→ regenerating site with Galaxy excluded …')
    run_site_build()

    print('→ copying source trees …')
    copy_sources(out)

    print('→ rewriting CDN refs …')
    total_rewrites = 0
    rewritten_files = 0
    for html in (out / 'analysis').rglob('*.html'):
        n = rewrite_file(html, out)
        if n > 0:
            total_rewrites += n
            rewritten_files += 1
    print(f'  rewrote {total_rewrites} refs across {rewritten_files} files')

    # Also rewrite the one CSS (countries pyvis occasionally inlines CDN URL in CSS)
    for css in (out / 'analysis').rglob('*.css'):
        # Same substitution, but depth computed like HTML
        rel = css.relative_to(out / 'analysis')
        depth = len(rel.parts) - 1
        original = css.read_text(encoding='utf-8', errors='ignore')
        new = rewrite_cdn_refs(original, depth_from_vendor=depth)
        if new != original:
            css.write_text(new, encoding='utf-8')

    print('→ verifying no un-allowlisted external URLs …')
    findings = verify_no_external_urls(out)
    if findings:
        print(f'!! {len(findings)} un-allowlisted external URL(s) — fix before shipping:',
              file=sys.stderr)
        for path, url in findings[:20]:
            print(f'   {path.relative_to(out)}: {url}', file=sys.stderr)
        return 1

    readme = out / 'README.txt'
    readme.write_text(
        'IYP Offline Analysis Atlas\n'
        '==========================\n\n'
        '打开 · Open:  analysis/web/site/index.html  (double-click)\n\n'
        '所有交互图表（中国 / 九国 / 复杂网络 / Globe）均已本地化；\n'
        '无需联网、无需本地 HTTP 服务器。Galaxy 127K-AS 视图因浏览器安全限制\n'
        '（file:// 无法 fetch 二进制数据）未包含在离线版本中；若需要，请在\n'
        '在线版本 analysis/web/site/ 下浏览。\n\n'
        'All interactive charts (China / Countries / Complex Network / Globe)\n'
        'are fully localised; no internet or local HTTP server required.\n'
        'The Galaxy 127K-AS view is excluded because Chrome blocks the\n'
        'fetch() it needs over file://; use the online version for that.\n',
        encoding='utf-8')

    print(f'\nDone. Open: {out / "analysis/web/site/index.html"}')
    return 0
```

Update the `main()` function's top to `def main() -> int:` and make sure the `return` statements match. Change the `--self-test` branch to `return 0` as well.

The full updated `main()` body should look like:

```python
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', type=Path, default=DEFAULT_OUT, …)
    ap.add_argument('--skip-download', action='store_true', …)
    ap.add_argument('--verify-only', action='store_true', …)
    ap.add_argument('--self-test', action='store_true', …)
    args = ap.parse_args()

    if args.self_test:
        self_test()
        print('self-test OK')
        return 0

    # … the verify-only + full pipeline code above …
```

And the `__main__` block:

```python
if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 2: Smoke-test `--verify-only` on a missing directory**

```
python3 -m analysis.web.build_offline --verify-only --out /tmp/does-not-exist
```
Expected: prints `/tmp/does-not-exist does not exist`, exits 1.

- [ ] **Step 3: Commit**

```bash
git add analysis/web/build_offline.py
git commit -m "build_offline: wire main() pipeline + README.txt emission"
```

---

## Task 8: End-to-end run + manual smoke test

**Files:**
- Modified (by run): `offline-site/**/*` (gitignored output — do NOT commit these).

- [ ] **Step 1: Full build**

```
python3 -m analysis.web.build_offline 2>&1 | tail -20
```

Expected output tail:
```
Building offline bundle at /Volumes/.../offline-site
→ fetching vendor libraries …
  fetch  https://unpkg.com/3d-force-graph@1.77/dist/3d-force-graph.min.js
  fetch  https://unpkg.com/globe.gl@2.32/dist/globe.gl.min.js
  fetch  https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/vis-network.min.css
  fetch  https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/vis-network.min.js
  fetch  https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/css/bootstrap.min.css
  fetch  https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/js/bootstrap.bundle.min.js
→ regenerating site with Galaxy excluded …
wrote 95 pages in 0.Xs
→ copying source trees …
  copy   analysis/web/site (X.X MB)
  copy   analysis/china/html (26.X MB)
  copy   analysis/countries/html (213.X MB)
  copy   analysis/complex_network_images (13.X MB)
  copy   analysis/as_globe/html (4.X MB)
→ rewriting CDN refs …
  rewrote N refs across M files
→ verifying no un-allowlisted external URLs …
Done. Open: /Volumes/.../offline-site/analysis/web/site/index.html
```

Exit code 0.

- [ ] **Step 2: Verify Galaxy is absent from the offline site**

```
ls offline-site/analysis/web/site/globe/
```
Expected: 3 directories (`strata/`, `globe/`, `force/`) + `index.html`. No `galaxy/`.

```
test ! -e offline-site/analysis/as_galaxy && echo "as_galaxy excluded" || echo "STILL PRESENT"
```
Expected: `as_galaxy excluded`.

- [ ] **Step 3: Verify vendor files exist**

```
find offline-site/analysis/vendor -type f
```
Expected: 6 files (3d-force-graph, globe.gl, vis-network.min.css, vis-network.min.js, bootstrap.min.css, bootstrap.bundle.min.js).

- [ ] **Step 4: Spot-check CDN rewrites**

```
grep -l "unpkg.com\|jsdelivr.net\|cdnjs.cloudflare" offline-site/analysis/countries/html/*.html offline-site/analysis/as_globe/html/*.html | head
```
Expected: only the files containing `unpkg.com/maki@2.1.0/icons/` (allowlisted) OR zero files. Any hit on `3d-force-graph`, `globe.gl`, `bootstrap`, or `vis-network` is a bug.

Confirm a specific rewrite:
```
grep -o 'vendor/globe.gl@2.32[^"]*' offline-site/analysis/as_globe/html/as_globe.html
```
Expected: `vendor/globe.gl@2.32/dist/globe.gl.min.js` (with appropriate `../` prefix).

- [ ] **Step 5: Manual browser smoke test**

Open `offline-site/analysis/web/site/index.html` by double-clicking (or `open offline-site/analysis/web/site/index.html` on macOS).

Manual checks:
- Home page loads with "Analysis Atlas" header, 4 track cards (China / Countries / Network / Globe).
- Click into China → step05 peering → Plotly chart renders.
- Click into Countries → CN profile → dashboards render (vis-network / bootstrap loaded from vendor).
- Click into Network → step05 index (panel grid from our earlier pilot) → click a panel → PNG displays.
- Click into Globe → 3 views present (NO Galaxy); open any → WebGL renders.
- Open browser DevTools → Network tab → confirm zero requests to `unpkg.com`, `cdnjs.cloudflare.com`, or `cdn.jsdelivr.net`.

- [ ] **Step 6: Verify-only idempotency check**

```
python3 -m analysis.web.build_offline --verify-only
```
Expected: `verify-only: clean (no external URLs outside allowlist).` — exit 0.

- [ ] **Step 7: Re-run with `--skip-download` is fast**

```
time python3 -m analysis.web.build_offline --skip-download 2>&1 | tail -3
```
Expected: completes in < 30s (no network fetch), still exit 0.

- [ ] **Step 8: No commit needed** — `offline-site/` is gitignored. Only source changes in prior tasks are committed.

---

## Self-Review

1. **Spec coverage:**
   - Clean target dir → Task 4 (`copy_sources` removes + recopies).
   - Download vendor libraries → Task 2.
   - Run site build with Galaxy suppressed → Tasks 3 + 4 (env var + subprocess).
   - Copy source trees → Task 4 (`copy_sources`).
   - Rewrite CDN URLs → Task 5.
   - Verify no unexpected external URLs → Task 6.
   - Emit README.txt → Task 7.
   - CLI flags `--out`, `--skip-download`, `--verify-only` → Task 1 + Task 7.
   - Allowlist for license/attribution URLs → Task 6.
   - `maki@2.1.0/icons/` allowlisted → Task 1 `EXTERNAL_ALLOWLIST_PREFIXES`.
   - Galaxy drop → Task 3.
   - No iframe-resize JS patch needed (existing try/catch handles it) → noted in plan header; no task.
   - No CSS patch needed (existing `min-height: 720px`) → noted in plan header; no task.
   - Directory mirror layout → Task 4 (`SOURCE_TREES` preserves structure).
   - Re-run durability — Task 4 `copy_sources` overwrites idempotently; Task 2 `skip` flag for vendor. ✓

2. **Placeholder scan:** No TBD / TODO. Every code block is complete. Step outputs are concrete.

3. **Type consistency:** `VENDOR_MAP: dict[str, str]`, `SOURCE_TREES: list[str]`, `EXTERNAL_ALLOWLIST_PREFIXES: tuple[str, ...]` used consistently. `Path` types passed through `vendor_dir`, `out`, `html_path`. `rewrite_cdn_refs(html, depth_from_vendor)` signature matches consumer in `rewrite_file()`. `verify_no_external_urls(out) -> list[tuple[Path, str]]` matches consumer in `main()`.

4. **Ordering:** Task 1 scaffolds CLI. Task 2 adds download. Task 3 is a sibling edit to nav.py that Task 4 consumes. Tasks 4+5+6 are pure Python additions that don't touch each other. Task 7 wires main(). Task 8 runs the whole thing.
