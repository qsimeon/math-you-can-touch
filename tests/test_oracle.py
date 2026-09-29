import random
import unittest
from math import gcd

from kobon.oracle import triangles_by_interior


BASELINE = [(2 * index, -1, -index * index) for index in range(18)]


def affine_preimage(lines):
    """Express each line after x=2u+3v+5, y=-u+2v-7."""
    return [
        (2 * a - b, 3 * a + 2 * b, 5 * a - 7 * b + c)
        for a, b, c in lines
    ]


def permuted_expected(triangles, order):
    old_to_new = {old: new for new, old in enumerate(order)}
    return sorted(tuple(sorted(old_to_new[index] for index in triangle)) for triangle in triangles)


def random_lines(seed, count):
    generator = random.Random(seed)
    lines = []
    while len(lines) < count:
        line = tuple(generator.randint(-20, 20) for _ in range(3))
        if not (line[0] or line[1]):
            continue
        divisor = gcd(gcd(abs(line[0]), abs(line[1])), abs(line[2]))
        factor = 1 if (line[0] or line[1]) > 0 else -1
        normalized = tuple(factor * x // divisor for x in line)
        if normalized not in lines:
            lines.append(normalized)
    return lines


class InteriorOracleTests(unittest.TestCase):
    def test_hand_derivable_triangles_and_degeneracies(self):
        triangle = [(1, 0, 0), (0, 1, 0), (1, 1, -2)]
        self.assertEqual(triangles_by_interior(triangle), [(0, 1, 2)])
        self.assertEqual(
            triangles_by_interior(triangle + [(1, 0, -1)]), [(1, 2, 3)]
        )
        self.assertEqual(
            triangles_by_interior([(1, 0, 0), (0, 1, 0), (1, 1, 0)]), []
        )
        self.assertEqual(
            triangles_by_interior([(1, 0, 0), (1, 0, -1), (0, 1, 0)]), []
        )

    def test_vertex_touch_does_not_cross_open_interior(self):
        outer_triangle = [(1, 0, 0), (0, 1, 0), (1, 1, -4)]
        touch_at_vertex = (1, 1, 0)
        self.assertEqual(
            triangles_by_interior(outer_triangle + [touch_at_vertex]), [(0, 1, 2)]
        )

    def test_tiny_triangle_with_large_coefficients(self):
        scale = 10**30
        lines = [(scale, 0, 0), (0, scale, 0), (scale, scale, -1)]
        self.assertEqual(triangles_by_interior(lines), [(0, 1, 2)])

    def test_baseline_has_sixteen_faces(self):
        self.assertEqual(len(triangles_by_interior(BASELINE)), 16)

    def test_affine_scaling_and_permutation_invariance(self):
        lines = BASELINE[:8]
        expected = triangles_by_interior(lines)
        self.assertEqual(triangles_by_interior(affine_preimage(lines)), expected)

        factors = [-7, 3, -5, 11, 2, -13, 17, 19]
        scaled = [
            tuple(factor * coordinate for coordinate in line)
            for line, factor in zip(lines, factors)
        ]
        self.assertEqual(triangles_by_interior(scaled), expected)

        order = [4, 0, 7, 2, 5, 1, 6, 3]
        self.assertEqual(
            triangles_by_interior([lines[index] for index in order]),
            permuted_expected(expected, order),
        )

    def test_deterministic_random_arrangements_preserve_faces_under_transforms(self):
        for seed in range(10):
            with self.subTest(seed=seed):
                lines = random_lines(seed, 7)
                triangles = triangles_by_interior(lines)
                self.assertEqual(triangles, sorted(triangles))
                self.assertTrue(all(len(set(triangle)) == 3 for triangle in triangles))
                self.assertEqual(triangles_by_interior(affine_preimage(lines)), triangles)

                order = list(reversed(range(len(lines))))
                self.assertEqual(
                    triangles_by_interior([lines[index] for index in order]),
                    permuted_expected(triangles, order),
                )


if __name__ == "__main__":
    unittest.main()
