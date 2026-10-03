// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
// Icon Forge checks: the same small-size heuristics as the 16px X-ray, run on
// the live design. They are a coach, not the gate: the IconFlow CLI renders in
// a pinned Chromium and still requires a human review before `ship`.
import { toSvg, contrast } from './model.js';
import { fieldFromImage, nearest, decodeGrid, COLLISION_RADIUS } from './shapefield.js';
import collision from './collision.js';

// The generic forms every OS already owns, as 16px fields (CC0, derived from
// the CLI's index). A design inside the CLI's collision radius of one, with
// the same topology, is that form at 16px.
const GENERIC = collision.entries.map((e) => ({ ...e, field: { grid: decodeGrid(e.grid), components: e.components, holes: e.holes } }));
// The Forge's own "close" band. The nearest draft a human rejected in the
// casebook sat at 0.170 (docs/NEIGHBOURHOOD.md): outside the radius, and
// still the wrong shape. A coach should say so; the CLI's gate does not.
const NEAR = 0.2;


export function loadSvg(svg) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
  });
}

export function rasterise(img, size, canvas = document.createElement('canvas')) {
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  ctx.clearRect(0, 0, size, size);
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(img, 0, 0, size, size);
  return canvas;
}

const pixels = (canvas) => canvas.getContext('2d', { willReadFrequently: true })
  .getImageData(0, 0, canvas.width, canvas.height).data;
