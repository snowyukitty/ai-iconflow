// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
// Icon Forge project kit: the hand-off from a sketch to the IconFlow CLI.
// One zip holding a ready iconflow.toml, the master, the finalists and a
// README of the exact commands, so `iconflow check` runs the moment it is
// unpacked. Pure functions: no DOM, no network, testable under Node.
import { toSvg, ordered } from './model.js';

// ---------- a minimal STORE-only zip writer ----------
const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n += 1) {
    let c = n;
    for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c >>> 0;
  }
  return table;
})();

export function crc32(bytes) {
  let c = 0xffffffff;
  for (let i = 0; i < bytes.length; i += 1) c = CRC_TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function dosTime(date) {
  const time = (date.getHours() << 11) | (date.getMinutes() << 5) | (date.getSeconds() >> 1);
  const day = ((date.getFullYear() - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate();
  return [time, day];
}

// files: [{ name, text }]. Returns the zip as a Uint8Array.
export function zip(files, date = new Date()) {
  const enc = new TextEncoder();
  const [time, day] = dosTime(date);
  const chunks = [];
  const central = [];
  let offset = 0;
  for (const file of files) {
    const name = enc.encode(file.name);
    const data = enc.encode(file.text);
    const crc = crc32(data);
    const local = new DataView(new ArrayBuffer(30));
    local.setUint32(0, 0x04034b50, true);
    local.setUint16(4, 20, true);
    local.setUint16(6, 0x0800, true);     // names are UTF-8
    local.setUint16(8, 0, true);          // stored
    local.setUint16(10, time, true);
    local.setUint16(12, day, true);
    local.setUint32(14, crc, true);
    local.setUint32(18, data.length, true);
    local.setUint32(22, data.length, true);
    local.setUint16(26, name.length, true);
    local.setUint16(28, 0, true);
    chunks.push(new Uint8Array(local.buffer), name, data);

    const entry = new DataView(new ArrayBuffer(46));
    entry.setUint32(0, 0x02014b50, true);
    entry.setUint16(4, 20, true);
    entry.setUint16(6, 20, true);
    entry.setUint16(8, 0x0800, true);
    entry.setUint16(10, 0, true);
    entry.setUint16(12, time, true);
    entry.setUint16(14, day, true);
    entry.setUint32(16, crc, true);
    entry.setUint32(20, data.length, true);
    entry.setUint32(24, data.length, true);
    entry.setUint16(28, name.length, true);
    entry.setUint32(42, offset, true);
    central.push(new Uint8Array(entry.buffer), name);
    offset += 30 + name.length + data.length;
  }
  const size = central.reduce((n, c) => n + c.length, 0);
  const end = new DataView(new ArrayBuffer(22));
  end.setUint32(0, 0x06054b50, true);
  end.setUint16(8, files.length, true);
  end.setUint16(10, files.length, true);
  end.setUint32(12, size, true);
  end.setUint32(16, offset, true);
  const parts = [...chunks, ...central, new Uint8Array(end.buffer)];
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let at = 0;
  for (const p of parts) { out.set(p, at); at += p.length; }
  return out;
}

// ---------- the kit ----------
export function slug(text) {
  const s = String(text || '').normalize('NFKD').toLowerCase()
    .replace(/[^\w\s-]/g, '').trim().replace(/[\s_]+/g, '-').replace(/-+/g, '-').slice(0, 40);
  return s.replace(/^-|-$/g, '') || 'my-icon';
}

const toml = (value) => `"${String(value).replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\n/g, '\\n')}"`;
const tomlList = (values) => `[${values.map(toml).join(', ')}]`;

function palette(design) {
  const colours = [];
  if (design.card.shape !== 'none') colours.push(design.card.color);
  for (const p of ordered(design)) if (!p.cut && !colours.includes(p.color)) colours.push(p.color);
  return colours;
}

// brief: { key, title, goal }; checks: [{ level, title }] from the Forge at export.
export function kitFiles({ name, design, finalists = [], brief = {}, checks = [], shareUrl = '' }) {
  const project = slug(name);
  const noCard = design.card.shape === 'none';
  // A menu-bar brief gets the tray target and its own transparent drawing:
  // a card's alpha is a black square in a macOS menu bar, so the tray is
  // built from the mark alone (docs/OUTPUT_TARGETS.md, AGENTS.md step 4).
  const tray = brief.key === 'tray';
  const kept = finalists.map((f, i) => (f ? { letter: 'abc'[i], design: f } : null)).filter(Boolean);
  const lines = (list) => list.join('\n') + '\n';

  const config = lines([
    '# IconFlow project brief and deterministic build contract.',
    '# Started in the Icon Forge (https://ai-iconflow.com/forge/). Fill in the',
    '# empty brief fields before review: a visual decision without a product',
    '# job is not a complete brief (docs/DESIGN_PLAYBOOK.md).',
    'schema_version = 1',
    '',
    '[project]',
    `name = ${toml(project)}`,
    'master = "master.svg"',
    'output = "icon-out"',
    'casebook = "casebook"',
    '',
    '[brief]',
    `app_intent = ${toml(brief.goal || '')}`,
    'user_job = ""',
    'essence = ""',
    'personality = []',
    '',
    '[design]',
    `palette = ${tomlList(palette(design))}`,
    'cliches = []',
    'signature_device = ""',
    'device_family = ""',
    'device_detail = ""',
    'concept_lens = ""',
    '',
    '[build]',
    `targets = ${tray ? '["web", "tray"]' : '["web"]'}`,
    `theme_color = ${toml(noCard ? '#0b0d12' : design.card.color)}`,
    'background_color = "#ffffff"',
    'electron_radius = 0',
    'tray_ts = false',
    `tray_svg = ${tray ? '"tray.svg"' : '""'}`,
    'tray_template_mode = "auto"',
    'color_scheme = "light"',
    'optimize_png = true',
    '',
    '[neighbours]',
    '# The Forge checked these generic forms live; listing them here makes',
    '# `iconflow check` gate them too (docs/NEIGHBOURHOOD.md).',
    'avoid = ["@collision"]',
    'family = []',
    'portfolio = []',
    '',
    '[review]',
    'status = "pending"',
    'source_sha256 = ""',
    'contract_sha256 = ""',
    'scores = {}',
    'notes = ""',
  ]);

  const compare = kept.length >= 2
    ? ['', '## 2. Bake off the finalists', '', '```sh', `iconflow compare ${kept.map((k) => `finalists/${k.letter}.svg`).join(' ')} --out bake.png`, '```', '',
      'Open `bake.png`. Promote the most distinctive one that is still legible at 16px to `master.svg` (the Forge wrote the design you had open as the master).']
    : [];
  const status = checks.length
    ? ['', '## What the Forge saw at export', '', ...checks.map((c) => `- ${c.level === 'pass' ? '✓' : c.level === 'fail' ? '✗' : '!'} ${c.title}`), '',
      'These are browser heuristics. The CLI renders in a pinned Chromium and still asks a person to review.']
    : [];
  const readme = lines([
    `# ${project}`,
    '',
    `Sketched in the [Icon Forge](https://ai-iconflow.com/forge/)${brief.title ? ` for the brief “${brief.title}”` : ''}.`,
    shareUrl ? `Reopen this design in the Forge: ${shareUrl}` : '',
    '',
    '## 1. Check the master',
    '',
    '```sh',
    'pip install iconflow   # or: uv tool install iconflow',
    'iconflow setup         # one-time pinned Chromium download',
    `iconflow check master.svg --config iconflow.toml${tray ? ' --tray-svg tray.svg --tray-template-mode auto' : ''}`,
    'iconflow neighbours master.svg --config iconflow.toml --sheet neighbours.png',
    '```',
    ...compare,
    '',
    `## ${kept.length >= 2 ? 3 : 2}. Write the brief, review, ship`,
    '',
    'Fill in `[brief]` in `iconflow.toml` (who it is for, the job, one-word essence), then:',
    '',
    '```sh',
    'iconflow review --config iconflow.toml --html review.html',
    'iconflow ship --config iconflow.toml --review master-review.json',
    '```',
    '',
    '`ship` refuses until every review axis scores 4/5 or better against this exact `master.svg`.',
    ...status,
    '',
    'The icon is yours: no attribution, no share-alike, commercial use unrestricted.',
  ]).replace(/\n{3,}/g, '\n\n');

  return [
    { name: `${project}/iconflow.toml`, text: config },
    { name: `${project}/master.svg`, text: toSvg(design, { metadata: true }) },
    ...(tray ? [{ name: `${project}/tray.svg`, text: toSvg(design, { mode: 'mark' }) }] : []),
    ...kept.map((k) => ({ name: `${project}/finalists/${k.letter}.svg`, text: toSvg(k.design, { metadata: true }) })),
    { name: `${project}/README.md`, text: readme },
  ];
}
