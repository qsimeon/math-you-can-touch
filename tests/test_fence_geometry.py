"""Cross-language checks for the standalone browser BigInt fence scorer."""
import json
import shutil
import tempfile
import subprocess
import unittest
from pathlib import Path

from kobon.geometry import triangles_by_adjacency
from kobon.oracle import triangles_by_interior
from kobon.verify import verify_file, verify_lines

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'site' / 'fence-geometry.js'
DATA = json.loads((ROOT / 'site' / 'data.js').read_text()[len('window.LEARNING_DATA = '):-2])


class FenceGeometryTests(unittest.TestCase):
    def browser_score(self, lines):
        program = """const G=require(process.argv[1]);let input='';process.stdin.on('data',x=>input+=x);process.stdin.on('end',()=>{const r=G.score(JSON.parse(input));process.stdout.write(JSON.stringify({score:r.score,faces:r.faces,lines:r.lines.map(x=>x.map(String))}));});"""
        result = subprocess.run(
            [shutil.which('bun') or 'bun', '-e', program, str(MODULE)],
            input=json.dumps([[str(value) for value in row] for row in lines]),
            text=True, capture_output=True, check=True,
        )
        return json.loads(result.stdout)

    def assert_all_agree(self, lines):
        primary = triangles_by_adjacency(lines)
        independent = triangles_by_interior(lines)
        verified = verify_lines([list(row) for row in lines], len(lines))
        browser = self.browser_score(lines)
        expected = [list(face) for face in primary]
        self.assertEqual(primary, independent)
        self.assertEqual(verified['triangle_line_indices'], expected)
        self.assertEqual(browser['faces'], expected)
        self.assertEqual(browser['score'], len(expected))

    def test_all_saved_frames_match_both_unchanged_verifiers(self):
        for record in DATA['kobon']['snapshots'] + DATA['kobon']['motion']['frames']:
            lines = [tuple(map(int, row)) for row in record['lines']]
            with self.subTest(record=record.get('id', record.get('offset'))):
                self.assert_all_agree(lines)
                self.assertEqual(self.browser_score(lines)['score'], record['score'])

    def test_adversarial_parallel_concurrent_and_tiny_fixtures(self):
        fixtures = [
            [(1, 0, 0), (0, 1, 0), (1, 1, -1), (1, 1, 0)],
            [(1, 0, 0), (0, 1, 0), (10**30, 10**30, -1), (1, -1, 0)],
            [(1, 0, 0), (0, 1, 0), (1, 1, 0)],
            [(2*i, -1, -i*i) for i in range(9)],
        ]
        for lines in fixtures:
            with self.subTest(lines=lines):
                self.assert_all_agree(lines)

    def test_published_line_seven_rotation_export_keeps_other_lines_and_verifies(self):
        published = next(item for item in DATA['kobon']['snapshots'] if item['score'] == 93)
        lines = [tuple(map(int, row)) for row in published['lines']]
        program = """const G=require(process.argv[1]);const fs=require('fs');const d=JSON.parse(fs.readFileSync(process.argv[2],'utf8').slice(23,-2));const lines=d.kobon.snapshots.find(s=>s.score===93).lines;const changed=G.rotateRational(lines,6,1n,20n);process.stdout.write(JSON.stringify({lines:changed.map(r=>r.map(String)),json:G.exportJSON(changed)}));"""
        result = subprocess.run([shutil.which('bun') or 'bun', '-e', program, str(MODULE), str(ROOT/'site'/'data.js')], text=True, capture_output=True, check=True)
        changed = json.loads(result.stdout)
        exact_lines = [tuple(map(int, row)) for row in changed['lines']]
        self.assertEqual(len(exact_lines), 18)
        self.assertNotEqual(exact_lines[6], lines[6])
        self.assertEqual(exact_lines[:6], lines[:6])
        self.assertEqual(exact_lines[7:], lines[7:])
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'edited-published-93-lines.json'
            target.write_text(changed['json'])
            report = verify_file(target)
        self.assertEqual(report['triangle_line_indices'], [list(face) for face in triangles_by_adjacency(exact_lines)])
        self.assertEqual(triangles_by_adjacency(exact_lines), triangles_by_interior(exact_lines))

    def test_strict_boundary_and_exact_snapped_moves(self):
        result = subprocess.run(
            [shutil.which('bun') or 'bun', '-e', """const G=require(process.argv[1]);const good=[[1n,0n,0n],[0n,1n,0n],[1n,1n,-1n]];const moved=G.translateParallel(good,0,2n);let invalid=[];for(const x of [[[0n,0n,0n],...good.slice(1)],[[1n,0n,0n],[2n,0n,0n],[0n,1n,0n]],[[10n**30n+1n,0n,0n],...good.slice(1)]])try{G.score(x)}catch(e){invalid.push(e.message)}process.stdout.write(JSON.stringify({moved:moved.map(r=>r.map(String)),score:G.score(good).score,invalid}));""", str(MODULE)],
            text=True, capture_output=True, check=True,
        )
        value = json.loads(result.stdout)
        self.assertEqual(value['score'], 1)
        self.assertEqual(value['moved'][0], ['1', '0', '2'])
        self.assertEqual(len(value['invalid']), 3)


if __name__ == '__main__':
    unittest.main()
