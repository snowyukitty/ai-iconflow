document.documentElement.classList.add('js');

const header = document.querySelector('[data-header]');
const menuButton = document.querySelector('[data-menu]');
const nav = document.querySelector('#site-nav');

const updateHeader = () => header?.classList.toggle('is-scrolled', window.scrollY > 24);
updateHeader();
window.addEventListener('scroll', updateHeader, { passive: true });

const setMenu = (open) => {
  menuButton.setAttribute('aria-expanded', String(open));
  menuButton.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
  nav?.classList.toggle('is-open', open);
};
menuButton?.addEventListener('click', () => setMenu(menuButton.getAttribute('aria-expanded') !== 'true'));
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && menuButton?.getAttribute('aria-expanded') === 'true') { setMenu(false); menuButton.focus(); }
});
document.addEventListener('click', (event) => {
  if (menuButton?.getAttribute('aria-expanded') === 'true' && !event.target.closest('.site-header')) setMenu(false);
});

nav?.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => { if (menuButton) setMenu(false); }));

const revealItems = document.querySelectorAll('.reveal');
if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        revealObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.11 });
  revealItems.forEach((item) => revealObserver.observe(item));
} else {
  revealItems.forEach((item) => item.classList.add('is-visible'));
}

const lab = document.querySelector('[data-proof-lab]');
if (lab) {
  const actual = lab.querySelector('[data-actual]');
  const zoom = lab.querySelector('[data-zoom]');
  const measure = lab.querySelector('[data-measure]');
  const workbench = lab.querySelector('.proof-workbench');
  const actualStage = lab.querySelector('.actual-stage');

  lab.querySelectorAll('[data-size]').forEach((button) => {
    button.addEventListener('click', () => {
      const size = Number(button.dataset.size);
      lab.querySelectorAll('[data-size]').forEach((item) => {
        const selected = item === button;
        item.classList.toggle('is-active', selected);
        item.setAttribute('aria-pressed', String(selected));
      });
      const source = `/assets/proof/icon-${size}.png?v=petal`;
      actual.src = source;
      actual.width = size;
      actual.height = size;
      zoom.src = source;
      measure.textContent = `${size} × ${size}`;
    });
  });

  lab.querySelectorAll('[data-surface]').forEach((button) => {
    if (button === workbench) return;
    button.addEventListener('click', () => {
      lab.querySelectorAll('[data-surface-controls] button').forEach((item) => {
        const selected = item === button;
        item.classList.toggle('is-active', selected);
        item.setAttribute('aria-pressed', String(selected));
      });
      workbench.dataset.surface = button.dataset.surface;
    });
  });

  lab.querySelectorAll('[data-crop]').forEach((button) => {
    button.addEventListener('click', () => {
      lab.querySelectorAll('[data-crop-controls] button').forEach((item) => {
        const selected = item === button;
        item.classList.toggle('is-active', selected);
        item.setAttribute('aria-pressed', String(selected));
      });
      actualStage.dataset.crop = button.dataset.crop;
    });
  });

  const sourceToggle = lab.querySelector('[data-source-toggle]');
  const receipt = lab.querySelector('[data-receipt-status]');
  const receiptTitle = lab.querySelector('[data-receipt-title]');
  const receiptCopy = lab.querySelector('[data-receipt-copy]');
  sourceToggle?.addEventListener('change', () => {
    const stale = sourceToggle.checked;
    receipt.classList.toggle('is-approved', !stale);
    receipt.classList.toggle('is-stale', stale);
    receiptTitle.textContent = stale ? 'Receipt rejected' : 'Source-bound approval';
    receiptCopy.textContent = stale ? 'The SVG changed after review. Ship is blocked.' : 'Current SVG matches the reviewed hash.';
  });
}

const scrub = document.querySelector('[data-hero-scrub]');
if (scrub) {
  const icon = document.querySelector('.hero-icon');
  const wrap = icon.closest('.hero-icon-wrap');
  const sizeLabel = document.querySelector('[data-hero-size]');
  const loupe = document.querySelector('[data-hero-loupe]');
  const zoom = document.querySelector('[data-hero-zoom]');
  const actual = document.querySelector('[data-hero-actual]');
  const sizes = [16, 24, 32, 48, 64, 128];
  scrub.addEventListener('input', () => {
    const index = Number(scrub.value);
    const native = index < sizes.length;
    const size = sizes[index];
    if (native) {
      const source = `/assets/proof/icon-${size}.png?v=petal`;
      zoom.src = source;
      actual.src = source;
      actual.width = size;
      actual.height = size;
    }
    icon.hidden = native;
    loupe.hidden = !native;
    wrap.classList.toggle('is-native', native);
    sizeLabel.textContent = native ? `native ${size} × ${size} px · exact pixels` : 'review gate passed · 6/6';
    scrub.setAttribute('aria-valuetext', native ? `${size} pixels` : 'vector source');
  });
}

const galleryDialog = document.querySelector('[data-gallery-dialog]');
document.querySelector('[data-open-gallery]')?.addEventListener('click', () => galleryDialog?.showModal());
galleryDialog?.addEventListener('click', (event) => {
  if (event.target === galleryDialog) galleryDialog.close();
});

document.querySelectorAll('[data-copy-command]').forEach((copyButton) => {
  copyButton.addEventListener('click', async () => {
    const selector = copyButton.dataset.copyTarget;
    const source = selector
      ? document.querySelector(selector)
      : document.querySelector('[data-install-command]');
    if (!source) return;

    try {
      await navigator.clipboard.writeText(source.textContent.trim());
      copyButton.textContent = 'Copied';
    } catch {
      const range = document.createRange();
      range.selectNodeContents(source);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      copyButton.textContent = 'Selected';
    }
    window.setTimeout(() => { copyButton.textContent = 'Copy'; }, 1600);
  });
});
