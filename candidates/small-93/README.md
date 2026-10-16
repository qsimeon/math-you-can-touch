# The 93 with small numbers

These 18 lines form 93 triangular faces, and every coefficient is a whole number between -42 and 42. Each `[a, b, c]` in `solution.json` means `a*x + b*y + c = 0`. Every pair of lines crosses and no three meet at a point.

The crossing pattern is the one in `prior-art-93` after its three parallel pairs are separated by adding 1 to the first coefficient of lines 1, 7 and 13. The construction is Johannes Bader's, recovered from Pavlo Savchuk's LineOrder drawing. The `prior-art-93` folder records the source and its CC BY 4.0 credit. Only the size of the numbers is new. The reconstruction needs coefficients up to 736,030,939, and this drawing of the same pattern needs at most 42.

`tools/straighten.py` found it by discarding the coordinates, keeping only the order in which each line meets the others, and searching for new straight lines with that order. The search needs NumPy and SciPy, and the recount needs only Python:

```sh
python3 -m tools.straighten all-crossing-93 --margins 0.025 --seeds 40 --out small-93-run.json
python3 -c "from kobon.verify import verify_file; print(verify_file('candidates/small-93/solution.json')['score'])"
```

The first command tries 40 random starts and keeps the drawing with the smallest numbers, which seed 5 produces. The second prints 93 after both exact counters agree on every triangle.
