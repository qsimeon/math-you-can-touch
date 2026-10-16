"""Nonhalting certificates: soundness on every table and rejection of bad certificates."""
import unittest

from busybeaver.core import compare_simulations, enumerate_tables
from tools.beaver_certificates import (
    certify,
    check,
    check_record_cycle,
    halt_unreachable,
    reachable_slots,
)

TRAIL = (((1, "R", "A"), (1, "R", "H")), ((0, "L", "A"), (0, "L", "A")))
CHAMPION = (((1, "R", "B"), (1, "L", "B")), ((1, "L", "A"), (1, "R", "H")))


class CertificateTests(unittest.TestCase):
    def test_every_table_is_resolved_and_no_halter_is_certified(self):
        counts = {"halted": 0, "repeat": 0, "certified": 0}
        longest = 0
        for table in enumerate_tables():
            result = compare_simulations(table, step_limit=100)
            cert = certify(table)
            if result["status"] == "HALTED":
                self.assertIsNone(cert, table)
                counts["halted"] += 1
                longest = max(longest, result["steps"])
            elif result["status"] == "NONHALTING_BY_TRANSLATION_CYCLE":
                counts["repeat"] += 1
            else:
                self.assertIsNotNone(cert, table)
                self.assertTrue(check(table, cert), table)
                counts["certified"] += 1
        self.assertEqual({"halted": 9784, "repeat": 5040, "certified": 5912}, counts)
        self.assertEqual(6, longest)

    def test_static_reachability(self):
        # B is never entered and 1 is never written, so only (A, 0) is ever read.
        table = (((0, "R", "A"), (1, "L", "H")), ((1, "L", "H"), (1, "L", "H")))
        self.assertEqual({("A", 0)}, reachable_slots(table))
        self.assertTrue(halt_unreachable(table))
        self.assertFalse(halt_unreachable(TRAIL))

    def test_trail_writer_and_champion(self):
        cert = certify(TRAIL)
        self.assertEqual({"kind": "record-cycle", "side": "R", "t1": 0, "t2": 1}, cert)
        self.assertTrue(check(TRAIL, cert))
        self.assertIsNone(certify(CHAMPION))

    def test_tampered_certificates_are_rejected(self):
        good = {"kind": "record-cycle", "side": "R", "t1": 0, "t2": 1}
        self.assertFalse(check_record_cycle(TRAIL, dict(good, side="L")))
        self.assertFalse(check_record_cycle(TRAIL, dict(good, t1=1, t2=1)))
        self.assertFalse(check_record_cycle(CHAMPION, {"side": "R", "t1": 0, "t2": 4}))
        self.assertFalse(check(TRAIL, {"kind": "made-up"}))
        for table, raw in ((CHAMPION, {"side": s, "t1": a, "t2": b})
                           for s in "RL" for a in range(6) for b in range(a + 1, 8)):
            self.assertFalse(check_record_cycle(table, raw), raw)


if __name__ == "__main__":
    unittest.main()
