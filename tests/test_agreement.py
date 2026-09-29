import random
import unittest
from unittest.mock import patch
from kobon.io import canonical
from kobon.verify import verify_lines


class AgreementTests(unittest.TestCase):
    def test_baseline(self):
        self.assertEqual(verify_lines([(2*i,-1,-i*i) for i in range(18)])['score'],16)

    def test_exact_random_sets(self):
        rng=random.Random(20260927)
        for trial in range(150):
            n=3+trial%10
            rows=set()
            while len(rows)<n:
                row=tuple(rng.randint(-6,6) for _ in range(3))
                if row[0] or row[1]:rows.add(canonical(row))
            with self.subTest(trial=trial,n=n):
                report=verify_lines(sorted(rows),n)
                self.assertTrue(report['verified'])
                self.assertFalse(report['official_evaluator_run'])

    def test_mismatch_fails_closed(self):
        with patch('kobon.verify.triangles_by_interior',return_value=[]):
            with self.assertRaisesRegex(ValueError,'disagree'):
                verify_lines([[1,0,0],[0,1,0],[1,1,-1]],3)

    def test_very_small_split(self):
        m=10**30
        report=verify_lines([(1,0,0),(0,1,0),(m,m,-1),(1,-1,0)],4)
        self.assertEqual(report['triangle_line_indices'],[[0,2,3],[1,2,3]])
