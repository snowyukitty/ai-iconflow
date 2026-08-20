// Remix Lab: one semantic source, live design parameters, exact native pixels.
// Everything renders in the visitor's own browser; nothing is uploaded.
(() => {
  const lab = document.querySelector('[data-remix-lab]');
  if (!lab) return;

  const PIKA = (c, sw) =>
    `<path d="M212 628C212 454 334 338 512 342C680 346 790 448 786 604C782 734 678 806 508 806C338 806 212 752 212 628Z" fill="${c.body}" stroke="${c.body}" stroke-width="${sw}"/>` +
    `<ellipse cx="340" cy="332" rx="76" ry="108" fill="${c.body}" transform="rotate(-18 340 332)"/>` +
    `<ellipse cx="454" cy="322" rx="72" ry="104" fill="${c.body}" transform="rotate(10 454 322)"/>` +
    `<path d="M266 658C334 602 410 588 488 618C550 642 592 688 616 748C532 790 418 796 326 760Z" fill="${c.cove}"/>`;
  const EYE = (c, r) => `<circle cx="658" cy="486" r="${r}" fill="${c.ink}"/>`;
  const STEM = (c, sw) => `<path d="M760 548L842 468" stroke="${c.body}" stroke-width="${sw}" stroke-linecap="round"/>`;

  const OBJECTS = {
    petal: {
      title: 'Petal Haypile', essence: 'gather', object: 'three oversized petals',
      body: (c) => PIKA(c, 44) + EYE(c, 28) + STEM(c, 60) +
        `<g><path d="M820 454C758 390 774 304 858 276C904 346 886 420 820 454Z" fill="${c.a1}" stroke="${c.body}" stroke-width="28"/>` +
        `<path d="M856 502C818 432 854 356 942 356C964 434 930 492 856 502Z" fill="${c.a2}" stroke="${c.body}" stroke-width="28"/>` +
        `<path d="M790 426C726 382 724 300 794 254C854 310 850 382 790 426Z" fill="${c.a3}" stroke="${c.body}" stroke-width="28"/></g>`,
    },
    balloon: {
      title: 'Balloon Haypile', essence: 'lift', object: 'one large three-gore balloon',
      body: (c) => `<defs><clipPath id="rx-clip"><path d="M660 100C754 100 828 176 828 262C828 348 748 434 660 486C572 434 492 348 492 262C492 176 566 100 660 100Z"/></clipPath></defs>` +
        `<g transform="translate(-69 3) scale(1.02)">` +
        `<path d="M660 474L712 676" stroke="${c.body}" stroke-width="72" stroke-linecap="round"/>` +
        `<path d="M660 100C754 100 828 176 828 262C828 348 748 434 660 486C572 434 492 348 492 262C492 176 566 100 660 100Z" fill="${c.a1}"/>` +
        `<g clip-path="url(#rx-clip)"><path d="M660 100C590 170 566 340 660 486C754 340 730 170 660 100Z" fill="${c.a2}"/>` +
        `<path d="M660 100C730 170 754 340 660 486C748 434 828 348 828 262C828 176 754 100 660 100Z" fill="${c.a3}"/></g>` +
        `<path d="M660 100C754 100 828 176 828 262C828 348 748 434 660 486C572 434 492 348 492 262C492 176 566 100 660 100Z" fill="none" stroke="${c.body}" stroke-width="40"/>` +
        `<g transform="translate(168 380) scale(0.65)">${PIKA(c, 68)}${EYE(c, 40)}${STEM(c, 84)}</g></g>`,
    },
    canopy: {
      title: 'Canopy Haypile', essence: 'descend', object: 'a deep panelled canopy on two unequal risers',
      body: (c) => `<g transform="translate(12 10)">` +
        `<path d="M242 348L436 556" stroke="${c.body}" stroke-width="64" stroke-linecap="round"/>` +
        `<path d="M692 348L620 610" stroke="${c.body}" stroke-width="64" stroke-linecap="round"/>` +
        `<path d="M220 338A246 234 0 0 1 712 338Q630 406 548 338Q466 406 384 338Q302 406 220 338Z" fill="${c.a1}"/>` +
        `<path d="M466 104C356 168 300 270 384 338Q466 406 548 338C632 270 576 168 466 104Z" fill="${c.a2}"/>` +
        `<path d="M466 104C576 168 632 270 548 338Q630 406 712 338A246 234 0 0 0 466 104Z" fill="${c.a3}"/>` +
        `<path d="M466 104C356 168 300 270 384 338" fill="none" stroke="${c.body}" stroke-width="36"/>` +
        `<path d="M466 104C576 168 632 270 548 338" fill="none" stroke="${c.body}" stroke-width="36"/>` +
        `<path d="M220 338A246 234 0 0 1 712 338Q630 406 548 338Q466 406 384 338Q302 406 220 338Z" fill="none" stroke="${c.body}" stroke-width="44"/>` +
        `<g transform="translate(216 400) scale(0.63)">${PIKA(c, 70)}${EYE(c, 44)}${STEM(c, 92)}</g></g>`,
    },
  };

  const PALETTES = {
    graphite: { card: '#191a20', body: '#fff4e8', cove: '#59c7c1', a1: '#ff5a4f', a2: '#f2b84b', a3: '#845ec2' },
    paper: { card: '#fff4e8', body: '#191a20', cove: '#59c7c1', a1: '#ff5a4f', a2: '#f2b84b', a3: '#845ec2' },
    lagoon: { card: '#0f5f63', body: '#fff4e8', cove: '#f2b84b', a1: '#ff5a4f', a2: '#ffd27a', a3: '#9be7e1' },
    dusk: { card: '#2c1f4a', body: '#ffe3d2', cove: '#ff8a80', a1: '#ffd27a', a2: '#7ad1ff', a3: '#ff5a4f' },
  };

  const DEFAULT = { object: 'petal', ...PALETTES.graphite, radius: 22, scale: 100, mirror: false, card: PALETTES.graphite.card, cardOn: true, surface: 'dark' };
  const state = { ...DEFAULT };

  const luminance = (hex) => {
    const [r, g, b] = hexToRgb(hex);
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
  };
  const svgFor = (s) => {
    // The eye takes the card color on a card; without one it contrasts with the body.
    const ink = s.cardOn ? s.card : (luminance(s.body) > 0.5 ? '#191a20' : '#fff4e8');
    const c = { body: s.body, cove: s.cove, a1: s.a1, a2: s.a2, a3: s.a3, ink };
    const rx = Math.round((s.radius / 100) * 944);
    const k = s.scale / 100;
    const flip = s.mirror ? -k : k;
    const card = s.cardOn ? `<rect x="40" y="40" width="944" height="944" rx="${rx}" fill="${s.card}"/>` : '';
    const o = OBJECTS[s.object];
    return `<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024" role="img" aria-labelledby="t d">` +
      `<title id="t">IconFlow remix — ${o.title}</title><desc id="d">A low-eared pika with its hay store carries ${o.object}. Unreviewed remix from the IconFlow Remix Lab.</desc>` +
      card + `<g transform="translate(512 512) scale(${flip} ${k}) translate(-512 -512)">${o.body(c)}</g></svg>`;
  };

  const hexToRgb = (hex) => {
    const n = parseInt(hex.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  };

  const q = (sel) => lab.querySelector(sel);
  const qa = (sel) => Array.from(lab.querySelectorAll(sel));
  const preview = q('[data-remix-preview]');
  const sizeCanvases = qa('canvas[data-native]');
  const zoom = q('canvas[data-remix-zoom]');
  const silhouette = q('canvas[data-remix-silhouette]');
  const template = q('canvas[data-remix-template]');
  const templateNote = q('[data-template-note]');
  const stage = q('[data-remix-stage]');
  const colorInputs = qa('input[type="color"][data-color]');
  const radius = q('[data-radius]');
  const scale = q('[data-scale]');
  const radiusOut = q('[data-radius-out]');
  const scaleOut = q('[data-scale-out]');
  const mirror = q('[data-mirror]');
  const cardOn = q('[data-card-on]');
  const status = q('[data-remix-status]');

  const paint = (img, s) => {
    sizeCanvases.forEach((canvas) => {
      const size = Number(canvas.dataset.native);
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, size, size);
      ctx.drawImage(img, 0, 0, size, size);
    });
    const base = sizeCanvases.find((canvas) => canvas.dataset.native === '16');
    const zctx = zoom.getContext('2d');
    zctx.imageSmoothingEnabled = false;
    zctx.clearRect(0, 0, zoom.width, zoom.height);
    zctx.drawImage(base, 0, 0, zoom.width, zoom.height);

    // Silhouette: color removed, what shape is left against the card?
    const work = document.createElement('canvas');
    work.width = work.height = 128;
    const wctx = work.getContext('2d');
    wctx.drawImage(img, 0, 0, 128, 128);
    const data = wctx.getImageData(0, 0, 128, 128);
    const px = data.data;
    const [cr, cg, cb] = hexToRgb(s.card);
    const sil = silhouette.getContext('2d').createImageData(128, 128);
    const tpl = template.getContext('2d').createImageData(128, 128);
    for (let i = 0; i < px.length; i += 4) {
      const a = px[i + 3];
      const onCard = s.cardOn && Math.abs(px[i] - cr) + Math.abs(px[i + 1] - cg) + Math.abs(px[i + 2] - cb) < 90;
      const visible = a > 128 && !onCard;
      sil.data[i] = sil.data[i + 1] = sil.data[i + 2] = visible ? 255 : 0;
      sil.data[i + 3] = 255;
      // macOS reads the source alpha as-is (iconflow's 'alpha' template mode),
      // so keep the anti-aliased coverage instead of thresholding it.
      tpl.data[i] = tpl.data[i + 1] = tpl.data[i + 2] = 0;
      tpl.data[i + 3] = a;
    }
    silhouette.getContext('2d').putImageData(sil, 0, 0);
    template.getContext('2d').putImageData(tpl, 0, 0);
    templateNote.textContent = s.cardOn
      ? 'Alpha template = a featureless rounded square. This is why the brand ships a linked mark-only tray source.'
      : 'Alpha template keeps the whole silhouette but no interior feature. For a menu bar, cut one identifying feature clean through as a transparent hole (docs/LEARNINGS.md L42).';
  };

  let pending = 0;
  let sequence = 0;
  const render = () => {
    cancelAnimationFrame(pending);
    pending = requestAnimationFrame(() => {
      // Snapshot the state so a slow decode cannot paint with newer thresholds,
      // and drop any load that finishes after a later render started.
      const snapshot = { ...state };
      const ticket = ++sequence;
      const svg = svgFor(snapshot);
      const url = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
      preview.src = url;
      const img = new Image();
      img.onload = () => { if (ticket === sequence) paint(img, snapshot); };
      img.onerror = () => { if (ticket === sequence) flash('This remix could not be rendered. Reset and try again.'); };
      img.src = url;
      stage.dataset.surface = snapshot.surface;
      lab.dataset.object = snapshot.object;
    });
  };

  const syncControls = () => {
    syncPalette();
    colorInputs.forEach((input) => { input.value = state[input.dataset.color]; });
    radius.value = state.radius; radiusOut.textContent = `${state.radius}%`;
    scale.value = state.scale; scaleOut.textContent = `${state.scale}%`;
    mirror.checked = state.mirror; cardOn.checked = state.cardOn;
    qa('[data-object]').forEach((b) => {
      const on = b.dataset.object === state.object;
      b.classList.toggle('is-active', on); b.setAttribute('aria-pressed', String(on));
    });
    qa('[data-remix-surface]').forEach((b) => {
      const on = b.dataset.remixSurface === state.surface;
      b.classList.toggle('is-active', on); b.setAttribute('aria-pressed', String(on));
    });
  };

  qa('[data-object]').forEach((b) => b.addEventListener('click', () => { state.object = b.dataset.object; syncControls(); render(); }));
  qa('[data-palette]').forEach((b) => b.addEventListener('click', () => { Object.assign(state, PALETTES[b.dataset.palette]); syncControls(); render(); }));
  const syncPalette = () => {
    qa('[data-palette]').forEach((b) => {
      const preset = PALETTES[b.dataset.palette];
      const on = Object.keys(preset).every((k) => state[k] === preset[k]);
      b.classList.toggle('is-active', on); b.setAttribute('aria-pressed', String(on));
    });
  };
  qa('[data-remix-surface]').forEach((b) => b.addEventListener('click', () => { state.surface = b.dataset.remixSurface; syncControls(); render(); }));
  colorInputs.forEach((input) => input.addEventListener('input', () => { state[input.dataset.color] = input.value; syncPalette(); render(); }));
  radius.addEventListener('input', () => { state.radius = Number(radius.value); radiusOut.textContent = `${state.radius}%`; render(); });
  scale.addEventListener('input', () => { state.scale = Number(scale.value); scaleOut.textContent = `${state.scale}%`; render(); });
  mirror.addEventListener('change', () => { state.mirror = mirror.checked; render(); });
  cardOn.addEventListener('change', () => { state.cardOn = cardOn.checked; render(); });
  q('[data-remix-reset]')?.addEventListener('click', () => { Object.assign(state, DEFAULT); syncControls(); render(); });

  const flash = (text) => {
    status.textContent = text;
    window.clearTimeout(flash.timer);
    flash.timer = window.setTimeout(() => { status.textContent = ''; }, 2400);
  };
  const fallback = q('[data-remix-fallback]');
  const copy = async (text, done) => {
    try {
      await navigator.clipboard.writeText(text);
      fallback.hidden = true;
      flash(done);
    } catch {
      // No clipboard access: reveal the text so it can be selected by hand.
      fallback.value = text;
      fallback.hidden = false;
      fallback.focus();
      fallback.select();
      flash('Clipboard blocked — the text is shown below; select and copy it.');
    }
  };
  q('[data-remix-copy-svg]')?.addEventListener('click', () => copy(svgFor(state), 'SVG copied. Save it as master.svg.'));
  q('[data-remix-download]')?.addEventListener('click', () => {
    // A data: URL keeps the download inside the site's CSP (no blob: source).
    const link = document.createElement('a');
    link.href = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svgFor(state))}`;
    link.download = 'master.svg';
    document.body.append(link); link.click(); link.remove();
    flash('Downloaded master.svg — now run iconflow check / review / ship.');
  });
  q('[data-remix-copy-brief]')?.addEventListener('click', () => {
    const o = OBJECTS[state.object];
    const brief = [
      'Use IconFlow (https://github.com/snowyukitty/ai-iconflow) to turn this remix into a reviewed, platform-ready icon family.',
      `Source: the attached master.svg from the IconFlow Remix Lab — ${o.title}: a low-eared pika with its hay store carries ${o.object}.`,
      `Palette: card ${state.cardOn ? state.card : 'transparent'}, body ${state.body}, cove ${state.cove}, accents ${state.a1} ${state.a2} ${state.a3}; card radius ${state.radius}%; mark scale ${state.scale}%${state.mirror ? '; mirrored' : ''}.`,
      `Essence: ${o.essence}. Avoid the AI-sparkle, robot, and blue-purple monogram clichés; keep one signature device.`,
      'Follow ai-iconflow/AGENTS.md: read docs/LEARNINGS.md, write iconflow.toml with python -m iconflow init, run check, then review (inspect the 16px pixels and every target), ship only when every rubric axis is at least 4/5, and record the case with iconflow case new.',
    ].join('\n');
    copy(brief, 'Agent brief copied. Paste it next to your master.svg.');
  });

  syncControls();
  render();
})();
