// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
// Icon Forge workbench: a three.js projection of the model. It owns no design
// state; it draws what it is given and reports picks and drags back.
import * as THREE from './vendor/three-0.169.0/three.module.min.js';
import { OrbitControls } from './vendor/three-0.169.0/OrbitControls.js';
import { GRID, RING_INNER, ordered } from './model.js';

const S = 100;              // SVG units per world unit: the grid is 10.24 wide
const C = GRID / S / 2;     // world centre of the grid
const LAYER_H = 44;         // SVG units between layers
const PIECE_D = 34;         // extrusion depth in SVG units
const CARD_D = 22;

function roundRect(w, h, r) {
  const s = new THREE.Shape();
  const x = -w / 2; const y = -h / 2;
  r = Math.min(r, w / 2, h / 2);
  s.moveTo(x + r, y);
  s.lineTo(x + w - r, y); s.absarc(x + w - r, y + r, r, -Math.PI / 2, 0);
  s.lineTo(x + w, y + h - r); s.absarc(x + w - r, y + h - r, r, 0, Math.PI / 2);
  s.lineTo(x + r, y + h); s.absarc(x + r, y + h - r, r, Math.PI / 2, Math.PI);
  s.lineTo(x, y + r); s.absarc(x + r, y + r, r, Math.PI, Math.PI * 1.5);
  return s;
}

// Shapes are built y-up; laid flat, shape +y becomes world -z, which is SVG -y.
// So a wedge pointing "up" here points up in the stamp view and in the SVG.
function shapeOf(p) {
  const hw = p.w / 2; const hh = p.h / 2;
  switch (p.type) {
    case 'circle': { const s = new THREE.Shape(); s.absarc(0, 0, hw, 0, Math.PI * 2); return s; }
    case 'block': return roundRect(p.w, p.h, Math.min(hw, hh) * 0.22);
    case 'bar': return roundRect(p.w, p.h, Math.min(hw, hh));
    case 'wedge': { const s = new THREE.Shape(); s.moveTo(0, hh); s.lineTo(hw, -hh); s.lineTo(-hw, -hh); s.closePath(); return s; }
    case 'ring': {
      const s = new THREE.Shape(); s.absarc(0, 0, hw, 0, Math.PI * 2);
      const hole = new THREE.Path(); hole.absarc(0, 0, hw * RING_INNER, 0, Math.PI * 2, true);
      s.holes.push(hole); return s;
    }
    case 'arc': {
      const s = new THREE.Shape(); const ri = hw * RING_INNER;
      s.moveTo(-hw, 0); s.absarc(0, 0, hw, Math.PI, 0, true);
      s.lineTo(ri, 0); s.absarc(0, 0, ri, 0, Math.PI, false); s.closePath();
      return s;
    }
    default: return new THREE.Shape();
  }
}

function extrude(shape, depth, bevel) {
  const geo = new THREE.ExtrudeGeometry(shape, {
    depth, curveSegments: 40, bevelEnabled: bevel > 0,
    bevelThickness: bevel, bevelSize: bevel * 0.8, bevelSegments: 3,
  });
  geo.scale(1 / S, 1 / S, 1 / S);
  return geo;
}

