"""Exact best-first search over one-vertex line translations ("wall crossings").

Each move holds one line's direction fixed and slides it just past the nearest
vertex of the other lines. In a simple arrangement this flips exactly one
triangle: the moving line swaps two neighbors in its crossing order, and each of
those two lines swaps it with the other. States are deduplicated by crossing
order, so rescaled coordinates of one arrangement are counted once.

This is a bounded exploratory search. A run that finds nothing proves no bound.
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import math
import time
from fractions import Fraction
from functools import cmp_to_key
from itertools import combinations
from pathlib import Path

from kobon.geometry import intersection
from kobon.io import MAX_COEFFICIENT, load_solution, validate_lines
from kobon.verify import verify_lines

ROOT = Path(__file__).resolve().parents[1]
ANCHOR = ROOT / "candidates/prior-art-93/solution.json"
SEPARATED = (1, 7, 13)  # add 1 to a on these lines to break the three parallel pairs


def all_crossing_start():
    lines = [list(row) for row in load_solution(ANCHOR)]
    for index in SEPARATED:
        lines[index][0] += 1
    return [tuple(row) for row in lines]


def simplest_between(lo, hi):
    """Rational with the smallest denominator strictly inside (lo, hi)."""
    lo, hi = Fraction(lo), Fraction(hi)
    if not lo < hi:
        raise ValueError("interval must satisfy lo < hi")
    whole = math.floor(lo)
    if whole + 1 < hi:
        # Smallest-magnitude integer in the interval.
        if lo < 0 < hi:
            return Fraction(0)
        return Fraction(whole + 1) if hi > 0 else Fraction(math.ceil(hi) - 1)
    upper_inverse = None if lo == whole else 1 / (lo - whole)
    lower_inverse = 1 / (hi - whole)
    if upper_inverse is None:
        tail = Fraction(math.floor(lower_inverse) + 1)
    else:
        tail = simplest_between(lower_inverse, upper_inverse)
    return whole + 1 / tail


def _parameter(line, point):
    """Position of a homogeneous point along the oriented direction (b, -a)."""
    a, b, _ = line
    x, y, w = point
    return Fraction(x * b - y * a, w)


def _direction_compare(first, second):
    """Exact counterclockwise angle order of direction vectors (b, -a)."""
    u = (first[1], -first[0])
    v = (second[1], -second[0])
    half_u = u[1] < 0 or (u[1] == 0 and u[0] < 0)
    half_v = v[1] < 0 or (v[1] == 0 and v[0] < 0)
    if half_u != half_v:
        return 1 if half_u else -1
    cross = u[0] * v[1] - u[1] * v[0]
    return -1 if cross > 0 else (1 if cross < 0 else 0)


def crossing_key(lines):
    """Oriented crossing order on every line plus cyclic order of directions."""
    rows = []
    for i, line in enumerate(lines):
        crossings = []
        for j, other in enumerate(lines):
            if i == j:
                continue
            point = intersection(line, other)
            if point is None:
                raise ValueError("crossing_key requires every pair to cross")
            crossings.append((_parameter(line, point), j))
        crossings.sort()
        if any(p == q for (p, _), (q, _) in zip(crossings, crossings[1:])):
            raise ValueError("crossing_key requires a simple arrangement")
        rows.append(tuple(j for _, j in crossings))
    directions = sorted(range(len(lines)),
                        key=cmp_to_key(lambda i, j: _direction_compare(lines[i], lines[j])))
    return tuple(rows), tuple(directions)


def _primitive(values):
    divisor = math.gcd(*(abs(v) for v in values))
    return tuple(v // divisor for v in values)


def translation_move(lines, index, direction):
    """Slide one line past its nearest vertex in direction +1 or -1 (changing c).

    Returns (new_line, crossed_pair, None) or (None, crossed_pairs_or_None, reason).
    """
    # Work in the primitive direction so the offset choice is scale-free.
    g = math.gcd(abs(lines[index][0]), abs(lines[index][1]))
    a, b = lines[index][0] // g, lines[index][1] // g
    c = Fraction(lines[index][2], g)
    others = [k for k in range(len(lines)) if k != index]
    by_threshold = {}
    for j, k in combinations(others, 2):
        point = intersection(lines[j], lines[k])
        if point is None:
            continue
        x, y, w = point
        threshold = Fraction(-(a * x + b * y), w)
        by_threshold.setdefault(threshold, []).append((j, k))
    if c in by_threshold:
        return None, None, "moving line already passes through a vertex"
    ahead = sorted(t for t in by_threshold if (t - c) * direction > 0)
    if direction < 0:
        ahead.reverse()
    if not ahead:
        return None, None, "no vertex in this direction"
    nearest = ahead[0]
    if len(by_threshold[nearest]) > 1:
        return None, by_threshold[nearest], "tied nearest threshold"
    if len(ahead) > 1:
        offset = simplest_between(min(nearest, ahead[1]), max(nearest, ahead[1]))
    else:
        offset = Fraction(math.floor(nearest) + 1 if direction > 0 else math.ceil(nearest) - 1)
    q = offset.denominator
    new_line = _primitive((a * q, b * q, offset.numerator))
    if any(abs(v) > MAX_COEFFICIENT for v in new_line):
        return None, by_threshold[nearest], "coefficient limit"
    return new_line, by_threshold[nearest][0], None


def evaluate(lines):
    """Both exact counters must agree; also confirm simple and all-crossing."""
    report = verify_lines([list(row) for row in lines], n=len(lines))
    crossing_key(lines)
    return report["score"]


def run(start, budget, stop_at=None, log_path=None):
    """Best-first expansion. Budget counts distinct exact drawings evaluated."""
    start = [tuple(row) for row in validate_lines([list(r) for r in start], n=len(start))]
    started = time.time()
    states = []
    seen = {}
    heap = []
    counts = {"evaluated": 0, "duplicate": 0, "rejected": {}}
    log = open(log_path, "w", encoding="utf-8") if log_path else None

    def record(entry):
        if log:
            log.write(json.dumps(entry, separators=(",", ":")) + "\n")

    def add(lines, parent, move):
        key = crossing_key(lines)
        if key in seen:
            counts["duplicate"] += 1
            record(dict(move, parent=parent, outcome="duplicate", state=seen[key]))
            return None
        score = evaluate(lines)
        state = len(states)
        seen[key] = state
        depth = 0 if parent is None else states[parent]["depth"] + 1
        states.append(dict(lines=lines, score=score, parent=parent, depth=depth, move=move))
        counts["evaluated"] += 1
        heapq.heappush(heap, (-score, state))
        record(dict(move, parent=parent, outcome="evaluated", state=state, score=score,
                    depth=depth, lines=[list(r) for r in lines] if parent is None else None,
                    new_line=None if parent is None else list(lines[move["line"]])))
        return state

    add(start, None, {"line": None, "direction": None, "crossed": None})
    stop_reason = "frontier exhausted"
    expanded = 0
    while heap:
        if counts["evaluated"] >= budget:
            stop_reason = "drawing budget"
            break
        if stop_at is not None and max(s["score"] for s in states) >= stop_at:
            stop_reason = f"reached {stop_at}"
            break
        _, current = heapq.heappop(heap)
        expanded += 1
        lines = states[current]["lines"]
        for index in range(len(lines)):
            for direction in (1, -1):
                if counts["evaluated"] >= budget:
                    break
                new_line, crossed, reason = translation_move(lines, index, direction)
                move = {"line": index, "direction": direction,
                        "crossed": list(crossed) if crossed and reason is None else None}
                if reason:
                    counts["rejected"][reason] = counts["rejected"].get(reason, 0) + 1
                    record(dict(move, parent=current, outcome="rejected", reason=reason,
                                tied=[list(p) for p in crossed] if crossed else None))
                    continue
                child = list(lines)
                child[index] = new_line
                add(child, current, move)
    if log:
        log.close()
    histogram = {}
    for state in states:
        histogram[state["score"]] = histogram.get(state["score"], 0) + 1
    best = max(range(len(states)), key=lambda s: (states[s]["score"], -s))
    return {
        "budget": budget,
        "evaluated": counts["evaluated"],
        "expanded": expanded,
        "duplicate_moves": counts["duplicate"],
        "rejected_moves": counts["rejected"],
        "stop_reason": stop_reason,
        "start_score": states[0]["score"],
        "best_score": states[best]["score"],
        "best_state": best,
        "best_lines": [list(r) for r in states[best]["lines"]],
        "score_histogram": {str(k): histogram[k] for k in sorted(histogram, reverse=True)},
        "max_depth": max(s["depth"] for s in states),
        "max_coefficient_digits": max(len(str(abs(v))) for s in states for r in s["lines"] for v in r),
        "elapsed_seconds": round(time.time() - started, 3),
    }, states


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--budget", type=int, default=1000)
    parser.add_argument("--stop-at", type=int, default=94)
    parser.add_argument("--out", required=True, help="new run directory")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    summary, states = run(all_crossing_start(), args.budget, args.stop_at, out / "moves.jsonl")
    summary["sources"] = {name: file_sha256(ROOT / name) for name in (
        "tools/wall_crossing_pilot.py", "candidates/prior-art-93/solution.json",
        "kobon/geometry.py", "kobon/oracle.py", "kobon/io.py", "kobon/verify.py")}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    best = [s for s in states if s["score"] == summary["best_score"]]
    (out / "best.json").write_text(json.dumps(
        [{"lines": [list(r) for r in s["lines"]], "score": s["score"], "depth": s["depth"]}
         for s in best], indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("best_lines", "sources")}, indent=2))


if __name__ == "__main__":
    main()
