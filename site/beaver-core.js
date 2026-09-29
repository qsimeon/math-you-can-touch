/* A bounded, pure simulator for the 2-state/2-symbol blank-tape teaching model.
   UMD: CommonJS for Bun/Node checks; window.BeaverCore for the local page. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.BeaverCore = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const LIMIT = 100;
  const PRESETS = Object.freeze({
    halt: { title: 'The six-step finisher', description: 'Predict: will the finisher halt, prove a repeat, or remain unknown by step 100?', table: [[[1, 'R', 'B'], [1, 'L', 'B']], [[1, 'L', 'A'], [1, 'R', 'H']]] },
    cycle: { title: 'The wandering blank tape', description: 'Predict: will the blank wanderer halt, prove a repeat, or remain unknown by step 100?', table: [[[0, 'R', 'A'], [0, 'R', 'A']], [[0, 'R', 'A'], [0, 'R', 'A']]] },
    unknown: { title: 'The growing trail', description: 'Predict: will the growing trail halt, prove a repeat, or remain unknown by step 100?', table: [[[1, 'R', 'A'], [1, 'R', 'A']], [[1, 'R', 'A'], [1, 'R', 'A']]] }
  });
  function validateTable(table) {
    if (!Array.isArray(table) || table.length !== 2 || table.some(row => !Array.isArray(row) || row.length !== 2)) throw new Error('Exactly two state rows with two symbol rules each are required.');
    for (const row of table) for (const rule of row) {
      if (!Array.isArray(rule) || rule.length !== 3 || ![0, 1].includes(rule[0]) || !['L', 'R'].includes(rule[1]) || !['A', 'B', 'H'].includes(rule[2])) throw new Error('Each rule needs a 0/1 write, L/R move, and A/B/H next state.');
    }
    return table.map(row => row.map(rule => [...rule]));
  }
  function normalized(state, head, ones) {
    return `${state}|${ones.map(position => position - head).sort((a, b) => a - b).join(',')}`;
  }
  function initial() {
    return { step: 0, state: 'A', head: 0, ones: [], seen: { 'A|': [0, 0] }, status: 'READY', repeat: null, action: null };
  }
  function advance(table, previous, limit = LIMIT) {
    validateTable(table);
    if (!Number.isInteger(limit) || limit < 1 || limit > LIMIT) throw new Error('Step limit must be an integer from 1 through 100.');
    if (!previous || !Number.isInteger(previous.step) || !Array.isArray(previous.ones) || !previous.seen || !['A', 'B', 'H'].includes(previous.state)) throw new Error('Invalid simulation state.');
    if (previous.status !== 'READY') return previous;
    if (previous.step >= limit) return { ...previous, status: 'UNKNOWN_AT_LIMIT' };
    const { head, state } = previous;
    const read = previous.ones.includes(head) ? 1 : 0;
    const [write, move, next] = table[state === 'A' ? 0 : 1][read];
    const ones = previous.ones.filter(position => position !== head);
    if (write) ones.push(head);
    ones.sort((a, b) => a - b);
    const newHead = head + (move === 'L' ? -1 : 1);
    const step = previous.step + 1;
    const action = { from: state, read, write, move, next, at: head, head: newHead };
    let status = 'READY', repeat = null;
    const seen = { ...previous.seen };
    if (next === 'H') status = 'HALTED';
    else {
      const signature = normalized(next, newHead, ones);
      const earlier = seen[signature];
      if (earlier) repeat = {
        previous_step: earlier[0], current_step: step, period: step - earlier[0],
        previous_head: earlier[1], current_head: newHead, shift: newHead - earlier[1],
        state: next, normalized_ones: ones.map(position => position - newHead).sort((a, b) => a - b)
      };
      if (repeat) status = 'NONHALTING_BY_TRANSLATION_CYCLE';
      else seen[signature] = [step, newHead];
    }
    if (status === 'READY' && step === limit) status = 'UNKNOWN_AT_LIMIT';
    return { step, state: next, head: newHead, ones, seen, status, repeat, action };
  }
  function simulate(table, limit = LIMIT) {
    let frame = initial();
    while (frame.status === 'READY') frame = advance(table, frame, limit);
    const result = { status: frame.status, steps: frame.step };
    if (frame.status === 'HALTED') result.ones = frame.ones.length;
    if (frame.repeat) result.repeat = frame.repeat;
    return result;
  }
  return { LIMIT, PRESETS, validateTable, normalized, initial, advance, simulate };
});
