// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
// Icon Forge model: the piece list is the single source of truth. The 3D
// workbench and the SVG master are both projections of it, so the thing you
// build is exactly the thing you export. No DOM and no three.js in here.

export const GRID = 1024;
export const SNAP = 16;
export const TYPES = ['circle', 'block', 'wedge', 'ring', 'arc', 'bar'];
// Round pieces have one size; the inspector hides their height.
export const ROUND = new Set(['circle', 'ring', 'arc']);
export const PALETTE = ['#fff4e8', '#191a20', '#ff5a4f', '#ffb547', '#6ce0a0', '#4d8dff', '#a46bff', '#2e3a55'];
export const CARD_SHAPES = ['squircle', 'circle', 'none'];
export const RING_INNER = 0.6;
export const DEFAULT_SIZE = {
  circle: [260, 260], block: [320, 320], wedge: [340, 300],
  ring: [400, 400], arc: [440, 440], bar: [420, 112],
};
const MAX_PIECES = 24;
const HEX = /^#[0-9a-f]{6}$/;

// Worked examples. Each one passes every Forge check, including the
// neighbourhood: none is a generic form at 16px. They are there to show what
// "few, bold pieces with one idea" looks like, not to be shipped as-is.
const P = (type, x, y, w, h, rot, color, layer, cut = false) => ({ type, x, y, w, h, rot, color, layer, cut });
export const SEEDS = {
  // A cat asleep, curled into a crescent: a focus timer without a clock.
  nap: {
    card: { shape: 'squircle', color: '#2e3a55' },
    pieces: [
      P('circle', 512, 576, 640, 640, 0, '#ffb547', 0),
      P('circle', 704, 496, 448, 448, 0, '#000000', 1, true),
      P('wedge', 304, 336, 176, 192, 340, '#ffb547', 2),
      P('wedge', 448, 288, 176, 192, 15, '#ffb547', 2),
      P('circle', 768, 272, 112, 112, 0, '#fff4e8', 3),
    ],
  },
  // Sun, sky and horizon: one condition, read in one glance.
  tide: {
    card: { shape: 'squircle', color: '#4d8dff' },
    pieces: [
      P('arc', 512, 640, 768, 768, 0, '#ffb547', 0),
      P('circle', 512, 640, 272, 272, 0, '#ffb547', 0),
      P('bar', 512, 688, 832, 128, 0, '#fff4e8', 1),
    ],
  },
  // Two halves passing a message across: conversation without a bubble.
  relay: {
    card: { shape: 'squircle', color: '#191a20' },
    pieces: [
      P('arc', 432, 448, 544, 544, 270, '#ff5a4f', 0),
      P('arc', 592, 592, 544, 544, 90, '#6ce0a0', 0),
      P('circle', 512, 512, 144, 144, 0, '#fff4e8', 1),
    ],
  },
  // A gauge with no card: a menu-bar mark whose silhouette is the whole idea.
  dial: {
    card: { shape: 'none', color: '#2e3a55' },
    pieces: [
      P('arc', 512, 640, 832, 832, 0, '#6ce0a0', 0),
      P('bar', 624, 528, 432, 112, 315, '#6ce0a0', 0),
      P('circle', 512, 640, 224, 224, 0, '#6ce0a0', 0),
    ],
  },
};

export function seed(name) {
  return SEEDS[name] ? sanitize(SEEDS[name]) : null;
}

export function example() {
  return seed('nap');
}

export function blank() {
  return { card: { shape: 'squircle', color: '#2e3a55' }, pieces: [] };
}

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const num = (v, lo, hi, fallback) => (Number.isFinite(+v) ? clamp(Math.round(+v), lo, hi) : fallback);

// Everything that arrives from outside (share link, local storage, an
// imported SVG) passes through here, so a hostile payload can only ever
// become a bounded list of known shapes.
export function sanitize(raw) {
  if (!raw || typeof raw !== 'object') return null;
  const card = raw.card && typeof raw.card === 'object' ? raw.card : {};
  const out = {
    card: {
      shape: CARD_SHAPES.includes(card.shape) ? card.shape : 'squircle',
      color: HEX.test(card.color) ? card.color : '#2e3a55',
    },
    pieces: [],
  };
  const list = Array.isArray(raw.pieces) ? raw.pieces.slice(0, MAX_PIECES) : [];
  list.forEach((p, i) => {
    if (!p || !TYPES.includes(p.type)) return;
    const w = num(p.w, 32, GRID, 256);
    out.pieces.push({
      id: i + 1,
      type: p.type,
      x: num(p.x, 0, GRID, 512),
      y: num(p.y, 0, GRID, 512),
      w,
      h: ROUND.has(p.type) ? w : num(p.h, 32, GRID, 256),
      rot: ((num(p.rot, -720, 720, 0) % 360) + 360) % 360,
      color: HEX.test(p.color) ? p.color : PALETTE[0],
      layer: num(p.layer, 0, 40, 0),
      cut: p.cut === true,
    });
  });
  return out;
}

export function nextId(design) {
  return design.pieces.reduce((m, p) => Math.max(m, p.id), 0) + 1;
}

export function ordered(design) {
  // Stable: equal layers keep insertion order, which is also the 3D order.
  return design.pieces.map((p, i) => [p, i]).sort((a, b) => a[0].layer - b[0].layer || a[1] - b[1]).map(([p]) => p);
}

