import unittest
from pathlib import Path

from kobon.io import load_solution
from tools.segment_audit import audit


ROOT = Path(__file__).resolve().parents[1]


class SegmentAuditTests(unittest.TestCase):
    def test_saved_witnesses(self):
        for name, faces, parallels, edges, unused in (
            ('best', 76, 1, 286, 58),
            ('prior-art-93', 93, 3, 282, 3),
        ):
            with self.subTest(name=name):
                lines = load_solution(ROOT / f'candidates/{name}/solution.json')
                result = audit(lines)
                self.assertEqual((result['triangular_faces'], len(result['parallel_pairs']),
                                  result['bounded_segments'], len(result['unused_segments'])),
                                 (faces, parallels, edges, unused))
                self.assertEqual([], result['multiple_points'])
        result = audit(load_solution(ROOT / 'candidates/prior-art-93/solution.json'))
        self.assertEqual([0, 7, 12], [item['line'] for item in result['unused_segments']])
        self.assertEqual([[[15], [16]], [[4], [3]], [[10], [9]]],
                         [item['endpoint_crossings'] for item in result['unused_segments']])

    def test_parallel_pairs_can_be_separated_without_losing_faces(self):
        lines = [list(row) for row in load_solution(ROOT / 'candidates/prior-art-93/solution.json')]
        for index in (1, 7, 13):
            lines[index][0] += 1
        result = audit(lines)
        self.assertEqual(93, result['triangular_faces'])
        self.assertEqual([], result['parallel_pairs'])
        self.assertEqual([], result['multiple_points'])
        self.assertEqual(288, result['bounded_segments'])
        self.assertEqual(9, len(result['unused_segments']))
        self.assertEqual(288 - 3 * 93, len(result['unused_segments']))

    def test_exact_line_translation_crosses_one_vertex(self):
        lines = [list(row) for row in load_solution(ROOT / 'candidates/prior-art-93/solution.json')]
        for index in (1, 7, 13):
            lines[index][0] += 1
        lines[0] = [0, 2, -727]
        result = audit(lines)
        self.assertEqual((90, 0, 0, 18),
                         (result['triangular_faces'], len(result['parallel_pairs']),
                          len(result['multiple_points']), len(result['unused_segments'])))

    def test_concurrency_withholds_unused_segment_identity(self):
        # Three lines through the origin, one transversal. Concurrency is legal,
        # but U=E-3T does not apply here.
        lines = [(1, 0, 0), (0, 1, 0), (1, 1, 0), (1, 2, -2)]
        result = audit(lines)
        self.assertIsNone(result['unused_segments'])
        self.assertTrue(result['multiple_points'])

    def test_all_parallel_has_no_bounded_segments(self):
        result = audit([(1, 0, 0), (1, 0, -1), (1, 0, -2)])
        self.assertEqual((result["triangular_faces"], result["bounded_segments"],
                          len(result["unused_segments"])), (0, 0, 0))

    def test_input_validation_before_segment_count(self):
        with self.assertRaisesRegex(ValueError, 'proportional duplicate'):
            audit([(1, 0, 0), (2, 0, 0), (0, 1, 0)])
        with self.assertRaisesRegex(ValueError, 'integers'):
            audit([(1.0, 0, 0), (0, 1, 0), (1, 1, -2)])
