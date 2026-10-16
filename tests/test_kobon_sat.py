"""The SAT search for many-triangle drawings: its encoding, its checker and
its symmetry, each tested against something independent."""
import random
import unittest
from fractions import Fraction
from itertools import combinations, product

from tools.kobon_sat import (
    build,
    check,
    crossing_orders,
    is_signotope,
    mirror,
    projective_triangles,
    rotate,
    same_drawing,
    signotope_clauses,
    signotope_from_lines,
    signs_from_text,
    solve,
    turned,
    triangles,
)

try:
    import pysat  # noqa: F401
    HAVE_PYSAT = True
except ImportError:  # the public checkout tests without third-party packages
    HAVE_PYSAT = False

needs_pysat = unittest.skipUnless(HAVE_PYSAT, "python-sat is not installed")

# Largest triangle counts for simple drawings of n pseudolines (Bartholdi,
# Blanc and Loisel 2008).
KNOWN = {3: 1, 4: 2, 5: 5, 6: 7, 7: 11, 8: 14, 9: 21}


def wiring(n, rng):
    """A random drawing of n pseudolines, built by swapping neighbours that
    have not crossed yet. Returns the signs and each line's crossing order."""
    heights = list(range(n))
    signs, orders = {}, [[] for _ in range(n)]
    while True:
        spots = [i for i in range(n - 1) if heights[i] < heights[i + 1]]
        if not spots:
            return signs, orders
        i = rng.choice(spots)
        a, c = heights[i], heights[i + 1]
        for h, b in enumerate(heights):
            if a < b < c:
                signs[(a, b, c)] = h > i
        orders[a].append(c)
        orders[c].append(a)
        heights[i], heights[i + 1] = c, a


def random_straight(rng, n):
    while True:
        lines = [(rng.randint(-40, 40), rng.randint(1, 40), rng.randint(-300, 300)) for _ in range(n)]
        try:
            return lines, signotope_from_lines(lines)
        except ValueError:
            continue


class Checker(unittest.TestCase):
    def test_signotope_rule_by_brute_force(self):
        # n = 5 has 62 drawings among the 1,024 sign choices.
        triples = list(combinations(range(5), 3))
        count = sum(is_signotope(5, dict(zip(triples, bits))) for bits in product((False, True), repeat=10))
        self.assertEqual(count, 62)

    def test_crossing_orders_match_the_wiring(self):
        rng = random.Random(1)
        for _ in range(200):
            n = rng.randint(3, 10)
            signs, orders = wiring(n, rng)
            self.assertTrue(is_signotope(n, signs))
            self.assertEqual(crossing_orders(n, signs), orders)

    def test_triangles_match_exact_geometry(self):
        from kobon.verify import verify_lines
        rng = random.Random(2)
        for _ in range(25):
            n = rng.randint(4, 10)
            lines, (order, signs) = random_straight(rng, n)
            exact = verify_lines(lines, n)["triangle_line_indices"]
            rank = {line: position for position, line in enumerate(order)}
            expected = sorted(tuple(sorted(rank[i] for i in t)) for t in exact)
            self.assertEqual(sorted(triangles(n, signs)), expected)

    def test_the_93_drawing(self):
        from tools.wall_crossing_pilot import all_crossing_start
        order, signs = signotope_from_lines(all_crossing_start())
        self.assertTrue(is_signotope(18, signs))
        self.assertEqual(len(triangles(18, signs)), 93)

    def test_check_rejects_bad_answers(self):
        from tools.wall_crossing_pilot import all_crossing_start
        signs = signotope_from_lines(all_crossing_start())[1]
        self.assertEqual(check(18, signs, 93), 93)
        with self.assertRaises(ValueError):
            check(18, signs, 94)
        broken = dict(signs)
        broken[(0, 1, 2)] = not broken[(0, 1, 2)]
        broken[(0, 1, 3)] = broken[(0, 1, 2)]
        broken[(0, 2, 3)] = not broken[(0, 1, 2)]
        broken[(1, 2, 3)] = broken[(0, 1, 2)]
        with self.assertRaises(ValueError):
            check(18, broken, 0)

    def test_signs_round_trip_through_text(self):
        rng = random.Random(3)
        signs, _ = wiring(9, rng)
        text = "".join("1" if signs[t] else "0" for t in sorted(signs))
        self.assertEqual(signs_from_text(9, text), signs)


