const list = document.querySelector('[data-signals-list]');
const status = document.querySelector('#signals-status');

const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, (character) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
}[character]));

const card = (item) => `
  <article class="signal-card" id="${escapeHtml(item.id)}">
    <div class="signal-art">
      <img src="${escapeHtml(item.assets.svg)}" width="360" height="360" loading="lazy" alt="${escapeHtml(item.noun)}">
      <span class="signal-native"><img src="${escapeHtml(item.assets.native)}" width="16" height="16" loading="lazy" alt="">Actual 16×16</span>
    </div>
    <div class="signal-copy">
      <span class="signal-index">Study ${String(item.number).padStart(2, '0')} · <span class="signal-style">${escapeHtml(item.style)}</span></span>
      <h3>${escapeHtml(item.title)}</h3>
      <p class="signal-job">${escapeHtml(item.user_job)}</p>
      <dl>
        <div><dt>Original noun</dt><dd>${escapeHtml(item.noun)}</dd></div>
        <div><dt>Signature</dt><dd>${escapeHtml(item.signature_device)}</dd></div>
        <div><dt>Avoided</dt><dd>${escapeHtml(item.cliche_avoided)}</dd></div>
      </dl>
      <div class="signal-links"><a href="${escapeHtml(item.assets.svg)}">SVG source</a><a href="${escapeHtml(item.assets.proof)}">128px proof</a><a href="${escapeHtml(item.assets.silhouette)}">Silhouette</a><a href="${escapeHtml(item.assets.receipt)}">Receipt</a><a href="${escapeHtml(item.assets.case)}">Case record</a></div>
    </div>
  </article>`;

fetch('/assets/gallery/social-signals/catalog.json')
  .then((response) => {
    if (!response.ok) throw new Error(`catalog returned ${response.status}`);
    return response.json();
  })
  .then((catalog) => {
    if (catalog.admitted_count !== 20 || catalog.cases.length !== 20) throw new Error('catalog is not the 20-study edition');
    list.innerHTML = catalog.cases.map(card).join('');
    list.setAttribute('aria-busy', 'false');
    status.textContent = '20 reviewed practice specimens · 20 techniques · zero official assets';
  })
  .catch((error) => {
    list.setAttribute('aria-busy', 'false');
    status.textContent = 'Social Signals catalog unavailable.';
    list.innerHTML = `<p class="signals-error">${escapeHtml(error.message)}</p>`;
  });