const lum = (r, g, b) => (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;

// iconflow/qa.py _luma_spread: std-dev of luminance after compositing on bg.
function lumaSpread(canvas, bg) {
  const px = pixels(canvas);
  const n = px.length / 4;
  const lum = new Float64Array(n);
  let mean = 0;
  for (let i = 0; i < n; i += 1) {
    const a = px[i * 4 + 3] / 255;
    const [r, g, b] = [0, 1, 2].map((c) => px[i * 4 + c] * a + bg[c] * (1 - a));
    lum[i] = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
    mean += lum[i];
  }
  mean /= n;
  let variance = 0;
  for (let i = 0; i < n; i += 1) variance += (lum[i] - mean) ** 2;
  return Math.sqrt(variance / n);
}

// Otsu threshold over the luminance of opaque pixels (as in the X-ray).
function otsu(values) {
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
}

// 4-connected regions of transparent / dark / light pixels at least `minArea`
// in size. `minArea` 64 at 128px is one whole pixel at 16px.
function regions(canvas, threshold, minArea) {
  const n = canvas.width;
  const px = pixels(canvas);
  const cls = new Uint8Array(n * n);
  for (let i = 0; i < n * n; i += 1) {
    cls[i] = px[i * 4 + 3] < 128 ? 0 : (lum(px[i * 4], px[i * 4 + 1], px[i * 4 + 2]) > threshold ? 2 : 1);
  }
  const seen = new Uint8Array(n * n);
  const stack = [];
  let count = 0;
  for (let s = 0; s < n * n; s += 1) {
    if (seen[s]) continue;
    seen[s] = 1; stack.push(s);
    let area = 0;
    while (stack.length) {
      const p = stack.pop(); area += 1;
      const x = p % n; const y = (p / n) | 0;
      if (x > 0 && !seen[p - 1] && cls[p - 1] === cls[p]) { seen[p - 1] = 1; stack.push(p - 1); }
      if (x < n - 1 && !seen[p + 1] && cls[p + 1] === cls[p]) { seen[p + 1] = 1; stack.push(p + 1); }
      if (y > 0 && !seen[p - n] && cls[p - n] === cls[p]) { seen[p - n] = 1; stack.push(p - n); }
      if (y < n - 1 && !seen[p + n] && cls[p + n] === cls[p]) { seen[p + n] = 1; stack.push(p + n); }
    }
    if (area >= minArea) count += 1;
  }
  return count;
}

// Alpha footprint of the mark alone at 128px: bounding box, solidity, and
// how much enclosed transparency (holes a template image can show) it has.
function footprint(canvas) {
  const n = canvas.width;
  const px = pixels(canvas);
  const solid = new Uint8Array(n * n);
  let area = 0; let minX = n; let minY = n; let maxX = -1; let maxY = -1;
  for (let i = 0; i < n * n; i += 1) {
    if (px[i * 4 + 3] >= 128) {
      solid[i] = 1; area += 1;
      const x = i % n; const y = (i / n) | 0;
      minX = Math.min(minX, x); maxX = Math.max(maxX, x); minY = Math.min(minY, y); maxY = Math.max(maxY, y);
    }
  }
  if (!area) return { drawn: false };
  const outside = new Uint8Array(n * n);
  const flood = [];
  for (let i = 0; i < n; i += 1) {
    [i, (n - 1) * n + i, i * n, i * n + n - 1].forEach((p) => {
      if (!solid[p] && !outside[p]) { outside[p] = 1; flood.push(p); }
    });
  }
  while (flood.length) {
    const p = flood.pop(); const x = p % n; const y = (p / n) | 0;
    [x > 0 ? p - 1 : -1, x < n - 1 ? p + 1 : -1, y > 0 ? p - n : -1, y < n - 1 ? p + n : -1]
      .forEach((m) => { if (m >= 0 && !solid[m] && !outside[m]) { outside[m] = 1; flood.push(m); } });
  }
  let holes = 0;
  for (let i = 0; i < n * n; i += 1) if (!solid[i] && !outside[i]) holes += 1;
  const box = (maxX - minX + 1) * (maxY - minY + 1);
  return {
    drawn: true,
    span: Math.max(maxX - minX + 1, maxY - minY + 1) / n,
    margin: Math.min(minX, minY, n - 1 - maxX, n - 1 - maxY) / n,
    solidity: area / box,
    holeShare: holes / (area + holes),
  };
}

// Returns { verdicts, score, total }. Each verdict: { key, level, title, text }.
export async function runChecks(design, budget) {
  const visible = design.pieces.filter((p) => !p.cut);
  if (!visible.length) {
    return {
      score: 0,
      total: 6,
      neighbours: [],
      field: null,
      verdicts: [{ key: 'empty', level: 'warn', title: 'The board is empty', text: 'Add a piece from the shelf to start.' }],
    };
  }
  const [full, mark] = await Promise.all([loadSvg(toSvg(design)), loadSvg(toSvg(design, { mode: 'mark' }))]);
  const c128 = rasterise(full, 128);
  const c16 = rasterise(full, 16);
  const m128 = rasterise(mark, 128);
  const verdicts = [];

  // 1. Legibility: regions that matter at 128px must still exist at 16px.
  const p128 = pixels(c128);
  const opaque = [];
  for (let i = 0; i < 128 * 128; i += 1) {
    if (p128[i * 4 + 3] >= 128) opaque.push(lum(p128[i * 4], p128[i * 4 + 1], p128[i * 4 + 2]));
  }
  const threshold = otsu(opaque);
  const before = regions(c128, threshold, 64);
  const after = regions(c16, threshold, 1);
  const lost = Math.max(0, before - after);
  if (before <= 1) {
    verdicts.push({ key: 'legible', level: 'warn', title: '16px: one flat shape', text: 'Everything reads as a single region. Give the mark an inner feature: a contrasting piece or a cut.' });
  } else if (lost >= Math.max(2, Math.ceil(before * 0.4))) {
    verdicts.push({ key: 'legible', level: 'fail', title: `16px: ${lost} of ${before} shapes merge`, text: 'Gaps that read when large close up at 16px. Make pieces bigger, spread them apart, or remove one.' });
  } else if (lost > 0) {
    verdicts.push({ key: 'legible', level: 'warn', title: `16px: ${lost} of ${before} shapes merge`, text: 'Most of it survives. Look at the 16px tile for the gap that closed.' });
  } else {
    verdicts.push({ key: 'legible', level: 'pass', title: `16px: all ${before} shapes survive`, text: 'Every region that matters at 128px is still its own region at 16px.' });
  }

  // 2. Tray: a template image keeps alpha only.
  const fp = footprint(m128);
  if (fp.solidity > 0.88 && fp.holeShare < 0.02) {
    verdicts.push({ key: 'tray', level: 'warn', title: 'Tray: a solid blob', text: 'Without colour the mark is one filled shape. A cut piece gives the menu-bar version an inside.' });
  } else if (fp.holeShare < 0.01 && fp.solidity > 0.6) {
    verdicts.push({ key: 'tray', level: 'warn', title: 'Tray: outline only', text: 'No transparent hole inside the mark, so a template image keeps the outline and nothing else.' });
  } else {
    verdicts.push({ key: 'tray', level: 'pass', title: 'Tray: silhouette has an inside', text: 'With colour removed the mark still has openings, so it reads in a menu bar.' });
  }

  // 3. Framing: big enough to use its pixels, clear of the edge that launchers crop.
  if (fp.span < 0.5) {
    verdicts.push({ key: 'frame', level: 'warn', title: `Frame: mark spans ${Math.round(fp.span * 100)}%`, text: 'A small mark wastes the 16 pixels it has. Aim for about 60–80% of the frame.' });
  } else if (fp.margin < 0.06 && design.card.shape !== 'none') {
    verdicts.push({ key: 'frame', level: 'warn', title: 'Frame: touches the card edge', text: 'Rounded and maskable launchers crop the outer edge. Pull the mark inside the grid.' });
  } else {
    verdicts.push({ key: 'frame', level: 'pass', title: `Frame: mark spans ${Math.round(fp.span * 100)}%`, text: 'Big enough to use its pixels and clear of the cropped edge.' });
  }

  // 4. Contrast. First the CLI's own rule (iconflow/qa.py _luma_spread):
  // composite the render on a background and ask whether anything is left
  // but a flat blob. Then the Forge's: no piece may vanish into its card.
  const cliContrast = [
    ['white', c16, [255, 255, 255], 0.06, 16],
    ['dark', c16, [11, 13, 18], 0.06, 16],
    ['mid-gray', rasterise(full, 32), [128, 128, 128], 0.04, 32],
  ].filter(([, canvas, bg, floor]) => lumaSpread(canvas, bg) < floor);
  const faint = design.card.shape === 'none' ? [] : visible.filter((p) => contrast(p.color, design.card.color) < 1.6);
  if (cliContrast.length) {
    const [where, , , , size] = cliContrast[0];
    verdicts.push({ key: 'contrast', level: 'warn', title: `Contrast: weak on ${where} at ${size}px`, text: `Composited on ${where}, the ${size}px render is nearly one flat tone — the same warning \`iconflow check\` gives. Add a card, an outline in a contrasting colour, or a darker or lighter piece.` });
  } else if (faint.length) {
    verdicts.push({ key: 'contrast', level: 'warn', title: `Contrast: ${faint.length} piece${faint.length > 1 ? 's' : ''} vanish into the card`, text: 'A piece close to the card colour disappears at small sizes. Change its colour or the card.' });
  } else {
    verdicts.push({ key: 'contrast', level: 'pass', title: 'Contrast: reads on white, dark and grey', text: 'Every piece stands off its card, and the render keeps its contrast on light, dark and mid-grey backgrounds.' });
  }

  // 5. Neighbourhood: is this already a form every system owns?
  const field = fieldFromImage(full);
  const neighbours = nearest(field, GENERIC, 3);
  const top = neighbours[0];
  const d = top ? top.distance.toFixed(2) : '';
  const name = top ? `“${top.entry.title}”` : '';
  if (top && top.within) {
    verdicts.push({ key: 'neighbours', level: 'fail', title: `16px: reads as ${name}`, text: `At 16px this is the same shape as the generic form ${name} (distance ${d}, radius ${COLLISION_RADIUS}, same pieces and holes). Every system already owns that form. Change the silhouette, not the colour.` });
  } else if (top && top.distance <= NEAR) {
    verdicts.push({ key: 'neighbours', level: 'warn', title: `16px: close to ${name}`, text: `Distance ${d} from the generic form ${name}${top.sameTopology ? '' : ', with different pieces or holes'}. Outside the CLI’s radius, but close enough that a person may read it that way.` });
  } else {
    verdicts.push({ key: 'neighbours', level: 'pass', title: '16px: its own shape', text: `No generic form within ${NEAR}; the nearest is ${name} at ${d}. Not a clearance check — a person still judges distinctiveness.` });
  }

  // 6. Simplicity: the brief's piece budget.
  const used = design.pieces.length;
  if (used > budget) {
    verdicts.push({ key: 'budget', level: 'fail', title: `Budget: ${used} of ${budget} pieces`, text: 'Over the brief’s budget. Icons that survive 16px are usually fewer, bolder pieces.' });
  } else {
    verdicts.push({ key: 'budget', level: 'pass', title: `Budget: ${used} of ${budget} pieces`, text: 'Within the brief’s budget.' });
  }

  return { verdicts, field, neighbours, score: verdicts.filter((v) => v.level === 'pass').length, total: verdicts.length };
}
