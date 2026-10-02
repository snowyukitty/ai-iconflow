// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
// 16px X-ray: drop an icon, see the pixels it actually becomes.
// Everything runs in the visitor's browser. The file is read with FileReader
// into a data: URL (the site CSP allows data: images, not blob:), decoded by
// an <img> (which never executes SVG script), and analysed on canvases.
(() => {
  const root = document.querySelector('[data-xray]');
  if (!root) return;

  const q = (sel) => root.querySelector(sel);
  const qa = (sel) => Array.from(root.querySelectorAll(sel));
  const MAX_BYTES = 5 * 1024 * 1024;
  const TAB_LIGHT = [222, 225, 230];
  const TAB_DARK = [53, 54, 58];

  const drop = q('[data-xray-drop]');
  const input = q('[data-xray-input]');
  const status = q('[data-xray-status]');
  const results = q('[data-xray-results]');
  const original = q('[data-xray-original]');
  const zoom = q('canvas[data-xray-zoom]');
  const silhouette = q('canvas[data-xray-silhouette]');
  const verdictList = q('[data-xray-verdicts]');
  const headline = q('[data-xray-headline]');
  let current = null;

  const say = (text) => { status.textContent = text; };

  // ---------- loading ----------

  // An SVG with only a viewBox has no intrinsic size in some browsers, which
  // makes drawImage paint nothing. Give it one before decoding.
  const sizedSvg = (text) => {
    const doc = new DOMParser().parseFromString(text, 'image/svg+xml');
    const svg = doc.documentElement;
    if (!svg || svg.nodeName.toLowerCase() !== 'svg' || doc.querySelector('parsererror')) return null;
    const vb = (svg.getAttribute('viewBox') || '').trim().split(/[\s,]+/).map(Number);
    const hasSize = /^\d/.test(svg.getAttribute('width') || '') && /^\d/.test(svg.getAttribute('height') || '');
    if (!hasSize || /%/.test(svg.getAttribute('width') || '')) {
      const [w, h] = vb.length === 4 && vb[2] > 0 && vb[3] > 0 ? [vb[2], vb[3]] : [1024, 1024];
      const k = 1024 / Math.max(w, h);
      svg.setAttribute('width', String(Math.round(w * k)));
      svg.setAttribute('height', String(Math.round(h * k)));
    }
    return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(new XMLSerializer().serializeToString(svg))}`;
  };

  const loadUrl = (url, name) => new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => (img.naturalWidth && img.naturalHeight ? resolve(img) : reject(new Error('empty')));
    img.onerror = () => reject(new Error('decode'));
    img.decoding = 'async';
    img.src = url;
    img.alt = name;
  });

  const readFile = (file) => {
    if (!file) return;
    if (file.size > MAX_BYTES) { say('That file is over 5 MB. Icons rarely are — try the source SVG or a 1024px PNG.'); return; }
    const isSvg = file.type === 'image/svg+xml' || /\.svg$/i.test(file.name);
    const reader = new FileReader();
    reader.onerror = () => say('The browser could not read that file.');
    reader.onload = () => {
      const url = isSvg ? sizedSvg(String(reader.result)) : String(reader.result);
      if (!url) { say('That SVG did not parse. Check that it opens in a browser on its own.'); return; }
      run(url, file.name);
    };
    if (isSvg) reader.readAsText(file); else reader.readAsDataURL(file);
  };

  const run = async (url, name) => {
    say(`Rendering ${name}…`);
    try {
      const img = await loadUrl(url, name);
      current = analyse(img, name);
      paint(current);
      say(`${name} — rendered and checked in your browser. Nothing was uploaded.`);
      results.hidden = false;
      if (!run.scrolled) { results.scrollIntoView({ behavior: 'smooth', block: 'start' }); run.scrolled = true; }
    } catch {
      say(`${name} could not be decoded as an image. SVG, PNG, ICO, WebP and JPEG are supported.`);
    }
  };

  // ---------- rendering ----------

  // Draw the icon square, aspect preserved and centred, as a launcher would.
  const rasterise = (img, size) => {
    const c = document.createElement('canvas');
    c.width = c.height = size;
    const ctx = c.getContext('2d', { willReadFrequently: true });
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    const k = size / Math.max(img.naturalWidth, img.naturalHeight);
    const w = img.naturalWidth * k;
    const h = img.naturalHeight * k;
    ctx.drawImage(img, (size - w) / 2, (size - h) / 2, w, h);
    return c;
  };

  const lum = (r, g, b) => (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;

  // Otsu threshold over the luminance of opaque pixels.
  const otsu = (values) => {
    if (!values.length) return 0.5;
    const hist = new Array(64).fill(0);
    values.forEach((v) => { hist[Math.min(63, Math.floor(v * 64))] += 1; });
    let sum = 0;
    hist.forEach((n, i) => { sum += n * i; });
    let sumB = 0; let wB = 0; let best = 0; let split = 32;
    for (let i = 0; i < 64; i += 1) {
      wB += hist[i];
      if (!wB) continue;
      const wF = values.length - wB;
      if (!wF) break;
      sumB += i * hist[i];
      const between = wB * wF * ((sumB / wB) - ((sum - sumB) / wF)) ** 2;
      if (between > best) { best = between; split = i + 1; }
    }
    return split / 64;
  };

  // Classify every pixel as transparent, dark or light, then count the
  // 4-connected regions large enough to matter. A region of `minArea` pixels
  // at 128px is one whole pixel at 16px: if it does not survive there, a
  // feature the designer drew has merged into its neighbour.
  const regions = (canvas, threshold, minArea) => {
    const n = canvas.width;
    const px = canvas.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, n, n).data;
    const cls = new Uint8Array(n * n);
    for (let i = 0; i < n * n; i += 1) {
      const a = px[i * 4 + 3];
      cls[i] = a < 128 ? 0 : (lum(px[i * 4], px[i * 4 + 1], px[i * 4 + 2]) > threshold ? 2 : 1);
    }
    const seen = new Uint8Array(n * n);
    let count = 0;
    const stack = [];
    for (let s = 0; s < n * n; s += 1) {
      if (seen[s]) continue;
      seen[s] = 1; stack.push(s);
      let area = 0;
      while (stack.length) {
        const p = stack.pop(); area += 1;
        const x = p % n; const y = (p / n) | 0;
        const next = [x > 0 ? p - 1 : -1, x < n - 1 ? p + 1 : -1, y > 0 ? p - n : -1, y < n - 1 ? p + n : -1];
        next.forEach((m) => { if (m >= 0 && !seen[m] && cls[m] === cls[p]) { seen[m] = 1; stack.push(m); } });
      }
      if (area >= minArea) count += 1;
    }
    return count;
  };

  const analyse = (img, name) => {
    const c16 = rasterise(img, 16);
    const c32 = rasterise(img, 32);
    const c128 = rasterise(img, 128);
    const p16 = c16.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, 16, 16).data;
    const p128 = c128.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, 128, 128).data;

    // Bounding box and coverage of what is actually drawn.
    let minX = 128; let minY = 128; let maxX = -1; let maxY = -1; const opaque128 = [];
    for (let i = 0; i < 128 * 128; i += 1) {
      if (p128[i * 4 + 3] > 24) {
        const x = i % 128; const y = (i / 128) | 0;
        minX = Math.min(minX, x); maxX = Math.max(maxX, x); minY = Math.min(minY, y); maxY = Math.max(maxY, y);
      }
      if (p128[i * 4 + 3] >= 128) opaque128.push(lum(p128[i * 4], p128[i * 4 + 1], p128[i * 4 + 2]));
    }
    const drawn = maxX >= 0;
    const span = drawn ? Math.max(maxX - minX + 1, maxY - minY + 1) / 128 : 0;

    let alphaSum = 0;
    const nearLight = []; const nearDark = [];
    for (let i = 0; i < 256; i += 1) {
      const a = p16[i * 4 + 3];
      alphaSum += a;
      if (a >= 128) {
        const l = lum(p16[i * 4], p16[i * 4 + 1], p16[i * 4 + 2]);
        nearLight.push(Math.abs(l - lum(...TAB_LIGHT)) < 0.1);
        nearDark.push(Math.abs(l - lum(...TAB_DARK)) < 0.1);
      }
    }
    // A template image can only show what alpha encodes: the outer silhouette
    // plus transparent holes cut through it. Measure both at 128px, where the
    // anti-aliased rim of a rounded card no longer dominates.
    const solidMask = new Uint8Array(128 * 128);
    let solidArea = 0;
    for (let i = 0; i < 128 * 128; i += 1) if (p128[i * 4 + 3] >= 128) { solidMask[i] = 1; solidArea += 1; }
    const outside = new Uint8Array(128 * 128);
    const flood = [];
    for (let i = 0; i < 128; i += 1) [i, 127 * 128 + i, i * 128, i * 128 + 127].forEach((p) => { if (!solidMask[p] && !outside[p]) { outside[p] = 1; flood.push(p); } });
    while (flood.length) {
      const p = flood.pop(); const x = p % 128; const y = (p / 128) | 0;
      [x > 0 ? p - 1 : -1, x < 127 ? p + 1 : -1, y > 0 ? p - 128 : -1, y < 127 ? p + 128 : -1]
        .forEach((m) => { if (m >= 0 && !solidMask[m] && !outside[m]) { outside[m] = 1; flood.push(m); } });
    }
    let holes = 0;
    for (let i = 0; i < 128 * 128; i += 1) if (!solidMask[i] && !outside[i]) holes += 1;
    const boxArea = drawn ? (maxX - minX + 1) * (maxY - minY + 1) : 1;
    const solidity = solidArea / boxArea;
    const holeShare = solidArea ? holes / (solidArea + holes) : 0;
    const fade = (arr) => (arr.length ? arr.filter(Boolean).length / arr.length : 0);

    const threshold = otsu(opaque128);
    const before = regions(c128, threshold, 64);
    const after = regions(c16, threshold, 1);

    const verdicts = [];
    // 1. Menu-bar template: macOS keeps alpha and discards colour.
    if (!drawn) {
      verdicts.push({ level: 'fail', title: 'Nothing visible', text: 'Every pixel is transparent at this size.' });
    } else if (alphaSum / (256 * 255) > 0.97 || (solidity > 0.88 && holeShare < 0.02)) {
      verdicts.push({ level: 'fail', title: 'Menu bar: black square', text: 'The alpha is one solid block, so as a macOS template image everything inside it — colour, lines, lettering — disappears into a tinted square. Ship a separate transparent tray drawing.', link: '/reference/tray-icons/' });
    } else if (holeShare < 0.01) {
      verdicts.push({ level: 'warn', title: 'Menu bar: outline only', text: 'There is no transparent hole inside the shape, so a template image keeps the outline and nothing else. Cut one identifying feature clean through.', link: '/reference/tray-icons/' });
    } else {
      verdicts.push({ level: 'pass', title: 'Menu bar: shape survives', text: 'Alpha carries interior detail, so a template image keeps a readable silhouette.' });
    }
    // 2. Features that merge between 128px and 16px.
    const lost = Math.max(0, before - after);
    if (before <= 1) {
      verdicts.push({ level: 'warn', title: '16px: one flat shape', text: 'At 128px the icon is already a single region — there is no internal feature for a 16px reader to recognise.' });
    } else if (lost >= Math.max(2, Math.ceil(before * 0.4))) {
      verdicts.push({ level: 'fail', title: `16px: ${lost} of ${before} shapes merge`, text: 'Shapes that read at 128px close up at 16px. Thicken strokes, widen gaps, or drop detail until the 16px pixels still name the thing.' });
    } else if (lost > 0) {
      verdicts.push({ level: 'warn', title: `16px: ${lost} of ${before} shapes merge`, text: 'Most of the structure survives; check the zoom for the counter or gap that closed.' });
    } else {
      verdicts.push({ level: 'pass', title: `16px: all ${before} shapes survive`, text: 'Every region large enough to matter at 128px is still its own region at 16px.' });
    }
    // 3. Browser tab contrast, on both themes.
    const fl = fade(nearLight); const fd = fade(nearDark);
    if (fl > 0.6 || fd > 0.6) {
      const where = fl > fd ? 'light' : 'dark';
      verdicts.push({ level: 'warn', title: `Tab: fades on ${where} theme`, text: `${Math.round(Math.max(fl, fd) * 100)}% of the visible pixels sit within 10% of a ${where} tab bar's luminance. Add an edge or a contrasting card.` });
    } else {
      verdicts.push({ level: 'pass', title: 'Tab: reads on light and dark', text: 'The visible pixels stand apart from both light and dark browser chrome.' });
    }
    // 4. Framing: a tiny mark wastes the few pixels it has.
    if (drawn && span < 0.62) {
      verdicts.push({ level: 'warn', title: `Framing: ${Math.round(span * 16)}px of 16px used`, text: 'The artwork occupies a small part of the canvas, so it renders even smaller than it needs to. Trim the padding for favicons.' });
    } else if (drawn) {
      verdicts.push({ level: 'pass', title: `Framing: ${Math.round(span * 16)}px of 16px used`, text: 'The mark uses the canvas it is given.' });
    }

    return { name, img, c16, c32, c128, verdicts, before, after };
  };

  // ---------- painting ----------

  const toTemplate = (src, rgb) => {
    const n = src.width;
    const out = document.createElement('canvas');
    out.width = out.height = n;
    const ctx = out.getContext('2d');
    const d = src.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, n, n);
    for (let i = 0; i < d.data.length; i += 4) {
      // macOS template mode: colour is discarded, alpha is the shape.
      d.data[i] = rgb[0]; d.data[i + 1] = rgb[1]; d.data[i + 2] = rgb[2];
    }
    ctx.putImageData(d, 0, 0);
    return out;
  };

  const blit = (canvas, src) => {
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(src, 0, 0, canvas.width, canvas.height);
  };

  const drawZoom = (canvas, c16) => {
    blit(canvas, c16);
    const ctx = canvas.getContext('2d');
    const cell = canvas.width / 16;
    ctx.strokeStyle = 'rgba(255,244,232,.08)';
    ctx.lineWidth = 1;
    for (let i = 1; i < 16; i += 1) {
      ctx.beginPath(); ctx.moveTo(i * cell + 0.5, 0); ctx.lineTo(i * cell + 0.5, canvas.height); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, i * cell + 0.5); ctx.lineTo(canvas.width, i * cell + 0.5); ctx.stroke();
    }
  };

  const drawSilhouette = (canvas, c128) => {
    const d = c128.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, 128, 128);
    for (let i = 0; i < d.data.length; i += 4) {
      const v = d.data[i + 3] > 128 ? 255 : 0;
      d.data[i] = d.data[i + 1] = d.data[i + 2] = v; d.data[i + 3] = 255;
    }
    const tmp = document.createElement('canvas');
    tmp.width = tmp.height = 128;
    tmp.getContext('2d').putImageData(d, 0, 0);
    blit(canvas, tmp);
  };

  const paint = (r) => {
    original.src = r.img.src;
    drawZoom(zoom, r.c16);
    drawSilhouette(silhouette, r.c128);
    // Native-size slots: canvases whose backing store is the exact raster.
    qa('canvas[data-native]').forEach((canvas) => {
      const src = canvas.dataset.native === '32' ? r.c32 : r.c16;
      const mode = canvas.dataset.mode;
      blit(canvas, mode === 'template-light' ? toTemplate(src, [0, 0, 0])
        : mode === 'template-dark' ? toTemplate(src, [255, 255, 255]) : src);
    });
    verdictList.replaceChildren(...r.verdicts.map((v) => {
      const li = document.createElement('li');
      li.className = `xray-verdict is-${v.level}`;
      const mark = document.createElement('span');
      mark.className = 'xray-mark';
      mark.textContent = v.level === 'pass' ? '✓' : v.level === 'warn' ? '!' : '✕';
      mark.setAttribute('aria-label', v.level === 'pass' ? 'Pass' : v.level === 'warn' ? 'Warning' : 'Fail');
      const body = document.createElement('div');
      const h = document.createElement('strong'); h.textContent = v.title;
      const p = document.createElement('p'); p.textContent = v.text;
      body.append(h, p);
      if (v.link) {
        const a = document.createElement('a'); a.href = v.link; a.textContent = 'Why, and the fix →';
        body.append(a);
      }
      li.append(mark, body);
      return li;
    }));
    const fails = r.verdicts.filter((v) => v.level === 'fail').length;
    const warns = r.verdicts.filter((v) => v.level === 'warn').length;
    headline.textContent = fails ? `${fails} failure${fails > 1 ? 's' : ''} at 16px` : warns ? `Survives, with ${warns} warning${warns > 1 ? 's' : ''}` : 'Survives 16px';
    headline.dataset.level = fails ? 'fail' : warns ? 'warn' : 'pass';
  };

  // ---------- sharing ----------

  const card = (r) => {
    const c = document.createElement('canvas');
    c.width = 1200; c.height = 630;
    const ctx = c.getContext('2d');
    ctx.fillStyle = '#191a20'; ctx.fillRect(0, 0, 1200, 630);
    ctx.imageSmoothingEnabled = false;
    // 16px at 20x with grid.
    const z = document.createElement('canvas'); z.width = z.height = 320; drawZoom(z, r.c16);
    ctx.fillStyle = '#22232b'; ctx.fillRect(56, 120, 352, 352);
    ctx.drawImage(z, 72, 136);
    ctx.fillStyle = '#fff4e8';
    ctx.font = '800 46px Inter, system-ui, sans-serif';
    ctx.fillText(headline.textContent, 56, 84);
    ctx.font = '600 18px ui-monospace, Consolas, monospace';
    ctx.fillStyle = '#a5a6ad';
    ctx.fillText('16px · every pixel, 20× zoom', 56, 506);
    // Menu-bar contexts at 4x.
    const strip = (y, bg, rgb, label) => {
      ctx.fillStyle = bg; ctx.fillRect(448, y, 300, 72);
      ctx.drawImage(toTemplate(r.c16, rgb), 474, y + 4, 64, 64);
      ctx.fillStyle = rgb[0] ? '#fff4e8' : '#191a20';
      ctx.font = '600 16px ui-monospace, Consolas, monospace';
      ctx.fillText(label, 560, y + 42);
    };
    strip(120, '#dee1e6', [0, 0, 0], 'menu bar · light');
    strip(204, '#35363a', [255, 255, 255], 'menu bar · dark');
    ctx.fillStyle = '#dee1e6'; ctx.fillRect(448, 288, 146, 72); ctx.drawImage(r.c16, 489, 292, 64, 64);
    ctx.fillStyle = '#35363a'; ctx.fillRect(602, 288, 146, 72); ctx.drawImage(r.c16, 643, 292, 64, 64);
    ctx.fillStyle = '#a5a6ad'; ctx.fillText('tab · light / dark', 448, 384);
    // Verdicts.
    ctx.textBaseline = 'top';
    r.verdicts.forEach((v, i) => {
      const y = 120 + i * 62;
      ctx.fillStyle = v.level === 'pass' ? '#6ce0a0' : v.level === 'warn' ? '#ffc35a' : '#ff5a4f';
      ctx.font = '800 26px Inter, system-ui, sans-serif';
      ctx.fillText(v.level === 'pass' ? '✓' : v.level === 'warn' ? '!' : '✕', 788, y);
      ctx.fillStyle = '#fff4e8';
      ctx.font = '700 20px Inter, system-ui, sans-serif';
      ctx.fillText(v.title, 824, y + 3);
    });
    ctx.textBaseline = 'alphabetic';
    ctx.fillStyle = '#ff5a4f'; ctx.fillRect(56, 556, 1088, 2);
    ctx.fillStyle = '#fff4e8'; ctx.font = '700 22px Inter, system-ui, sans-serif';
    ctx.fillText('ai-iconflow.com/xray', 56, 596);
    ctx.fillStyle = '#a5a6ad'; ctx.font = '500 18px Inter, system-ui, sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText('IconFlow 16px X-ray · rendered in the browser, nothing uploaded', 1144, 596);
    return c;
  };

  const save = (href, filename) => {
    const link = document.createElement('a');
    link.href = href; link.download = filename;
    document.body.append(link); link.click(); link.remove();
  };

  q('[data-xray-card]')?.addEventListener('click', () => {
    if (!current) return;
    save(card(current).toDataURL('image/png'), '16px-xray.png');
    say('Saved 16px-xray.png — attach it to an issue, a PR, or a post.');
  });

  q('[data-xray-copy]')?.addEventListener('click', async () => {
    if (!current) return;
    const lines = [
      `16px X-ray: ${headline.textContent}`,
      ...current.verdicts.map((v) => `${v.level === 'pass' ? '[pass]' : v.level === 'warn' ? '[warn]' : '[FAIL]'} ${v.title}`),
      'Checked at https://ai-iconflow.com/xray/ — fix and ship with `pip install iconflow`.',
    ].join('\n');
    try { await navigator.clipboard.writeText(lines); say('Result copied as text.'); }
    catch { say(lines); }
  });

  // ---------- input ----------

  input.addEventListener('change', () => readFile(input.files?.[0]));
  ['dragenter', 'dragover'].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.add('is-over'); }));
  ['dragleave', 'drop'].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.remove('is-over'); }));
  drop.addEventListener('drop', (e) => readFile(e.dataTransfer?.files?.[0]));
  window.addEventListener('paste', (e) => {
    const file = Array.from(e.clipboardData?.files || [])[0];
    if (file) { readFile(file); return; }
    const text = e.clipboardData?.getData('text') || '';
    if (/^\s*<svg[\s>]/i.test(text) || /^\s*<\?xml/i.test(text)) {
      const url = sizedSvg(text);
      if (url) run(url, 'pasted SVG');
    }
  });
  // Dropping a file anywhere else on the page would navigate away from it.
  ['dragover', 'drop'].forEach((t) => window.addEventListener(t, (e) => { if (!drop.contains(e.target)) e.preventDefault(); }));

  qa('[data-xray-sample]').forEach((b) => b.addEventListener('click', async () => {
    try {
      const res = await fetch(b.dataset.xraySample);
      const text = await res.text();
      run(sizedSvg(text), b.dataset.label || 'sample');
    } catch { say('That sample could not be loaded.'); }
  }));
})();
