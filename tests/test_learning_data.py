import json
import unittest
from pathlib import Path
from fractions import Fraction
from kobon.io import validate_lines
from kobon.verify import verify_lines
from kobon.geometry import triangle_vertices
from busybeaver.core import simulate_dict,simulate_set

R=Path(__file__).resolve().parents[1]
class LearningDataTests(unittest.TestCase):
 def test_all_saved_geometry_and_motion(self):
  data=json.loads((R/'site/data.js').read_text()[len('window.LEARNING_DATA = '):-2])
  original=data['kobon']['snapshots'][-1]
  base={tuple(t['indices']) for t in original['triangles']}
  for snap in data['kobon']['snapshots']+data['kobon']['motion']['frames']:
   lines=validate_lines([[int(c) for c in row] for row in snap['lines']])
   report=verify_lines(lines)
   self.assertEqual(report['score'],snap['score'])
   self.assertEqual(report['triangle_line_indices'],[t['indices'] for t in snap['triangles']])
   for t in snap['triangles']:
    exact=triangle_vertices(lines,t['indices'])
    self.assertEqual([[str(x),str(y)] for x,y in exact],t['exact_vertices'])
    self.assertEqual([[float(x),float(y)] for x,y in exact],t['vertices'])
   if 'gained' in snap:
    faces={tuple(t['indices']) for t in snap['triangles']}
    self.assertEqual(sorted(faces-base),[tuple(x) for x in snap['gained']])
    self.assertEqual(sorted(base-faces),[tuple(x) for x in snap['lost']])
  zero=next(x for x in data['kobon']['motion']['frames'] if x['offset']==0)
  self.assertEqual(zero['lines'],original['lines']);self.assertEqual(zero['score'],93)
 def test_trace_and_counts(self):
  data=json.loads((R/'site/data.js').read_text()[len('window.LEARNING_DATA = '):-2])['busybeaver']
  summary=data['summary']
  self.assertEqual(summary['total'],summary['halted']+summary['nonhalting']+summary['unknown'])
  self.assertEqual(simulate_set(data['champion']['table'],trace=True)['trace'],data['champion']['trace'])
  self.assertEqual(simulate_dict(data['champion']['table'])['steps'],6)
