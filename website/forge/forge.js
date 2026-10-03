// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
// Icon Forge: build an icon from 3D pieces, stamp it to one SVG master.
// Everything runs in the visitor's browser. The design lives in memory, in
// localStorage, and in a share link's #fragment; nothing is sent anywhere.
import {
  GRID, SNAP, PALETTE, ROUND, DEFAULT_SIZE,
  example, blank, sanitize, nextId, ordered, toSvg, fromSvgText, encode, decode, contrast,
} from './model.js';
import { runChecks, loadSvg, rasterise } from './checks.js';

const root = document.querySelector('[data-forge]');
const q = (sel) => root.querySelector(sel);
const qa = (sel) => Array.from(root.querySelectorAll(sel));
const STORE = 'iconflow-forge:v1';
const HISTORY = 80;

let design = example();
let selectedId = null;
let briefBudget = 8;
const past = [];
const future = [];

// ---------- persistence ----------
function restore() {
  const hash = /^#d=([\w-]+)$/.exec(window.location.hash);
  if (hash) {
    const shared = decode(hash[1]);
    if (shared) return { design: shared };
  }
  try {
    const saved = JSON.parse(window.localStorage.getItem(STORE) || 'null');
    const d = saved && sanitize(saved.design);
    if (d) return { design: d, brief: saved.brief };
  } catch { /* private mode or blocked storage: start fresh */ }
  return {};
}
function persist() {
  try {
    window.localStorage.setItem(STORE, JSON.stringify({ design, brief: q('[data-forge-brief]').value }));
  } catch { /* not fatal */ }
}

// ---------- history ----------
const snapshot = () => JSON.stringify({ design, selectedId });
function record() {
  past.push(snapshot());
  if (past.length > HISTORY) past.shift();
  future.length = 0;
}
function travel(from, to) {
  if (!from.length) return;
  to.push(snapshot());
  const state = JSON.parse(from.pop());
  design = state.design;
  selectedId = state.selectedId;
  render();
}
function change(fn) {
  record();
  fn();
  render();
}

const selected = () => design.pieces.find((p) => p.id === selectedId) || null;
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const snap = (v) => Math.round(v / SNAP) * SNAP;

// ---------- the 3D workbench (optional: the panel works without it) ----------
let bench = null;
const stage = q('[data-forge-stage]');

async function startWorkbench() {
  try {
    const { createWorkbench } = await import('./scene.js');
    bench = createWorkbench(stage, {
      pick(id) { if (id !== selectedId) { selectedId = id; render(); } },
      dragStart() { record(); },
      dragMove(id, x, y, fine) {
        const p = design.pieces.find((piece) => piece.id === id);
        if (!p) return;
        p.x = clamp(Math.round(fine ? x : snap(x)), 0, GRID);
        p.y = clamp(Math.round(fine ? y : snap(y)), 0, GRID);
        render();
      },
      dragEnd() {},
    });
  } catch (error) {
    console.warn('Icon Forge: 3D workbench unavailable', error);
    bench = null;
  }
  if (!bench) q('[data-forge-nogl]').hidden = false;
  render();
}

