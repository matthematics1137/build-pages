// Injects the shared sidebar and renders Prev/Next using the generated manifest.
(function(){
  function getRoot() {
    const script = document.currentScript || document.querySelector('script[src*="site-nav.js"]');
    const abs = new URL(script ? script.getAttribute('src') : 'assets/js/site-nav.js', document.baseURI);
    return abs.href.replace(/assets\/js\/site-nav\.js(?:\?.*)?$/, '');
  }

  async function injectSidebar(){
    const container = document.getElementById('sidebar');
    if (!container) return;
    const root = getRoot();
    try {
      const res = await fetch(root + 'assets/partials/sidebar.html?v=20250930');
      const html = await res.text();
      container.innerHTML = html;
      const basePath = new URL(root).pathname; // e.g., /mathematical-economics/
      container.querySelectorAll('a[href^="/"]').forEach(a => {
        const href = a.getAttribute('href');
        if (href.startsWith(basePath)) return; // already rooted under repo base
        a.setAttribute('href', root + href.replace(/^\//,''));
      });
      const links = container.querySelectorAll('a[data-match]');
      links.forEach(a => {
        const pat = a.getAttribute('data-match');
        const currentPath = decodeURIComponent(location.pathname);
        if (currentPath.endsWith(pat) || currentPath.includes(pat)) {
          a.classList.add('active');
        }
      });
    } catch (e) {}
  }

  async function loadManifest(){
    const root = getRoot();
    try {
      const res = await fetch(root + 'assets/site.json?v=20250930');
      return await res.json();
    } catch (e) { return []; }
  }

  async function renderPrevNext(){
    const el = document.getElementById('section-nav');
    if (!el) return;
    const root = getRoot();
    const path = decodeURIComponent(location.pathname);
    const manifest = await loadManifest();
    const flat = [];
    for (const sect of manifest) {
      for (const p of sect.pages) {
        flat.push(new URL(p.path.replace(/^\//,''), root).pathname);
      }
    }
    const idx = flat.indexOf(path);
    if (idx === -1) return;
    const prev = flat[idx-1];
    const next = flat[idx+1];
    const makeBtn = (href, label, disabled) => disabled ?
      `<span class="button" style="opacity:.5;pointer-events:none">${label}</span>` :
      `<a class="button" href="${href}">${label}</a>`;
    el.innerHTML = `
      <div class="buttons">
        ${makeBtn(prev, '← Previous', !prev)}
        ${makeBtn(next, 'Next →', !next)}
      </div>
    `;
  }

  document.addEventListener('DOMContentLoaded', function(){
    injectSidebar();
    renderPrevNext();
    // Toggle button
    const btn = document.getElementById('navToggle');
    const backdrop = document.getElementById('backdrop');
    function toggle(open){
      const willOpen = open ?? !document.body.classList.contains('nav-open');
      document.body.classList.toggle('nav-open', willOpen);
      if (btn) btn.setAttribute('aria-expanded', String(willOpen));
      try { localStorage.setItem('navOpen', willOpen ? '1' : '0'); } catch(e) {}
    }
    // Restore previous sidebar state so it doesn't collapse on navigation
    try {
      const saved = localStorage.getItem('navOpen');
      const shouldOpen = saved === '1';
      document.body.classList.toggle('nav-open', shouldOpen);
      if (btn) btn.setAttribute('aria-expanded', String(shouldOpen));
    } catch(e) {}
    if (btn) btn.addEventListener('click', () => toggle());
    if (backdrop) backdrop.addEventListener('click', () => toggle(false));
    document.addEventListener('keydown', (e)=>{ if (e.key === 'Escape') toggle(false); });

    // Theme toggle
    const tbtn = document.getElementById('themeToggle');
    const rootEl = document.documentElement;
    const saved = localStorage.getItem('theme');
    if (saved === 'light' || saved === 'dark') rootEl.setAttribute('data-theme', saved);
    function updateLabel(){
      if (!tbtn) return;
      const mode = rootEl.getAttribute('data-theme') || 'auto';
      tbtn.textContent = mode === 'dark' ? '☾' : (mode === 'light' ? '☀' : '◎');
      tbtn.title = 'Toggle light/dark (current: ' + mode + ')';
    }
    updateLabel();
    if (tbtn) tbtn.addEventListener('click', () => {
      const current = rootEl.getAttribute('data-theme');
      const next = current === 'dark' ? 'light' : (current === 'light' ? null : 'dark');
      if (next) { rootEl.setAttribute('data-theme', next); localStorage.setItem('theme', next); }
      else { rootEl.removeAttribute('data-theme'); localStorage.removeItem('theme'); }
      updateLabel();
    });

    // Font size slider (global)
    const fs = document.getElementById('fontSize');
    const rootEl2 = document.documentElement;
    const savedFs = parseInt(localStorage.getItem('fontSizePct') || '', 10);
    const initialFs = Number.isFinite(savedFs) ? savedFs : 140;
    rootEl2.style.fontSize = initialFs + '%';
    if (fs) {
      fs.value = String(initialFs);
      fs.addEventListener('input', () => {
        const v = Math.max(90, Math.min(220, parseInt(fs.value, 10) || initialFs));
        rootEl2.style.fontSize = v + '%';
        localStorage.setItem('fontSizePct', String(v));
      });
    }
  });
})();