class Charts(unittest.TestCase):
    def test_recharting_keeps_the_count_with_the_line_at_infinity(self):
        from tools.compare_93 import recharts
        rng = random.Random(13)
        checked = 0
        for _ in range(15):
            n = rng.randint(4, 8)
            lines, (order, signs) = random_straight(rng, n)
            for j, moved in recharts(lines):
                self.assertTrue(is_signotope(n, moved))
                self.assertEqual(projective_triangles(n, moved), projective_triangles(n, signs))
                checked += 1
        self.assertGreater(checked, 50)

    def test_new_93_is_not_bader_in_disguise(self):
        import json
        from tools.compare_93 import bader_variants
        with open("candidates/sat-93-a/solution.json", encoding="utf-8") as stream:
            lines = [tuple(l) for l in json.load(stream)["lines"]]
        signs = signotope_from_lines(lines)[1]
        self.assertEqual(len(triangles(18, signs)), 93)
        self.assertEqual(projective_triangles(18, signs), 102)
        self.assertEqual({projective_triangles(18, v) for _, v in bader_variants()}, {105})


class Pictures(unittest.TestCase):
    def test_wiring_diagram_shades_every_triangle(self):
        from tools.draw_wiring import svg, sweep
        rng = random.Random(12)
        for _ in range(20):
            n = rng.randint(3, 10)
            signs, orders = wiring(n, rng)
            columns, heights = sweep(n, signs)
            self.assertEqual(sum(len(c) for c in columns), n * (n - 1) // 2)
            self.assertEqual(heights[-1], list(range(n))[::-1])
            self.assertEqual(svg(n, signs, "t").count("<polygon"), len(triangles(n, signs)))


class Turning(unittest.TestCase):
    def test_rotate_keeps_triangles_on_pseudolines(self):
        rng = random.Random(4)
        for _ in range(200):
            n = rng.randint(3, 10)
            signs, _ = wiring(n, rng)
            turned = rotate(n, signs)
            self.assertTrue(is_signotope(n, turned))
            old = {0: n - 1, **{i: i - 1 for i in range(1, n)}}
            back = sorted(tuple(sorted(old[v] for v in t)) for t in triangles(n, turned))
            self.assertEqual(back, sorted(triangles(n, signs)))

    def test_n_turns_make_a_half_turn(self):
        rng = random.Random(5)
        n = 8
        signs, _ = wiring(n, rng)
        turned = signs
        for _ in range(n):
            turned = rotate(n, turned)
        self.assertEqual(turned, {t: not v for t, v in signs.items()})

    def test_turned_recipe_matches_repeated_turns(self):
        rng = random.Random(9)
        for _ in range(30):
            n = rng.randint(4, 9)
            signs, _ = wiring(n, rng)
            steps = rng.randint(0, 2 * n)
            moved = signs
            for _ in range(steps):
                moved = rotate(n, moved)
            recipe = turned(n, steps)
            self.assertEqual(moved, {t: signs[src] != flip for t, (src, flip) in recipe.items()})

    def test_the_93_is_threefold(self):
        from tools.wall_crossing_pilot import all_crossing_start
        signs = signotope_from_lines(all_crossing_start())[1]
        moved, fixed_by = signs, []
        for steps in range(1, 36):
            moved = rotate(18, moved)
            if moved == signs:
                fixed_by.append(steps)
        self.assertEqual(fixed_by, [12, 24])

    def test_mirror_is_an_exact_reflection(self):
        rng = random.Random(10)
        for _ in range(40):
            n = rng.randint(4, 9)
            lines, (order, signs) = random_straight(rng, n)
            reflected = [(-a, b, c) for a, b, c in lines]
            order2, signs2 = signotope_from_lines(reflected)
            self.assertEqual(order2, order[::-1])
            self.assertEqual(mirror(n, signs), signs2)
            self.assertEqual(len(triangles(n, signs2)), len(triangles(n, signs)))

    def test_same_drawing_and_the_line_at_infinity(self):
        rng = random.Random(11)
        for _ in range(60):
            n = rng.randint(4, 10)
            signs, _ = wiring(n, rng)
            moved = mirror(n, signs)
            for _ in range(rng.randint(0, 2 * n)):
                moved = rotate(n, moved)
            self.assertTrue(same_drawing(n, signs, moved))
            # turning never changes the count with the line at infinity
            self.assertEqual(projective_triangles(n, moved), projective_triangles(n, signs))
        # three lines: four triangles in the projective plane
        self.assertEqual(projective_triangles(3, {(0, 1, 2): False}), 4)
        # flipping one triangle of the 93 gives a different drawing
        from tools.wall_crossing_pilot import all_crossing_start
        signs = signotope_from_lines(all_crossing_start())[1]
        flipped = dict(signs)
        a, b, c = triangles(18, signs)[0]
        flipped[(a, b, c)] = not flipped[(a, b, c)]
        self.assertTrue(is_signotope(18, flipped))
        self.assertFalse(same_drawing(18, signs, flipped))

    def test_rotate_is_an_exact_turn_of_straight_lines(self):
        rng = random.Random(6)
        checked = 0
        for _ in range(150):
            n = rng.randint(4, 9)
            lines, (order, signs) = random_straight(rng, n)
            p, q, h = rng.choice([(3, 4, 5), (5, 12, 13), (8, 15, 17), (20, 21, 29)])
            cos, sin = Fraction(p, h), Fraction(q, h)
            # Turning by less than a right angle; a line whose new y
            # coefficient is negative has passed the vertical.
            turned = [(a * cos - b * sin, a * sin + b * cos, Fraction(c)) for a, b, c in lines]
            try:
                order2, signs2 = signotope_from_lines(turned)
            except ValueError:
                continue
            passed = sum(b < 0 for _, b, _ in turned)
            self.assertEqual(order2, order[n - passed:] + order[:n - passed])
            moved = signs
            for _ in range(passed):
                moved = rotate(n, moved)
            self.assertEqual(moved, signs2)
            checked += 1
        self.assertGreater(checked, 100)


@needs_pysat
class Encoding(unittest.TestCase):
    def drawings(self, n):
        from pysat.formula import IDPool
        from pysat.solvers import Solver
        pool = IDPool()
        chi = {t: pool.id(t) for t in combinations(range(n), 3)}
        with Solver(name="cadical195", bootstrap_with=signotope_clauses(n, chi)) as engine:
            return sum(1 for _ in engine.enum_models())

    def test_counts_of_drawings(self):
        # Known counts of simple drawings of 4, 5 and 6 pseudolines.
        self.assertEqual([self.drawings(n) for n in (4, 5, 6)], [8, 62, 908])

    def test_triangle_variables_mean_triangles(self):
        """Fix the signs of a real drawing; each triangle variable can be true
        exactly when the checker sees that triangle."""
        from pysat.solvers import Solver
        from tools.wall_crossing_pilot import all_crossing_start
        rng = random.Random(7)
        cases = [signotope_from_lines(all_crossing_start())[1]]
        cases += [wiring(rng.randint(5, 10), rng)[0] for _ in range(10)]
        for signs in cases:
            n = max(max(t) for t in signs) + 1
            clauses, chi, tri, _ = build(n, 0, per_line_cap=False)
            fixed = [[chi[t] if v else -chi[t]] for t, v in signs.items()]
            seen = set(triangles(n, signs))
            with Solver(name="cadical195", bootstrap_with=clauses + fixed) as engine:
                for t, variable in tri.items():
                    self.assertEqual(engine.solve(assumptions=[variable]), t in seen, t)

    def test_small_maxima_both_encodings(self):
        for n, k in KNOWN.items():
            for structure in (False, True):
                found = solve(n, k, structure=structure)
                self.assertEqual(found["status"], "found", (n, k, structure))
                self.assertGreaterEqual(found["triangles"], k)
                self.assertEqual(solve(n, k + 1, structure=structure)["status"], "impossible", (n, structure))

    def test_the_93_drawing_satisfies_the_structure(self):
        """Turn the 93 until a full line comes first; the structured formula
        for at least 93 must then accept its signs."""
        from pysat.solvers import Solver
        from tools.wall_crossing_pilot import all_crossing_start
        signs = signotope_from_lines(all_crossing_start())[1]
        found = triangles(18, signs)
        while sum(0 in t for t in found) < 16:
            signs = rotate(18, signs)
            found = triangles(18, signs)
        clauses, chi, _, _ = build(18, 93, structure=True)
        fixed = [[chi[t] if v else -chi[t]] for t, v in signs.items()]
        with Solver(name="cadical195", bootstrap_with=clauses + fixed) as engine:
            self.assertTrue(engine.solve())
        clauses, chi, _, _ = build(18, 94, structure=True)
        with Solver(name="cadical195", bootstrap_with=clauses + fixed) as engine:
            self.assertFalse(engine.solve())

    def test_threefold_formula(self):
        from pysat.solvers import Solver
        from tools.wall_crossing_pilot import all_crossing_start
        signs = signotope_from_lines(all_crossing_start())[1]
        while sum(0 in t for t in triangles(18, signs)) < 16:
            signs = rotate(18, signs)
        for at_least, expected in ((93, True), (94, False)):
            clauses, chi, _, _ = build(18, at_least, structure=True, fold=3)
            fixed = [[chi[t] if v else -chi[t]] for t, v in signs.items()]
            with Solver(name="cadical195", bootstrap_with=clauses + fixed) as engine:
                self.assertEqual(engine.solve(), expected)
        # whatever a threefold search returns really is threefold
        for n, k in ((6, 6), (9, 18), (12, 30)):
            found = solve(n, k, structure=True, fold=3)
            self.assertEqual(found["status"], "found")
            signs = signs_from_text(n, found["signs"])
            moved = signs
            for _ in range(2 * n // 3):
                moved = rotate(n, moved)
            self.assertEqual(moved, signs)

    def test_counting_rules_out_the_known_bounds(self):
        from tools.kobon_sat import full_line_bounds
        self.assertEqual(full_line_bounds(18, 94), (12, 12, 15))
        for n, k in ((13, 48), (15, 66), (16, 73), (17, 86)):
            result = solve(n, k, structure=True)
            self.assertEqual(result["status"], "impossible", (n, k))
            self.assertLess(result["seconds_to_solve"], 1)

    def test_cnf_file_is_the_same_formula(self):
        import os
        import tempfile
        from tools.kobon_sat import write_cnf
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "f.cnf")
            top, count = write_cnf(path, 9, 21, "totalizer", True, 3)
            clauses, _, _, expected_top = build(9, 21, True, "totalizer", True, 3)
            with open(path, encoding="ascii") as stream:
                lines = [line.split() for line in stream if not line.startswith("c")]
        self.assertEqual(lines[0], ["p", "cnf", str(expected_top), str(len(clauses))])
        self.assertEqual([[int(v) for v in line[:-1]] for line in lines[1:]], clauses)
        self.assertEqual((top, count), (expected_top, len(clauses)))

    def test_edge_bounds(self):
        self.assertEqual(solve(3, 0)["status"], "found")
        self.assertEqual(solve(3, 2)["status"], "impossible")
        self.assertEqual(solve(4, 5, structure=True)["status"], "impossible")



try:
    import scipy  # noqa: F401
    HAVE_SCIPY = True
except ImportError:
    HAVE_SCIPY = False


@unittest.skipUnless(HAVE_SCIPY, "scipy is not installed")
class Straightening(unittest.TestCase):
    def test_small_patterns_straighten_exactly(self):
        # Every simple drawing of at most eight pseudolines can be straightened
        # (Goodman and Pollack), so the method should not fail on them.
        from tools.straighten import straighten
        rng = random.Random(8)
        for _ in range(10):
            n = rng.randint(4, 8)
            signs, _ = wiring(n, rng)
            lines = next(filter(None, (straighten(n, signs, seed=s) for s in range(10))), None)
            self.assertIsNotNone(lines)
            order, got = signotope_from_lines(lines)
            self.assertEqual((order, got), (list(range(n)), signs))

    def test_command_line_records_every_start(self):
        import json
        import os
        import subprocess
        import sys
        import tempfile
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        lines, (_, signs) = random_straight(random.Random(12), 5)
        with tempfile.TemporaryDirectory() as folder:
            source = os.path.join(folder, "lines.json")
            out = os.path.join(folder, "out.json")
            with open(source, "w", encoding="utf-8") as stream:
                json.dump({"lines": [list(line) for line in lines]}, stream)
            subprocess.run([sys.executable, "-m", "tools.straighten", source, "--margins", "0.01,0.001",
                            "--seeds", "2", "--out", out], cwd=root, check=True, capture_output=True)
            with open(out, encoding="utf-8") as stream:
                result = json.load(stream)
        self.assertEqual((result["margins"], result["seeds"], result["starts"]), ([0.01, 0.001], 2, 4))
        self.assertEqual((result["n"], result["pattern_triangles"]), (5, len(triangles(5, signs))))

    def test_the_93_with_small_numbers(self):
        from kobon.verify import verify_file
        from tools.straighten import straighten
        from tools.wall_crossing_pilot import all_crossing_start
        signs = signotope_from_lines(all_crossing_start())[1]
        lines = straighten(18, signs, margin=0.025, seed=5)
        self.assertEqual(max(abs(v) for line in lines for v in line), 42)
        self.assertEqual(verify_file("candidates/small-93/solution.json")["score"], 93)
        import json
        with open("candidates/small-93/solution.json", encoding="utf-8") as stream:
            self.assertEqual([tuple(l) for l in json.load(stream)["lines"]], lines)


if __name__ == "__main__":
    unittest.main()
