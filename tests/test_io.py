import json
import tempfile
import unittest
from pathlib import Path
from kobon.io import load_solution, validate_lines

TRIANGLE = [[1, 0, 0], [0, 1, 0], [1, 1, -1]]


class InputTests(unittest.TestCase):
    def test_valid_and_permitted_degeneracies(self):
        for lines in [TRIANGLE, [[1,0,0],[1,0,-1],[0,1,0]],
                      [[1,0,0],[0,1,0],[1,1,0]]]:
            self.assertEqual(len(validate_lines(lines,3)),3)

    def test_rejections(self):
        for lines in [TRIANGLE[:2], TRIANGLE+[[1,1,1]],
                      [[1,0,0],[0,1,0],[0,0,1]],
                      [[1,0,0],[0,1,0],[-2,0,0]],
                      [[True,0,0],[0,1,0],[1,1,-1]],
                      [[1.0,0,0],[0,1,0],[1,1,-1]],
                      [[10**30+1,0,0],[0,1,0],[1,1,-1]],
                      [[1,0],[0,1,0],[1,1,-1]]]:
            with self.subTest(lines=lines), self.assertRaises(ValueError):
                validate_lines(lines,3)
        for n in [True,2,101,3.0]:
            with self.assertRaises(ValueError): validate_lines(TRIANGLE,n)

    def test_file_contract(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'solution.json'
            p.write_text(json.dumps({'lines':TRIANGLE}))
            self.assertEqual(load_solution(p,3),[tuple(x) for x in TRIANGLE])
            p.write_bytes(b'\xef\xbb\xbf'+json.dumps({'lines':TRIANGLE}).encode())
            self.assertEqual(load_solution(p,3),[tuple(x) for x in TRIANGLE])
            link=Path(d)/'link';link.symlink_to(p)
            with self.assertRaises(ValueError):load_solution(link,3)
            for raw in [b'{}', b'[]',b'{"lines":[],"lines":[]}',
                        b'{"lines":NaN}',b'{"lines":Infinity}',
                        b'{"lines":[],"extra":1}',b'\xff',b' '*65537,
                        b'['*2000+b']'*2000]:
                p.write_bytes(raw)
                with self.subTest(raw=raw[:40]),self.assertRaises(ValueError):
                    load_solution(p,3)

    def test_baseline_input(self):
        p=Path(__file__).resolve().parents[1]/'candidates/baseline/solution.json'
        self.assertEqual(load_solution(p),[(2*i,-1,-i*i) for i in range(18)])
