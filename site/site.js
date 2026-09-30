(() => {
  'use strict';

  const SVG_NS = 'http://www.w3.org/2000/svg';
  const VIEW = { width: 1000, height: 700, padding: 46 };
  const TRACE_CAP = 21;
  const state = {
    data: null, snapshots: [], snapshotIndex: 0, selectedFace: null, facesVisible: true,
    viewBounds: null, traceIndex: 0, traceTimer: null, presentation: false, sceneIndex: 0
  };
  const $ = (id) => document.getElementById(id);
  const el = {
    dataState: $('dataState'), dataStateMessage: $('dataStateMessage'), exhibition: $('exhibition'),
    resultLedger: $('resultLedger'), crossToggle: $('crossToggle'), crossedLesson: $('crossedLesson'), lessonFace: $('lessonFace'), lessonCaption: $('lessonCaption'), lessonExplanation: $('lessonExplanation'),
    snapshotPicker: $('snapshotPicker'), snapshotReadout: $('snapshotReadout'), arrangement: $('arrangement'), arrangementLines: $('arrangementLines'), arrangementFaces: $('arrangementFaces'),
    faceToggle: $('faceToggle'), zoomOut: $('zoomOut'), zoomIn: $('zoomIn'), zoomFace: $('zoomFace'), resetGeometry: $('resetGeometry'), downloadGeometry: $('downloadGeometry'),
    faceCount: $('faceCount'), faceList: $('faceList'), faceExplanation: $('faceExplanation'), supportDetails: $('supportDetails'), supportLines: $('supportLines'),
    searchOutcome: $('searchOutcome'), runRows: $('runRows'), tape: $('tape'), traceStatus: $('traceStatus'), traceReset: $('traceReset'), traceStep: $('traceStep'), traceRun: $('traceRun'), traceFeedback: $('traceFeedback'), transitionTable: $('transitionTable'), beaverSummary: $('beaverSummary'),
    sourceList: $('sourceList'), limitationList: $('limitationList'), formalStatus: $('formalStatus'),
    presentationToggle: $('presentationToggle'), presentationControls: $('presentationControls'), previousScene: $('previousScene'), nextScene: $('nextScene'), exitPresentation: $('exitPresentation'), sceneIndicator: $('sceneIndicator')
  };

  function node(tag, attributes = {}) {
    const result = document.createElementNS(SVG_NS, tag);
    Object.entries(attributes).forEach(([name, value]) => result.setAttribute(name, String(value)));
    return result;
  }
  function clear(element) { element.replaceChildren(); }
  function isNumber(value) { return typeof value === 'number' && Number.isFinite(value); }
  function isNonnegativeInteger(value) { return Number.isInteger(value) && value >= 0; }
  function isIntegerText(value) { return typeof value === 'string' && /^-?(?:0|[1-9]\d*)$/.test(value); }
  function isHttpsUrl(value) { try { return typeof value === 'string' && new URL(value).protocol === 'https:'; } catch { return false; } }
  function text(value, fallback = 'not supplied') { return typeof value === 'string' && value.trim() ? value : fallback; }
  function currentSnapshot() { return state.snapshots[state.snapshotIndex]; }
  function sourceEntries() { return [...state.data.sources, ...state.data.busybeaver.sources]; }
  function validPoint(point) { return Array.isArray(point) && point.length === 2 && point.every(isNumber); }
  function validTriangle(triangle) {
    return triangle && Array.isArray(triangle.indices) && triangle.indices.length === 3 && new Set(triangle.indices).size === 3 && triangle.indices.every((index) => Number.isInteger(index) && index >= 0 && index < 18) && Array.isArray(triangle.vertices) && triangle.vertices.length === 3 && triangle.vertices.every(validPoint);
  }
  function validSnapshot(snapshot) {
    return snapshot && typeof snapshot.id === 'string' && snapshot.id.trim() && typeof snapshot.label === 'string' && isNonnegativeInteger(snapshot.score) && Array.isArray(snapshot.lines) && snapshot.lines.length === 18 && snapshot.lines.every((line) => Array.isArray(line) && line.length === 3 && line.every(isIntegerText) && !(line[0] === '0' && line[1] === '0')) && Array.isArray(snapshot.triangles) && snapshot.score === snapshot.triangles.length && snapshot.triangles.every(validTriangle) && Array.isArray(snapshot.bounds) && snapshot.bounds.length === 4 && snapshot.bounds.every(isNumber) && snapshot.bounds[0] < snapshot.bounds[2] && snapshot.bounds[1] < snapshot.bounds[3];
  }
  function validRun(run) { return run && typeof run.id === 'string' && typeof run.method === 'string' && isNonnegativeInteger(run.seed) && isNonnegativeInteger(run.initial) && isNonnegativeInteger(run.best) && isNonnegativeInteger(run.proposals) && isNumber(run.elapsed_seconds) && run.elapsed_seconds >= 0 && typeof run.stop_reason === 'string'; }
  function validSource(source) { return source && typeof source.title === 'string' && source.title.trim() && isHttpsUrl(source.url); }
  function validTraceState(entry) { return entry && isNonnegativeInteger(entry.step) && typeof entry.state === 'string' && entry.state.trim() && Number.isInteger(entry.head) && Array.isArray(entry.ones) && entry.ones.every(Number.isInteger); }
  function hasExpectedSnapshot(snapshots, id, score) { return snapshots.some((snapshot) => snapshot.id === id && snapshot.score === score); }
  function validData(data) {
    const snapshots = data?.kobon?.snapshots, pilot = data?.kobon?.pilot, beaver = data?.busybeaver, summary = beaver?.summary, champion = beaver?.champion;
    return data && typeof data === 'object' && Array.isArray(snapshots) && snapshots.length > 0 && snapshots.every(validSnapshot) && hasExpectedSnapshot(snapshots, 'our76', 76) && hasExpectedSnapshot(snapshots, 'prior93', 93) && pilot && Array.isArray(pilot.runs) && pilot.runs.every(validRun) && pilot.best === 93 && pilot.improved === false && beaver && summary && isNonnegativeInteger(summary.total) && isNonnegativeInteger(summary.halted) && isNonnegativeInteger(summary.nonhalting) && isNonnegativeInteger(summary.unknown) && summary.total === summary.halted + summary.nonhalting + summary.unknown && isNonnegativeInteger(summary.step_limit) && summary.step_limit > 0 && champion && Array.isArray(champion.table) && champion.table.length > 0 && champion.table.every((row) => Array.isArray(row) && row.length === 2 && row.every((instruction) => Array.isArray(instruction) && instruction.length === 3)) && Array.isArray(champion.trace) && champion.trace.length > 0 && champion.trace.every(validTraceState) && Array.isArray(data.sources) && data.sources.every(validSource) && Array.isArray(beaver.sources) && beaver.sources.every(validSource) && data.formal && typeof data.formal.status === 'string' && typeof data.formal.explanation === 'string';
  }

  function showProblem(message) {
    el.exhibition.hidden = true;
    el.dataState.hidden = false;
    el.dataStateMessage.textContent = message;
  }
  function formatNumber(value) { return isNumber(value) ? new Intl.NumberFormat().format(value) : 'not supplied'; }
  function display(value) { return isNumber(value) ? formatNumber(value) : text(value); }
  function createHtml(tag, content = '', className = '') {
    const result = document.createElement(tag); result.textContent = content; if (className) result.className = className; return result;
  }

  function renderResults() {
    clear(el.resultLedger);
    const original = state.snapshots.find((snapshot) => snapshot.id === 'our76');
    const recovered = state.snapshots.find((snapshot) => snapshot.id === 'prior93');
    const pilot = state.data.kobon.pilot;
    const cards = [
      { label: 'Our original search', value: `${formatNumber(original.score)} yards`, body: `Our local search produced ${formatNumber(original.score)} triangular yards with 18 fences.` },
      { label: 'Bader’s published construction', value: `${formatNumber(recovered.score)} yards`, body: `Johannes Bader’s published construction has ${formatNumber(recovered.score)} triangular yards. We rebuilt it with exact integer coordinates from Pavlo Savchuk’s LineOrder drawing and recounted it.` },
      { label: 'Trying to beat it', value: `${formatNumber(pilot.best)} yards`, body: `${formatNumber(pilot.runs.length)} fixed search runs reported ${formatNumber(pilot.runs.reduce((total, run) => total + run.proposals, 0))} bounded integer changes to Bader’s construction. None reported more than ${formatNumber(pilot.best)}. The full search logs are not included with this site.` }
    ];
    cards.forEach((card) => {
      const article = document.createElement('article');
      article.append(createHtml('p', card.label, 'kicker'), createHtml('p', card.value, 'record-value'), createHtml('p', card.body));
      el.resultLedger.append(article);
    });
  }

  function renderLesson() {
    const crossed = el.crossToggle.checked;
    $('threeLineTitle').textContent = crossed ? 'A fourth fence splits the original yard.' : 'Three fences enclose one triangular yard.';
    $('threeLineDescription').textContent = crossed ? 'The fourth fence cuts the original triangle. The smaller triangular piece counts, and the four-sided piece does not. One yard still counts.' : 'Three fences meet at three corners. No other fence cuts the triangle between them. One yard counts.';
    el.crossedLesson.toggleAttribute('hidden', !crossed);
    $('oldYard').classList.toggle('is-divided', crossed);
    el.lessonCaption.textContent = crossed ? 'The new fence cuts the big yard, so it no longer counts.' : 'Three fences close in one yard.';
    el.lessonExplanation.textContent = crossed ? 'The top piece is a smaller triangle with nothing crossing it, so it counts. The bottom piece has four sides, so it does not. The total is still one yard, but a different one.' : 'Three fences cross at three corners. Nothing cuts through the triangle between them, so it counts as one yard.';
  }

  function snapshotName(snapshot) { return `${text(snapshot.label, snapshot.id)} · ${formatNumber(snapshot.score)} yards`; }
  function setSnapshot(index) {
    state.snapshotIndex = Math.max(0, Math.min(index, state.snapshots.length - 1));
    state.selectedFace = null; state.viewBounds = null;
    renderResults(); renderSnapshotPicker(); renderGeometry(); renderFaceInspector();
  }
  function renderSnapshotPicker() {
    clear(el.snapshotPicker);
    state.snapshots.forEach((snapshot, index) => {
      const button = document.createElement('button'); button.type = 'button'; button.textContent = snapshotName(snapshot);
      button.setAttribute('aria-pressed', String(index === state.snapshotIndex));
      button.addEventListener('click', () => setSnapshot(index)); el.snapshotPicker.append(button);
    });
    const snapshot = currentSnapshot();
    el.snapshotReadout.textContent = `${text(snapshot.label, snapshot.id)}: ${formatNumber(snapshot.score)} yards from ${formatNumber(snapshot.lines.length)} fences.`;
  }
  function rawBounds(snapshot) {
    const xs = [snapshot.bounds[0], snapshot.bounds[2], ...snapshot.triangles.flatMap((face) => face.vertices.map(([x]) => x))];
    const ys = [snapshot.bounds[1], snapshot.bounds[3], ...snapshot.triangles.flatMap((face) => face.vertices.map(([, y]) => y))];
    const xMin = Math.min(...xs), xMax = Math.max(...xs), yMin = Math.min(...ys), yMax = Math.max(...ys);
    const width = Math.max(xMax - xMin, 1e-8), height = Math.max(yMax - yMin, 1e-8), padding = Math.max(width, height) * .06;
    return [xMin - padding, yMin - padding, xMax + padding, yMax + padding];
  }
  function activeBounds() { return state.viewBounds || rawBounds(currentSnapshot()); }
  function mapPoint([x, y], bounds) {
    const [xMin, yMin, xMax, yMax] = bounds;
    const scale = Math.min((VIEW.width - VIEW.padding * 2) / (xMax - xMin), (VIEW.height - VIEW.padding * 2) / (yMax - yMin));
    const w = (xMax - xMin) * scale, h = (yMax - yMin) * scale;
    return [(VIEW.width - w) / 2 + (x - xMin) * scale, VIEW.height - (VIEW.height - h) / 2 - (y - yMin) * scale];
  }
  function clipLine(line, bounds) {
    const [a, b, c] = line.map(Number); if (![a, b, c].every(Number.isFinite)) return null;
    const [xMin, yMin, xMax, yMax] = bounds, points = [];
    const add = (x, y) => { if (Number.isFinite(x) && Number.isFinite(y) && x >= xMin - 1e-7 && x <= xMax + 1e-7 && y >= yMin - 1e-7 && y <= yMax + 1e-7 && !points.some(([px, py]) => Math.abs(px - x) < 1e-7 && Math.abs(py - y) < 1e-7)) points.push([x, y]); };
    if (Math.abs(b) > 1e-14) { add(xMin, -(a * xMin + c) / b); add(xMax, -(a * xMax + c) / b); }
    if (Math.abs(a) > 1e-14) { add(-(b * yMin + c) / a, yMin); add(-(b * yMax + c) / a, yMax); }
    if (points.length < 2) return null;
    let pair = [points[0], points[1]], distance = -1;
    for (let i = 0; i < points.length; i += 1) for (let j = i + 1; j < points.length; j += 1) {
      const next = (points[i][0] - points[j][0]) ** 2 + (points[i][1] - points[j][1]) ** 2;
      if (next > distance) { distance = next; pair = [points[i], points[j]]; }
    }
    return pair;
  }
  function renderGeometry() {
    const snapshot = currentSnapshot(), bounds = activeBounds(), selected = state.selectedFace;
    clear(el.arrangementFaces); clear(el.arrangementLines);
    const selectedLines = selected === null ? [] : snapshot.triangles[selected].indices;
    if (state.facesVisible) snapshot.triangles.forEach((face, index) => {
      const polygon = node('polygon', { points: face.vertices.map((point) => mapPoint(point, bounds).join(',')).join(' '), class: `arrangement-face${selected === index ? ' is-selected' : ''}`, tabindex: selected === index ? 0 : -1, role: 'button', 'aria-label': `Yard ${index + 1}, made by fences ${face.indices.map((line) => line + 1).join(', ')}` });
      polygon.addEventListener('click', () => selectFace(index));
      polygon.addEventListener('keydown', (event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); selectFace(index); } });
      el.arrangementFaces.append(polygon);
    });
    snapshot.lines.forEach((line, index) => {
      const clipped = clipLine(line, bounds); if (!clipped) return;
      const [start, end] = clipped.map((point) => mapPoint(point, bounds));
      el.arrangementLines.append(node('line', { x1: start[0], y1: start[1], x2: end[0], y2: end[1], class: `arrangement-line${selectedLines.includes(index) ? ' is-supporting' : ''}` }));
    });
    const title = el.arrangement.querySelector('title'); const description = el.arrangement.querySelector('desc');
    title.textContent = `${snapshotName(snapshot)} line arrangement`;
    description.textContent = `${formatNumber(snapshot.lines.length)} fences and ${formatNumber(snapshot.triangles.length)} triangular yards. Select a shaded yard to see its three fences.`;
    el.zoomFace.disabled = selected === null;
  }
  function selectFace(index, focusList = false) {
    const count = currentSnapshot().triangles.length; state.selectedFace = ((index % count) + count) % count;
    renderGeometry(); renderFaceInspector(); if (focusList) el.faceList.querySelector('[aria-pressed="true"]')?.focus();
  }
  function renderFaceInspector() {
    const snapshot = currentSnapshot(); clear(el.faceList); el.faceCount.textContent = String(snapshot.triangles.length);
    snapshot.triangles.forEach((face, index) => {
      const item = document.createElement('li'), button = document.createElement('button'); button.type = 'button';
      button.setAttribute('aria-pressed', String(index === state.selectedFace));
      button.append(createHtml('span', `Yard ${index + 1}`), createHtml('span', `Fences ${face.indices.map((line) => line + 1).join(', ')}`));
      button.addEventListener('click', () => selectFace(index, true)); item.append(button); el.faceList.append(item);
    });
    if (state.selectedFace === null) { el.faceExplanation.textContent = 'Click a shaded yard or pick one from the list. With the drawing focused, the left and right arrow keys step through them.'; el.supportDetails.hidden = true; return; }
    const face = snapshot.triangles[state.selectedFace];
    el.faceExplanation.textContent = `Yard ${state.selectedFace + 1} is one triangular yard. The three highlighted fences form its sides, and no other fence crosses it.`;
    el.supportDetails.hidden = false; clear(el.supportLines);
    face.indices.forEach((lineIndex) => el.supportLines.append(createHtml('li', `Fence ${lineIndex + 1}: (${snapshot.lines[lineIndex][0]})x + (${snapshot.lines[lineIndex][1]})y + (${snapshot.lines[lineIndex][2]}) = 0`)));
  }
  function scaleBounds(factor) {
    const [xMin, yMin, xMax, yMax] = activeBounds(), cx = (xMin + xMax) / 2, cy = (yMin + yMax) / 2;
    const width = (xMax - xMin) * factor, height = (yMax - yMin) * factor;
    state.viewBounds = [cx - width / 2, cy - height / 2, cx + width / 2, cy + height / 2]; renderGeometry();
  }
  function zoomSelectedFace() {
    if (state.selectedFace === null) return;
    const vertices = currentSnapshot().triangles[state.selectedFace].vertices, xs = vertices.map(([x]) => x), ys = vertices.map(([, y]) => y);
    const span = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys), 1e-6) * 1.8;
    const cx = (Math.max(...xs) + Math.min(...xs)) / 2, cy = (Math.max(...ys) + Math.min(...ys)) / 2;
    state.viewBounds = [cx - span / 2, cy - span / 2, cx + span / 2, cy + span / 2]; renderGeometry();
  }
  function exactSolutionJson(lines) {
    if (!lines.every((line) => Array.isArray(line) && line.length === 3 && line.every(isIntegerText) && !(line[0] === '0' && line[1] === '0'))) throw new Error('This geometry is not a valid exact line list.');
    return `{"lines":[${lines.map((line) => `[${line.join(',')}]`).join(',')}]}`;
  }
  function downloadLines() {
    try {
      const payload = exactSolutionJson(currentSnapshot().lines);
      const url = URL.createObjectURL(new Blob([payload], { type: 'application/json;charset=utf-8' }));
      const link = document.createElement('a'); link.href = url; link.download = 'solution.json'; link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) { el.faceExplanation.textContent = `The download failed: ${error.message}`; }
  }

  function methodLabel(method) {
    return { translate: 'Slide one fence', tilt: 'Tilt or shift one fence' }[method] || text(method);
  }
  function roundedSeconds(seconds) { return `${seconds.toFixed(2)} s`; }
  function renderSearch() {
    const runs = state.data.kobon.pilot.runs;
    clear(el.searchOutcome); clear(el.runRows);
    const best = state.data.kobon.pilot.best;
    const proposals = runs.reduce((total, run) => total + run.proposals, 0);
    [{ value: formatNumber(runs.length), label: 'search runs' }, { value: formatNumber(best), label: 'best count, the same as the start' }, { value: formatNumber(proposals), label: 'changes tried' }].forEach((item) => {
      const box = document.createElement('div'); box.append(createHtml('strong', item.value), createHtml('span', item.label)); el.searchOutcome.append(box);
    });
    runs.forEach((run) => {
      const row = document.createElement('tr');
      [run.id, methodLabel(run.method), run.initial, run.best, run.proposals, roundedSeconds(run.elapsed_seconds), ({ proposal_budget:'Used all its tries', time_budget:'Reached its time limit', improved_witness:'Found a better drawing' }[run.stop_reason] || text(run.stop_reason))].forEach((value) => row.append(createHtml('td', display(value))));
      el.runRows.append(row);
    });
  }

  function trace() { return state.data.busybeaver.champion.trace; }
  function traceStateLimit() { return Math.min(trace().length, TRACE_CAP); }
  function currentTrace() { return trace()[state.traceIndex]; }
  function tapeRange(entry) {
    const ones = entry.ones; const min = Math.min(entry.head, ...ones, -5), max = Math.max(entry.head, ...ones, 5);
    const span = Math.min(17, Math.max(11, max - min + 5));
    return [entry.head - Math.floor(span / 2), entry.head + Math.ceil(span / 2)];
  }
  function renderBeaver() {
    const entry = currentTrace(); if (!entry) return;
    const [start, end] = tapeRange(entry); clear(el.tape); const ones = new Set(entry.ones);
    for (let index = start; index <= end; index += 1) {
      const cell = document.createElement('div'); cell.className = `tape-cell${index === entry.head ? ' is-head' : ''}`;
      cell.append(createHtml('span', ones.has(index) ? '1' : '0'), createHtml('small', index === entry.head ? `robot · ${index}` : String(index)));
      if (index === entry.head) { const robot = document.createElement('i'); robot.className = 'robot'; robot.setAttribute('aria-hidden', 'true'); cell.append(robot); }
      el.tape.append(cell);
    }
    el.tape.setAttribute('aria-label', `Saved step ${entry.step}. State ${entry.state}. The robot is at square ${entry.head}. ${entry.ones.length ? `Marked squares: ${entry.ones.join(', ')}.` : 'No squares are marked.'} Every other square is blank.`);
    const limit = traceStateLimit();
    el.traceStatus.textContent = `Saved step ${entry.step} of ${trace()[limit - 1].step} · state ${entry.state}${entry.state === 'H' ? ' (halted)' : ''}`;
    el.traceStep.disabled = state.traceIndex >= limit - 1;
    renderTransitionTable(entry); renderBeaverSummary();
  }
  function renderTransitionTable(entry) {
    clear(el.transitionTable); const table = state.data.busybeaver.champion.table; const currentSymbol = entry.ones.includes(entry.head) ? 1 : 0;
    table.forEach((row, stateIndex) => row.forEach((instruction, read) => {
      const item = document.createElement('div'); const stateName = String.fromCharCode(65 + stateIndex); const active = entry.state === stateName && currentSymbol === read;
      item.className = `transition-row${active ? ' is-active' : ''}`;
      const value = `write ${instruction[0]}, move ${instruction[1] === 'L' ? 'left' : 'right'}, ${instruction[2] === 'H' ? 'halt' : `go to ${instruction[2]}`}`;
      item.append(createHtml('span', `In ${stateName}, reading ${read}`), createHtml('code', value)); el.transitionTable.append(item);
    }));
  }
  function renderBeaverSummary() {
    clear(el.beaverSummary); const summary = state.data.busybeaver.summary;
    [
      { label: 'robots halted', value: summary.halted },
      { label: 'proved to keep running by a complete repeated pattern', value: summary.nonhalting },
      { label: 'unresolved by our checker at 100 steps', value: summary.unknown },
      { label: 'steps per robot, at most', value: summary.step_limit }
    ].forEach((item) => {
      const paragraph = document.createElement('p'); paragraph.append(createHtml('strong', formatNumber(item.value)), document.createTextNode(` ${item.label}.`)); el.beaverSummary.append(paragraph);
    });
  }
  function resetTrace() { stopTrace(); state.traceIndex = 0; renderBeaver(); el.traceFeedback.textContent = 'Back to the start.'; }
  function nextTrace() {
    const limit = traceStateLimit();
    if (state.traceIndex >= limit - 1) { stopTrace(); el.traceFeedback.textContent = `That is the end of the saved run, at step ${currentTrace().step}.`; return; }
    state.traceIndex += 1; renderBeaver(); el.traceFeedback.textContent = `Step ${currentTrace().step}: the robot is now in state ${currentTrace().state}.`;
  }
  function stopTrace() { if (state.traceTimer) window.clearInterval(state.traceTimer); state.traceTimer = null; el.traceRun.setAttribute('aria-pressed', 'false'); el.traceRun.textContent = 'Play'; }
  function runTrace() {
    if (state.traceTimer) { stopTrace(); el.traceFeedback.textContent = 'Paused.'; return; }
    if (state.traceIndex >= traceStateLimit() - 1) state.traceIndex = 0;
    el.traceRun.setAttribute('aria-pressed', 'true'); el.traceRun.textContent = 'Pause'; el.traceFeedback.textContent = 'Playing four steps per second.';
    state.traceTimer = window.setInterval(nextTrace, 250);
  }

  function renderSources() {
    clear(el.sourceList); clear(el.limitationList);
    const uniqueSources = new Map(); sourceEntries().forEach((source) => { if (isHttpsUrl(source.url) && !uniqueSources.has(source.url)) uniqueSources.set(source.url, source); });
    if (!uniqueSources.size) el.sourceList.append(createHtml('li', 'No sources were included.'));
    uniqueSources.forEach((source) => { const item = document.createElement('li'), link = document.createElement('a'); link.href = source.url; link.target = '_blank'; link.rel = 'noreferrer'; link.textContent = text(source.title, source.url); item.append(link); el.sourceList.append(item); });
    const limits = Array.isArray(state.data.busybeaver.limitations) ? state.data.busybeaver.limitations : [];
    if (!limits.length) el.limitationList.append(createHtml('li', 'No limits were included.'));
    limits.forEach((limit) => el.limitationList.append(createHtml('li', text(limit).replace('UNKNOWN_AT_LIMIT', 'Unresolved by this checker'))));
    const formal = state.data.formal || {}; el.formalStatus.textContent = text(formal.explanation, '');
  }

  function scenes() { return [...document.querySelectorAll('[data-scene]')]; }
  function updatePresentation() {
    const all = scenes(), current = all[state.sceneIndex]; el.sceneIndicator.textContent = `Scene ${state.sceneIndex + 1} of ${all.length}: ${current.dataset.scene}`;
    el.previousScene.disabled = state.sceneIndex === 0; el.nextScene.disabled = state.sceneIndex === all.length - 1;
  }
  function goScene(delta) { const all = scenes(); state.sceneIndex = Math.max(0, Math.min(all.length - 1, state.sceneIndex + delta)); all[state.sceneIndex].scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' }); updatePresentation(); }
  function setPresentation(active) {
    state.presentation = active; document.body.classList.toggle('presentation-active', active); el.presentationControls.hidden = !active; el.presentationToggle.setAttribute('aria-pressed', String(active)); el.presentationToggle.textContent = active ? 'Exit presentation mode' : 'Presentation mode ↗';
    if (active) { state.sceneIndex = Math.max(0, scenes().findIndex((scene) => scene.getBoundingClientRect().top >= -10)); updatePresentation(); }
  }

  function bind() {
    el.crossToggle.addEventListener('change', renderLesson);
    el.faceToggle.addEventListener('click', () => { state.facesVisible = !state.facesVisible; el.faceToggle.textContent = state.facesVisible ? 'Hide shading' : 'Show shading'; el.faceToggle.setAttribute('aria-pressed', String(state.facesVisible)); renderGeometry(); });
    el.zoomIn.addEventListener('click', () => scaleBounds(.7)); el.zoomOut.addEventListener('click', () => scaleBounds(1.4)); el.zoomFace.addEventListener('click', zoomSelectedFace);
    el.resetGeometry.addEventListener('click', () => { state.viewBounds = null; renderGeometry(); }); el.downloadGeometry.addEventListener('click', downloadLines);
    el.arrangement.addEventListener('keydown', (event) => { if (event.metaKey || event.ctrlKey || event.altKey || !['ArrowLeft', 'ArrowRight'].includes(event.key) || !currentSnapshot().triangles.length) return; event.preventDefault(); event.stopPropagation(); selectFace((state.selectedFace ?? (event.key === 'ArrowRight' ? -1 : 0)) + (event.key === 'ArrowRight' ? 1 : -1)); });
    el.traceReset.addEventListener('click', resetTrace); el.traceStep.addEventListener('click', nextTrace); el.traceRun.addEventListener('click', runTrace);
    el.presentationToggle.addEventListener('click', () => setPresentation(!state.presentation)); el.previousScene.addEventListener('click', () => goScene(-1)); el.nextScene.addEventListener('click', () => goScene(1)); el.exitPresentation.addEventListener('click', () => setPresentation(false));
    document.addEventListener('keydown', (event) => { if (event.key === 'Escape' && state.presentation) setPresentation(false); else if (state.presentation && event.key === 'ArrowRight') { event.preventDefault(); goScene(1); } else if (state.presentation && event.key === 'ArrowLeft') { event.preventDefault(); goScene(-1); } });
  }
  function initialize() {
    const data = window.LEARNING_DATA;
    if (!validData(data)) { showProblem('The saved data failed its checks, so the page is hiding every number and drawing. Check data.js and reload.'); return; }
    state.data = data; state.snapshots = data.kobon.snapshots;
    const preferred = state.snapshots.findIndex((snapshot) => /our|76|best/i.test(`${snapshot.id} ${snapshot.label || ''}`)); state.snapshotIndex = preferred >= 0 ? preferred : 0;
    el.dataState.hidden = true; el.exhibition.hidden = false;
    renderLesson(); renderResults(); renderSnapshotPicker(); renderGeometry(); renderFaceInspector(); renderSearch(); renderBeaver(); renderSources(); bind();
  }
  initialize();
})();
