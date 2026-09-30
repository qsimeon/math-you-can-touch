(() => {
  'use strict';
  const C = window.BeaverCore;
  const $ = id => document.getElementById(id);
  const ui = { tape: $('tape'), tapeSummary: $('tapeSummary'),
    step: $('step'), back: $('back'), run: $('run'), reset: $('reset'), ruleRows: $('ruleRows'),
    preset: $('preset'), title: $('presetTitle'), challenge: $('challenge'), count: $('stepReadout'),
    narration: $('narration'), outcome: $('outcome'), feedback: $('predictionFeedback'), badge: $('robotBadge'),
    compare: $('cycleCompare'), previousLabel: $('previousLabel'), currentLabel: $('currentLabel'),
    previousTape: $('previousTape'), currentTape: $('currentTape'), compareDetail: $('compareDetail') };
  if (!C) { ui.outcome.textContent = 'The robot simulator did not load, so nothing ran.'; return; }
  let table = C.validateTable(C.PRESETS.halt.table);
  let history = [C.initial()], prediction = null, timer = null;
  const frame = () => history[history.length - 1];
  const cell = (n, f) => f.ones.includes(n) ? 1 : 0;
  function stop() {
    if (timer !== null) { clearInterval(timer); timer = null; }
    ui.run.textContent = 'Run';
  }
  function description(f) {
    if (!f.action) return 'The robot starts in state A on a blank tape. Make a prediction, or press Step once to begin.';
    const a = f.action;
    return `Step ${f.step}: in state ${a.from}, the robot read ${a.read} at square ${a.at}. It wrote ${a.write}, moved ${a.move === 'L' ? 'left' : 'right'} to square ${a.head}, then ${a.next === 'H' ? 'halted' : a.next === a.from ? `stayed in state ${a.next}` : `switched to state ${a.next}`}.`;
  }
  function conclusion(f) {
    if (f.status === 'HALTED') return `Halted at step ${f.step}, leaving ${f.ones.length} marked ${f.ones.length === 1 ? 'square' : 'squares'}.`;
    if (f.status === 'NONHALTING_BY_TRANSLATION_CYCLE') {
      const r = f.repeat, offset = r.normalized_ones.length ? r.normalized_ones.join(', ') : 'none';
      return `Proved repeat: steps ${r.previous_step} and ${r.current_step} show the same state ${r.state} and the same complete set of 1s around the robot. ${r.shift === 0 ? 'The robot is back on the same square.' : `The robot has moved ${Math.abs(r.shift)} square${Math.abs(r.shift) === 1 ? '' : 's'} ${r.shift > 0 ? 'right' : 'left'}.`} Every other square is blank and identical rules apply after translation, so it will repeat ${r.period === 1 ? 'this step' : `these ${r.period} steps`} forever and never halt.`;
    }
    if (f.status === 'UNKNOWN_AT_LIMIT') return `Unresolved by this checker at step 100. It saw no halt and no complete repeat. The known two-state theorem shows this robot never halts.`;
    return 'No result yet.';
  }
  function drawTape(f) {
    ui.tape.replaceChildren();
    for (let n = f.head - 4; n <= f.head + 4; n++) {
      const value = cell(n, f), head = n === f.head;
      const tile = document.createElement('div');
      tile.className = `tape-cell${head ? ' is-head' : ''}${value ? ' is-marked' : ''}${f.action?.at === n ? ' just-written' : ''}`;
      tile.setAttribute('aria-label', `Square ${n}: ${value}${head ? ', robot here' : ''}`);
      const symbol = document.createElement('strong'); symbol.textContent = String(value);
      const position = document.createElement('small'); position.textContent = `${head ? 'head ' : ''}${n}`;
      tile.append(symbol, position); ui.tape.append(tile);

    }
    ui.tapeSummary.textContent = `${f.ones.length} marked ${f.ones.length === 1 ? 'square' : 'squares'} on the whole tape${f.ones.some(n => Math.abs(n - f.head) > 4) ? ', some out of view' : ''}.`;
  }
  function renderComparison(f) {
    ui.compare.hidden = !f.repeat;
    if (!f.repeat) return;
    const r = f.repeat;
    const earlier = history[r.previous_step];
    if (!earlier) { ui.compare.hidden = true; return; }
    ui.previousLabel.textContent = `Step ${earlier.step} · state ${earlier.state} · head ${earlier.head}`;
    ui.currentLabel.textContent = `Step ${f.step} · state ${f.state} · head ${f.head}`;
    for (const [container, snapshot] of [[ui.previousTape, earlier], [ui.currentTape, f]]) {
      container.replaceChildren();
      for (let relative = -4; relative <= 4; relative++) {
        const tile = document.createElement('span');
        tile.textContent = String(cell(snapshot.head + relative, snapshot));
        tile.title = `Offset ${relative}: ${tile.textContent}`;
        tile.className = relative === 0 ? 'compare-head' : '';
        container.append(tile);
      }
    }
    const offsets = r.normalized_ones.length ? r.normalized_ones.join(', ') : 'none';
    const outside = r.normalized_ones.length === 0 ? 'Both entire tapes are blank; no square is marked.' : r.normalized_ones.some(position => Math.abs(position) > 4) ? 'Some marks are beyond the nine squares shown.' : 'No marks lie outside the nine squares shown.';
    ui.compareDetail.textContent = `Line up the robot in both rows and they match: the same state and the same complete set of marked offsets (${offsets}). ${outside} Every square beyond is blank in both, so the rest of the run must repeat too.`;
  }
  function render() {
    const f = frame();
    ui.count.textContent = `Step ${f.step} of 100 · state ${f.state} · head at ${f.head}`;
    ui.narration.textContent = description(f);
    ui.outcome.textContent = conclusion(f);
    ui.badge.textContent = `STATE ${f.state} · ${f.state === 'H' ? 'HALTED' : `READS ${cell(f.head, f)}`}`;
    renderComparison(f);
    ui.back.disabled = history.length <= 1;
    ui.step.disabled = f.status !== 'READY' || timer !== null;
    ui.run.disabled = f.status !== 'READY';
    document.querySelectorAll('[data-predict]').forEach(button => { button.disabled = f.step !== 0; });
    if (f.status !== 'READY') ui.feedback.textContent = prediction === null ? 'Reset the tape to make a prediction.' : prediction === f.status ? 'Your prediction matched.' : `Not this time. ${f.status === 'UNKNOWN_AT_LIMIT' ? 'Still running at 100 means the robot neither halted nor repeated within the step limit.' : 'The explanation above shows why.'}`;
    else ui.feedback.textContent = prediction === null ? (f.step === 0 ? 'Pick one, then step or run to find out.' : 'Reset the tape to make a prediction.') : 'Prediction saved. Now step or run.';
    const read = cell(f.head, f);
    for (const row of ui.ruleRows.rows) row.classList.toggle('active-rule', f.state !== 'H' && row.dataset.state === f.state && Number(row.dataset.read) === read);
    drawTape(f);
    const strip = $('actionStrip'); strip.replaceChildren();
    if (f.status !== 'READY') {
      const done = document.createElement('span');
      done.textContent = f.status === 'HALTED' ? 'The robot has stopped.' : f.status === 'UNKNOWN_AT_LIMIT' ? 'The checker stopped at 100 steps without a proof. The known two-state result tells us the robot never halts.' : 'The complete tape pattern has repeated. The robot will not halt.';
      strip.append(done);
    } else {
      const [write, move, next] = table[f.state === 'A' ? 0 : 1][read];
      for (const label of [`Read ${read}`, `Write ${write}`, move === 'L' ? '← Move left' : 'Move right →', next === 'H' ? 'Stop at H' : `Use state ${next}`]) {
        const chip = document.createElement('span'); chip.textContent = label; strip.append(chip);
      }
    }
    strip.setAttribute('aria-label', f.status === 'READY' ? 'Next rule' : 'Result');
  }
  function takeStep() {
    if (frame().status !== 'READY') { stop(); return; }
    history.push(C.advance(table, frame()));
    if (frame().status !== 'READY') stop();
    render();
  }
  function reset(clearPrediction = true) {
    stop(); history = [C.initial()];
    if (clearPrediction) prediction = null;
    document.querySelectorAll('[data-predict]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.predict === prediction)));
    render();
  }
  function ruleSelect(state, read, field, values, current) {
    const select = document.createElement('select');
    select.setAttribute('aria-label', `State ${state}, reads ${read}: ${field}`);
    for (const [value, label] of values) {
      const option = document.createElement('option'); option.value = String(value); option.textContent = label; select.append(option);
    }
    select.value = String(current);
    select.addEventListener('change', () => {
      table[state === 'A' ? 0 : 1][read][{ Write: 0, Move: 1, Next: 2 }[field]] = field === 'Write' ? Number(select.value) : select.value;
      ui.preset.value = 'custom'; ui.title.textContent = 'Your robot';
      ui.challenge.textContent = 'Will this checker see a halt, prove a repeat, or reach step 100 without either?';
      reset();
    });
    return select;
  }
  function fillRules() {
    ui.ruleRows.replaceChildren();
    for (const state of ['A', 'B']) for (const read of [0, 1]) {
      const row = document.createElement('tr'); row.dataset.state = state; row.dataset.read = String(read);
      const name = document.createElement('th'); name.scope = 'row'; name.textContent = `In ${state}, reads ${read}`; row.append(name);
      const action = table[state === 'A' ? 0 : 1][read];
      for (const [field, choices, value] of [
        ['Write', [[0, '0'], [1, '1']], action[0]],
        ['Move', [['L', '← left'], ['R', 'right →']], action[1]],
        ['Next', [['A', 'A'], ['B', 'B'], ['H', 'H (halt)']], action[2]]
      ]) { const td = document.createElement('td'); td.append(ruleSelect(state, read, field, choices, value)); row.append(td); }
      ui.ruleRows.append(row);
    }
  }
  ui.step.addEventListener('click', takeStep);
  ui.back.addEventListener('click', () => { stop(); if (history.length > 1) history.pop(); render(); });
  ui.reset.addEventListener('click', () => reset());
  ui.run.addEventListener('click', () => {
    if (timer !== null) { stop(); render(); return; }
    if (frame().status !== 'READY') return;
    ui.run.textContent = 'Pause'; ui.step.disabled = true;
    timer = setInterval(takeStep, 500);
  });
  ui.preset.addEventListener('change', () => {
    const preset = C.PRESETS[ui.preset.value];
    if (!preset) return;
    table = C.validateTable(preset.table); ui.title.textContent = preset.title; ui.challenge.textContent = preset.description;
    fillRules(); reset();
  });
  document.querySelectorAll('[data-predict]').forEach(button => button.addEventListener('click', () => {
    prediction = button.dataset.predict;
    document.querySelectorAll('[data-predict]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    render();
  }));
  fillRules(); render();
})();
