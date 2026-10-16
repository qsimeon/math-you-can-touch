"""Exact wall-crossing move: geometry invariants, rational choice and run ledger."""
import json
import random
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from kobon.geometry import intersection
from kobon.verify import verify_lines
from tools.wall_crossing_pilot import (
    all_crossing_start,
    crossing_key,
    run,
    simplest_between,
    translation_move,
)


def _brute_simplest(lo, hi, limit=60):
    for q in range(1, limit + 1):
        candidates = [Fraction(p, q) for p in range(-limit * q, limit * q + 1)
                      if lo < Fraction(p, q) < hi]
        if candidates:
            return min(candidates, key=abs)
    return None


class SimplestRationalTests(unittest.TestCase):
    def test_matches_brute_force_denominator(self):
        rng = random.Random(5)
        for _ in range(400):
            a = Fraction(rng.randint(-300, 300), rng.randint(1, 40))
            b = Fraction(rng.randint(-300, 300), rng.randint(1, 40))
            if a == b:
                continue
            lo, hi = min(a, b), max(a, b)
            got = simplest_between(lo, hi)
            self.assertTrue(lo < got < hi, (lo, hi, got))
            self.assertEqual(_brute_simplest(lo, hi).denominator, got.denominator, (lo, hi))

    def test_integer_endpoints_are_excluded(self):
        self.assertEqual(Fraction(7, 2), simplest_between(3, 4))
        self.assertEqual(Fraction(0), simplest_between(-1, 1))
        self.assertEqual(Fraction(-2), simplest_between(Fraction(-5, 2), Fraction(-3, 2)))
        with self.assertRaises(ValueError):
            simplest_between(1, 1)


class TranslationMoveTests(unittest.TestCase):
    def setUp(self):
        self.lines = all_crossing_start()

    def test_start_is_simple_all_crossing_93(self):
        self.assertEqual(93, verify_lines([list(r) for r in self.lines])["score"])
        crossing_key(self.lines)  # raises on parallel pairs or triple points

    def test_reproduces_published_checked_example(self):
        # docs/RESEARCH.md: translating line 0 to [0, 2, -727] gives 90 faces.
        outcomes = [translation_move(self.lines, 0, d) for d in (1, -1)]
        new_lines = [o[0] for o in outcomes if o[0] is not None]
        self.assertIn((0, 2, -727), new_lines)
        child = list(self.lines)
        child[0] = (0, 2, -727)
        self.assertEqual(90, verify_lines([list(r) for r in child])["score"])

    def test_every_move_is_one_triangle_flip(self):
        before_rows, before_dirs = crossing_key(self.lines)
        moves = 0
        for index in range(18):
            for direction in (1, -1):
                new_line, crossed, reason = translation_move(self.lines, index, direction)
                if reason:
                    continue
                moves += 1
                old = self.lines[index]
                self.assertEqual(0, old[0] * new_line[1] - old[1] * new_line[0])  # parallel
                self.assertGreater(old[0] * new_line[0] + old[1] * new_line[1], 0)  # same side
                child = list(self.lines)
                child[index] = new_line
                rows, dirs = crossing_key(child)
                self.assertEqual(before_dirs, dirs)
                j, k = crossed
                changed = {i for i in range(18) if rows[i] != before_rows[i]}
                self.assertEqual({index, j, k}, changed)
                for line, pair in ((index, (j, k)), (j, (index, k)), (k, (index, j))):
                    old_row, new_row = before_rows[line], rows[line]
                    p, q = sorted(old_row.index(x) for x in pair)
                    self.assertEqual(1, q - p)  # neighbors before the flip
                    swapped = list(old_row)
                    swapped[p], swapped[q] = swapped[q], swapped[p]
                    self.assertEqual(tuple(swapped), new_row)
        self.assertGreater(moves, 20)

    def test_tied_vertices_are_rejected(self):
        # Moving y = 0 upward (c decreasing) meets (0,1) and (2,1) at once on y = 1.
        lines = [(0, 1, 0), (1, 0, 0), (0, 1, -1), (1, -1, -1)]
        new_line, tied, reason = translation_move(lines, 0, -1)
        self.assertIsNone(new_line)
        self.assertEqual("tied nearest threshold", reason)
        self.assertEqual({(1, 2), (2, 3)}, {tuple(pair) for pair in tied})
        # Downward, the single vertex (0,-1) is crossed and the line lands beyond it.
        new_line, crossed, reason = translation_move(lines, 0, 1)
        self.assertIsNone(reason)
        self.assertEqual((1, 3), tuple(crossed))
        self.assertEqual((0, 1, 2), new_line)


class RunLedgerTests(unittest.TestCase):
    def test_small_run_replays_from_ledger(self):
        start = [(1, 0, 0), (0, 1, 0), (1, 1, -5), (1, -3, 1), (2, 1, -9), (3, -1, -2)]
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "moves.jsonl"
            summary, states = run(start, budget=40, log_path=log)
            rows = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertLessEqual(summary["evaluated"], 40)
        evaluated = [r for r in rows if r["outcome"] == "evaluated"]
        self.assertEqual(summary["evaluated"], len(evaluated))
        rebuilt = {0: [tuple(r) for r in evaluated[0]["lines"]]}
        for row in evaluated[1:]:
            lines = list(rebuilt[row["parent"]])
            lines[row["line"]] = tuple(row["new_line"])
            rebuilt[row["state"]] = lines
            self.assertEqual(row["score"], verify_lines([list(r) for r in lines], n=6)["score"])
        keys = {crossing_key(lines) for lines in rebuilt.values()}
        self.assertEqual(len(rebuilt), len(keys))  # deduplicated by crossing order


if __name__ == "__main__":
    unittest.main()
