const controls = document.querySelector('[data-matrix-controls]');
const emojiSelect = document.querySelector('[data-emoji-select]');
const styleSelect = document.querySelector('[data-style-select]');
const emojiAxis = document.querySelector('[data-emoji-axis]');
const styleAxis = document.querySelector('[data-style-axis]');
const detail = document.querySelector('[data-matrix-detail]');
const status = document.querySelector('#matrix-status');

// Initial representative cell when the URL carries no #cell-id hash; shared with the complete matrix page.
const REPRESENTATIVE_CELL = 'u2764-fe0f--mascot';

let catalog;
let selectedEmoji;
let selectedStyle;

const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, (character) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
}[character]));

const cellId = () => `${selectedEmoji}--${selectedStyle}`;

const renderAxes = () => {
  emojiAxis.innerHTML = catalog.emoji.map((item) => `<button type="button" data-emoji="${escapeHtml(item.id)}" aria-pressed="${item.id === selectedEmoji}" title="${escapeHtml(item.cldr_short_name)}">${String(item.rank).padStart(2, '0')} · ${escapeHtml(item.cldr_short_name)}</button>`).join('');
  styleAxis.innerHTML = catalog.styles.map((item) => `<button type="button" data-style="${escapeHtml(item.id)}" aria-pressed="${item.id === selectedStyle}">${String(item.index).padStart(2, '0')} · ${escapeHtml(item.id)}</button>`).join('');
  emojiSelect.value = selectedEmoji;
  styleSelect.value = selectedStyle;
};

const renderDetail = (updateUrl = true) => {
  const item = catalog.cells.find((candidate) => candidate.id === cellId());
  if (!item) return;
  detail.innerHTML = `
    <div class="matrix-art">
      <div class="matrix-vector"><img src="${escapeHtml(item.assets.svg)}" width="440" height="440" loading="lazy" decoding="async" alt="Original ${escapeHtml(item.cldr_short_name)} study in ${escapeHtml(item.style)} construction"></div>
      <div class="matrix-proofs">
        <figure><img class="matrix-native" src="${escapeHtml(item.assets.native)}" width="16" height="16" loading="lazy" decoding="async" alt=""><figcaption>Actual 16×16</figcaption></figure>
        <figure><img class="matrix-zoom" src="${escapeHtml(item.assets.native)}" width="128" height="128" loading="lazy" decoding="async" alt=""><figcaption>Pixel zoom · native 16px</figcaption></figure>
        <figure><img class="matrix-silhouette" src="${escapeHtml(item.assets.silhouette)}" width="128" height="128" loading="lazy" decoding="async" alt=""><figcaption>128px silhouette</figcaption></figure>
      </div>
    </div>
    <div class="matrix-copy-detail">
      <span class="matrix-coordinate">Rank ${String(item.rank).padStart(2, '0')} · style ${String(item.style_index).padStart(2, '0')} · practice specimen</span>
      <h3>${escapeHtml(item.cldr_short_name)}</h3>
      <p>One semantic meaning rebuilt through the <strong>${escapeHtml(item.style)}</strong> construction grammar. The material treatment is subordinate to recognizability at native size.</p>
      <dl><div><dt>Code points</dt><dd>${escapeHtml(item.unicode_sequence)}</dd></div><div><dt>Style</dt><dd>${escapeHtml(item.style)}</dd></div><div><dt>Contract</dt><dd>Original clean-room geometry · source-bound review</dd></div></dl>
      <div class="matrix-links"><a href="${escapeHtml(item.assets.svg)}">SVG source</a><a href="${escapeHtml(item.assets.proof)}">128px proof</a><a href="${escapeHtml(item.assets.receipt)}">Receipt</a><a href="${escapeHtml(item.assets.case)}">Case record</a></div>
    </div>`;
  detail.setAttribute('aria-busy', 'false');
  renderAxes();
  status.textContent = `${item.id} · 400/400 cells available`;
  document.title = `${item.cldr_short_name} × ${item.style} — IconFlow Emoji Matrix`;
  if (updateUrl) history.replaceState(null, '', `#${item.id}`);
};

const chooseFromHash = () => {
  const hash = decodeURIComponent(location.hash.slice(1));
  const item = catalog.cells.find((candidate) => candidate.id === hash);
  if (item) {
    selectedEmoji = item.emoji_id;
    selectedStyle = item.style;
  }
};

controls.addEventListener('submit', (event) => {
  event.preventDefault();
  selectedEmoji = emojiSelect.value;
  selectedStyle = styleSelect.value;
  renderDetail();
});

emojiAxis.addEventListener('click', (event) => {
  const button = event.target.closest('[data-emoji]');
  if (!button) return;
  selectedEmoji = button.dataset.emoji;
  renderDetail();
});

styleAxis.addEventListener('click', (event) => {
  const button = event.target.closest('[data-style]');
  if (!button) return;
  selectedStyle = button.dataset.style;
  renderDetail();
});

window.addEventListener('hashchange', () => {
  chooseFromHash();
  renderDetail(false);
});

fetch('/assets/gallery/emoji-matrix/catalog.json')
  .then((response) => {
    if (!response.ok) throw new Error(`catalog returned ${response.status}`);
    return response.json();
  })
  .then((value) => {
    if (value.emoji_count !== 20 || value.style_count !== 20 || value.cell_count !== 400 || value.cells.length !== 400) throw new Error('catalog is not the complete 20 × 20 matrix');
    catalog = value;
    const representative = catalog.cells.find((item) => item.id === REPRESENTATIVE_CELL);
    selectedEmoji = representative ? representative.emoji_id : catalog.emoji[0].id;
    selectedStyle = representative ? representative.style : catalog.styles[0].id;
    emojiSelect.innerHTML = catalog.emoji.map((item) => `<option value="${escapeHtml(item.id)}">${String(item.rank).padStart(2, '0')} · ${escapeHtml(item.cldr_short_name)}</option>`).join('');
    styleSelect.innerHTML = catalog.styles.map((item) => `<option value="${escapeHtml(item.id)}">${String(item.index).padStart(2, '0')} · ${escapeHtml(item.id)}</option>`).join('');
    chooseFromHash();
    renderDetail(false);
  })
  .catch((error) => {
    detail.setAttribute('aria-busy', 'false');
    status.textContent = 'Emoji Matrix catalog unavailable.';
    detail.innerHTML = `<p class="matrix-error">${escapeHtml(error.message)}</p>`;
  });
