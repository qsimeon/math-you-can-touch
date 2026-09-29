import random
import unittest
from fractions import Fraction
from kobon.geometry import intersection, cartesian, triangles_by_adjacency


class GeometryTests(unittest.TestCase):
    def test_intersection(self):
        self.assertEqual(cartesian(intersection((2,0,-1),(0,3,-1))),
                         (Fraction(1,2),Fraction(1,3)))
        self.assertEqual(intersection((-2,0,1),(0,-3,1)),(3,2,6))
        self.assertIsNone(intersection((1,0,0),(2,0,-1)))

    def test_basic_faces(self):
        triangle=[(1,0,0),(0,1,0),(1,1,-2)]
        self.assertEqual(triangles_by_adjacency(triangle),[(0,1,2)])
        self.assertEqual(triangles_by_adjacency(triangle+[(1,0,-1)]),[(1,2,3)])
        self.assertEqual(triangles_by_adjacency(triangle+[(1,-1,0)]),[(0,2,3),(1,2,3)])
        self.assertEqual(triangles_by_adjacency([(1,0,0),(0,1,0),(1,1,0)]),[])
        self.assertEqual(triangles_by_adjacency([(1,0,i) for i in range(3)]),[])

    def test_touching_vertex_does_not_split(self):
        lines=[(1,0,0),(0,1,0),(1,1,-1),(1,1,0)]
        self.assertEqual(triangles_by_adjacency(lines),[(0,1,2)])

    def test_tiny_faces(self):
        m=10**30
        self.assertEqual(triangles_by_adjacency([(1,0,0),(0,1,0),(m,m,-1)]),[(0,1,2)])

    def test_baseline_and_max_n(self):
        for n in [3,18,100]:
            self.assertEqual(len(triangles_by_adjacency([(2*i,-1,-i*i) for i in range(n)])),n-2)

    def test_affine_scaling_and_order(self):
        lines=[(2*i,-1,-i*i) for i in range(18)]
        changed=[(2*a+b,a+b,3*a-4*b+c) for a,b,c in lines]
        wanted=triangles_by_adjacency(lines)
        self.assertEqual(triangles_by_adjacency(changed),wanted)
        self.assertEqual(triangles_by_adjacency([tuple(-7*x for x in l) for l in changed]),wanted)
        order=list(range(18));random.Random(33).shuffle(order)
        actual=triangles_by_adjacency([lines[i] for i in order])
        self.assertEqual({tuple(sorted(order[j] for j in t)) for t in actual},set(wanted))