// ---------- preview + checks ----------
let previewTicket = 0;
let checkTimer = 0;
function preview() {
  const ticket = ++previewTicket;
  const master = toSvg(design);
  q('[data-forge-master]').src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(master)}`;
  Promise.all([loadSvg(master), loadSvg(toSvg(design, { mode: 'silhouette' }))]).then(([full, sil]) => {
    if (ticket !== previewTicket) return;
    qa('canvas[data-px]').forEach((canvas) => {
      rasterise(canvas.dataset.mode === 'silhouette' ? sil : full, +canvas.dataset.px, canvas);
    });
  }).catch(() => {});
  clearTimeout(checkTimer);
  checkTimer = setTimeout(() => {
    runChecks(design, briefBudget).then((result) => {
      if (ticket === previewTicket) showChecks(result);
    }).catch(() => {});
  }, 140);
}

function showChecks({ verdicts, score, total }) {
  const list = q('[data-forge-checks]');
  list.replaceChildren(...verdicts.map((v) => {
    const li = document.createElement('li');
    li.className = `is-${v.level}`;
    const title = document.createElement('strong');
    title.textContent = v.title;
    const text = document.createElement('span');
    text.textContent = v.text;
    li.append(title, text);
    return li;
  }));
  const label = q('[data-forge-score-text]');
  const ready = score === total && total > 0 && design.pieces.length > 0;
  label.textContent = ready
    ? label.dataset.labelReady
    : (label.dataset.labelScore || '{score} of {total}').replace('{score}', score).replace('{total}', total);
  q('[data-forge-score]').classList.toggle('is-ready', ready);
  const stars = q('[data-forge-stars]');
  stars.replaceChildren(...Array.from({ length: total }, (_, i) => {
    const s = document.createElement('i');
    if (i < score) s.className = 'on';
    return s;
  }));
}

// ---------- panel ----------
const typeName = (type) => root.querySelector(`[data-add="${type}"] span:last-child`)?.textContent || type;

function swatches(host, current, onPick) {
  host.replaceChildren(...PALETTE.map((color) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'forge-swatch';
    b.dataset.color = color;
    b.setAttribute('aria-label', color);
    b.setAttribute('aria-pressed', String(color === current));
    b.style.setProperty('--swatch', color);
    b.addEventListener('click', () => onPick(color));
    return b;
  }));
}

function renderInspector() {
  const p = selected();
  q('[data-forge-none]').hidden = !!p;
  q('[data-forge-fields]').hidden = !p;
  if (!p) return;
  ['w', 'h', 'rot'].forEach((field) => {
    const input = q(`[data-field="${field}"]`);
    if (document.activeElement !== input) input.value = p[field];
    q(`[data-out="${field}"]`).textContent = field === 'rot' ? `${p.rot}°` : p[field];
  });
  q('[data-only-flat]').hidden = ROUND.has(p.type);
  q('[data-action="cut"]').setAttribute('aria-pressed', String(p.cut));
  swatches(q('[data-forge-swatches]'), p.color, (color) => change(() => { p.color = color; }));
}

function renderLayers() {
  const list = q('[data-forge-layers]');
  const layerLabel = list.dataset.labelLayer || 'layer {n}';
  const cutLabel = list.dataset.labelCut || 'cut';
  list.replaceChildren(...ordered(design).reverse().map((p) => {
    const li = document.createElement('li');
    const b = document.createElement('button');
    b.type = 'button';
    b.setAttribute('aria-pressed', String(p.id === selectedId));
    const chip = document.createElement('span');
    chip.className = `forge-layer-chip${p.cut ? ' is-cut' : ''}`;
    chip.style.setProperty('--swatch', p.color);
    const name = document.createElement('span');
    name.textContent = typeName(p.type);
    const meta = document.createElement('small');
    meta.textContent = layerLabel.replace('{n}', p.layer + 1) + (p.cut ? ` · ${cutLabel}` : '');
    b.append(chip, name, meta);
    b.addEventListener('click', () => { selectedId = p.id; render(); });
    li.append(b);
    return li;
  }));
}

function renderCard() {
  qa('[data-card]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.card === design.card.shape)));
  swatches(q('[data-forge-card-swatches]'), design.card.color, (color) => change(() => { design.card.color = color; }));
}

function render() {
  if (bench) bench.sync(design, selectedId);
  renderInspector();
  renderLayers();
  renderCard();
  q('[data-action="undo"]').disabled = !past.length;
  q('[data-action="redo"]').disabled = !future.length;
  preview();
  persist();
}

// ---------- actions ----------
function addPiece(type) {
  change(() => {
    const [w, h] = DEFAULT_SIZE[type];
    const top = design.pieces.reduce((m, p) => Math.max(m, p.layer), -1);
    // Pick a colour that stands off the card, rotating through the palette.
    const n = design.pieces.length;
    const usable = PALETTE.filter((c) => contrast(c, design.card.color) >= 2);
    const color = (usable.length ? usable : PALETTE)[n % (usable.length || PALETTE.length)];
    const id = nextId(design);
    const offset = (n % 4) * 32;
    design.pieces.push({ id, type, x: 512 + offset, y: 512 + offset, w, h, rot: 0, color, layer: top + 1, cut: false });
    selectedId = id;
  });
}

function act(name) {
  const p = selected();
  switch (name) {
    case 'undo': travel(past, future); return;
    case 'redo': travel(future, past); return;
    case 'reset-view': bench?.resetView(); return;
    case 'example': change(() => { design = example(); selectedId = null; }); return;
    case 'clear': change(() => { design = { ...blank(), card: { ...design.card } }; selectedId = null; }); return;
    case 'export': download(); return;
    case 'copy-svg': copy(toSvg(design, { metadata: true }), q('[data-action="copy-svg"]')); return;
    case 'share': copy(`${window.location.origin}/forge/#d=${encode(design)}`, q('[data-action="share"]')); return;
    default: break;
  }
  if (!p) return;
  switch (name) {
    case 'cut': change(() => { p.cut = !p.cut; }); break;
    case 'up': change(() => { p.layer = Math.min(40, p.layer + 1); }); break;
    case 'down': change(() => { p.layer = Math.max(0, p.layer - 1); }); break;
    case 'duplicate': change(() => {
      const id = nextId(design);
      design.pieces.push({ ...p, id, x: clamp(p.x + 48, 0, GRID), y: clamp(p.y + 48, 0, GRID) });
      selectedId = id;
    }); break;
    case 'delete': change(() => { design.pieces = design.pieces.filter((x) => x !== p); selectedId = null; }); break;
    default: break;
  }
}

