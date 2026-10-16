"""Count bounded line segments and triangle usage for exact line arrangements.

This diagnostic uses validated input and independently checked triangular faces.
The unused-segment identity applies only when every finite vertex has degree two.
"""
import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict
from fractions import Fraction
from itertools import combinations

# Direct script execution adds tools/, not the checkout root, to sys.path.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kobon.geometry import intersection
from kobon.io import load_solution, validate_lines
from kobon.verify import verify_lines


def _ordered(points, line):
    axis = 0 if line[1] else 1
    return sorted(points, key=lambda point: Fraction(point[axis], point[2]))


def audit(lines):
    """Return integer segment counts; omit triangle-usage totals with triple points."""
    lines = validate_lines([list(row) for row in lines], n=len(lines))
    report = verify_lines(lines, n=len(lines))
    points_on_lines = [set() for _ in lines]
    through = defaultdict(set)
    parallel_pairs = []
    for i, j in combinations(range(len(lines)), 2):
        point = intersection(lines[i], lines[j])
        if point is None:
            parallel_pairs.append([i, j])
        else:
            points_on_lines[i].add(point)
            points_on_lines[j].add(point)
            through[point].update((i, j))
    triples = [dict(point=list(point), lines=sorted(indices))
               for point, indices in through.items() if len(indices) >= 3]
    triples.sort(key=lambda item: item['point'])
    edges = []
    for index, line in enumerate(lines):
        ordered = _ordered(points_on_lines[index], line)
        edges.extend((index, left, right) for left, right in zip(ordered, ordered[1:]))
    result = dict(lines=len(lines), triangular_faces=report['score'],
                  finite_vertices=len(through), bounded_segments=len(edges),
                  parallel_pairs=parallel_pairs, multiple_points=triples)
    if triples:
        result['unused_segments'] = None
        result['usage_note'] = ('The 3T segment identity is withheld when lines meet '
                                'at a triple point; a segment may border two triangles.')
        return result

    used = set()
    for i, j, k in report['triangle_line_indices']:
        p, q, r = (intersection(lines[a], lines[b])
                   for a, b in ((i, j), (i, k), (j, k)))
        used.update(((i, frozenset((p, q))), (j, frozenset((p, r))),
                     (k, frozenset((q, r)))))
    assert len(used) == 3 * report['score']
    unused = []
    for index, left, right in edges:
        if (index, frozenset((left, right))) not in used:
            unused.append(dict(line=index, endpoint_crossings=[
                sorted(through[left] - {index}), sorted(through[right] - {index})]))
    assert len(unused) == len(edges) - len(used)
    expected = sum(max(len(points) - 1, 0) for points in points_on_lines)
    assert len(edges) == expected
    if all(points_on_lines):
        assert expected == len(lines) * (len(lines) - 2) - 2 * len(parallel_pairs)
    result['unused_segments'] = unused
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('solution', help='JSON file containing exact lines')
    args = parser.parse_args()
    with open(args.solution, encoding='utf-8') as stream:
        data = json.load(stream)
    if not isinstance(data, dict) or not isinstance(data.get('lines'), list):
        parser.error('a solution with a lines array is required')
    lines = load_solution(args.solution, n=len(data['lines']))
    print(json.dumps(audit(lines), indent=2))


if __name__ == '__main__':
    main()
