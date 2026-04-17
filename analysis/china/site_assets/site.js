/* analysis/china · site.js
 * caption dialog · theme · keyboard nav · search · TOC · copy link
 */
(() => {
  'use strict';

  /* -------- theme -------- */
  const THEME_KEY = 'iyp-cn-theme';
  const root = document.documentElement;
  const savedTheme = localStorage.getItem(THEME_KEY);
  if (savedTheme) root.setAttribute('data-theme', savedTheme);

  const themeBtn = document.querySelector('[data-action="toggle-theme"]');
  if (themeBtn) {
    themeBtn.addEventListener('click', () => {
      const cur = root.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
      const next = cur === 'light' ? 'dark' : 'light';
      if (next === 'dark') root.removeAttribute('data-theme');
      else root.setAttribute('data-theme', next);
      localStorage.setItem(THEME_KEY, next);
    });
  }

  /* -------- caption dialog -------- */
  document.querySelectorAll('.cap-btn[data-cap]').forEach(btn => {
    btn.addEventListener('click', () => {
      const dlg = document.getElementById(btn.dataset.cap);
      if (!dlg) return;
      if (typeof dlg.showModal === 'function') dlg.showModal();
      else dlg.setAttribute('open', '');
    });
  });

  document.querySelectorAll('dialog.cap-dialog').forEach(dlg => {
    // Close button
    dlg.querySelector('.cap-close')?.addEventListener('click', () => dlg.close());
    // Click on backdrop closes dialog
    dlg.addEventListener('click', (e) => {
      if (e.target === dlg) dlg.close();
    });
  });

  /* -------- keyboard nav (← / →) -------- */
  document.addEventListener('keydown', (e) => {
    if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) return;
    if (document.querySelector('dialog[open]')) return;
    if (e.key === 'ArrowLeft') {
      const prev = document.querySelector('.step-foot a.prev[href]');
      if (prev && !prev.classList.contains('disabled')) prev.click();
    } else if (e.key === 'ArrowRight') {
      const next = document.querySelector('.step-foot a.next[href]');
      if (next && !next.classList.contains('disabled')) next.click();
    } else if (e.key === '/') {
      const search = document.querySelector('.search-box input');
      if (search) { e.preventDefault(); search.focus(); }
    }
  });

  /* -------- copy link -------- */
  document.querySelectorAll('.copy-btn[data-target]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const anchor = btn.dataset.target;
      const url = `${location.origin}${location.pathname}${anchor ? '#' + anchor : ''}`;
      try {
        await navigator.clipboard.writeText(url);
        const orig = btn.innerHTML;
        btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
        btn.style.color = 'var(--accent-2)';
        setTimeout(() => { btn.innerHTML = orig; btn.style.color = ''; }, 1400);
      } catch (err) {
        console.warn('clipboard error', err);
      }
    });
  });

  /* -------- search / filter on index -------- */
  const searchInput = document.querySelector('.hub .search-box input');
  const stepCards = document.querySelectorAll('.hub .step-card');
  const filterChips = document.querySelectorAll('.hub .filter-chip');
  const phases = document.querySelectorAll('.hub .phase');
  let activeFilter = 'all';
  let searchQ = '';

  function applyFilter() {
    const q = searchQ.trim().toLowerCase();
    stepCards.forEach(card => {
      const text = (card.textContent || '').toLowerCase();
      const phase = card.dataset.phase || '';
      const matchesPhase = activeFilter === 'all' || phase === activeFilter;
      const matchesQ = !q || text.includes(q);
      card.style.display = (matchesPhase && matchesQ) ? '' : 'none';
    });
    // hide phases with no visible cards
    phases.forEach(ph => {
      const vis = [...ph.querySelectorAll('.step-card')]
        .some(c => c.style.display !== 'none');
      ph.style.display = vis ? '' : 'none';
    });
  }

  if (searchInput) {
    searchInput.addEventListener('input', (e) => { searchQ = e.target.value; applyFilter(); });
  }
  filterChips.forEach(chip => {
    chip.addEventListener('click', () => {
      filterChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      activeFilter = chip.dataset.filter || 'all';
      applyFilter();
    });
  });

  /* -------- scroll reveal (for long pages) -------- */
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach(en => {
        if (en.isIntersecting) {
          en.target.style.animationPlayState = 'running';
          io.unobserve(en.target);
        }
      });
    }, { threshold: 0.08 });
    document.querySelectorAll('.chart-card, .phase').forEach(el => {
      el.style.animationPlayState = 'paused';
      io.observe(el);
    });
  }

  /* -------- back-to-top -------- */
  document.querySelectorAll('[data-action="top"]').forEach(btn => {
    btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
  });

})();
