/* Exact integer line-arrangement geometry. Rendering must convert these results to Number explicitly. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.FenceGeometry = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, () => {
  'use strict';
  const LIMIT = 10n ** 30n;
  const abs = (v) => v < 0n ? -v : v;
  const gcd = (a, b) => { a = abs(a); b = abs(b); while (b) [a, b] = [b, a % b]; return a; };
  const gcd3 = (a, b, c) => gcd(gcd(a, b), c);
  const rational = (n, d = 1n) => { if (!d) throw new Error('zero denominator'); if (d < 0n) [n, d] = [-n, -d]; const g = gcd(n, d); return { n: n / g, d: d / g }; };
  const cmp = (a, b) => (a.n * b.d < b.n * a.d ? -1 : a.n * b.d > b.n * a.d ? 1 : 0);
  const add = (a, b) => rational(a.n * b.d + b.n * a.d, a.d * b.d);
  const sub = (a, b) => rational(a.n * b.d - b.n * a.d, a.d * b.d);
  const mulInt = (a, n) => rational(a.n * n, a.d);
  const sign = (a) => a.n < 0n ? -1 : a.n > 0n ? 1 : 0;
  const parse = (value) => typeof value === 'bigint' ? value : (typeof value === 'string' && /^-?(?:0|[1-9]\d*)$/.test(value) ? BigInt(value) : null);
  function canonical(line) {
    if (!Array.isArray(line) || line.length !== 3) throw new Error('each line must be a triple');
    let [a, b, c] = line.map(parse);
    if ([a, b, c].some(v => v === null || abs(v) > LIMIT)) throw new Error('coefficients must be integers with magnitude <= 10^30');
    if (!a && !b) throw new Error('line normal cannot be zero');
    const g = gcd3(a, b, c); [a, b, c] = [a / g, b / g, c / g];
    if ((a || b) < 0n) [a, b, c] = [-a, -b, -c];
    return [a, b, c];
  }
  function validate(lines, expected) {
    if (!Array.isArray(lines) || (expected !== undefined && lines.length !== expected)) throw new Error(`exactly ${expected} lines required`);
    const seen = new Set(); const out = lines.map(canonical);
    out.forEach(line => { const key = line.join(','); if (seen.has(key)) throw new Error('proportional duplicate lines'); seen.add(key); });
    return out;
  }
  function intersection(first, second) {
    const [a, b, c] = first, [d, e, f] = second; const w = a * e - b * d;
    if (!w) return null;
    let x = b * f - c * e, y = c * d - a * f, q = gcd3(x, y, w);
    if (w < 0n) q = -q;
    return [x / q, y / q, w / q];
  }
  const pointEqual = (a, b) => a[0] === b[0] && a[1] === b[1] && a[2] === b[2];
  const pointKey = (p) => p.join(',');
  function adjacency(lines) {
    const n = lines.length, meets = new Map(), vertices = Array.from({ length: n }, () => new Map());
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) { const p = intersection(lines[i], lines[j]); meets.set(`${i},${j}`, p); if (p) { vertices[i].set(pointKey(p), p); vertices[j].set(pointKey(p), p); } }
    const neighbors = vertices.map((points, i) => { const axis = lines[i][1] ? 0 : 1; const ordered = [...points.values()].sort((p, q) => cmp(rational(p[axis], p[2]), rational(q[axis], q[2]))); return new Set(ordered.slice(1).map((p, x) => [pointKey(ordered[x]), pointKey(p)].sort().join('|'))); });
    const get = (i, j) => meets.get(i < j ? `${i},${j}` : `${j},${i}`);
    const faces = [];
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) for (let k = j + 1; k < n; k++) { const p = get(i, j), q = get(i, k), r = get(j, k); if (!p || !q || !r || pointEqual(p, q)) continue; const edge = (x, y) => [pointKey(x), pointKey(y)].sort().join('|'); if (neighbors[i].has(edge(p, q)) && neighbors[j].has(edge(p, r)) && neighbors[k].has(edge(q, r))) faces.push([i, j, k]); }
    return faces;
  }
  function interior(lines) {
    const faces = [];
    for (let i = 0; i < lines.length; i++) for (let j = i + 1; j < lines.length; j++) for (let k = j + 1; k < lines.length; k++) {
      const p = intersection(lines[i], lines[j]), q = intersection(lines[j], lines[k]), r = intersection(lines[k], lines[i]); if (!p || !q || !r) continue;
      const px = rational(p[0], p[2]), py = rational(p[1], p[2]), qx = rational(q[0], q[2]), qy = rational(q[1], q[2]), rx = rational(r[0], r[2]), ry = rational(r[1], r[2]);
      const signed = sub({ n: sub(qx, px).n * sub(ry, py).n, d: sub(qx, px).d * sub(ry, py).d }, { n: sub(qy, py).n * sub(rx, px).n, d: sub(qy, py).d * sub(rx, px).d });
      if (!sign(signed)) continue;
      const vertices = [[px, py], [qx, qy], [rx, ry]];
      const crossed = lines.some(([a, b, c]) => { const values = vertices.map(([x, y]) => add(add(mulInt(x, a), mulInt(y, b)), rational(c))); return values.some(v => sign(v) < 0) && values.some(v => sign(v) > 0); });
      if (!crossed) faces.push([i, j, k]);
    }
    return faces;
  }
  function score(input) { const lines = validate(input); const faces = adjacency(lines), independent = interior(lines); if (JSON.stringify(faces) !== JSON.stringify(independent)) throw new Error('exact scorers disagree'); return { lines, faces, score: faces.length }; }
  function vertices(lines, triple) { const [i, j, k] = triple; return [intersection(lines[i], lines[j]), intersection(lines[i], lines[k]), intersection(lines[j], lines[k])].map(p => [Number(p[0]) / Number(p[2]), Number(p[1]) / Number(p[2])]); }
  function translateParallel(lines, index, amount) { const out = validate(lines).map(line => [...line]); const [a, b, c] = out[index]; const delta = parse(amount); if (delta === null) throw new Error('snap amount must be an integer'); out[index] = canonical([a, b, c + delta]); return validate(out); }
  function rotateRational(lines, index, numerator = 1n, denominator = 20n) { const out = validate(lines).map(line => [...line]); const p = parse(numerator), q = parse(denominator); if (p === null || q === null || !q) throw new Error('rotation requires an integer nonzero denominator'); const [a, b, c] = out[index], q2 = q*q, p2 = p*p, cosine = q2-p2, sine = 2n*p*q, scale = q2+p2; out[index] = canonical([cosine*a-sine*b, sine*a+cosine*b, scale*c]); return validate(out); }
  function exportJSON(lines) { return `{\"lines\":[${validate(lines).map(line => `[${line.join(',')}]`).join(',')}]}`; }
  return { LIMIT, canonical, validate, intersection, adjacency, interior, score, vertices, translateParallel, rotateRational, exportJSON, rational, cmp };
});
