// analysis/web site runtime: keyboard nav, TOC dialog, iframe autosize, lightbox, hero counters.
(function () {
  'use strict';

  // ---- keyboard navigation ----
  document.addEventListener('keydown', function (e) {
    // Ignore key presses inside form fields
    const tag = (e.target && e.target.tagName) || '';
    if (tag === 'INPUT' || tag === 'TEXTAREA' || e.target.isContentEditable) return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;

    if (e.key === 'ArrowLeft') {
      const prev = document.querySelector('[data-nav="prev"]');
      if (prev) { window.location.href = prev.getAttribute('href'); }
    } else if (e.key === 'ArrowRight') {
      const next = document.querySelector('[data-nav="next"]');
      if (next) { window.location.href = next.getAttribute('href'); }
    } else if (e.key === 'g' || e.key === 'G') {
      e.preventDefault();
      openTOC();
    } else if (e.key === 'd' || e.key === 'D') {
      const dlg = document.getElementById('cap-dialog');
      if (dlg && typeof dlg.showModal === 'function' && !dlg.open) {
        e.preventDefault();
        dlg.showModal();
      }
    } else if (e.key === 'Escape') {
      closeAnyOpenDialog();
    }
  });

  function openTOC() {
    const dlg = document.getElementById('toc-dialog');
    if (!dlg) return;
    if (typeof dlg.showModal === 'function' && !dlg.open) {
      dlg.showModal();
    }
  }

  function closeAnyOpenDialog() {
    document.querySelectorAll('dialog[open]').forEach(function (d) { d.close(); });
  }

  // ---- TOC triggers + 图解 triggers ----
  document.addEventListener('click', function (e) {
    const trigger = e.target.closest('[data-toc-trigger]');
    if (trigger) { e.preventDefault(); openTOC(); return; }
    const closer = e.target.closest('[data-toc-close]');
    if (closer) { e.preventDefault(); closeAnyOpenDialog(); return; }
    const cap = e.target.closest('[data-cap-trigger]');
    if (cap) {
      e.preventDefault();
      const dlg = document.getElementById('cap-dialog');
      if (dlg && typeof dlg.showModal === 'function' && !dlg.open) dlg.showModal();
      return;
    }
    const capClose = e.target.closest('[data-cap-close]');
    if (capClose) { e.preventDefault(); closeAnyOpenDialog(); return; }
  });

  // Close 图解 dialog by clicking backdrop
  document.querySelectorAll('dialog.cap-dialog').forEach(function (dlg) {
    dlg.addEventListener('click', function (e) {
      const rect = dlg.getBoundingClientRect();
      const inside = e.clientX >= rect.left && e.clientX <= rect.right
                  && e.clientY >= rect.top  && e.clientY <= rect.bottom;
      if (!inside) dlg.close();
    });
  });

  // ---- phase filter (china hub) ----
  document.querySelectorAll('[data-filter-chip]').forEach(function (chip) {
    chip.addEventListener('click', function () {
      const group = chip.getAttribute('data-filter-group') || 'default';
      const val = chip.getAttribute('data-filter-chip');
      document.querySelectorAll('[data-filter-chip][data-filter-group="' + group + '"]').forEach(function (c) {
        c.classList.toggle('is-active', c === chip);
      });
      document.querySelectorAll('[data-filter-target="' + group + '"]').forEach(function (node) {
        const phases = (node.getAttribute('data-filter-phase') || '').split(/\s+/);
        const show = (val === 'all') || phases.indexOf(val) !== -1;
        node.style.display = show ? '' : 'none';
      });
    });
  });

  // ---- iframe auto-height (same-origin only) ----
  function autosize(frame) {
    try {
      const doc = frame.contentDocument || (frame.contentWindow && frame.contentWindow.document);
      if (!doc || !doc.body) return;
      const h = Math.max(doc.documentElement.scrollHeight, doc.body.scrollHeight);
      if (h > 280) {
        frame.style.height = (h + 16) + 'px';
      }
    } catch (err) {
      /* cross-origin: skip */
    }
  }
  document.querySelectorAll('iframe.chart-frame').forEach(function (frame) {
    frame.addEventListener('load', function () { autosize(frame); });
    // Re-measure after resize in case the embedded Plotly chart reflows
    let t;
    window.addEventListener('resize', function () {
      clearTimeout(t);
      t = setTimeout(function () { autosize(frame); }, 150);
    });
  });

  // ---- PNG lightbox ----
  document.querySelectorAll('[data-lightbox]').forEach(function (img) {
    img.addEventListener('click', function () {
      const dlg = document.getElementById('lightbox-dialog');
      const target = dlg ? dlg.querySelector('img') : null;
      if (!dlg || !target) return;
      target.src = img.getAttribute('src');
      target.alt = img.getAttribute('alt') || '';
      if (typeof dlg.showModal === 'function' && !dlg.open) dlg.showModal();
    });
  });
  const lightbox = document.getElementById('lightbox-dialog');
  if (lightbox) {
    lightbox.addEventListener('click', function (e) {
      if (e.target === lightbox || e.target.matches('[data-close]')) lightbox.close();
    });
  }

  // ---- hero counter animation ----
  function runCounters() {
    document.querySelectorAll('[data-counter]').forEach(function (el) {
      const target = parseFloat(el.getAttribute('data-target') || '0');
      const decimals = parseInt(el.getAttribute('data-decimals') || '0', 10);
      const suffix = el.getAttribute('data-suffix') || '';
      const duration = 1400;
      const start = performance.now();
      function tick(t) {
        const k = Math.min(1, (t - start) / duration);
        const eased = 1 - Math.pow(1 - k, 3);
        const v = target * eased;
        el.textContent = v.toFixed(decimals) + suffix;
        if (k < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', runCounters);
  } else {
    runCounters();
  }
})();
