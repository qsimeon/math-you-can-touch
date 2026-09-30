(() => {
  'use strict';
  const G = window.FenceGeometry, $ = (id) => document.getElementById(id);
  const el = { tableTitle:$('tableTitle'), eyebrow:$('workbenchEyebrow'), workbenchTitle:$('fenceWorkbenchTitle'), workbenchDescription:$('workbenchDescription'), published:$('editPublished'), download:$('downloadFence'), readout:$('recordReadout'), picker:$('snapshotPicker'), svg:$('fenceSvg'), faces:$('fenceFaces'), lines:$('fenceLines'), handles:$('fenceHandles'), list:$('fenceList'), score:$('liveScore'), hint:$('dragHint'), edit:$('editMode'), pan:$('panMode'), left:$('turnLeft'), right:$('turnRight'), undo:$('undoFence'), reset:$('resetFence'), slider:$('motionSlider'), frameReadout:$('motionFrameReadout'), motionScore:$('motionScore'), changed:$('motionChanged'), resetMotion:$('resetMotion'), lesson:$('motionLesson'), next:$('nextFace'), previous:$('previousFace'), faceTitle:$('faceTitle'), faceExplanation:$('faceExplanation'), support:$('supportDetails'), supportLines:$('supportLines') };
  const PUZZLE = [[1n,0n,-220n],[0n,1n,-320n],[1n,-1n,20n],[0n,1n,-220n]];
  const ns = 'http://www.w3.org/2000/svg';
  const tag = (name, attributes = {}) => { const node = document.createElementNS(ns, name); Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value)); return node; };
  const clone = (lines) => lines.map((line) => [...line]);
  const state = { snapshots:[], snapshot:null, lines:[], original:[], selected:0, undo:[], mode:'edit', drag:null, pan:{x:0,y:0}, motion:null, motionIndex:null, frame:null, faces:[], selectedFace:null, kind:'warmup', origin:'warmup', sourceLabel:'', map:null, zoom:1, viewBounds:null };
  const number = (value) => Number(value);
  const rawLines = (record) => record.lines.map((row) => row.map(BigInt));
  const formatOffset = (offset) => Number(offset) > 0 ? `+${offset}` : String(offset);
  const lineText = (line) => `${line[0]}x ${BigInt(line[1]) < 0n ? '−' : '+'} ${BigInt(line[1]) < 0n ? -BigInt(line[1]) : line[1]}y ${BigInt(line[2]) < 0n ? '−' : '+'} ${BigInt(line[2]) < 0n ? -BigInt(line[2]) : line[2]} = 0`;

  function bounds(lines) {
    // Remote intersections need not bound any face. Frame the counted regions first.
    const points = G.score(lines).faces.flatMap(triple => G.vertices(lines, triple));
    if (!points.length) {
      for (let first = 0; first < lines.length; first += 1) for (let second = first + 1; second < lines.length; second += 1) {
        const point = G.intersection(lines[first], lines[second]);
        if (point) points.push([number(point[0]) / number(point[2]), number(point[1]) / number(point[2])]);
      }
    }
    if (!points.length) return [-10,-10,10,10];
    const xs = points.map((point) => point[0]), ys = points.map((point) => point[1]);
    const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys), pad = Math.max(maxX - minX, maxY - minY, .1) * .12;
    return [minX - pad, minY - pad, maxX + pad, maxY + pad];
  }

  function mapFor(lines) {
    const b = state.viewBounds || bounds(lines), width = 720, height = 480, span = Math.max(b[2] - b[0], b[3] - b[1]), scale = Math.min((width - 48) / span, (height - 48) / span) * state.zoom;
    return { b, scale, x:(x) => (x - (b[0] + b[2]) / 2) * scale + width / 2 + state.pan.x, y:(y) => height / 2 - (y - (b[1] + b[3]) / 2) * scale + state.pan.y, unx:(x) => (x - width / 2 - state.pan.x) / scale + (b[0] + b[2]) / 2, uny:(y) => (height / 2 - y + state.pan.y) / scale + (b[1] + b[3]) / 2 };
  }

  function clipped(line, map) {
    const [a,b,c] = line.map(number), x0 = map.unx(0), x1 = map.unx(720), y0 = map.uny(480), y1 = map.uny(0), points = [];
    const add = (x, y) => { if (Number.isFinite(x) && Number.isFinite(y) && x >= x0 - 1e-8 && x <= x1 + 1e-8 && y >= y0 - 1e-8 && y <= y1 + 1e-8 && !points.some((point) => Math.hypot(point[0] - x, point[1] - y) < 1e-7)) points.push([x,y]); };
    if (b) { add(x0, -(a * x0 + c) / b); add(x1, -(a * x1 + c) / b); }
    if (a) { add(-(b * y0 + c) / a, y0); add(-(b * y1 + c) / a, y1); }
    return points.length > 1 ? points.slice(0, 2) : null;
  }

  function clearFace() {
    state.selectedFace = null;
    el.faceTitle.textContent = 'Choose a triangular yard';
    el.faceExplanation.textContent = 'Click a shaded triangular yard to highlight the three fences that enclose it.';
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
    if (state.kind === 'published') return `Edited published construction: ${score} triangular yards · exact count`;
    if (state.kind === 'editedMotion') return `Edited copy of saved frame ${formatOffset(state.frame.offset)}: ${score} triangular yards · exact count`;
    if (state.kind === 'motion') return `Saved frame ${formatOffset(state.frame.offset)}: ${score} triangular yards · exact count`;
    if (state.kind === 'editedSnapshot') return `Edited copy of saved ${state.sourceLabel}: ${score} triangular yards · exact count`;
    if (state.kind === 'snapshot') return `Saved ${state.sourceLabel}: ${score} triangular yards · exact count`;
    return `${score} triangular yards · exact count`;
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
    report.faces.forEach((triple, index) => {
      const points = G.vertices(state.lines, triple).map(([x,y]) => `${map.x(x)},${map.y(y)}`).join(' ');
      const polygon = tag('polygon', { points, class:`yard${index === state.selectedFace ? ' is-selected' : ''}`, 'data-face':index });
      polygon.addEventListener('click', () => showFace(index));
      el.faces.append(polygon);
    });
    state.lines.forEach((line, index) => {
      const end = clipped(line, map);
      if (!end) return;
      const selected = index === state.selected, supporting = state.selectedFace !== null && state.faces[state.selectedFace]?.includes(index);
      const path = tag('line', { x1:map.x(end[0][0]), y1:map.y(end[0][1]), x2:map.x(end[1][0]), y2:map.y(end[1][1]), class:`fence ${selected ? 'is-selected' : ''} ${supporting ? 'is-support' : ''}`, 'data-index':index, tabindex:'-1' });
      path.addEventListener('click', () => select(index));
      el.lines.append(path);
      if (selected) {
        const middleX = (end[0][0] + end[1][0]) / 2, middleY = (end[0][1] + end[1][1]) / 2;
        el.handles.append(tag('circle', { cx:map.x(middleX), cy:map.y(middleY), r:11, class:'fence-handle', 'aria-label':'Drag selected fence handle' }));
      }
    });
    renderList();
    el.next.disabled = el.previous.disabled = $('focusFace').disabled = !state.faces.length;
    return true;
  }

  function select(index) { state.selected = index; drawSvg(); }

  function showFace(index) {
    if (!state.faces.length) return;
    state.selectedFace = ((index % state.faces.length) + state.faces.length) % state.faces.length;
    const face = state.faces[state.selectedFace];
    el.faceTitle.textContent = `Face ${state.selectedFace + 1}`;
    el.faceExplanation.textContent = 'These three exact supporting equations enclose this triangular face. No other fence crosses its interior.';
    el.supportLines.replaceChildren();
    face.forEach((lineIndex) => { const item = document.createElement('li'); item.textContent = `Fence ${lineIndex + 1}: ${lineText(state.lines[lineIndex])}`; el.supportLines.append(item); });
    el.support.hidden = false;
    drawSvg();
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
    const dx = (pointer.x - state.drag.point.x) / map.scale, dy = -(pointer.y - state.drag.point.y) / map.scale;
    const amount = BigInt(Math.round(-(number(a) * dx + number(b) * dy)));
    if (!amount) return false;
    try { return applyCandidate(G.translateParallel(baseline, state.selected, amount), baseline); } catch (error) { return reject(error, baseline); }
  }

  function svgPoint(event) { return new DOMPoint(event.clientX, event.clientY).matrixTransform(el.svg.getScreenCTM().inverse()); }

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
      if (state.mode === 'pan') {
        state.pan = { x:state.drag.pan.x + deltaX, y:state.drag.pan.y + deltaY };
        drawSvg();
        return;
      }
      state.lines = clone(state.drag.lines);
      state.drag.changed = moveBy(point, state.drag.lines) || state.drag.changed;
    });
    el.svg.addEventListener('pointerup', (event) => finishDrag(event, false));
    el.svg.addEventListener('pointercancel', (event) => finishDrag(event, true));
    el.edit.onclick = () => setMode('edit'); el.pan.onclick = () => setMode('pan');
    $('slideLeft').onclick = () => slide(-1); $('slideRight').onclick = () => slide(1);
    $('zoomIn').onclick = () => { state.zoom = Math.min(64, state.zoom * 1.5); drawSvg(); };
    $('zoomOut').onclick = () => { state.zoom = Math.max(.25, state.zoom / 1.5); drawSvg(); };
    $('fitView').onclick = () => { state.viewBounds = bounds(state.lines); state.zoom = 1; state.pan = {x:0,y:0}; drawSvg(); };
    $('focusFace').onclick = focusFace; $('warmup').onclick = loadWarmup;
    el.left.onclick = () => turn(-1); el.right.onclick = () => turn(1); el.published.onclick = loadPublished; el.download.onclick = downloadExact;
    el.undo.onclick = () => { if (state.undo.length) { const previous = state.undo.pop(); state.lines = previous.lines; state.kind = previous.kind; applyWorkbench(state.kind, state.sourceLabel); drawSvg({ geometryChanged:true }); } };
    el.reset.onclick = () => { state.zoom = 1; state.viewBounds = bounds(state.original); state.lines = clone(state.original); state.kind = state.origin; state.undo = []; state.pan = { x:0, y:0 }; applyWorkbench(state.kind, state.sourceLabel); drawSvg({ geometryChanged:true }); };
    el.svg.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowDown' || event.key === 'ArrowRight') { event.preventDefault(); select((state.selected + 1) % state.lines.length); }
      if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') { event.preventDefault(); select((state.selected + state.lines.length - 1) % state.lines.length); }
      if (event.key === '[' || event.key === ']') { event.preventDefault(); slide(event.key === '[' ? -1 : 1); }
      if (event.key.toLowerCase() === 'z' && state.undo.length) { event.preventDefault(); el.undo.click(); }
    });
  }

  function setMode(mode) {
    state.mode = mode;
    el.edit.setAttribute('aria-pressed', String(mode === 'edit')); el.pan.setAttribute('aria-pressed', String(mode === 'pan'));
    el.hint.textContent = mode === 'edit' ? 'Edit mode: drag only the round handle to slide an exact parallel fence.' : 'Pan mode: drag the board to move the view. Fences will not change.';
  }

  function turn(amount) {
    const baseline = clone(state.lines);
    try {
      const candidate = G.rotateRational(baseline, state.selected, BigInt(amount), 20n);
      applyCandidate(candidate, baseline, { recordUndo:true });
    } catch (error) { reject(error, baseline); }
  }

  function slide(direction) {
    const baseline = clone(state.lines), [a,b] = baseline[state.selected];
    const amount = BigInt(Math.round(direction * Math.hypot(number(a), number(b)) * 8 / state.map.scale)) || BigInt(direction);
    try { applyCandidate(G.translateParallel(baseline, state.selected, amount), baseline, { recordUndo:true }); }
    catch (error) { reject(error, baseline); }
  }

  function focusFace() {
    if (!state.faces.length) return;
    if (state.selectedFace === null) showFace(0);
    const vertices = G.vertices(state.lines, state.faces[state.selectedFace]);
    const xs = vertices.map(p => p[0]), ys = vertices.map(p => p[1]);
    const pad = Math.max(Math.max(...xs)-Math.min(...xs), Math.max(...ys)-Math.min(...ys), .001) * .3;
    state.viewBounds = [Math.min(...xs)-pad, Math.min(...ys)-pad, Math.max(...xs)+pad, Math.max(...ys)+pad];
    state.zoom = 1; state.pan = {x:0,y:0}; drawSvg();
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
      el.workbenchDescription.textContent = 'Choose any fence. In Edit mode, drag its round handle to slide it parallel. The rotation buttons apply a small rational rotation, then every move snaps to an exact integer equation before scoring.'; el.reset.textContent = 'Reset puzzle';
    }
  }

  function loadSaved(kind, lines, { snapshot = null, frame = null, label = '' } = {}) {
    state.snapshot = snapshot; state.motionIndex = frame ? state.motion.frames.indexOf(frame) : null; state.frame = frame; state.origin = kind; state.kind = kind; state.sourceLabel = label; state.original = clone(lines); state.lines = clone(lines); state.selected = 0; state.undo = []; state.pan = { x:0, y:0 }; state.zoom = 1; state.viewBounds = bounds(lines);
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
      button.setAttribute('aria-pressed', String((state.kind === 'snapshot' || state.kind === 'editedSnapshot') && index === state.snapshot));
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
    state.snapshots = window.LEARNING_DATA.kobon.snapshots; attachEditor(); setupMotion(); loadWarmup();
    el.next.onclick = () => showFace((state.selectedFace ?? -1) + 1); el.previous.onclick = () => showFace((state.selectedFace ?? 0) - 1);
  }

  init();
})();
