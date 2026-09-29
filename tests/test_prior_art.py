"""Regression tests for deterministic, data-only prior-art reconstruction."""
from pathlib import Path
from itertools import combinations
import json
import unittest
from tools.reconstruct_prior_art_93 import endpoint_line, reconstruct
from kobon.verify import verify_lines
from kobon.io import load_solution
from kobon.geometry import intersection

ROOT = Path(__file__).resolve().parents[1]


class PriorArtTests(unittest.TestCase):
    def test_horizontal(self):
        self.assertEqual(endpoint_line(["0", "2", "3", "2"]), [0, 1, -2])

    def test_vertical(self):
        self.assertEqual(endpoint_line(["2", "0", "2", "3"]), [1, 0, -2])

    def test_endpoint_order(self):
        first = endpoint_line(["1.2", "4.7", "2.3", "8.9"])
        self.assertEqual(first, endpoint_line(["2.3", "8.9", "1.2", "4.7"]))

    def test_repeated_endpoint(self):
        with self.assertRaises(ValueError):
            endpoint_line(["1", "2", "1", "2"])

    def test_source_identity(self):
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            reconstruct(b"<svg />")

    def test_published_candidate(self):
        source = ROOT / "evidence/prior-art-93/source/kobon_18_93tri_lines.svg"
        solution = reconstruct(source.read_bytes())
        self.assertEqual(verify_lines(solution["lines"])["score"], 93)

    def test_saved_candidate_matches_reconstruction(self):
        source = ROOT / "evidence/prior-art-93/source/kobon_18_93tri_lines.svg"
        stored = load_solution(ROOT / "candidates/prior-art-93/solution.json")
        rebuilt = reconstruct(source.read_bytes())["lines"]
        self.assertEqual(stored, [tuple(line) for line in rebuilt])

    def test_saved_report_and_certificate(self):
        lines = load_solution(ROOT / "candidates/prior-art-93/solution.json")
        actual = verify_lines(lines)
        saved = json.loads((ROOT / "evidence/prior-art-93/verification.json").read_text())
        certificate = json.loads((ROOT / "evidence/prior-art-93/geometry.json").read_text())
        self.assertEqual(actual["triangle_line_indices"], saved["triangle_line_indices"])
        self.assertEqual(actual["triangle_line_indices"],
                         [t["supporting_line_indices"] for t in certificate["triangles"]])
        self.assertEqual(actual["verifier_identity"], saved["verifier_identity"])

    def test_candidate_degeneracy_is_explicit(self):
        lines = load_solution(ROOT / "candidates/prior-art-93/solution.json")
        parallel = [list(pair) for pair in combinations(range(18), 2)
                    if intersection(*(lines[i] for i in pair)) is None]
        self.assertEqual(parallel, [[0, 1], [6, 7], [12, 13]])
        for i, j, k in combinations(range(18), 3):
            point = intersection(lines[i], lines[j])
            if point is not None:
                self.assertNotEqual(sum(a * b for a, b in zip(lines[k], point)), 0)
