"""Try to turn a crossing pattern into real straight lines.

Use lines y = m_i x + c_i, numbered by increasing slope, so line i is the one
the pattern calls i. For three lines a < b < c, the crossing of a and c lies
above b exactly when

    f = (m_a - m_b)(c_c - c_a) + (c_a - c_b)(m_a - m_c)

is negative. (The crossing is at x = (c_c - c_a)/(m_a - m_c); compare the
heights there and multiply by m_a - m_c, which is negative.)

With the slopes held fixed, f is linear in the intercepts, and with the
intercepts held fixed it is linear in the slopes. So the search alternates two
linear programs. Each asks every triple's f to have the right sign by a margin
and minimises the total shortfall. When nothing falls short, the floating
point lines are rounded to integers and the pattern is recounted exactly. A
failure proves nothing: the pattern may still be straight in some other way,
or not at all.
"""
from __future__ import annotations

import argparse
import json
import random
from itertools import combinations
from pathlib import Path


def _rows(n, signs, fixed, free_is_slope):
    """One row per triple: coefficients of f over the free variables."""
    rows, wanted = [], []
    for a, b, c in combinations(range(n), 3):
        row = [0.0] * n
        if free_is_slope:
            ca, cb, cc = fixed[a], fixed[b], fixed[c]
            row[a], row[b], row[c] = cc - cb, -(cc - ca), -(ca - cb)
        else:
            ma, mb, mc = fixed[a], fixed[b], fixed[c]
            row[a], row[b], row[c] = mb - mc, -(ma - mc), ma - mb
        rows.append(row)
        wanted.append(-1.0 if signs[(a, b, c)] else 1.0)  # sign f must have
    return rows, wanted


def _step(n, signs, fixed, free_is_slope, margin):
    """Minimise total shortfall: wanted * f >= margin - slack, slack >= 0."""
    import numpy as np
    from scipy.optimize import linprog

    rows, wanted = _rows(n, signs, fixed, free_is_slope)
    k = len(rows)
    A = np.zeros((k, n + k))
    A[:, :n] = -np.array(wanted)[:, None] * np.array(rows)
    A[np.arange(k), n + np.arange(k)] = -1.0
    b = np.full(k, -margin)
    if free_is_slope:  # keep the slope order: m_{i+1} - m_i >= margin
        order = np.zeros((n - 1, n + k))
        for i in range(n - 1):
            order[i, i], order[i, i + 1] = 1.0, -1.0
        A = np.vstack([A, order])
        b = np.concatenate([b, np.full(n - 1, -margin)])
    cost = np.concatenate([np.zeros(n), np.ones(k)])
    bounds = [(-1.0, 1.0)] * n + [(0.0, None)] * k
    answer = linprog(cost, A_ub=A, b_ub=b, bounds=bounds, method="highs")
    if not answer.success:
        return list(fixed), float("inf")
    return list(answer.x[:n]), float(answer.fun)


def wrong_signs(n, signs, slopes, intercepts):
    count = 0
    for a, b, c in combinations(range(n), 3):
        f = ((slopes[a] - slopes[b]) * (intercepts[c] - intercepts[a])
             + (intercepts[a] - intercepts[b]) * (slopes[a] - slopes[c]))
        if (f < 0) != signs[(a, b, c)] or f == 0:
            count += 1
    return count


def exact_lines(n, signs, slopes, intercepts):
    """Round every line to integers at a common scale D, smallest D first,
    and keep the first rounding whose exact crossing pattern is the requested
    one. The line y = m x + c becomes (mD) x - D y + cD = 0, divided by the
    common factor of its three numbers."""
    from math import gcd
    from tools.kobon_sat import signotope_from_lines

    scales = list(range(1, 400)) + [int(400 * 1.05 ** k) for k in range(1, 400)]
    for scale in scales:
        lines = []
        for m, c in zip(slopes, intercepts):
            a, b, k = round(m * scale), -scale, round(c * scale)
            g = gcd(gcd(a, b), k)
            lines.append((a // g, b // g, k // g))
        try:
            order, got = signotope_from_lines(lines)
        except ValueError:
            continue
        if order == list(range(n)) and got == signs:
            return lines
    return None


def straighten(n, signs, margin=1e-3, seed=0, rounds=60):
    """One attempt from a random start. Returns integer lines with exactly
    this crossing pattern, or None.

    Lines live in the box where slopes and intercepts are between -1 and 1.
    A larger margin asks every crossing to clear its neighbour by more, which
    is harder to satisfy but survives coarser rounding, so the integers come
    out smaller."""
    rng = random.Random(seed)
    slopes = sorted(rng.uniform(-1, 1) for _ in range(n))
    intercepts = [rng.uniform(-1, 1) for _ in range(n)]
    last = None
    for _ in range(rounds):
        intercepts, _ = _step(n, signs, slopes, False, margin)
        slopes, shortfall = _step(n, signs, intercepts, True, margin)
        if shortfall < 1e-12 or (last is not None and shortfall >= last - 1e-12):
            break
        last = shortfall
    if wrong_signs(n, signs, slopes, intercepts):
        return None
    return exact_lines(n, signs, slopes, intercepts)


def smallest(n, signs, margins, seeds):
    """Try every margin and seed; keep the drawing whose largest coefficient
    is smallest. Returns (lines, margin, seed) or None."""
    best = None
    for margin in margins:
        for seed in range(seeds):
            lines = straighten(n, signs, margin, seed)
            if lines is None:
                continue
            size = max(abs(v) for line in lines for v in line)
            if best is None or size < best[0]:
                best = (size, lines, margin, seed)
    return None if best is None else best[1:]


def main():
    from tools.kobon_sat import signotope_from_lines, signs_from_text, triangles
    from kobon.verify import verify_lines

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("source", help="kobon_sat result (has 'signs'), a solution file (has 'lines'), or all-crossing-93")
    parser.add_argument("--margins", default="0.025,0.02,0.017,0.014,0.012,0.01,0.003,0.001")
    parser.add_argument("--seeds", type=int, default=40)
    parser.add_argument("--out", required=True, help="new JSON file")
    args = parser.parse_args()
    out = Path(args.out)
    if out.exists():
        raise SystemExit(f"{out} already exists")
    if args.source == "all-crossing-93":
        from tools.wall_crossing_pilot import all_crossing_start
        record = {"lines": all_crossing_start()}
    else:
        record = json.loads(Path(args.source).read_text(encoding="utf-8"))
    if "signs" in record:
        n = record["n"]
        signs = signs_from_text(n, record["signs"])
    else:
        n = len(record["lines"])
        order, signs = signotope_from_lines([tuple(line) for line in record["lines"]])
    margins = [float(v) for v in args.margins.split(",")]
    found = smallest(n, signs, margins, args.seeds)
    result = {"n": n, "pattern_triangles": len(triangles(n, signs)), "straightened": found is not None,
              "margins": margins, "seeds": args.seeds, "starts": len(margins) * args.seeds}
    if found:
        lines, margin, seed = found
        result.update(margin=margin, seed=seed, largest_coefficient=max(abs(v) for l in lines for v in l),
                      exact_triangles=verify_lines(lines, n)["score"], lines=[list(l) for l in lines])
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "lines"}, indent=2))


if __name__ == "__main__":
    main()
