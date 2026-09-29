(() => {
  'use strict';
  const G = window.FenceGeometry, $ = (id) => document.getElementById(id);
  const el = { tableTitle:$('tableTitle'), eyebrow:$('workbenchEyebrow'), workbenchTitle:$('fenceWorkbenchTitle'), workbenchDescription:$('workbenchDescription'), published:$('editPublished'), download:$('downloadFence'), stage:$('webglStage'), fallback:$('webglFallback'), loading:$('loadingState'), readout:$('recordReadout'), picker:$('snapshotPicker'), svg:$('fenceSvg'), faces:$('fenceFaces'), lines:$('fenceLines'), handles:$('fenceHandles'), list:$('fenceList'), score:$('liveScore'), hint:$('dragHint'), edit:$('editMode'), camera:$('cameraMode'), left:$('turnLeft'), right:$('turnRight'), undo:$('undoFence'), reset:$('resetFence'), slider:$('motionSlider'), frameReadout:$('motionFrameReadout'), motionScore:$('motionScore'), changed:$('motionChanged'), resetMotion:$('resetMotion'), lesson:$('motionLesson'), top:$('topView'), fit:$('fitView'), central:$('centralView'), orbitLeft:$('orbitLeft'), orbitRight:$('orbitRight'), orbitUp:$('orbitUp'), orbitDown:$('orbitDown'), next:$('nextFace'), previous:$('previousFace'), faceTitle:$('faceTitle'), faceExplanation:$('faceExplanation'), support:$('supportDetails'), supportLines:$('supportLines') };
  const PUZZLE = [[1n,0n,-220n],[0n,1n,-320n],[1n,-1n,20n],[0n,1n,-220n]];
  const ns = 'http://www.w3.org/2000/svg';
  const tag = (name, attributes = {}) => { const node = document.createElementNS(ns, name); Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value)); return node; };
  const clone = (lines) => lines.map((line) => [...line]);
  const state = { snapshots:[], snapshot:null, lines:[], original:[], selected:0, undo:[], mode:'edit', drag:null, pan:{x:0,y:0}, motion:null, motionIndex:null, frame:null, faces:[], selectedFace:null, kind:'warmup', origin:'warmup', sourceLabel:'', map:null };
  let renderer, scene, camera, raycaster, meshes = [], fenceObjects = [], target;
  const number = (value) => Number(value);
  const rawLines = (record) => record.lines.map((row) => row.map(BigInt));
  const formatOffset = (offset) => Number(offset) > 0 ? `+${offset}` : String(offset);
  const lineText = (line) => `${line[0]}x ${BigInt(line[1]) < 0n ? '−' : '+'} ${BigInt(line[1]) < 0n ? -BigInt(line[1]) : line[1]}y ${BigInt(line[2]) < 0n ? '−' : '+'} ${BigInt(line[2]) < 0n ? -BigInt(line[2]) : line[2]} = 0`;

  function bounds(lines) {
    const points = [];
    for (let first = 0; first < lines.length; first += 1) for (let second = first + 1; second < lines.length; second += 1) {
      const point = G.intersection(lines[first], lines[second]);
      if (point) points.push([number(point[0]) / number(point[2]), number(point[1]) / number(point[2])]);
    }
    if (!points.length) return [-10,-10,10,10];
    const xs = points.map((point) => point[0]), ys = points.map((point) => point[1]);
    const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys), pad = Math.max(maxX - minX, maxY - minY, .1) * .12;
    return [minX - pad, minY - pad, maxX + pad, maxY + pad];
  }

  function mapFor(lines) {
    const b = bounds(lines), width = 720, height = 480, span = Math.max(b[2] - b[0], b[3] - b[1]), scale = Math.min((width - 48) / span, (height - 48) / span);
    return { b, scale, x:(x) => (x - (b[0] + b[2]) / 2) * scale + width / 2 + state.pan.x, y:(y) => height / 2 - (y - (b[1] + b[3]) / 2) * scale + state.pan.y, unx:(x) => (x - width / 2 - state.pan.x) / scale + (b[0] + b[2]) / 2, uny:(y) => (height / 2 - y + state.pan.y) / scale + (b[1] + b[3]) / 2 };
  }

  function clipped(line, map) {
    const [a,b,c] = line.map(number), [x0,y0,x1,y1] = map.b, points = [];
    const add = (x, y) => { if (Number.isFinite(x) && Number.isFinite(y) && x >= x0 - 1e-8 && x <= x1 + 1e-8 && y >= y0 - 1e-8 && y <= y1 + 1e-8 && !points.some((point) => Math.hypot(point[0] - x, point[1] - y) < 1e-7)) points.push([x,y]); };
    if (b) { add(x0, -(a * x0 + c) / b); add(x1, -(a * x1 + c) / b); }
    if (a) { add(-(b * y0 + c) / a, y0); add(-(b * y1 + c) / a, y1); }
    return points.length > 1 ? points.slice(0, 2) : null;
  }

  function clearFace() {
    state.selectedFace = null;
    el.faceTitle.textContent = 'Choose a triangular yard';
    el.faceExplanation.textContent = 'Click a raised triangular yard to highlight the three fences that enclose it.';
    el.supportLines.replaceChildren();
    el.support.hidden = true;
  }

  function sourceDescription(score) {
    if (state.kind === 'published') return `Edited version of the supplied 93-face prior-art construction: ${score} triangular yards. This live exploration makes no novelty or optimality claim.`;
    if (state.kind === 'editedMotion') return `Edited copy of saved motion frame at offset ${formatOffset(state.frame.offset)}: ${score} triangular yards. Reset restores the supplied exact frame.`;
    if (state.kind === 'motion') return `Saved motion frame at offset ${formatOffset(state.frame.offset)}: ${score} triangular yards, rendered from its supplied exact line equations.`;
    if (state.kind === 'editedSnapshot') return `Edited copy of saved ${state.sourceLabel} arrangement: ${score} triangular yards. Reset restores the supplied exact arrangement.`;
    if (state.kind === 'snapshot') return `Saved ${state.sourceLabel} arrangement: ${score} triangular yards, rendered from its supplied exact line equations.`;
    return `Live warm-up: ${score} triangular yards. The count is recomputed from exact integer lines, not from the screen drawing.`;
  }

  function scoreLabel(score) {
    if (state.kind === 'published') return `Edited published construction: ${score} triangular yards · exact BigInt score`;
    if (state.kind === 'editedMotion') return `Edited copy of saved frame ${formatOffset(state.frame.offset)}: ${score} triangular yards · exact BigInt score`;
    if (state.kind === 'motion') return `Saved frame ${formatOffset(state.frame.offset)}: ${score} triangular yards · exact BigInt score`;
    if (state.kind === 'editedSnapshot') return `Edited copy of saved ${state.sourceLabel}: ${score} triangular yards · exact BigInt score`;
    if (state.kind === 'snapshot') return `Saved ${state.sourceLabel}: ${score} triangular yards · exact BigInt score`;
    return `${score} triangular yards · exact BigInt score`;
  }

  function updateExact() {
    el.tableTitle.textContent = state.lines.length === 4 ? '4 fences. A small warm-up.' : `${state.lines.length} fences. A delicate balance.`;
    const report = G.score(state.lines);
    state.faces = report.faces;
    el.score.textContent = scoreLabel(report.score);
    el.readout.textContent = sourceDescription(report.score);
    if (state.kind === 'motion' && report.score !== state.frame.score) throw new Error(`saved frame score mismatch: expected ${state.frame.score}, got ${report.score}`);
    return report;
  }

  function drawSvg({ geometryChanged = false } = {}) {
    let report;
    try { report = updateExact(); } catch (error) { el.score.textContent = `Move rejected: ${error.message}`; return false; }
    if (geometryChanged) clearFace();
    const map = mapFor(state.lines);
    state.map = map;
    el.faces.replaceChildren(); el.lines.replaceChildren(); el.handles.replaceChildren();
    report.faces.forEach((triple) => {
      const points = G.vertices(state.lines, triple).map(([x,y]) => `${map.x(x)},${map.y(y)}`).join(' ');
      el.faces.append(tag('polygon', { points, class:'yard' }));
    });
    state.lines.forEach((line, index) => {
      const end = clipped(line, map);
      if (!end) return;
      const selected = index === state.selected;
      const path = tag('line', { x1:map.x(end[0][0]), y1:map.y(end[0][1]), x2:map.x(end[1][0]), y2:map.y(end[1][1]), class:`fence ${selected ? 'is-selected' : ''}`, 'data-index':index, tabindex:'-1' });
      path.addEventListener('click', () => select(index));
      el.lines.append(path);
      if (selected) {
        const middleX = (end[0][0] + end[1][0]) / 2, middleY = (end[0][1] + end[1][1]) / 2;
        el.handles.append(tag('circle', { cx:map.x(middleX), cy:map.y(middleY), r:11, class:'fence-handle', 'aria-label':'Drag selected fence handle' }));
      }
    });
    renderList(); renderThree(map);
    return true;
  }

  function select(index) { state.selected = index; drawSvg(); }

  function showFace(index) {
    if (!state.faces.length) return;
    state.selectedFace = ((index % state.faces.length) + state.faces.length) % state.faces.length;
    const face = state.faces[state.selectedFace];
    el.faceTitle.textContent = `Face ${state.selectedFace + 1}`;
    el.faceExplanation.textContent = 'This raised tile is certified by its three exact supporting fence equations.';
    el.supportLines.replaceChildren();
    face.forEach((lineIndex) => { const item = document.createElement('li'); item.textContent = `Fence ${lineIndex + 1}: ${lineText(state.lines[lineIndex])}`; el.supportLines.append(item); });
    el.support.hidden = false;
    renderThree(state.map);
  }

  function renderList() {
    el.list.replaceChildren();
    state.lines.forEach((line, index) => {
      const button = document.createElement('button');
      button.type = 'button'; button.textContent = `Fence ${index + 1}: ${lineText(line)}`;
      button.setAttribute('aria-pressed', String(index === state.selected));
      button.addEventListener('click', () => select(index));
      const item = document.createElement('li'); item.append(button); el.list.append(item);
    });
    el.undo.disabled = !state.undo.length;
  }

  function reject(error, baseline) {
    state.lines = clone(baseline);
    el.score.textContent = `Move rejected: ${error.message}`;
    renderList();
    return false;
  }

  function markEdited() {
    if (state.kind === 'snapshot') state.kind = 'editedSnapshot';
    if (state.kind === 'motion') state.kind = 'editedMotion';
    applyWorkbench(state.kind, state.sourceLabel);
  }

  function applyCandidate(candidate, baseline, { recordUndo = false } = {}) {
    try { G.score(candidate); } catch (error) { return reject(error, baseline); }
    if (recordUndo) state.undo.push({ lines:clone(baseline), kind:state.kind });
    state.lines = candidate;
    markEdited();
    return drawSvg({ geometryChanged:true });
  }

  function moveBy(pointer, baseline) {
    const map = mapFor(baseline), [a,b,c] = baseline[state.selected];
    const x = map.unx(pointer.x), y = map.uny(pointer.y);
    const amount = BigInt(Math.round(-(number(a) * x + number(b) * y + number(c))));
    if (!amount) return false;
    try { return applyCandidate(G.translateParallel(baseline, state.selected, amount), baseline); } catch (error) { return reject(error, baseline); }
  }

  function svgPoint(event) { const rect = el.svg.getBoundingClientRect(); return { x:(event.clientX - rect.left) * 720 / rect.width, y:(event.clientY - rect.top) * 480 / rect.height }; }

  function finishDrag(event, canceled) {
    if (!state.drag || event.pointerId !== state.drag.id) return;
    try { el.svg.releasePointerCapture(event.pointerId); } catch (_) { }
    const drag = state.drag;
    state.drag = null;
    if (canceled) { state.lines = clone(drag.lines); state.kind = drag.kind; applyWorkbench(state.kind, state.sourceLabel); drawSvg({ geometryChanged:true }); return; }
    if (drag.changed) state.undo.push({ lines:clone(drag.lines), kind:drag.kind });
    renderList();
  }

  function attachEditor() {
    el.svg.addEventListener('pointerdown', (event) => {
      const handle = event.target.closest?.('.fence-handle');
      if (state.mode === 'edit' && !handle) return;
      event.preventDefault();
      const point = svgPoint(event);
      el.svg.setPointerCapture(event.pointerId);
      state.drag = { id:event.pointerId, point, lines:clone(state.lines), kind:state.kind, pan:{...state.pan}, moved:false, changed:false };
    });
    el.svg.addEventListener('pointermove', (event) => {
      if (!state.drag || event.pointerId !== state.drag.id) return;
      const point = svgPoint(event), deltaX = point.x - state.drag.point.x, deltaY = point.y - state.drag.point.y;
      state.drag.moved ||= Math.abs(deltaX) + Math.abs(deltaY) > 3;
      if (!state.drag.moved) return;
      if (state.mode === 'camera') {
        state.pan = { x:state.drag.pan.x + deltaX, y:state.drag.pan.y + deltaY };
        drawSvg();
        return;
      }
      state.lines = clone(state.drag.lines);
      state.drag.changed = moveBy(point, state.drag.lines) || state.drag.changed;
    });
    el.svg.addEventListener('pointerup', (event) => finishDrag(event, false));
    el.svg.addEventListener('pointercancel', (event) => finishDrag(event, true));
    el.edit.onclick = () => setMode('edit'); el.camera.onclick = () => setMode('camera');
    el.left.onclick = () => turn(-1); el.right.onclick = () => turn(1); el.published.onclick = loadPublished; el.download.onclick = downloadExact;
    el.undo.onclick = () => { if (state.undo.length) { const previous = state.undo.pop(); state.lines = previous.lines; state.kind = previous.kind; applyWorkbench(state.kind, state.sourceLabel); drawSvg({ geometryChanged:true }); } };
    el.reset.onclick = () => { state.lines = clone(state.original); state.kind = state.origin; state.undo = []; state.pan = { x:0, y:0 }; applyWorkbench(state.kind, state.sourceLabel); drawSvg({ geometryChanged:true }); };
    el.svg.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowDown' || event.key === 'ArrowRight') { event.preventDefault(); select((state.selected + 1) % state.lines.length); }
      if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') { event.preventDefault(); select((state.selected + state.lines.length - 1) % state.lines.length); }
      if (event.key.toLowerCase() === 'z' && state.undo.length) { event.preventDefault(); el.undo.click(); }
    });
  }

  function setMode(mode) {
    state.mode = mode;
    el.edit.setAttribute('aria-pressed', String(mode === 'edit')); el.camera.setAttribute('aria-pressed', String(mode === 'camera'));
    el.hint.textContent = mode === 'edit' ? 'Edit mode: drag only the round handle to slide an exact parallel fence.' : 'Camera mode: drag the tabletop to pan it. Fences will not change.';
  }

  function turn(amount) {
    const baseline = clone(state.lines);
    try {
      const candidate = G.rotateRational(baseline, state.selected, BigInt(amount), 20n);
      applyCandidate(candidate, baseline, { recordUndo:true });
    } catch (error) { reject(error, baseline); }
  }

  function addCylinder(start, end, radius, material) {
    const axis = end.clone().sub(start), length = axis.length();
    const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, length, 8), material);
    mesh.position.copy(start).add(end).multiplyScalar(.5);
    mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0), axis.normalize());
    scene.add(mesh); fenceObjects.push(mesh);
  }

  function setCamera(position) { camera.position.copy(position); camera.lookAt(target); resize(); }

  function zoom(direction) {
    const vector = camera.position.clone().sub(target), next = Math.max(5, Math.min(42, vector.length() + direction));
    setCamera(target.clone().add(vector.setLength(next)));
  }

  function initThree() {
    if (!window.THREE || !window.WebGLRenderingContext) { el.fallback.hidden = false; const paragraph = el.fallback.querySelector('p:last-child'), link = document.createElement('a'); link.href = 'index.html#kobon'; link.textContent = 'Open the 2D explanation'; paragraph.replaceChildren(document.createTextNode('WebGL is unavailable. The editable 2D tabletop below remains available and its score is exact. '), link); return; }
    try { renderer = new THREE.WebGLRenderer({ antialias:true, alpha:true }); } catch (_) { el.fallback.hidden = false; return; }
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2)); renderer.shadowMap.enabled = true; el.stage.append(renderer.domElement);
    scene = new THREE.Scene(); scene.background = new THREE.Color(0xdce3e5);
    camera = new THREE.PerspectiveCamera(38, 1, .1, 100); target = new THREE.Vector3(0, .2, 0); camera.position.set(17, 16, 20); camera.lookAt(target); raycaster = new THREE.Raycaster();
    scene.add(new THREE.HemisphereLight(0xf6f0df, 0x244a3f, 1.9));
    const lamp = new THREE.DirectionalLight(0xffeed1, 1.4); lamp.position.set(8,18,10); lamp.castShadow = true; scene.add(lamp);
    const table = new THREE.Mesh(new THREE.BoxGeometry(28, .55, 19), new THREE.MeshStandardMaterial({ color:0x356f5c, roughness:.82 })); table.position.y = 0; table.receiveShadow = true; scene.add(table);
    const trim = new THREE.Mesh(new THREE.BoxGeometry(28.5, .2, 19.5), new THREE.MeshStandardMaterial({ color:0x5d4331, roughness:.65 })); trim.position.y = -.32; scene.add(trim);
    new ResizeObserver(resize).observe(el.stage); window.addEventListener('resize', resize); attachCamera();
  }

  function disposeObjects(objects) {
    objects.forEach((object) => { scene.remove(object); object.geometry?.dispose(); if (Array.isArray(object.material)) object.material.forEach((material) => material.dispose()); else object.material?.dispose(); });
  }

  function renderThree(map) {
    if (!renderer || !map) return;
    disposeObjects(meshes); disposeObjects(fenceObjects); meshes = []; fenceObjects = [];
    const world = (x, y, height = 0) => new THREE.Vector3((x - 360) / 28, height, (240 - y) / 28);
    state.faces.forEach((triple, index) => {
      const points = G.vertices(state.lines, triple).map(([x,y]) => world(map.x(x), map.y(y), .5));
      const geometry = new THREE.BufferGeometry().setFromPoints(points); geometry.setIndex([0,1,2]); geometry.computeVertexNormals();
      const selected = index === state.selectedFace;
      const material = new THREE.MeshStandardMaterial({ color:selected ? 0xf6d083 : 0xbd674b, side:THREE.DoubleSide, transparent:true, opacity:selected ? .97 : .76, roughness:.6, emissive:selected ? 0x51200b : 0x000000 });
      const mesh = new THREE.Mesh(geometry, material); mesh.userData.face = index; mesh.castShadow = true; scene.add(mesh); meshes.push(mesh);
    });
    const rail = new THREE.MeshStandardMaterial({ color:0xf2ecda, roughness:.55, metalness:.05 });
    const activeRail = new THREE.MeshStandardMaterial({ color:0xc84238, roughness:.5 });
    state.lines.forEach((line, index) => {
      const end = clipped(line, map); if (!end) return;
      const material = index === state.selected ? activeRail : rail;
      const first = world(map.x(end[0][0]), map.y(end[0][1])), second = world(map.x(end[1][0]), map.y(end[1][1]));
      addCylinder(first.clone().setY(.46), first.clone().setY(1.45), .055, material);
      addCylinder(second.clone().setY(.46), second.clone().setY(1.45), .055, material);
      addCylinder(first.clone().setY(.78), second.clone().setY(.78), .045, material);
      addCylinder(first.clone().setY(1.23), second.clone().setY(1.23), .045, material);
    });
    resize();
  }

  function resize() {
    if (!renderer) return;
    const width = el.stage.clientWidth, height = el.stage.clientHeight;
    if (!width || !height) return;
    renderer.setSize(width, height, false); camera.aspect = width / height; camera.updateProjectionMatrix(); renderer.render(scene, camera);
  }

  function selectFaceFromCanvas(event) {
    const rect = renderer.domElement.getBoundingClientRect();
    raycaster.setFromCamera(new THREE.Vector2(((event.clientX - rect.left) / rect.width) * 2 - 1, -((event.clientY - rect.top) / rect.height) * 2 + 1), camera);
    const hit = raycaster.intersectObjects(meshes, false)[0];
    if (hit) showFace(hit.object.userData.face);
  }

  function attachCamera() {
    const canvas = renderer.domElement; let pointer;
    canvas.addEventListener('pointerdown', (event) => { pointer = { x:event.clientX, y:event.clientY, moved:false }; canvas.setPointerCapture(event.pointerId); });
    canvas.addEventListener('pointermove', (event) => { if (!pointer) return; const x = event.clientX - pointer.x, y = event.clientY - pointer.y; pointer.moved ||= Math.abs(x) + Math.abs(y) > 3; if (!pointer.moved) return; camera.position.x -= x * .025; camera.position.z += y * .025; camera.lookAt(target); pointer = { ...pointer, x:event.clientX, y:event.clientY }; resize(); });
    const finish = (event) => { if (!pointer) return; try { canvas.releasePointerCapture(event.pointerId); } catch (_) { } const wasClick = !pointer.moved; pointer = null; if (wasClick) selectFaceFromCanvas(event); };
    canvas.addEventListener('pointerup', finish); canvas.addEventListener('pointercancel', () => { pointer = null; });
    el.stage.addEventListener('keydown', (event) => {
      const key = event.key.toLowerCase();
      if (key === 'arrowleft') { event.preventDefault(); camera.position.x -= 2; setCamera(camera.position); }
      else if (key === 'arrowright') { event.preventDefault(); camera.position.x += 2; setCamera(camera.position); }
      else if (key === 'arrowup') { event.preventDefault(); camera.position.y += 2; setCamera(camera.position); }
      else if (key === 'arrowdown') { event.preventDefault(); camera.position.y = Math.max(3, camera.position.y - 2); setCamera(camera.position); }
      else if (key === '+' || key === '=') { event.preventDefault(); zoom(-2); }
      else if (key === '-') { event.preventDefault(); zoom(2); }
      else if (key === 't') { event.preventDefault(); setCamera(new THREE.Vector3(0,25,.1)); }
    });
    canvas.addEventListener('wheel', (event) => { event.preventDefault(); zoom(event.deltaY > 0 ? 2 : -2); }, { passive:false });
    el.top.onclick = () => setCamera(new THREE.Vector3(0,25,.1)); el.fit.onclick = () => setCamera(new THREE.Vector3(17,16,20)); el.central.onclick = () => setCamera(new THREE.Vector3(8,8,10));
    el.orbitLeft.onclick = () => { camera.position.x -= 2; setCamera(camera.position); }; el.orbitRight.onclick = () => { camera.position.x += 2; setCamera(camera.position); };
    el.orbitUp.onclick = () => { camera.position.y += 2; setCamera(camera.position); }; el.orbitDown.onclick = () => { camera.position.y = Math.max(3, camera.position.y - 2); setCamera(camera.position); };
  }

  function applyWorkbench(kind, label = '') {
    state.kind = kind;
    if (kind === 'published') {
      el.eyebrow.textContent = 'Published 93 · editable copy'; el.workbenchTitle.textContent = 'Move any of the eighteen fences.';
      el.workbenchDescription.textContent = 'This begins from the supplied 93-face published construction. Select any numbered fence, drag it parallel with a scale-aware screen mapping, or use a small exact rational rotation. The live score is computational evidence, not a novelty claim.'; el.reset.textContent = 'Reset published 93';
    } else if (kind === 'motion' || kind === 'editedMotion') {
      const edited = kind === 'editedMotion';
      el.eyebrow.textContent = edited ? 'Edited saved motion frame' : 'Saved motion frame'; el.workbenchTitle.textContent = `Frame at offset ${formatOffset(state.frame.offset)}.`;
      el.workbenchDescription.textContent = edited ? 'This is now a local edited copy. Reset restores the supplied exact frame.' : 'This is a supplied exact frame. Its fence equations and faces are rendered together; editing creates a separate local copy.'; el.reset.textContent = `Reset frame ${formatOffset(state.frame.offset)}`;
    } else if (kind === 'snapshot' || kind === 'editedSnapshot') {
      const edited = kind === 'editedSnapshot';
      el.eyebrow.textContent = edited ? 'Edited saved arrangement · local copy' : 'Saved arrangement · editable copy'; el.workbenchTitle.textContent = edited ? `Edited copy of ${label}.` : `Inspect ${label}.`;
      el.workbenchDescription.textContent = edited ? 'This local edited copy is separate from the saved source. Reset restores the supplied exact arrangement.' : 'This is a supplied exact arrangement. Select a fence to explore a separate local copy; the saved source remains unchanged.'; el.reset.textContent = `Reset saved ${label}`;
    } else {
      el.eyebrow.textContent = 'A four-line warm-up'; el.workbenchTitle.textContent = 'Make a triangle, then try to protect it.';
      el.workbenchDescription.textContent = 'Choose any fence. In Edit mode, drag its round handle to slide it parallel. The nudge buttons apply a small rational rotation, then every move snaps to an exact integer equation before scoring.'; el.reset.textContent = 'Reset puzzle';
    }
  }

  function loadSaved(kind, lines, { snapshot = null, frame = null, label = '' } = {}) {
    state.snapshot = snapshot; state.motionIndex = frame ? state.motion.frames.indexOf(frame) : null; state.frame = frame; state.origin = kind; state.kind = kind; state.sourceLabel = label; state.original = clone(lines); state.lines = clone(lines); state.selected = 0; state.undo = []; state.pan = { x:0, y:0 };
    applyWorkbench(kind, label); picker(); drawSvg({ geometryChanged:true });
  }

  function loadPublished() {
    const published = state.snapshots.find((snapshot) => snapshot.score === 93);
    if (published) loadSaved('published', rawLines(published));
  }

  function loadWarmup() { loadSaved('warmup', PUZZLE); }

  function downloadExact() {
    const blob = new Blob([G.exportJSON(state.lines)], { type:'application/json' }), url = URL.createObjectURL(blob), anchor = document.createElement('a');
    anchor.href = url; anchor.download = state.kind === 'published' ? 'edited-published-93-lines.json' : 'fence-lines.json'; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 0);
  }

  function picker() {
    el.picker.replaceChildren();
    state.snapshots.forEach((snapshot, index) => {
      const button = document.createElement('button'); button.type = 'button'; button.textContent = `${snapshot.label} · ${snapshot.score} faces`;
      button.setAttribute('aria-pressed', String(state.kind === 'snapshot' && index === state.snapshot));
      button.onclick = () => loadSaved('snapshot', rawLines(snapshot), { snapshot:index, label:snapshot.label }); el.picker.append(button);
    });
  }

  function loadMotion(index) {
    const frame = state.motion.frames[index];
    if (!frame) return;
    el.slider.value = String(index); el.frameReadout.textContent = formatOffset(frame.offset); el.motionScore.textContent = String(frame.score); el.changed.textContent = `+${frame.gained.length} / −${frame.lost.length}`;
    loadSaved('motion', rawLines(frame), { frame, label:`motion frame ${formatOffset(frame.offset)}` });
  }

  function setupMotion() {
    const motion = window.LEARNING_DATA.kobon.motion;
    if (!motion) return;
    state.motion = motion; el.lesson.hidden = false; el.slider.max = String(motion.frames.length - 1);
    const baseIndex = motion.frames.findIndex((frame) => Number(frame.offset) === 0), base = motion.frames[baseIndex];
    el.slider.value = String(baseIndex); el.frameReadout.textContent = formatOffset(base.offset); el.motionScore.textContent = String(base.score); el.changed.textContent = `+${base.gained.length} / −${base.lost.length}`;
    el.slider.oninput = () => loadMotion(Number(el.slider.value)); el.resetMotion.onclick = () => loadMotion(baseIndex);
  }

  function init() {
    if (!G || !window.LEARNING_DATA?.kobon?.snapshots) { el.readout.textContent = 'The local geometry data or exact scorer is unavailable.'; return; }
    state.snapshots = window.LEARNING_DATA.kobon.snapshots; initThree(); attachEditor(); setupMotion(); loadWarmup();
    el.next.onclick = () => showFace((state.selectedFace ?? -1) + 1); el.previous.onclick = () => showFace((state.selectedFace ?? 0) - 1);
    el.loading.hidden = true;
  }

  init();
})();
