// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
// A browser port of iconflow/shapefield.py: the deterministic 16px shape
// descriptor and the distance between two of them. Same constants, same
// figure policy, same topology rules, so the Forge's neighbourhood answer is
// the CLI's answer. tests/test_website.py pins the constants against the
// Python module; the browser parity test renders the collision set through
// this file and compares it with the checked-in index.

export const GRID = 16;
export const SAMPLE_SIZE = 64;
const BLOCK = SAMPLE_SIZE / GRID;
const CELL_STEPS = BLOCK * BLOCK;
const MIN_REGION = BLOCK * BLOCK;
const MIN_HOLE_WIDTH = 5;
const GRID_ALPHABET = '0123456789abcdefg';
const FOOTPRINT_ALPHA = 24;
const SOLID_ALPHA = 128;
const MIN_FIGURE_SHARE = 0.10;
const MAX_FIGURE_EDGE = 0.05;
const CARD_COVERAGE = 0.75;
const CARD_FIGURE_EDGE = 0.20;
export const COLLISION_RADIUS = 0.12;

export function decodeGrid(encoded) {
  return Array.from(encoded, (c) => GRID_ALPHABET.indexOf(c) / CELL_STEPS);
}

// ladder.otsu_threshold over a 256-bin histogram.
function otsu(histogram) {
  let total = 0; let sumAll = 0;
  histogram.forEach((count, i) => { total += count; sumAll += i * count; });
  if (!total) return 128;
  let sumBelow = 0; let weightBelow = 0; let best = -1; let threshold = 128;
  for (let i = 0; i < 256; i += 1) {
    weightBelow += histogram[i];
    if (weightBelow === 0) continue;
    const weightAbove = total - weightBelow;
    if (weightAbove === 0) break;
    sumBelow += i * histogram[i];
    const between = weightBelow * weightAbove * ((sumBelow / weightBelow) - ((sumAll - sumBelow) / weightAbove)) ** 2;
    if (between > best) { best = between; threshold = i; }
  }
  return threshold;
}

// Connected regions of truthy pixels, as arrays of flat indices.
function regions(solid, n, eight) {
  const seen = new Uint8Array(n * n);
  const out = [];
  const steps = eight
    ? [[-1, -1], [0, -1], [1, -1], [-1, 0], [1, 0], [-1, 1], [0, 1], [1, 1]]
    : [[0, -1], [-1, 0], [1, 0], [0, 1]];
  for (let start = 0; start < n * n; start += 1) {
    if (seen[start] || !solid[start]) continue;
    seen[start] = 1;
    const queue = [start];
    for (let head = 0; head < queue.length; head += 1) {
      const i = queue[head]; const x = i % n; const y = (i / n) | 0;
      for (const [dx, dy] of steps) {
        const nx = x + dx; const ny = y + dy;
        if (nx < 0 || ny < 0 || nx >= n || ny >= n) continue;
        const j = ny * n + nx;
        if (solid[j] && !seen[j]) { seen[j] = 1; queue.push(j); }
      }
    }
    out.push(queue);
  }
  return out;
}

function exteriorGround(solid, n) {
  const outside = new Uint8Array(n * n);
  const queue = [];
  for (let i = 0; i < n * n; i += 1) {
    const x = i % n; const y = (i / n) | 0;
    if ((x === 0 || y === 0 || x === n - 1 || y === n - 1) && !solid[i]) { outside[i] = 1; queue.push(i); }
  }
  for (let head = 0; head < queue.length; head += 1) {
    const i = queue[head]; const x = i % n; const y = (i / n) | 0;
    for (const [nx, ny] of [[x - 1, y], [x + 1, y], [x, y - 1], [x, y + 1]]) {
      if (nx < 0 || ny < 0 || nx >= n || ny >= n) continue;
      const j = ny * n + nx;
      if (!solid[j] && !outside[j]) { outside[j] = 1; queue.push(j); }
    }
  }
  return outside;
}

// figure_of: the recognisable shape of one 64px RGBA render (Uint8ClampedArray).
export function figureOf(rgba) {
  const n = SAMPLE_SIZE;
  const footprint = new Uint8Array(n * n);
  const solid = new Uint8Array(n * n);
  const luma = new Uint8Array(n * n);
  const histogram = new Array(256).fill(0);
  let anyFoot = false; let solidTotal = 0;
  for (let i = 0; i < n * n; i += 1) {
    const a = rgba[i * 4 + 3];
    // PIL's RGB -> L: ITU-R 601-2 luma, fixed point.
    luma[i] = (rgba[i * 4] * 19595 + rgba[i * 4 + 1] * 38470 + rgba[i * 4 + 2] * 7471 + 0x8000) >> 16;
    if (a >= FOOTPRINT_ALPHA) { footprint[i] = 1; anyFoot = true; }
    if (a >= SOLID_ALPHA) { solid[i] = 1; solidTotal += 1; histogram[luma[i]] += 1; }
  }
  if (!anyFoot) return new Uint8Array(n * n);
  if (!solidTotal) return footprint;

  const threshold = otsu(histogram);
  const dark = new Uint8Array(n * n);
  const light = new Uint8Array(n * n);
  for (let i = 0; i < n * n; i += 1) {
    if (!solid[i]) continue;
    if (luma[i] <= threshold) dark[i] = 1; else light[i] = 1;
  }
  const outside = exteriorGround(solid, n);
  const edge = new Uint8Array(n * n);
  let edgeTotal = 0;
  for (let i = 0; i < n * n; i += 1) {
    if (!solid[i]) continue;
    const x = i % n; const y = (i / n) | 0;
    if (x === 0 || y === 0 || x === n - 1 || y === n - 1
      || outside[i - 1] || outside[i + 1] || outside[i - n] || outside[i + n]) {
      edge[i] = 1; edgeTotal += 1;
    }
  }
  edgeTotal = edgeTotal || 1;
  const maxReach = solidTotal / (n * n) >= CARD_COVERAGE ? CARD_FIGURE_EDGE : MAX_FIGURE_EDGE;
  const enclosed = (cls) => {
    let count = 0; let reach = 0;
    for (let i = 0; i < n * n; i += 1) if (cls[i]) { count += 1; if (edge[i]) reach += 1; }
    return count / solidTotal >= MIN_FIGURE_SHARE && reach / edgeTotal <= maxReach;
  };
  const candidates = [dark, light].filter(enclosed);
  return candidates.length === 1 ? candidates[0] : footprint;
}

