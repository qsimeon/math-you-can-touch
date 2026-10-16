"""Compare 93-triangle crossing patterns with Bader's.

Prints, for each pattern, whether it is Bader's drawing turned or mirrored,
whether it is any way of separating Bader's three parallel pairs, and its
triangle count once the line at infinity is added (a number that does not
depend on which line is sent to infinity).
"""
from __future__ import annotations

import argparse
import json
from itertools import product
from pathlib import Path

from kobon.io import load_solution
from tools.kobon_sat import (projective_triangles, same_drawing, signotope_from_lines, signs_from_text,
                             triangles)
from tools.wall_crossing_pilot import ANCHOR, SEPARATED


def bader_variants():
    """Every way of separating the three parallel pairs by tilting one line
    of each pair a little either way, as (lines, crossing pattern)."""
    base = [list(row) for row in load_solution(ANCHOR)]
    variants = []
    for shifts in product((1, -1, 2, -2), repeat=3):
        lines = [list(row) for row in base]
        for index, shift in zip(SEPARATED, shifts):
            lines[index][0] += shift
        lines = [tuple(row) for row in lines]
        variants.append((lines, signotope_from_lines(lines)[1]))
    return variants


def adjugate(m):
    """Integer matrix with m times it equal to det(m) times the identity."""
    cofactor = [[0] * 3 for _ in range(3)]
    for i in range(3):
        for j in range(3):
            minor = [[v for col, v in enumerate(row) if col != j] for k, row in enumerate(m) if k != i]
            cofactor[i][j] = (-1) ** (i + j) * (minor[0][0] * minor[1][1] - minor[0][1] * minor[1][0])
    return [[cofactor[j][i] for j in range(3)] for i in range(3)]


def recharts(lines):
    """For each line j, send it to infinity and bring the old line at
    infinity back as an ordinary line, exactly. Yields (j, crossing pattern).

    A point (x, y) has homogeneous coordinates p = (x, y, 1), and the line
    (a, b, c) holds the points with a x + b y + c = 0. The map p -> M p whose
    third row is line j sends that line to infinity. Lines move by M's
    inverse, which is the adjugate up to a factor. The other two rows only
    choose an affine picture of the result; they are varied until no new
    line is vertical and no two are parallel."""
    for j, chosen in enumerate(lines):
        for t1, t2 in product(range(-3, 4), repeat=2):
            m = [[1, 0, t1], [0, 1, t2], list(chosen)]
            if sum(x * y for x, y in zip(chosen, (-t1, -t2, 1))) == 0:
                continue  # not invertible
            adj = adjugate(m)
            moved = [tuple(sum(line[i] * adj[i][k] for i in range(3)) for k in range(3))
                     for line in [l for i, l in enumerate(lines) if i != j] + [(0, 0, 1)]]
            try:
                yield j, signotope_from_lines(moved)[1]
                break
            except ValueError:
                continue


def load(path):
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if "signs" in record:
        return record["n"], signs_from_text(record["n"], record["signs"])
    lines = [tuple(row) for row in record["lines"]]
    return len(lines), signotope_from_lines(lines)[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("patterns", nargs="+", help="kobon_sat results or solution files")
    args = parser.parse_args()
    variants = bader_variants()
    charts = [signs for lines, _ in variants for _, signs in recharts(lines)]
    print(json.dumps({
        "bader_variants": len(variants), "bader_charts": len(charts),
        "triangles_in_bader_variants": sorted({len(triangles(18, v)) for _, v in variants}),
        "triangles_in_bader_charts": sorted({len(triangles(18, c)) for c in charts}),
        "bader_triangles_with_line_at_infinity": sorted({projective_triangles(18, v) for _, v in variants}
                                                        | {projective_triangles(18, c) for c in charts}),
    }))
    for path in args.patterns:
        n, signs = load(path)
        print(json.dumps({
            "pattern": path, "triangles": len(triangles(n, signs)),
            "is_a_separated_bader": any(same_drawing(n, v, signs) for _, v in variants),
            "is_a_rechart_of_a_separated_bader": any(same_drawing(n, c, signs) for c in charts),
            "triangles_with_line_at_infinity": projective_triangles(n, signs),
        }))


if __name__ == "__main__":
    main()
