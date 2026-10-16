"""Draw a crossing pattern as a wiring diagram with its triangles shaded.

Each line becomes a horizontal track. Reading left to right, two lines on
neighbouring tracks swap tracks where they cross. Crossings that can happen
at the same moment share a column, so the picture stays compact. Triangles
are drawn exactly as the pattern has them: the region bounded by three
wires between their three crossings.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.kobon_sat import crossing_orders, signotope_from_lines, signs_from_text, triangles


def sweep(n, signs):
    """Columns of crossings, each a list of (level, upper line, lower line),
    and the track of every line at every column boundary."""
    orders = crossing_orders(n, signs)
    nxt = [0] * n
    tracks = list(range(n))  # top to bottom
    columns, heights = [], [list(tracks)]
    while any(nxt[i] < n - 1 for i in range(n)):
        column, used = [], set()
        for level in range(n - 1):
            a, b = tracks[level], tracks[level + 1]
            if level in used or level - 1 in used:
                continue
            if nxt[a] < n - 1 and nxt[b] < n - 1 and orders[a][nxt[a]] == b and orders[b][nxt[b]] == a:
                column.append((level, a, b))
                used.add(level)
        if not column:
            raise ValueError("no crossing is ready; not a drawing")
        for level, a, b in column:
            tracks[level], tracks[level + 1] = b, a
            nxt[a] += 1
            nxt[b] += 1
        columns.append(column)
        heights.append(list(tracks))
    return columns, heights


def svg(n, signs, title, step=22, gap=26, pad=30):
    columns, heights = sweep(n, signs)
    where = {}  # crossing of a pair -> (column, level)
    for c, column in enumerate(columns):
        for level, a, b in column:
            where[frozenset((a, b))] = (c, level)
    track = [{line: h for h, line in enumerate(row)} for row in heights]

    def px(x):
        return pad + x * step

    def py(y):
        return pad + y * gap

    def wire_points(line, start, end):
        """Points of a wire from crossing column `start` to `end`, through
        the column boundaries between them (start < end)."""
        cs, ls = where[start]
        ce, le = where[end]
        points = [(cs + 0.5, ls + 0.5)]
        for boundary in range(cs + 1, ce + 1):
            points.append((boundary, track[boundary][line]))
        points.append((ce + 0.5, le + 0.5))
        return points

    width = px(len(columns)) + pad
    height = py(n - 1) + pad + 24
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
           f'<rect width="{width}" height="{height}" fill="#fbfaf7"/>']
    for x, y, z in triangles(n, signs):
        corners = sorted((frozenset(p) for p in ((x, y), (x, z), (y, z))), key=lambda p: where[p][0])
        first, middle, last = corners
        def shared(p, q):
            return next(iter(p & q))
        path = wire_points(shared(first, middle), first, middle)
        path += wire_points(shared(middle, last), middle, last)[1:]
        path += list(reversed(wire_points(shared(first, last), first, last)))[1:-1]
        points = " ".join(f"{px(a):.1f},{py(b):.1f}" for a, b in path)
        out.append(f'<polygon points="{points}" fill="#e8a33d" fill-opacity="0.75" stroke="none"/>')
    for line in range(n):
        points = []
        for boundary in range(len(heights)):
            points.append((boundary, track[boundary][line]))
        out.append('<polyline points="' + " ".join(f"{px(a):.1f},{py(b):.1f}" for a, b in points)
                   + '" fill="none" stroke="#1f2a44" stroke-width="1.3" stroke-linejoin="round"/>')
    out.append(f'<text x="{pad}" y="{height - 12}" font-family="Helvetica, Arial, sans-serif" font-size="15" '
               f'fill="#1f2a44">{title}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def load(source):
    if source == "all-crossing-93":
        from tools.wall_crossing_pilot import all_crossing_start
        lines = all_crossing_start()
        return len(lines), signotope_from_lines(lines)[1]
    record = json.loads(Path(source).read_text(encoding="utf-8"))
    if "signs" in record:
        return record["n"], signs_from_text(record["n"], record["signs"])
    lines = [tuple(row) for row in record["lines"]]
    return len(lines), signotope_from_lines(lines)[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("source", help="kobon_sat result, solution file, or all-crossing-93")
    parser.add_argument("--title", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    n, signs = load(args.source)
    Path(args.out).write_text(svg(n, signs, args.title), encoding="utf-8")


if __name__ == "__main__":
    main()