function download() {
  const a = document.createElement('a');
  a.href = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(toSvg(design, { metadata: true }))}`;
  a.download = 'master.svg';
  document.body.append(a);
  a.click();
  a.remove();
}

const status = q('[data-forge-status]');
function say(key) { status.textContent = status.dataset[key] || ''; }

function copy(text, button) {
  const original = button.textContent;
  navigator.clipboard.writeText(text).then(() => {
    button.textContent = button.dataset.labelDone || original;
    setTimeout(() => { button.textContent = original; }, 1600);
  }).catch(() => say('labelCopyfail'));
}

// ---------- wiring ----------
qa('[data-add]').forEach((b) => b.addEventListener('click', () => addPiece(b.dataset.add)));
qa('[data-action]').forEach((b) => b.addEventListener('click', () => act(b.dataset.action)));
qa('[data-view]').forEach((b) => b.addEventListener('click', () => {
  bench?.setView(b.dataset.view);
  qa('[data-view]').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
}));
qa('[data-card]').forEach((b) => b.addEventListener('click', () => change(() => { design.card.shape = b.dataset.card; })));

let sliderRecorded = false;
qa('[data-field]').forEach((input) => {
  input.addEventListener('input', () => {
    const p = selected();
    if (!p) return;
    if (!sliderRecorded) { record(); sliderRecorded = true; }
    const v = +input.value;
    p[input.dataset.field] = v;
    if (input.dataset.field === 'w' && ROUND.has(p.type)) p.h = v;
    render();
  });
  input.addEventListener('change', () => { sliderRecorded = false; });
});

const brief = q('[data-forge-brief]');
function applyBrief() {
  const option = brief.selectedOptions[0];
  briefBudget = +option.dataset.budget || 8;
  q('[data-forge-goal]').textContent = option.dataset.goal || '';
  render();
}
brief.addEventListener('change', applyBrief);

q('[data-forge-import]').addEventListener('change', (ev) => {
  const file = ev.target.files && ev.target.files[0];
  ev.target.value = '';
  if (!file || file.size > 2 * 1024 * 1024) { say('labelNotforge'); return; }
  const reader = new FileReader();
  reader.onload = () => {
    const opened = fromSvgText(String(reader.result));
    if (!opened) { say('labelNotforge'); return; }
    change(() => { design = opened; selectedId = null; });
    say('labelImported');
  };
  reader.readAsText(file);
});

window.addEventListener('keydown', (ev) => {
  const t = ev.target;
  if (t && (t.tagName === 'INPUT' || t.tagName === 'SELECT' || t.tagName === 'TEXTAREA')) return;
  const mod = ev.ctrlKey || ev.metaKey;
  if (mod && ev.key.toLowerCase() === 'z') { ev.preventDefault(); act(ev.shiftKey ? 'redo' : 'undo'); return; }
  if (mod && ev.key.toLowerCase() === 'y') { ev.preventDefault(); act('redo'); return; }
  if (mod) return;
  const p = selected();
  if (!p) return;
  const k = ev.key;
  const step = ev.shiftKey ? 64 : SNAP;
  const moves = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
  if (moves[k]) {
    ev.preventDefault();
    change(() => { p.x = clamp(p.x + moves[k][0], 0, GRID); p.y = clamp(p.y + moves[k][1], 0, GRID); });
  } else if (k === 'q' || k === 'e' || k === 'Q' || k === 'E') {
    const d = (k.toLowerCase() === 'e' ? 1 : -1) * (ev.shiftKey ? 5 : 15);
    change(() => { p.rot = (p.rot + d + 360) % 360; });
  } else if (k === '+' || k === '=' || k === '-' || k === '_') {
    const f = k === '-' || k === '_' ? 1 / 1.1 : 1.1;
    change(() => {
      p.w = clamp(Math.round(p.w * f / 8) * 8, 32, GRID);
      p.h = ROUND.has(p.type) ? p.w : clamp(Math.round(p.h * f / 8) * 8, 32, GRID);
    });
  } else if (k === '[' || k === ']') {
    act(k === ']' ? 'up' : 'down');
  } else if (k === 'd' || k === 'D') {
    act('duplicate');
  } else if (k === 'x' || k === 'X') {
    act('cut');
  } else if (k === 'Delete' || k === 'Backspace') {
    ev.preventDefault();
    act('delete');
  } else if (k === 'Escape') {
    selectedId = null;
    render();
  }
});

// ---------- start ----------
const restored = restore();
if (restored.design) design = restored.design;
if (restored.brief && brief.querySelector(`option[value="${CSS.escape(restored.brief)}"]`)) brief.value = restored.brief;
applyBrief();
startWorkbench();
