"""Independent exact verifier for triangular faces in a line arrangement."""

from fractions import Fraction
from itertools import combinations


def _intersection(first, second):
    """Return the exact intersection point, or None for parallel lines."""
    a1, b1, c1 = first
    a2, b2, c2 = second
    determinant = a1 * b2 - b1 * a2
    if determinant == 0:
        return None
    return (
        Fraction(b1 * c2 - c1 * b2, determinant),
        Fraction(c1 * a2 - a1 * c2, determinant),
    )


def _twice_signed_area(first, second, third):
    return (
        (second[0] - first[0]) * (third[1] - first[1])
        - (second[1] - first[1]) * (third[0] - first[0])
    )


def _value_at(line, point):
    a, b, c = line
    x, y = point
    return a * x + b * y + c


def _crosses_open_interior(line, vertices):
    values = [_value_at(line, vertex) for vertex in vertices]
    return min(values) < 0 < max(values)


def triangles_by_interior(lines):
    """Return sorted supporting-index triples for uncrossed triangular faces.

    Each candidate triple supplies three exact rational vertices.  It is a face
    precisely when the vertices have nonzero area and no input line has values
    of both strict signs at those vertices.
    """
    triangles = []
    for indices in combinations(range(len(lines)), 3):
        first, second, third = (lines[index] for index in indices)
        first_second = _intersection(first, second)
        second_third = _intersection(second, third)
        third_first = _intersection(third, first)
        if None in (first_second, second_third, third_first):
            continue
        vertices = (first_second, second_third, third_first)
        if _twice_signed_area(*vertices) == 0:
            continue
        if not any(_crosses_open_interior(line, vertices) for line in lines):
            triangles.append(indices)
    return triangles
