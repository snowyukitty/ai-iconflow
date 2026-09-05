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

const cards = [...grid.querySelectorAll('[data-case-id]')];
const empty = document.querySelector('[data-gallery-empty]');
const views = document.querySelector('[data-gallery-views]');

const render = () => {
  const query = search.value.trim().toLocaleLowerCase();
  let count = 0;
  cards.forEach((element) => {
    const matchesWorld = activeWorld === 'all' || element.dataset.world === activeWorld;
    const haystack = `${element.textContent} ${element.querySelector('.gallery-art img').alt}`.toLocaleLowerCase();
    const matchesQuery = !query || haystack.includes(query);
    element.hidden = !(matchesWorld && matchesQuery);
    if (!element.hidden) count += 1;
  });
  empty.hidden = count !== 0;
  status.textContent = `Showing ${count} of ${cases.length} proofed cases`;
};

views.addEventListener('click', (event) => {
  const button = event.target.closest('[data-view]');
  if (!button) return;
  const mode = button.dataset.view;
  grid.dataset.view = mode;
  cards.forEach((element) => {
    const image = element.querySelector('.gallery-art img');
    image.src = image.dataset[mode];
    const size = mode === 'native' ? 16 : mode === 'silhouette' ? 128 : 112;
    image.width = size;
    image.height = size;
  });
  views.querySelectorAll('button').forEach((item) => item.setAttribute('aria-pressed', String(item === button)));
});

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
  if (item && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) {
    event.preventDefault();
    openCase(item);
  }
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
    document.querySelector('[data-gallery-controls]').hidden = false;
    views.hidden = false;
    renderFilters();
    render();
  })
  .catch((error) => {
    grid.setAttribute('aria-busy', 'false');
    status.textContent = 'Showing 100 cases. Interactive previews are unavailable; case records remain readable.';
    console.warn('Gallery enhancement unavailable:', error.message);
  });
