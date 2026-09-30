(() => {
  'use strict';
  const G = window.FenceGeometry, $ = (id) => document.getElementById(id);
  const el = { tableTitle:$('tableTitle'), eyebrow:$('workbenchEyebrow'), workbenchTitle:$('fenceWorkbenchTitle'), workbenchDescription:$('workbenchDescription'), published:$('editPublished'), download:$('downloadFence'), readout:$('recordReadout'), picker:$('snapshotPicker'), svg:$('fenceSvg'), faces:$('fenceFaces'), lines:$('fenceLines'), handles:$('fenceHandles'), list:$('fenceList'), score:$('liveScore'), hint:$('dragHint'), edit:$('editMode'), pan:$('panMode'), left:$('turnLeft'), right:$('turnRight'), undo:$('undoFence'), reset:$('resetFence'), slider:$('motionSlider'), frameReadout:$('motionFrameReadout'), motionScore:$('motionScore'), changed:$('motionChanged'), resetMotion:$('resetMotion'), lesson:$('motionLesson'), next:$('nextFace'), previous:$('previousFace'), faceTitle:$('faceTitle'), faceExplanation:$('faceExplanation'), support:$('supportDetails'), supportLines:$('supportLines') };
  const PUZZLE = [[1n,0n,-220n],[0n,1n,-320n],[1n,-1n,20n],[0n,1n,-220n]];
  const ns = 'http://www.w3.org/2000/svg';
  const tag = (name, attributes = {}) => { const node = document.createElementNS(ns, name); Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value)); return node; };
  const clone = (lines) => lines.map((line) => [...line]);
  const state = { snapshots:[], snapshot:null, lines:[], original:[], selected:0, undo:[], mode:'edit', drag:null, pan:{x:0,y:0}, motion:null, motionIndex:null, frame:null, faces:[], selectedFace:null, kind:'warmup', origin:'warmup', sourceLabel:'', map:null, zoom:1, viewBounds:null, pivot:null, suppressClick:false, turnVector:null };
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
    el.faceTitle.textContent = 'Pick a yard';
    el.faceExplanation.textContent = 'Click a shaded yard to see its three fences.';
    el.supportLines.replaceChildren();
    el.support.hidden = true;
  }

  const yardCount = score => `${score} triangular ${score === 1 ? 'yard' : 'yards'}`;

  function sourceDescription(score) {
    if (state.kind === 'published') return `Your copy of Bader’s 93: ${yardCount(score)}, counted live as you edit.`;
    if (state.kind === 'editedMotion') return `Your edit of the position at offset ${formatOffset(state.frame.offset)}: ${yardCount(score)}, counted live. Reset brings back the saved position.`;
    if (state.kind === 'motion') return `Saved position at offset ${formatOffset(state.frame.offset)}: ${yardCount(score)}, recounted exactly when it loaded.`;
    if (state.kind === 'editedSnapshot') return `Your edit of saved ${state.sourceLabel}: ${yardCount(score)}, counted live. Reset brings back the saved drawing.`;
    if (state.kind === 'snapshot') return `Saved ${state.sourceLabel}: ${yardCount(score)}, recounted exactly when it loaded.`;
    return `Live warm-up: ${yardCount(score)}. The count updates as you move.`;
  }

  function scoreLabel(score) {
    if (state.kind === 'published') return `Your copy of Bader’s 93: ${yardCount(score)}`;
    if (state.kind === 'editedMotion') return `Edited copy of saved position ${formatOffset(state.frame.offset)}: ${yardCount(score)}`;
    if (state.kind === 'motion') return `Saved position ${formatOffset(state.frame.offset)}: ${yardCount(score)}`;
    if (state.kind === 'editedSnapshot') return `Your edit of saved ${state.sourceLabel}: ${yardCount(score)}`;
    if (state.kind === 'snapshot') return `Saved ${state.sourceLabel}: ${yardCount(score)}`;
    return `${yardCount(score)}`;
  }

  function updateExact() {
    el.tableTitle.textContent = state.lines.length === 4 ? '4 fences. A small warm-up.' : `${state.lines.length} fences.`;
    const report = G.score(state.lines);
    state.faces = report.faces;
    el.score.textContent = scoreLabel(report.score);
    el.readout.textContent = sourceDescription(report.score);
    if (state.kind === 'motion' && report.score !== state.frame.score) throw new Error(`saved frame score mismatch: expected ${state.frame.score}, got ${report.score}`);
    return report;
  }

  function drawSvg({ geometryChanged = false } = {}) {
    let report;
    try { report = updateExact(); } catch (error) { el.score.textContent = `That move was refused: ${error.message}`; return false; }
    if (geometryChanged) clearFace();
    setMode(state.mode);
    const map = mapFor(state.lines);
    state.map = map;
    el.faces.replaceChildren(); el.lines.replaceChildren(); el.handles.replaceChildren();
    let selectedHit = null;
    report.faces.forEach((triple, index) => {
      const points = G.vertices(state.lines, triple).map(([x,y]) => `${map.x(x)},${map.y(y)}`).join(' ');
      const polygon = tag('polygon', { points, class:`yard${index === state.selectedFace ? ' is-selected' : ''}`, 'data-face':index });
      polygon.addEventListener('click', () => { if (!state.suppressClick) showFace(index); });
      el.faces.append(polygon);
    });
    state.lines.forEach((line, index) => {
      const end = clipped(line, map);
      if (!end) return;
      const selected = index === state.selected, supporting = state.selectedFace !== null && state.faces[state.selectedFace]?.includes(index);
      const path = tag('line', { x1:map.x(end[0][0]), y1:map.y(end[0][1]), x2:map.x(end[1][0]), y2:map.y(end[1][1]), class:`fence ${selected ? 'is-selected' : ''} ${supporting ? 'is-support' : ''}`, 'data-index':index, tabindex:'-1' });
      const hit = path.cloneNode(); hit.setAttribute('class', 'fence-hit'); hit.setAttribute('aria-label', `Drag fence ${index + 1} to move it`);
      if (selected) selectedHit = hit;
      else el.lines.append(hit);
      el.lines.append(path);
      if (selected) {
        const pivot = state.pivot || [(end[0][0] + end[1][0]) / 2, (end[0][1] + end[1][1]) / 2];
        state.pivot = pivot;
        const cx = map.x(pivot[0]), cy = map.y(pivot[1]);
        const [a,b] = line.map(number), norm = Math.hypot(a,b);
        let dx = b / norm, dy = a / norm;
        if (state.turnVector && dx*state.turnVector[0]+dy*state.turnVector[1] < 0) { dx = -dx; dy = -dy; }
        state.turnVector = [dx,dy];
        const screenScale = Math.max(.1, el.svg.getBoundingClientRect().width / 720);
        // Keep the drawing small and touch targets generous at every viewport size.
        const radius = 50 / screenScale, hitRadius = 22 / screenScale;
        const tx = cx + dx * radius, ty = cy + dy * radius;
        el.handles.append(tag('circle', { cx, cy, r:hitRadius, class:'handle-hit move-hit', 'aria-label':'Drag to move this fence' }));
        el.handles.append(tag('circle', { cx, cy, r:5 / screenScale, class:'fence-handle' }));
        el.handles.append(tag('circle', { cx:tx, cy:ty, r:hitRadius, class:'handle-hit turn-hit', 'aria-label':'Drag to turn this fence' }));
        el.handles.append(tag('circle', { cx:tx, cy:ty, r:13 / screenScale, class:'turn-handle' }));
        const icon = tag('text', { x:tx, y:ty, class:'handle-icon', 'text-anchor':'middle', 'dominant-baseline':'central', 'font-size':17 / screenScale }); icon.textContent = '↻'; el.handles.append(icon);
      }
    });
    if (selectedHit) el.lines.append(selectedHit);
    $('selectedEquation').textContent = `Fence ${state.selected + 1}: ${lineText(state.lines[state.selected])}`;
    renderList();
    el.next.disabled = el.previous.disabled = $('focusFace').disabled = !state.faces.length;
    return true;
  }

  function select(index, { focusBoard = false } = {}) {
    state.selected = index; state.pivot = null; state.turnVector = null; drawSvg();
    if (focusBoard) el.svg.focus({ preventScroll:true });
  }

  function showFace(index) {
    if (!state.faces.length) return;
    state.selectedFace = ((index % state.faces.length) + state.faces.length) % state.faces.length;
    const face = state.faces[state.selectedFace];
    el.faceTitle.textContent = `Yard ${state.selectedFace + 1}`;
    el.faceExplanation.textContent = 'These three fences form this yard. No other fence cuts through it.';
    el.supportLines.replaceChildren();
    face.forEach((lineIndex) => { const item = document.createElement('li'); item.textContent = `Fence ${lineIndex + 1}: ${lineText(state.lines[lineIndex])}`; el.supportLines.append(item); });
    el.support.hidden = false;
    drawSvg();
  }

  function renderList() {
    el.list.replaceChildren();
    state.lines.forEach((line, index) => {
      const button = document.createElement('button');
      button.type = 'button'; button.textContent = `Fence ${index + 1}`; button.title = lineText(line); button.dataset.equation = lineText(line);
      button.setAttribute('aria-pressed', String(index === state.selected));
      button.addEventListener('click', () => select(index, { focusBoard:true }));
      const item = document.createElement('li'); item.append(button); el.list.append(item);
    });
    el.undo.disabled = !state.undo.length;
  }

  function reject(error, baseline) {
    state.lines = clone(baseline); state.pivot = null; drawSvg({geometryChanged:true});
    el.hint.textContent = error.message.includes('proportional duplicate') ? 'That would put two fences on the same line. The fence is unchanged.' : `That move can't be counted: ${error.message}. The fence is unchanged.`;
    return false;
  }

  function markEdited() {
    if (state.kind === 'snapshot') state.kind = 'editedSnapshot';
    if (state.kind === 'motion') state.kind = 'editedMotion';
    applyWorkbench(state.kind, state.sourceLabel);
  }

  function applyCandidate(candidate, baseline, { recordUndo = false } = {}) {
    try { G.score(candidate); } catch (error) { return reject(error, baseline); }
    if (recordUndo && candidate.some((line,i) => line.some((value,j) => value !== baseline[i][j]))) state.undo.push({ lines:clone(baseline), kind:state.kind });
    state.lines = candidate;
    markEdited();
    return drawSvg({ geometryChanged:true });
  }

  function moveBy(pointer, baseline) {
    const map = mapFor(baseline), [a,b] = baseline[state.selected];
    const dx = (pointer.x - state.drag.point.x) / map.scale, dy = -(pointer.y - state.drag.point.y) / map.scale;
    const amount = BigInt(Math.round(-(number(a) * dx + number(b) * dy)));
    state.pivot = null;
    try { return applyCandidate(G.translateParallel(baseline, state.selected, amount), baseline); } catch (error) { return reject(error, baseline); }
  }

  function svgPoint(event) { return new DOMPoint(event.clientX, event.clientY).matrixTransform(el.svg.getScreenCTM().inverse()); }

  function yardAt(point) {
    const inside = (a, b, c) => {
      const ab = (b[0] - a[0]) * (point.y - a[1]) - (b[1] - a[1]) * (point.x - a[0]);
      const bc = (c[0] - b[0]) * (point.y - b[1]) - (c[1] - b[1]) * (point.x - b[0]);
      const ca = (a[0] - c[0]) * (point.y - c[1]) - (a[1] - c[1]) * (point.x - c[0]);
      const epsilon = 1e-6;
      return (ab > epsilon && bc > epsilon && ca > epsilon) || (ab < -epsilon && bc < -epsilon && ca < -epsilon);
    };
    return state.faces.findIndex((face) => inside(...G.vertices(state.lines, face).map(([x,y]) => [state.map.x(x), state.map.y(y)])));
  }

  function finishDrag(event, canceled) {
    if (!state.drag || event.pointerId !== state.drag.id) return;
    const drag = state.drag;
    state.drag = null;
    try { el.svg.releasePointerCapture(event.pointerId); } catch (_) { }
    state.suppressClick = drag.moved;
    if (canceled) {
      state.lines = clone(drag.lines); state.kind = drag.kind; state.pan = drag.pan; state.pivot = drag.pivot;
      applyWorkbench(state.kind, state.sourceLabel); drawSvg({ geometryChanged:true }); return;
    }
    if (!drag.moved) {
      const yard = yardAt(svgPoint(event));
      if (yard >= 0) { state.suppressClick = true; showFace(yard); return; }
    }
    if (state.lines.some((line,i) => line.some((value,j) => value !== drag.lines[i][j]))) {
      state.undo.push({ lines:clone(drag.lines), kind:drag.kind });
    } else { state.kind = drag.kind; applyWorkbench(state.kind, state.sourceLabel); }
    renderList();
  }

  function rotatedAt(baseline, angle, pivot) {
    // Pointer input sets an approximate angle. Bound coefficients for repeated turns;
    // verify every resulting snapped integer equation with the exact scorer.
    const precision = Math.max(1e6, state.map.scale * 1e6);
    const a = Math.round(Math.cos(angle) * precision), b = Math.round(Math.sin(angle) * precision);
    const candidate = clone(baseline);
    candidate[state.selected] = [BigInt(a), BigInt(b), BigInt(Math.round(-a * pivot[0] - b * pivot[1]))];
    return G.validate(candidate);
  }

  function turnBy(point, drag) {
    const cx = state.map.x(drag.pivot[0]), cy = state.map.y(drag.pivot[1]);
    if (Math.hypot(point.x-cx, point.y-cy) < 12) return false;
    const start = Math.atan2(drag.point.y-cy, drag.point.x-cx);
    const now = Math.atan2(point.y-cy, point.x-cx);
    const [a,b] = drag.lines[state.selected].map(number);
    const angle = Math.atan2(b,a) - (now-start);
    try { return applyCandidate(rotatedAt(drag.lines, angle, drag.pivot), drag.lines); }
    catch (error) { return reject(error, drag.lines); }
  }

  function attachEditor() {
    el.svg.addEventListener('pointerdown', (event) => {
      if (event.button !== 0 || state.drag) return;
      state.suppressClick = false;
      const handle = event.target.closest?.('.fence-handle,.turn-handle,.handle-hit');
      const line = event.target.closest?.('[data-index]');
      event.preventDefault();
      const point = svgPoint(event), yard = yardAt(point), turning = (handle?.classList.contains('turn-handle') || handle?.classList.contains('turn-hit'));
      if (yard < 0 && line && Number(line.dataset.index) !== state.selected) select(Number(line.dataset.index));
      el.svg.focus({preventScroll:true});
      try { el.svg.setPointerCapture(event.pointerId); } catch (_) { }
      state.drag = { id:event.pointerId, point, lines:clone(state.lines), kind:state.kind,
        pan:{...state.pan}, pivot:state.pivot && [...state.pivot], action:state.mode === 'pan' ? 'pan' : turning ? 'turn' : handle || line ? 'move' : 'select', moved:false };
    });
    el.svg.addEventListener('pointermove', (event) => {
      if (!state.drag || event.pointerId !== state.drag.id) return;
      const point = svgPoint(event), deltaX = point.x - state.drag.point.x, deltaY = point.y - state.drag.point.y;
      state.drag.moved ||= Math.abs(deltaX) + Math.abs(deltaY) > 3;
      if (!state.drag.moved) return;
      if (state.drag.action === 'pan') {
        state.pan = { x:state.drag.pan.x + deltaX, y:state.drag.pan.y + deltaY };
        drawSvg(); return;
      }
      if (state.drag.action === 'select') return;
      if (state.drag.action === 'turn') turnBy(point, state.drag);
      else moveBy(point, state.drag.lines);
    });
    el.svg.addEventListener('pointerup', (event) => finishDrag(event, false));
    el.svg.addEventListener('pointercancel', (event) => finishDrag(event, true));
    el.svg.addEventListener('lostpointercapture', (event) => finishDrag(event, true));
    el.edit.onclick = () => setMode('edit'); el.pan.onclick = () => setMode('pan');
    $('slideLeft').onclick = () => slide(-1); $('slideRight').onclick = () => slide(1);
    $('zoomIn').onclick = () => { state.zoom = Math.min(64, state.zoom * 1.5); state.pivot = null; drawSvg(); };
    $('zoomOut').onclick = () => { state.zoom = Math.max(.25, state.zoom / 1.5); state.pivot = null; drawSvg(); };
    $('fitView').onclick = () => { state.viewBounds = bounds(state.lines); state.pivot = null; state.zoom = 1; state.pan = {x:0,y:0}; drawSvg(); };
    $('focusFace').onclick = focusFace; $('warmup').onclick = loadWarmup;
    el.left.onclick = () => turn(-1); el.right.onclick = () => turn(1); el.published.onclick = loadPublished; el.download.onclick = downloadExact;
    el.undo.onclick = () => { if (state.undo.length) { const previous = state.undo.pop(); state.pivot = null; state.lines = previous.lines; state.kind = previous.kind; applyWorkbench(state.kind, state.sourceLabel); drawSvg({ geometryChanged:true }); } };
    el.reset.onclick = () => { state.pivot = null; state.zoom = 1; state.viewBounds = bounds(state.original); state.lines = clone(state.original); state.kind = state.origin; state.undo = []; state.pan = { x:0, y:0 }; applyWorkbench(state.kind, state.sourceLabel); drawSvg({ geometryChanged:true }); };
    el.svg.closest('.viewer-shell').addEventListener('keydown', (event) => {
      if (event.metaKey || event.ctrlKey || event.altKey || event.target.closest('input,select,textarea,[contenteditable="true"]')) return;
      if (event.key === 'ArrowDown' || event.key === 'ArrowRight') { event.preventDefault(); select((state.selected + 1) % state.lines.length); }
      if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') { event.preventDefault(); select((state.selected + state.lines.length - 1) % state.lines.length); }
      if (event.key === '[' || event.key === ']') { event.preventDefault(); slide(event.key === '[' ? -1 : 1); }
      if (event.key.toLowerCase() === 'q' || event.key.toLowerCase() === 'e') { event.preventDefault(); turn(event.key.toLowerCase() === 'q' ? -1 : 1); }
      if (event.key.toLowerCase() === 'z' && state.undo.length) { event.preventDefault(); el.undo.click(); }
    });
  }

  function setMode(mode) {
    state.mode = mode;
    el.svg.classList.toggle('is-panning', mode === 'pan');
    el.edit.setAttribute('aria-pressed', String(mode === 'edit')); el.pan.setAttribute('aria-pressed', String(mode === 'pan'));
    el.hint.textContent = mode === 'edit' ? 'Drag a fence to slide it. Drag the red ↻ handle to turn it around the center dot.' : 'Drag the board to move the view. The fences stay put.';
  }

  function turn(amount) {
    const baseline = clone(state.lines), [a,b] = baseline[state.selected].map(number);
    if (!state.pivot) { el.hint.textContent = 'The selected fence is outside the view. Zoom out or choose a visible fence to turn it.'; return; }
    try {
      const candidate = rotatedAt(baseline, Math.atan2(b,a) - amount * Math.PI / 18, state.pivot);
      applyCandidate(candidate, baseline, { recordUndo:true });
    } catch (error) { reject(error, baseline); }
  }

  function slide(direction) {
    state.pivot = null;
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
    state.pivot = null; state.zoom = 1; state.pan = {x:0,y:0}; drawSvg();
  }

  function applyWorkbench(kind, label = '') {
    state.kind = kind;
    if (kind === 'published') {
      el.eyebrow.textContent = 'Bader’s 93 · your copy'; el.workbenchTitle.textContent = 'Move any of the 18 fences.';
      el.workbenchDescription.textContent = 'This is your copy of Johannes Bader’s published 93-yard drawing. Edits here do not set a new record.'; el.reset.textContent = 'Reset Bader’s 93'
    } else if (kind === 'motion' || kind === 'editedMotion') {
      const edited = kind === 'editedMotion';
      el.eyebrow.textContent = edited ? 'Saved position · your edit' : 'Saved position'; el.workbenchTitle.textContent = `Fence 1 at offset ${formatOffset(state.frame.offset)}.`;
      el.workbenchDescription.textContent = edited ? 'You are editing your own copy. Reset brings back the saved position.' : 'This position was saved and checked ahead of time. Move any fence to start your own copy.'; el.reset.textContent = `Reset position ${formatOffset(state.frame.offset)}`;
    } else if (kind === 'snapshot' || kind === 'editedSnapshot') {
      const edited = kind === 'editedSnapshot';
      el.eyebrow.textContent = edited ? 'Saved drawing · your edit' : 'Saved drawing'; el.workbenchTitle.textContent = edited ? `Your edit of ${label}.` : `${label}.`;
      el.workbenchDescription.textContent = edited ? 'The saved drawing is unchanged. Reset brings it back.' : 'Move any fence to start your own copy. The saved drawing stays unchanged.'; el.reset.textContent = `Reset saved ${label}`;
    } else {
      el.eyebrow.textContent = 'Warm-up'; el.workbenchTitle.textContent = 'Move a fence and watch yards appear and vanish.';
      el.workbenchDescription.textContent = 'Turn a fence with its red handle until a yard disappears. Then press Undo to bring it back.'; el.reset.textContent = 'Reset warm-up';
    }
  }

  function loadSaved(kind, lines, { snapshot = null, frame = null, label = '' } = {}) {
    state.snapshot = snapshot; state.motionIndex = frame ? state.motion.frames.indexOf(frame) : null; state.frame = frame; state.origin = kind; state.kind = kind; state.sourceLabel = label; state.original = clone(lines); state.lines = clone(lines); state.selected = 0; state.turnVector = null; state.undo = []; state.pan = { x:0, y:0 }; state.pivot = null; state.zoom = 1; state.viewBounds = bounds(lines);
    applyWorkbench(kind, label); picker(); drawSvg({ geometryChanged:true });
    $('quickWarmup').setAttribute('aria-pressed', String(kind === 'warmup'));
    $('quickPublished').setAttribute('aria-pressed', String(kind === 'published'));
  }

  function loadPublished() {
    const published = state.snapshots.find((snapshot) => snapshot.score === 93);
    if (published) loadSaved('published', rawLines(published), { label: 'Bader’s published construction' });
  }

  function loadWarmup() { loadSaved('warmup', PUZZLE); }

  function downloadExact() {
    const blob = new Blob([G.exportJSON(state.lines)], { type:'application/json' }), url = URL.createObjectURL(blob), anchor = document.createElement('a');
    anchor.href = url; anchor.download = state.kind === 'published' ? 'edited-published-93-lines.json' : 'fence-lines.json'; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 0);
  }

  function picker() {
    el.picker.replaceChildren();
    state.snapshots.forEach((snapshot, index) => {
      const button = document.createElement('button'); button.type = 'button'; button.textContent = `${snapshot.label} · ${snapshot.score} yards`;
      button.setAttribute('aria-pressed', String((state.kind === 'snapshot' || state.kind === 'editedSnapshot') && index === state.snapshot));
      button.onclick = () => loadSaved('snapshot', rawLines(snapshot), { snapshot:index, label:snapshot.score === 93 ? 'Bader’s 93-yard construction' : snapshot.label }); el.picker.append(button);
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
    if (!G || !window.LEARNING_DATA?.kobon?.snapshots) { el.readout.textContent = 'The fence data did not load, so nothing was counted.'; return; }
    state.snapshots = window.LEARNING_DATA.kobon.snapshots; attachEditor(); setupMotion(); loadWarmup();
    let boardWidth = el.svg.getBoundingClientRect().width;
    new ResizeObserver(() => {
      const width = el.svg.getBoundingClientRect().width;
      if (width !== boardWidth && !state.drag) { boardWidth = width; drawSvg(); }
    }).observe(el.svg);
    $('quickWarmup').onclick = loadWarmup; $('quickPublished').onclick = loadPublished;
    el.next.onclick = () => showFace((state.selectedFace ?? -1) + 1); el.previous.onclick = () => showFace((state.selectedFace ?? 0) - 1);
  }

  init();
})();
