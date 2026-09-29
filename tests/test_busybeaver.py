import json
import tempfile
import unittest
from pathlib import Path

from busybeaver.core import (compare_simulations, enumerate_tables, replay_record,
                             run_experiment, simulate_dict, simulate_set,
                             validate_table)


CHAMPION = [[[1, 'R', 'B'], [1, 'L', 'B']],
            [[1, 'L', 'A'], [1, 'R', 'H']]]


class BusyBeaverTests(unittest.TestCase):
    def test_labeled_enumeration_has_all_20736_tables(self):
        tables = list(enumerate_tables())
        self.assertEqual(12 ** 4, len(tables))
        self.assertEqual(12 ** 4, len(set(tables)))

    def test_halting_transition_counts_as_a_step(self):
        table = [[[0, 'R', 'H'], [0, 'R', 'H']],
                 [[0, 'R', 'H'], [0, 'R', 'H']]]
        self.assertEqual({'status': 'HALTED', 'steps': 1, 'ones': 0}, simulate_set(table))
        self.assertEqual(simulate_set(CHAMPION), simulate_dict(CHAMPION))
        self.assertEqual({'status': 'HALTED', 'steps': 6, 'ones': 4}, simulate_set(CHAMPION))

    def test_left_and_right_motion_are_visible_in_trace(self):
        left = [[[1, 'L', 'H'], [0, 'R', 'H']], [[0, 'R', 'H'], [0, 'R', 'H']]]
        right = [[[1, 'R', 'H'], [0, 'R', 'H']], [[0, 'R', 'H'], [0, 'R', 'H']]]
        self.assertEqual(-1, simulate_set(left, trace=True)['trace'][1]['head'])
        self.assertEqual(1, simulate_set(right, trace=True)['trace'][1]['head'])

    def test_translation_cycle_has_explicit_witness(self):
        moving_blank = [[[0, 'R', 'A'], [0, 'R', 'A']],
                         [[0, 'R', 'A'], [0, 'R', 'A']]]
        result = compare_simulations(moving_blank)
        self.assertEqual('NONHALTING_BY_TRANSLATION_CYCLE', result['status'])
        self.assertEqual({'previous_step': 0, 'current_step': 1, 'period': 1,
                          'previous_head': 0, 'current_head': 1, 'shift': 1,
                          'state': 'A', 'normalized_ones': []}, result['repeat'])

    def test_limit_is_unknown_not_nonhalting(self):
        growing_right = [[[1, 'R', 'A'], [1, 'R', 'A']],
                         [[1, 'R', 'A'], [1, 'R', 'A']]]
        self.assertEqual({'status': 'UNKNOWN_AT_LIMIT', 'steps': 3},
                         compare_simulations(growing_right, step_limit=3))

    def test_invalid_tables_and_bounds_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'next state'):
            validate_table([[[0, 'R', 'Z'], [0, 'R', 'A']], [[0, 'R', 'A'], [0, 'R', 'A']]])
        with self.assertRaisesRegex(ValueError, 'move'):
            validate_table([[[0, 'X', 'A'], [0, 'R', 'A']], [[0, 'R', 'A'], [0, 'R', 'A']]])
        with self.assertRaisesRegex(ValueError, 'positive'):
            simulate_set(CHAMPION, step_limit=0)
        with self.assertRaisesRegex(ValueError, 'at most 120'):
            run_experiment(Path(tempfile.gettempdir()) / 'invalid-busybeaver', deadline_seconds=121)

    def test_saved_record_replays_and_tamper_is_rejected(self):
        record = {'index': 7, 'table': CHAMPION, 'result': simulate_dict(CHAMPION)}
        self.assertEqual(record['result'], replay_record(record))
        record['result'] = dict(record['result'], steps=5)
        with self.assertRaisesRegex(AssertionError, 'does not replay'):
            replay_record(record)

    def test_small_artifact_run_is_complete_and_contract_shaped(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / 'busy-beaver'
            summary = run_experiment(destination, step_limit=10, deadline_seconds=120)
            self.assertEqual(12 ** 4, summary['total'])
            self.assertEqual(summary['total'], summary['halted'] + summary['nonhalting'] + summary['unknown'])
            self.assertEqual(1, summary['workers'])
            agreement = json.loads((destination / 'agreement.json').read_text())
            self.assertEqual('PASS', agreement['verdict'])
            self.assertEqual(summary['total'], agreement['compared'])
            self.assertEqual(summary['total'], agreement['replayed'])
            site_data = json.loads((destination / 'site-data.json').read_text())
            self.assertEqual({'total', 'halted', 'nonhalting', 'unknown', 'step_limit', 'max_halted_steps', 'max_halted_ones'},
                             set(site_data['summary']))
            self.assertEqual(2, len(site_data['champion']['table']))
            self.assertTrue(site_data['champion']['trace'])
