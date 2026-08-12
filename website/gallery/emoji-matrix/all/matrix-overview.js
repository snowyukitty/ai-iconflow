const poster = document.querySelector('[data-matrix-poster]');
const hotspots = document.querySelector('[data-matrix-hotspots]');
const columnAxis = document.querySelector('[data-column-axis]');
const rowAxis = document.querySelector('[data-row-axis]');
const inspector = document.querySelector('[data-cell-inspector]');
const status = document.querySelector('#overview-status');
const focusControls = document.querySelector('[data-focus-controls]');
const focusMode = document.querySelector('[data-focus-mode]');
const focusValue = document.querySelector('[data-focus-value]');
const focusGrid = document.querySelector('[data-focus-grid]');

let catalog;
let cells = [];
let activeIndex = 0;
let focusRendered = false;
const interactiveGrid = window.matchMedia('(min-width: 761px)');

const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, (character) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
}[character]));

const labelStyle = (id) => id.split('-').map((part) => part[0].toUpperCase() + part.slice(1)).join(' ');
const detailUrl = (item) => `/gallery/emoji-matrix/#${encodeURIComponent(item.id)}`;

const assertCatalog = (value) => {
  const complete = value.emoji_count === 20
    && value.style_count === 20
    && value.cell_count === 400
    && value.emoji?.length === 20
    && value.styles?.length === 20
    && value.cells?.length === 400
    && value.overview?.width === 2560
    && value.overview?.height === 2560;
  if (!complete) throw new Error('Catalog is not the complete reviewed 20 × 20 matrix.');
  const ids = new Set(value.cells.map((item) => item.id));
  if (ids.size !== 400) throw new Error('Catalog contains duplicate cell IDs.');
};

const renderAxes = () => {
  columnAxis.innerHTML = catalog.styles.map((item) => `<span data-column="${item.index - 1}"><b>${String(item.index).padStart(2, '0')}</b>${escapeHtml(item.id)}</span>`).join('');
  rowAxis.innerHTML = catalog.emoji.map((item) => `<span data-row="${item.rank - 1}"><b>${String(item.rank).padStart(2, '0')}</b>${escapeHtml(item.cldr_short_name)}</span>`).join('');
};

const markAxes = (item) => {
  document.querySelectorAll('.column-axis .is-active, .row-axis .is-active').forEach((node) => node.classList.remove('is-active'));
  columnAxis.querySelector(`[data-column="${item.style_index - 1}"]`)?.classList.add('is-active');
  rowAxis.querySelector(`[data-row="${item.rank - 1}"]`)?.classList.add('is-active');
};

const renderInspector = (index, moveFocus = false) => {
  activeIndex = Math.max(0, Math.min(399, index));
  const item = cells[activeIndex];
  hotspots.querySelectorAll('[role="gridcell"]').forEach((node, nodeIndex) => {
    node.tabIndex = nodeIndex === activeIndex ? 0 : -1;
    node.classList.toggle('is-active', nodeIndex === activeIndex);
  });
  const target = hotspots.children[activeIndex];
  if (moveFocus) target?.focus({ preventScroll: true });
  markAxes(item);
  if (!interactiveGrid.matches) {
    inspector.setAttribute('aria-busy', 'false');
    status.textContent = '400/400 reviewed cells · complete poster';
    return;
  }
  inspector.innerHTML = `
    <span class="inspector-coordinate">Row ${String(item.rank).padStart(2, '0')} · column ${String(item.style_index).padStart(2, '0')}</span>
    <div class="inspector-art"><img src="${escapeHtml(item.assets.svg)}" width="176" height="176" decoding="async" alt="Original ${escapeHtml(item.cldr_short_name)} study in ${escapeHtml(item.style)} construction"></div>
    <h3>${escapeHtml(item.cldr_short_name)}</h3>
    <p>${escapeHtml(labelStyle(item.style))}</p>
    <div class="inspector-native"><span>Actual 16 × 16</span><img src="${escapeHtml(item.assets.native)}" width="16" height="16" decoding="async" alt=""></div>
    <a href="${detailUrl(item)}">Open full specimen →</a>`;
  inspector.setAttribute('aria-busy', 'false');
  status.textContent = `${item.id} · 400/400 reviewed cells`;
};

