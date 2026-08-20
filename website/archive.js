// Living archive: pause the homepage marquee when it is off screen, and drive
// the filters, deep links, and detail dialog on /archive/.
(() => {
  const marquee = document.querySelector('[data-archive-marquee]');
  if (marquee) {
    // Clone each track once so the CSS translateX(-100%) loop is seamless.
    marquee.querySelectorAll('.archive-track').forEach((track) => {
      const copy = track.cloneNode(true);
      copy.setAttribute('aria-hidden', 'true');
      copy.querySelectorAll('a').forEach((link) => { link.tabIndex = -1; });
      track.after(copy);
    });
  }
  if (marquee && 'IntersectionObserver' in window) {
    const watch = new IntersectionObserver((entries) => {
      entries.forEach((entry) => marquee.classList.toggle('is-offscreen', !entry.isIntersecting));
    }, { threshold: 0.05 });
    watch.observe(marquee);
  }

  const body = document.querySelector('.archive-body');
  if (!body) return;

  const cards = Array.from(document.querySelectorAll('.archive-card'));
  const sections = Array.from(document.querySelectorAll('[data-round-section]'));
  const chips = Array.from(document.querySelectorAll('.archive-filters [data-filter]'));
  const count = document.querySelector('[data-filter-count]');

  const applyFilter = (filter) => {
    let shown = 0;
    cards.forEach((card) => {
      const visible = filter === 'all'
        || (filter === 'gated' && card.dataset.gated === 'true')
        || card.dataset.round === filter;
      card.hidden = !visible;
      if (visible) shown += 1;
    });
    sections.forEach((section) => {
      section.hidden = !section.querySelector('.archive-card:not([hidden])');
    });
    chips.forEach((chip) => {
      const on = chip.dataset.filter === filter;
      chip.classList.toggle('is-active', on);
      chip.setAttribute('aria-pressed', String(on));
    });
    if (count) count.textContent = `${shown} shown`;
  };
  chips.forEach((chip) => chip.addEventListener('click', () => applyFilter(chip.dataset.filter)));

  const dialog = document.querySelector('[data-archive-dialog]');
  const field = (name) => dialog?.querySelector(`[data-dialog-${name}]`);
  const open = (card) => {
    if (!dialog || typeof dialog.showModal !== 'function') return;
    const img = card.querySelector('.card-visual img');
    const proof = card.querySelector('.card-native img');
    const status = card.querySelector('.card-status');
    const scores = card.querySelector('.card-scores');
    const story = card.querySelector('.card-copy p');
    field('img').src = img.src;
    field('img').alt = img.alt;
    field('round').textContent = card.querySelector('.card-round').textContent;
    field('name').textContent = card.querySelector('h3').textContent;
    field('story').textContent = story ? story.textContent : '';
    field('status').textContent = status ? status.textContent : '';
    field('scores').textContent = scores ? `· ${scores.textContent} (legibility / distinctiveness / balance / color / scalability / craft)` : '';
    field('proof').src = proof.src;
    field('source').href = img.getAttribute('src');
    field('source').download = `${card.id}.svg`;
    dialog.showModal();
    if (history.replaceState) history.replaceState(null, '', `#${card.id}`);
  };
  cards.forEach((card) => {
    card.addEventListener('click', (event) => {
      if (event.target.closest('a')) return;
      open(card);
    });
    card.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); open(card); }
    });
  });
  dialog?.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); });

  const jump = () => {
    const id = decodeURIComponent(location.hash.slice(1));
    if (!id) return;
    const card = document.getElementById(id);
    if (!card || !card.classList.contains('archive-card')) return;
    applyFilter('all');
    cards.forEach((item) => item.classList.toggle('is-target', item === card));
    card.scrollIntoView({ block: 'center' });
    open(card);
  };
  window.addEventListener('hashchange', jump);
  jump();
})();