// field_from_mask: occupancy grid plus pieces, holes, coverage, aspect.
export function fieldFromMask(figure) {
  const n = SAMPLE_SIZE;
  const grid = [];
  for (let cy = 0; cy < GRID; cy += 1) {
    for (let cx = 0; cx < GRID; cx += 1) {
      let count = 0;
      for (let y = cy * BLOCK; y < (cy + 1) * BLOCK; y += 1) {
        for (let x = cx * BLOCK; x < (cx + 1) * BLOCK; x += 1) if (figure[y * n + x]) count += 1;
      }
      grid.push(count / CELL_STEPS);
    }
  }
  const pieces = regions(figure, n, true).filter((r) => r.length >= MIN_REGION).length;

  // Holes: ground that survives a 5x5 erosion, 4-connected, off the border.
  const r = (MIN_HOLE_WIDTH - 1) / 2;
  const deep = new Uint8Array(n * n);
  for (let y = 0; y < n; y += 1) {
    for (let x = 0; x < n; x += 1) {
      let ground = 1;
      for (let dy = -r; dy <= r && ground; dy += 1) {
        const yy = Math.min(n - 1, Math.max(0, y + dy));
        for (let dx = -r; dx <= r; dx += 1) {
          const xx = Math.min(n - 1, Math.max(0, x + dx));
          if (figure[yy * n + xx]) { ground = 0; break; }
        }
      }
      deep[y * n + x] = ground;
    }
  }
  let holes = 0;
  for (const region of regions(deep, n, false)) {
    if (region.length < MIN_REGION) continue;
    const touches = region.some((i) => { const x = i % n; const y = (i / n) | 0; return x === 0 || y === 0 || x === n - 1 || y === n - 1; });
    if (!touches) holes += 1;
  }

  let ink = 0; let minX = n; let maxX = -1; let minY = n; let maxY = -1;
  for (let i = 0; i < n * n; i += 1) {
    if (!figure[i]) continue;
    ink += 1;
    const x = i % n; const y = (i / n) | 0;
    minX = Math.min(minX, x); maxX = Math.max(maxX, x); minY = Math.min(minY, y); maxY = Math.max(maxY, y);
  }
  const round = (v, d) => Math.round(v * 10 ** d) / 10 ** d;
  return {
    grid,
    components: pieces,
    holes,
    coverage: round(ink / (n * n), 4),
    aspect: ink ? round((maxX - minX + 1) / (maxY - minY + 1), 3) : 0,
  };
}

export function fieldFromImage(img) {
  const canvas = document.createElement('canvas');
  canvas.width = SAMPLE_SIZE;
  canvas.height = SAMPLE_SIZE;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  ctx.drawImage(img, 0, 0, SAMPLE_SIZE, SAMPLE_SIZE);
  return fieldFromMask(figureOf(ctx.getImageData(0, 0, SAMPLE_SIZE, SAMPLE_SIZE).data));
}

const bucketPieces = (c) => Math.min(Math.max(c, 1), 3);
const bucketHoles = (h) => Math.min(Math.max(h, 0), 2);

export function separation(a, b) {
  let total = 0; let diff = 0;
  for (let i = 0; i < a.grid.length; i += 1) { total += a.grid[i] + b.grid[i]; diff += Math.abs(a.grid[i] - b.grid[i]); }
  return {
    distance: total > 0 ? diff / total : 0,
    sameTopology: bucketPieces(a.components) === bucketPieces(b.components)
      && bucketHoles(a.holes) === bucketHoles(b.holes),
  };
}

// Nearest entries of a set, each { entry, distance, sameTopology, within }.
export function nearest(field, entries, count = 3, radius = COLLISION_RADIUS) {
  return entries
    .map((entry) => ({ entry, ...separation(field, entry.field) }))
    .map((hit) => ({ ...hit, within: hit.distance <= radius && hit.sameTopology }))
    .sort((a, b) => a.distance - b.distance)
    .slice(0, count);
}