const buildHotspots = () => {
  hotspots.innerHTML = cells.map((item, index) => `<a role="gridcell" href="${detailUrl(item)}" tabindex="${index === 0 ? '0' : '-1'}" aria-rowindex="${item.rank}" aria-colindex="${item.style_index}" data-index="${index}" aria-label="${escapeHtml(item.cldr_short_name)}, ${escapeHtml(labelStyle(item.style))}"></a>`).join('');
  hotspots.addEventListener('pointerover', (event) => {
    const cell = event.target.closest('[data-index]');
    if (cell) renderInspector(Number(cell.dataset.index));
  });
  hotspots.addEventListener('focusin', (event) => {
    const cell = event.target.closest('[data-index]');
    if (cell) renderInspector(Number(cell.dataset.index));
  });
  hotspots.addEventListener('keydown', (event) => {
    const directions = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -20, ArrowDown: 20 };
    let next = directions[event.key] === undefined ? activeIndex : activeIndex + directions[event.key];
    if (event.key === 'Home') next = Math.floor(activeIndex / 20) * 20;
    if (event.key === 'End') next = Math.floor(activeIndex / 20) * 20 + 19;
    if (next === activeIndex && !['Home', 'End'].includes(event.key)) return;
    if (next < 0 || next > 399) return;
    event.preventDefault();
    renderInspector(next, true);
  });
};

const focusItems = () => {
  if (focusMode.value === 'style') return cells.filter((item) => item.style === focusValue.value);
  return cells.filter((item) => item.emoji_id === focusValue.value);
};

const updateFocusUrl = () => {
  const url = new URL(window.location.href);
  url.searchParams.set('axis', focusMode.value);
  url.searchParams.set('value', focusValue.value);
  history.replaceState(null, '', url);
};

const renderFocus = (updateUrl = true) => {
  const items = focusItems();
  if (items.length !== 20) throw new Error('Focus view must contain exactly 20 specimens.');
  focusGrid.innerHTML = items.map((item) => {
    const label = focusMode.value === 'style' ? item.cldr_short_name : labelStyle(item.style);
    const coordinate = focusMode.value === 'style' ? `Meaning ${String(item.rank).padStart(2, '0')}` : `Grammar ${String(item.style_index).padStart(2, '0')}`;
    return `<a class="focus-card" href="${detailUrl(item)}">
      <span class="focus-coordinate">${coordinate}</span>
      <span class="focus-art"><img src="${escapeHtml(item.assets.svg)}" width="112" height="112" loading="lazy" decoding="async" alt=""></span>
      <strong>${escapeHtml(label)}</strong>
      <span class="focus-proof"><img src="${escapeHtml(item.assets.native)}" width="16" height="16" loading="lazy" decoding="async" alt="">Actual 16px</span>
    </a>`;
  }).join('');
  focusGrid.setAttribute('aria-busy', 'false');
  focusRendered = true;
  if (updateUrl) updateFocusUrl();
};

const populateFocusValues = (requestedValue) => {
  const choices = focusMode.value === 'style' ? catalog.styles : catalog.emoji;
  focusValue.innerHTML = choices.map((item) => {
    const value = item.id;
    const label = focusMode.value === 'style'
      ? `${String(item.index).padStart(2, '0')} · ${labelStyle(item.id)}`
      : `${String(item.rank).padStart(2, '0')} · ${item.cldr_short_name}`;
    return `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`;
  }).join('');
  if (choices.some((item) => item.id === requestedValue)) focusValue.value = requestedValue;
};

focusMode.addEventListener('change', () => {
  populateFocusValues();
  renderFocus();
});

focusValue.addEventListener('change', () => renderFocus());
focusControls.addEventListener('submit', (event) => event.preventDefault());
interactiveGrid.addEventListener('change', (event) => {
  if (event.matches) renderInspector(activeIndex);
});

fetch('/assets/gallery/emoji-matrix/catalog.json')
  .then((response) => {
    if (!response.ok) throw new Error(`Catalog returned ${response.status}.`);
    return response.json();
  })
  .then((value) => {
    assertCatalog(value);
    catalog = value;
    cells = [...catalog.cells].sort((a, b) => a.rank - b.rank || a.style_index - b.style_index);
    poster.src = catalog.overview.asset;
    renderAxes();
    buildHotspots();
    renderInspector(0);

    const parameters = new URL(window.location.href).searchParams;
    const requestedMode = parameters.get('axis');
    const requestedValue = parameters.get('value');
    if (['meaning', 'style'].includes(requestedMode)) focusMode.value = requestedMode;
    populateFocusValues(requestedValue);
    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver((entries) => {
        if (!focusRendered && entries.some((entry) => entry.isIntersecting)) {
          renderFocus(false);
          observer.disconnect();
        }
      }, { rootMargin: '600px 0px' });
      observer.observe(focusGrid);
    } else {
      renderFocus(false);
    }
  })
  .catch((error) => {
    status.textContent = 'Complete matrix unavailable.';
    inspector.setAttribute('aria-busy', 'false');
    inspector.innerHTML = `<p class="overview-error">${escapeHtml(error.message)}</p>`;
    focusGrid.setAttribute('aria-busy', 'false');
    focusGrid.innerHTML = `<p class="overview-error">${escapeHtml(error.message)}</p>`;
  });
