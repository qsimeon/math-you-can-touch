# A second 93

These 18 lines form 93 triangular faces, and every coefficient is a whole number between -70 and 70. Each `[a, b, c]` in `solution.json` means `a*x + b*y + c = 0`. Every pair of lines crosses and no three meet at a point.

The drawing differs from Bader's. Its crossing pattern matches none of the versions of his drawing that can be made by turning it, mirroring it, separating his three parallel pairs, or sending a different line to infinity. A count that ignores those choices confirms the difference: with the line at infinity added as a nineteenth line, this drawing has 102 triangles and every version of Bader's has 105. We have not checked whether anyone has published this drawing before.

A SAT solver found the crossing pattern while searching only drawings that look the same after a turn by a third of a circle, the symmetry that Bader's 93 has. `tools/straighten.py` then found straight lines with exactly that pattern. Both exact counters agree on all 93 triangles:

```sh
python3 -c "from kobon.verify import verify_file; print(verify_file('candidates/sat-93-a/solution.json')['score'])"
python3 -m tools.compare_93 candidates/sat-93-a/solution.json
```

The second command repeats the comparison with Bader's drawing and needs no extra packages. `wiring.svg` shows the drawing as a wiring diagram, with each line as a horizontal track and the 93 triangles shaded.
