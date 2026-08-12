const grid = document.querySelector('[data-gallery-grid]');
const filters = document.querySelector('[data-gallery-filters]');
const search = document.querySelector('[data-gallery-search]');
const status = document.querySelector('#gallery-status');
const dialog = document.querySelector('[data-case-dialog]');
const detail = document.querySelector('[data-case-detail]');

let cases = [];
let activeWorld = 'all';

const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, (character) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
}[character]));

const card = (item) => `
  <article class="gallery-card" data-world="${escapeHtml(item.world)}">
    <button class="gallery-open" type="button" data-open-case="${escapeHtml(item.id)}" aria-label="Open ${escapeHtml(item.title)} case">
      <span class="gallery-number">${String(item.number).padStart(3, '0')}</span>
      <span class="gallery-art"><img src="${escapeHtml(item.assets.svg)}" width="112" height="112" loading="lazy" alt="${escapeHtml(item.noun)}"></span>
      <span class="gallery-native"><img src="${escapeHtml(item.assets.native)}" width="16" height="16" alt="">actual 16×16</span>
      <span class="gallery-coordinate">${escapeHtml(item.world)} · ${escapeHtml(item.technique)}</span>
      <strong>${escapeHtml(item.title)}</strong>
      <span class="gallery-job">${escapeHtml(item.user_job)}</span>
      <span class="gallery-device">Signature · ${escapeHtml(item.signature)}</span>
    </button>
  </article>`;

const render = () => {
  const query = search.value.trim().toLocaleLowerCase();
  const visible = cases.filter((item) => {
    const matchesWorld = activeWorld === 'all' || item.world === activeWorld;
    const haystack = `${item.title} ${item.world} ${item.technique} ${item.noun} ${item.user_job} ${item.signature}`.toLocaleLowerCase();
    return matchesWorld && (!query || haystack.includes(query));
  });
  grid.innerHTML = visible.map(card).join('');
  grid.setAttribute('aria-busy', 'false');
  status.textContent = `Showing ${visible.length} of ${cases.length} proofed cases`;
};

const renderFilters = () => {
  const worlds = [...new Set(cases.map((item) => item.world))].sort();
  filters.innerHTML = ['all', ...worlds].map((world) => `
    <button type="button" data-world-filter="${escapeHtml(world)}" aria-pressed="${world === 'all'}">
      ${world === 'all' ? `All ${cases.length}` : escapeHtml(world)}
    </button>`).join('');
};

const openCase = (item) => {
  detail.innerHTML = `
    <article class="case-detail">
      <div class="case-detail-art">
        <p>Editable SVG · displayed as vector</p>
        <img class="case-vector" src="${escapeHtml(item.assets.svg)}" width="256" height="256" alt="${escapeHtml(item.noun)}">
        <div class="case-pixel-proof"><span>Actual 16×16</span><img src="${escapeHtml(item.assets.native)}" width="16" height="16" alt="Exact native render of ${escapeHtml(item.title)}"></div>
        <figure><img src="${escapeHtml(item.assets.silhouette)}" width="128" height="128" alt="${escapeHtml(item.title)} silhouette"><figcaption>128px silhouette · shown at 1:1</figcaption></figure>
      </div>
      <div class="case-detail-copy">
        <p class="section-kicker">Case ${String(item.number).padStart(3, '0')} · ${escapeHtml(item.world)} / ${escapeHtml(item.technique)}</p>
        <h2 id="case-dialog-title">${escapeHtml(item.title)}</h2>
        <p class="case-detail-job">${escapeHtml(item.user_job)}</p>
        <dl><div><dt>Noun</dt><dd>${escapeHtml(item.noun)}</dd></div><div><dt>Essence</dt><dd>${escapeHtml(item.essence)}</dd></div><div><dt>Avoided</dt><dd>${escapeHtml(item.cliche)}</dd></div><div><dt>Signature</dt><dd>${escapeHtml(item.signature)}</dd></div></dl>
        <div class="case-links"><a href="${escapeHtml(item.assets.svg)}">SVG source</a><a href="${escapeHtml(item.assets.proof)}">128px proof</a><a href="${escapeHtml(item.assets.receipt)}">Receipt</a><a href="${escapeHtml(item.assets.case)}">Case record</a></div>
      </div>
    </article>`;
  dialog.showModal();
};

filters.addEventListener('click', (event) => {
  const button = event.target.closest('[data-world-filter]');
  if (!button) return;
  activeWorld = button.dataset.worldFilter;
  filters.querySelectorAll('button').forEach((item) => item.setAttribute('aria-pressed', String(item === button)));
  render();
});

search.addEventListener('input', render);

grid.addEventListener('click', (event) => {
  const button = event.target.closest('[data-open-case]');
  if (!button) return;
  const item = cases.find((candidate) => candidate.id === button.dataset.openCase);
  if (item) openCase(item);
});

dialog.addEventListener('click', (event) => {
  if (event.target === dialog) dialog.close();
});

fetch('/assets/gallery/catalog.json')
  .then((response) => {
    if (!response.ok) throw new Error(`catalog returned ${response.status}`);
    return response.json();
  })
  .then((catalog) => {
    if (catalog.case_count !== 100 || catalog.cases.length !== 100) throw new Error('catalog is not the 100-case edition');
    cases = catalog.cases;
    renderFilters();
    render();
  })
  .catch((error) => {
    grid.setAttribute('aria-busy', 'false');
    status.textContent = 'Gallery catalog unavailable.';
    grid.innerHTML = `<p class="gallery-error">${escapeHtml(error.message)}</p>`;
  });