// ---------- SVG ----------
const r1 = (v) => Math.round(v * 10) / 10;

export function pieceSvg(p, fill) {
  const t = `transform="translate(${p.x} ${p.y})${p.rot ? ` rotate(${p.rot})` : ''}"`;
  const hw = p.w / 2;
  const hh = p.h / 2;
  switch (p.type) {
    case 'circle':
      return `<circle ${t} r="${r1(hw)}" fill="${fill}"/>`;
    case 'block':
      return `<rect ${t} x="${r1(-hw)}" y="${r1(-hh)}" width="${p.w}" height="${p.h}" rx="${r1(Math.min(hw, hh) * 0.22)}" fill="${fill}"/>`;
    case 'bar':
      return `<rect ${t} x="${r1(-hw)}" y="${r1(-hh)}" width="${p.w}" height="${p.h}" rx="${r1(Math.min(hw, hh))}" fill="${fill}"/>`;
    case 'wedge':
      return `<path ${t} d="M0 ${r1(-hh)}L${r1(hw)} ${r1(hh)}H${r1(-hw)}Z" fill="${fill}"/>`;
    case 'ring': {
      const ri = r1(hw * RING_INNER);
      const ro = r1(hw);
      return `<path ${t} fill-rule="evenodd" fill="${fill}" d="M${-ro} 0a${ro} ${ro} 0 1 0 ${2 * ro} 0a${ro} ${ro} 0 1 0 ${-2 * ro} 0ZM${-ri} 0a${ri} ${ri} 0 1 0 ${2 * ri} 0a${ri} ${ri} 0 1 0 ${-2 * ri} 0Z"/>`;
    }
    case 'arc': {
      // The top half of a ring: an arch, a rainbow, a handle, a wifi band.
      const ri = r1(hw * RING_INNER);
      const ro = r1(hw);
      return `<path ${t} fill="${fill}" d="M${-ro} 0A${ro} ${ro} 0 0 1 ${ro} 0H${ri}A${ri} ${ri} 0 0 0 ${-ri} 0Z"/>`;
    }
    default:
      return '';
  }
}

export function cardSvg(card) {
  if (card.shape === 'none') return '';
  if (card.shape === 'circle') return `<circle cx="512" cy="512" r="512" fill="${card.color}"/>`;
  return `<rect width="1024" height="1024" rx="224" fill="${card.color}"/>`;
}

// mode: 'full' (the master), 'mark' (no card), 'silhouette' (mark, black).
// A cut piece masks every piece below it, never the card, so cutting reads
// as a hole in the mark rather than a hole in the app icon.
export function toSvg(design, { mode = 'full', metadata = false } = {}) {
  let body = '';
  let defs = '';
  let cuts = 0;
  for (const p of ordered(design)) {
    if (p.cut) {
      cuts += 1;
      defs += `<mask id="cut${cuts}" maskUnits="userSpaceOnUse" x="0" y="0" width="1024" height="1024"><rect width="1024" height="1024" fill="#fff"/>${pieceSvg(p, '#000')}</mask>`;
      body = `<g mask="url(#cut${cuts})">${body}</g>`;
    } else {
      body += pieceSvg(p, mode === 'silhouette' ? '#000' : p.color);
    }
  }
  const card = mode === 'full' ? cardSvg(design.card) : '';
  const meta = metadata
    ? `\n  <metadata id="iconflow-forge">${JSON.stringify(design)}</metadata>` : '';
  const title = metadata ? '\n  <title>Icon Forge master</title>' : '';
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">${title}${meta}${defs ? `\n  <defs>${defs}</defs>` : ''}${card ? `\n  ${card}` : ''}\n  ${body}\n</svg>\n`;
}

export function fromSvgText(text) {
  const match = /<metadata id="iconflow-forge">([\s\S]*?)<\/metadata>/.exec(text || '');
  if (!match) return null;
  try { return sanitize(JSON.parse(match[1])); } catch { return null; }
}

// ---------- share links: the design rides in the URL fragment ----------
// A fragment is never sent to the server, so a share link is the design
// itself, not a pointer to something stored somewhere.
const KEYS = ['type', 'x', 'y', 'w', 'h', 'rot', 'color', 'layer', 'cut'];

export function encode(design) {
  const compact = {
    c: [design.card.shape, design.card.color],
    p: design.pieces.map((p) => KEYS.map((k) => (k === 'cut' ? (p.cut ? 1 : 0) : p[k]))),
  };
  const bytes = new TextEncoder().encode(JSON.stringify(compact));
  let bin = '';
  bytes.forEach((b) => { bin += String.fromCharCode(b); });
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

export function decode(text) {
  try {
    const bin = atob(text.replace(/-/g, '+').replace(/_/g, '/'));
    const bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0));
    const compact = JSON.parse(new TextDecoder().decode(bytes));
    return sanitize({
      card: { shape: compact.c?.[0], color: compact.c?.[1] },
      pieces: (compact.p || []).map((row) => Object.fromEntries(KEYS.map((k, i) => [k, k === 'cut' ? row[i] === 1 : row[i]]))),
    });
  } catch {
    return null;
  }
}

// ---------- colour ----------
export function luminance(hex) {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}

export function contrast(a, b) {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}