export function createWorkbench(host, events) {
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, preserveDrawingBuffer: true });
  } catch {
    return null;
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  host.appendChild(renderer.domElement);
  renderer.domElement.setAttribute('aria-hidden', 'true');

  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#191a20');
  scene.fog = new THREE.Fog('#191a20', 26, 46);

  // Two cameras: an orbiting perspective for building, and a straight-down
  // orthographic "stamp" that is pixel-for-pixel the SVG.
  const persp = new THREE.PerspectiveCamera(38, 1, 0.1, 120);
  persp.position.set(C, 12.5, C + 15.5);
  const ortho = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 80);
  ortho.position.set(C, 30, C);
  ortho.up.set(0, 0, -1);
  ortho.lookAt(C, 0, C);

  const orbit = new OrbitControls(persp, renderer.domElement);
  orbit.target.set(C, 0, C);
  orbit.enableDamping = true;
  orbit.maxPolarAngle = Math.PI * 0.47;
  orbit.minDistance = 7;
  orbit.maxDistance = 32;
  orbit.update();
  const flat = new OrbitControls(ortho, renderer.domElement);
  flat.target.set(C, 0, C);
  flat.enableRotate = false;
  flat.minZoom = 0.6;
  flat.maxZoom = 4;
  flat.enabled = false;
  flat.update();
  let camera = persp;
  let view = 'orbit';

  scene.add(new THREE.HemisphereLight('#fff6ec', '#2b2d36', 1.5));
  const sun = new THREE.DirectionalLight('#fff1dc', 2.4);
  sun.position.set(C + 7, 16, C + 4);
  sun.target.position.set(C, 0, C);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  sun.shadow.bias = -0.0004;
  Object.assign(sun.shadow.camera, { left: -9, right: 9, top: 9, bottom: -9, near: 1, far: 40 });
  scene.add(sun, sun.target);
  const rim = new THREE.DirectionalLight('#ff8a7f', 0.5);
  rim.position.set(C - 10, 6, C - 8);
  scene.add(rim);

  const bench = new THREE.Mesh(
    new THREE.BoxGeometry(17, 0.8, 17),
    new THREE.MeshStandardMaterial({ color: '#2b2d36', roughness: 0.92 }),
  );
  bench.position.set(C, -0.41, C);
  bench.receiveShadow = true;
  scene.add(bench);
  const grid = new THREE.GridHelper(GRID / S, 16, '#55586a', '#33353f');
  grid.position.set(C, 0.004, C);
  scene.add(grid);
  // The 16px lattice: each cell is one pixel of a favicon.
  const pixelGrid = new THREE.GridHelper(GRID / S, 16, '#ff5a4f', '#ff5a4f');
  pixelGrid.material.transparent = true;
  pixelGrid.material.opacity = 0;
  pixelGrid.material.depthWrite = false;
  pixelGrid.visible = false;
  pixelGrid.position.set(C, 0.6, C);
  scene.add(pixelGrid);

  let cardMesh = null;
  let cardKey = '';
  const pieces = new Map();   // id -> { group, mesh, key, drop }
  let design = null;
  let selectedId = null;

  const cardTop = () => (design && design.card.shape !== 'none' ? CARD_D : 0);

  function syncCard() {
    const key = `${design.card.shape}|${design.card.color}`;
    if (key === cardKey) return;
    cardKey = key;
    if (cardMesh) { scene.remove(cardMesh); cardMesh.geometry.dispose(); cardMesh.material.dispose(); cardMesh = null; }
    if (design.card.shape === 'none') return;
    const shape = design.card.shape === 'circle'
      ? (() => { const s = new THREE.Shape(); s.absarc(0, 0, GRID / 2, 0, Math.PI * 2); return s; })()
      : roundRect(GRID, GRID, 224);
    cardMesh = new THREE.Mesh(extrude(shape, CARD_D, 0), new THREE.MeshStandardMaterial({ color: design.card.color, roughness: 0.75 }));
    cardMesh.rotation.x = -Math.PI / 2;
    cardMesh.position.set(C, 0, C);
    cardMesh.receiveShadow = true;
    cardMesh.renderOrder = ORDER_CARD;
    scene.add(cardMesh);
  }

  // A cut is not drawn; it is a depth-only prism standing on the card, up to
  // the cut's own layer. Drawn after the card and before the pieces, it makes
  // every piece below it fail the depth test inside its outline, so the card
  // (or the bare bench) shows through a real hole from any angle, and Stamp
  // view matches the SVG mask exactly. Pieces above the cut stand over it.
  const ORDER_CARD = 0;
  const ORDER_CUT = 1;
  const ORDER_PIECE = 2;
  const CUT_UNIT = 100;   // the prism is built CUT_UNIT tall and scaled to fit

  function materialFor(p) {
    if (!p.cut) return new THREE.MeshStandardMaterial({ color: p.color, roughness: 0.42, metalness: 0.04 });
    return new THREE.MeshBasicMaterial({ colorWrite: false });
  }

  function buildPiece(p, old) {
    const geo = extrude(shapeOf(p), p.cut ? CUT_UNIT : PIECE_D, p.cut ? 0 : 5);
    const mesh = new THREE.Mesh(geo, materialFor(p));
    mesh.rotation.x = -Math.PI / 2;
    mesh.castShadow = !p.cut;
    mesh.receiveShadow = !p.cut;
    mesh.renderOrder = p.cut ? ORDER_CUT : ORDER_PIECE;
    mesh.userData.id = p.id;
    const group = old ? old.group : new THREE.Group();
    if (old) { group.remove(old.mesh); old.mesh.geometry.dispose(); old.mesh.material.dispose(); if (old.edge) { group.remove(old.edge); old.edge.geometry.dispose(); } }
    group.add(mesh);
    let edge = null;
    if (p.cut) {
      // Only the rim of the hole is drawn, where it meets the card.
      const rim = new THREE.BufferGeometry().setFromPoints(shapeOf(p).getPoints(48).map((v) => new THREE.Vector3(v.x / S, v.y / S, 0)));
      edge = new THREE.LineLoop(rim, new THREE.LineBasicMaterial({ color: '#ff766d', transparent: true, opacity: 0.7 }));
      edge.renderOrder = ORDER_PIECE + 1;
      edge.rotation.x = -Math.PI / 2;
      group.add(edge);
    }
    if (!old) scene.add(group);
    return { group, mesh, edge, drop: old ? old.drop : 1 };
  }

  // Rebuild geometry only when a piece's shape or look changed; moves,
  // turns and layer changes just update the transform.
  function sync(next, selected) {
    design = next;
    selectedId = selected;
    syncCard();
    const live = new Set();
    const order = ordered(design);
    order.forEach((p, index) => {
      live.add(p.id);
      const key = `${p.type}|${p.w}|${p.h}|${p.color}|${p.cut}|${p.cut ? cardKey : ''}`;
      let entry = pieces.get(p.id);
      if (!entry) {
        entry = buildPiece(p, null);
        entry.drop = 0;
        pieces.set(p.id, entry);
      } else if (entry.key !== key) {
        entry = { ...buildPiece(p, entry) };
        pieces.set(p.id, entry);
      }
      entry.key = key;
      entry.layer = p.layer;
      entry.index = index;
      const g = entry.group;
      g.position.x = p.x / S;
      g.position.z = p.y / S;
      g.rotation.y = -THREE.MathUtils.degToRad(p.rot);
      // Pieces on the same layer still need a sliver of separation, or their
      // coplanar tops z-fight; insertion order decides who is on top.
      entry.baseY = (cardTop() + p.layer * LAYER_H) / S + index * 0.0015 + 0.002;
      if (p.cut) {
        // Stand on the card and reach just over the pieces this cut goes through.
        entry.baseY = cardTop() / S + 0.001;
        entry.mesh.scale.z = Math.max(0.01, (p.layer * LAYER_H - 4) / CUT_UNIT);
      }
      entry.mesh.material.emissive?.set(p.id === selectedId ? '#3a1410' : '#000000');
    });
    for (const [id, entry] of pieces) {
      if (live.has(id)) continue;
      scene.remove(entry.group);
      entry.mesh.geometry.dispose(); entry.mesh.material.dispose();
      pieces.delete(id);
    }
  }

  // ---------- picking and dragging ----------
  const ray = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  const floor = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
  const hitPoint = new THREE.Vector3();
  let drag = null;

  function aim(ev) {
    const r = renderer.domElement.getBoundingClientRect();
    ndc.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
  }
  function pickPiece() {
    const meshes = [...pieces.values()].map((e) => e.mesh);
    const hit = ray.intersectObjects(meshes, false)[0];
    return hit ? hit.object.userData.id : null;
  }
  function onFloor(height) {
    floor.constant = -height;
    return ray.ray.intersectPlane(floor, hitPoint) ? hitPoint : null;
  }

  const el = renderer.domElement;
  let downAt = null;
  el.addEventListener('pointerdown', (ev) => {
    if (ev.button !== 0) return;
    aim(ev);
    const id = pickPiece();
    downAt = { x: ev.clientX, y: ev.clientY, id };
    if (id == null) return;
    const p = design.pieces.find((q) => q.id === id);
    const entry = pieces.get(id);
    const at = onFloor(entry.baseY + PIECE_D / S);
    if (!at) return;
    drag = { id, dx: p.x - at.x * S, dy: p.y - at.z * S, height: entry.baseY + PIECE_D / S, moved: false };
    orbit.enabled = false; flat.enabled = false;
    el.setPointerCapture(ev.pointerId);
    events.pick(id);
  });
  el.addEventListener('pointermove', (ev) => {
    if (!drag) {
      aim(ev);
      el.style.cursor = pickPiece() != null ? 'grab' : '';
      return;
    }
    aim(ev);
    const at = onFloor(drag.height);
    if (!at) return;
    if (!drag.moved) { drag.moved = true; events.dragStart(drag.id); }
    el.style.cursor = 'grabbing';
    events.dragMove(drag.id, at.x * S + drag.dx, at.z * S + drag.dy, ev.shiftKey);
  });
  const end = (ev) => {
    if (drag) {
      if (drag.moved) events.dragEnd(drag.id);
      drag = null;
      orbit.enabled = view === 'orbit';
      flat.enabled = view === 'stamp';
      el.style.cursor = '';
    } else if (downAt && downAt.id == null && ev && Math.hypot(ev.clientX - downAt.x, ev.clientY - downAt.y) < 4) {
      events.pick(null);   // a click on empty space, not an orbit drag
    }
    downAt = null;
  };
  el.addEventListener('pointerup', end);
  el.addEventListener('pointercancel', () => end(null));

  // ---------- views ----------
  let tween = null;
  const ORBIT_HOME = new THREE.Vector3(C, 12.5, C + 15.5);
  function setView(next) {
    if (next === view) return;
    view = next;
    if (next === 'stamp') {
      // Fly the perspective camera overhead, then cut to the exact orthographic view.
      tween = { from: persp.position.clone(), to: new THREE.Vector3(C, 24, C + 0.001), fromT: orbit.target.clone(), t: 0, then: 'stamp' };
    } else {
      camera = persp;
      sun.castShadow = true;
      flat.enabled = false;
      persp.position.set(C, 24, C + 0.001);
      tween = { from: persp.position.clone(), to: ORBIT_HOME.clone(), fromT: orbit.target.clone(), t: 0, then: 'orbit' };
    }
    orbit.enabled = false;
  }
  function resetView() {
    if (view === 'stamp') { ortho.zoom = 1; ortho.updateProjectionMatrix(); flat.target.set(C, 0, C); ortho.position.set(C, 30, C); flat.update(); return; }
    tween = { from: persp.position.clone(), to: ORBIT_HOME.clone(), fromT: orbit.target.clone(), t: 0, then: 'orbit' };
  }

  function fit() {
    const w = host.clientWidth || 1; const h = host.clientHeight || 1;
    renderer.setSize(w, h, false);
    renderer.domElement.style.width = '100%';
    renderer.domElement.style.height = '100%';
    persp.aspect = w / h;
    // Hold the horizontal view a 16:10 stage gets at 38°, so a portrait phone
    // widens the lens instead of cropping the board's sides.
    const halfH = Math.atan(Math.tan(THREE.MathUtils.degToRad(19)) * 1.6);
    const vfov = THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(halfH) / (w / h)));
    persp.fov = THREE.MathUtils.clamp(vfov, 38, 64);
    persp.updateProjectionMatrix();
    const half = (GRID / S) * 0.62;
    const a = w / h;
    Object.assign(ortho, a >= 1
      ? { left: -half * a, right: half * a, top: half, bottom: -half }
      : { left: -half, right: half, top: half / a, bottom: -half / a });
    ortho.updateProjectionMatrix();
  }
  new ResizeObserver(fit).observe(host);
  fit();

  const clock = new THREE.Clock();
  renderer.setAnimationLoop(() => {
    const dt = Math.min(clock.getDelta(), 0.05);
    if (tween) {
      tween.t = Math.min(1, tween.t + dt * 2.4);
      const e = 1 - (1 - tween.t) ** 3;
      persp.position.lerpVectors(tween.from, tween.to, e);
      orbit.target.lerpVectors(tween.fromT, new THREE.Vector3(C, 0, C), e);
      persp.lookAt(orbit.target);
      if (tween.t === 1) {
        // Stamp is the SVG: flat, with no shadows for hidden pieces to cast into holes.
        if (tween.then === 'stamp') { camera = ortho; flat.enabled = true; sun.castShadow = false; } else { orbit.enabled = true; }
        tween = null;
      }
    } else if (view === 'orbit') {
      orbit.update();
    } else {
      flat.update();
    }
    // New pieces drop onto the board; the selected one floats a little.
    for (const entry of pieces.values()) {
      if (entry.drop < 1) entry.drop = Math.min(1, entry.drop + dt * 2.6);
      const d = entry.drop;
      const bounce = d < 1 ? (1 - d) ** 2 * 3.2 - Math.sin(d * Math.PI) * 0.08 : 0;
      const lift = entry.mesh.userData.id === selectedId && view === 'orbit' && entry.mesh.renderOrder !== ORDER_CUT ? 0.06 : 0;
      entry.group.position.y = entry.baseY + Math.max(-0.02, bounce) + lift;
    }
    pixelGrid.material.opacity += ((view === 'stamp' && !tween ? 0.35 : 0) - pixelGrid.material.opacity) * 0.15;
    pixelGrid.visible = pixelGrid.material.opacity > 0.01;
    pixelGrid.position.y = (cardTop() + 30 * LAYER_H) / S;
    renderer.render(scene, camera);
  });

  return { sync, setView, resetView, canvas: renderer.domElement, get view() { return view; } };
}
