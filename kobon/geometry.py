"""Exact bounded-face detection through consecutive arrangement vertices.

A side of a triangular face has no arrangement vertex strictly between its
endpoints. Conversely, a line cutting the interior crosses at least one side
away from its endpoints, so three consecutive sides certify an empty interior.
This uses the same geometric characterization as the public hill, not its runtime.
"""
from fractions import Fraction
from itertools import combinations
from math import gcd


def intersection(first, second):
    """Canonical homogeneous point (x, y, w), w > 0, or None if parallel."""
    a, b, c = first
    d, e, f = second
    w = a*e - b*d
    if not w:
        return None
    x, y = b*f - c*e, c*d - a*f
    divisor = gcd(gcd(abs(x), abs(y)), abs(w)) * (1 if w > 0 else -1)
    return x//divisor, y//divisor, w//divisor


def cartesian(point):
    x, y, w = point
    return Fraction(x,w), Fraction(y,w)


def triangles_by_adjacency(lines):
    """Return lexicographically ordered supporting line triples for valid input."""
    n = len(lines)
    meets = {}
    vertices = [set() for _ in lines]
    for i, j in combinations(range(n),2):
        point = intersection(lines[i],lines[j])
        meets[i,j] = point
        if point is not None:
            vertices[i].add(point)
            vertices[j].add(point)
    neighbors = []
    for (_, b, _), points in zip(lines,vertices):
        axis = 0 if b else 1
        ordered = sorted(points,key=lambda p:Fraction(p[axis],p[2]))
        neighbors.append({frozenset(pair) for pair in zip(ordered,ordered[1:])})
    result = []
    for i,j,k in combinations(range(n),3):
        p,q,r = meets[i,j],meets[i,k],meets[j,k]
        if p is None or q is None or r is None or p == q:
            continue
        if (frozenset((p,q)) in neighbors[i]
                and frozenset((p,r)) in neighbors[j]
                and frozenset((q,r)) in neighbors[k]):
            result.append((i,j,k))
    return result


def triangle_vertices(lines, indices):
    i,j,k = indices
    return [cartesian(intersection(lines[a],lines[b])) for a,b in [(i,j),(i,k),(j,k)]]
