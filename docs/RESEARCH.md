# Research notes

The playgrounds lead to two different research questions. With 18 straight lines, can we make more than the 93 undivided triangular regions in Johannes Bader's known construction, or show that 93 is the most? With a two-state tape robot, can our own checker explain why every machine that has not halted by step 100 will never halt? The second question now has a checked answer, described at the end of this note. The first remains open.

## The 76-to-93 gap

Our first program started from random 18-line drawings. An ordinary proposal changed one integer coefficient on one line by 1, 2, 5 or 12. Some proposals replaced the whole line instead. The program accepted moves that maintained or raised the count, and unconditionally accepted a fresh random start every 200 proposals. The initial coefficients were small: normal components between -30 and 30 and offsets between -150 and 150. Three seeds ran for 1,200 proposals each, about 37 seconds per seed. They found 76, 73 and 73 triangular faces. The public repository includes the 76 drawing and its seed/step provenance, but its full proposal ledger stays in the separate research workspace.

Bader built his earlier 93-face arrangement independently of our program. His [archived page](https://www.sop.tik.ee.ethz.ch/people/baderj/other.html) calls the drawing threefold rotationally symmetric. We reconstructed an exact integer-coordinate drawing from Pavlo Savchuk's [LineOrder gallery SVG](https://raw.githubusercontent.com/zegalur/line-order/2631b8793eb351be2ad6b8a91b7194eeb67e25bb/gallery/imgs/kobon_18_93tri_lines.svg). Its largest coefficient magnitude is 736,030,939, well outside the small coefficients used to start our original random runs. Both exact counters find 93 faces in our reconstruction. We have not established equality with Bader's original coordinates or crossing order. Bader's archived page describes the drawing, but not how he discovered it. Savchuk's later algorithm offers a different research method.

To measure the structure of these drawings, count the bounded pieces into which intersections divide each line. Assume no three lines meet. Let `p` be the number of parallel pairs. If each line crosses at least one other line, the total number of such *segments* on 18 lines is `E = 288 - 2p`. An all-parallel drawing has no triangles and is handled separately. Every triangular face uses three segments, and a segment cannot border triangular faces on both sides when each vertex joins exactly two lines. Thus the count of unused segments is `U = E - 3T`, where `T` is the number of triangular faces. Both saved drawings satisfy these conditions:

| Exact drawing | Parallel pairs `p` | Bounded segments `E` | Triangular faces `T` | Unused segments `U` |
| --- | ---: | ---: | ---: | ---: |
| Our original search | 1 | 286 | 76 | 58 |
| Reconstructed Bader construction | 3 | 282 | 93 | 3 |

The three unused segments in the reconstruction lie on line indices 0, 7 and 12, each belonging to a parallel pair. Indices start at zero in the downloaded line list. Use the [segment-audit command](../README.md#run-the-checks) to see their endpoint crossings. This measures a difference between two checked arrangements. The next question is whether changing one crossing at a time can improve a high-scoring drawing. In the saved 41-position motion study, moving one line of the 93 arrangement produced scores from 80 to 93. Four later runs starting at 93 each made 1,500 proposals, mostly changing one coefficient. Their restarts made three line-parameter changes before checking a new drawing. No summary reports an improvement, and the public copy does not include the per-proposal logs.

## From crossing patterns to straight lines

Savchuk's [2025 paper](https://arxiv.org/html/2507.07951v1) describes a structural search. Record, for each line, the order in which other lines cross it. A *pseudoline* can bend while retaining this pattern, so first search crossing orders without choosing exact coordinates. The paper encodes conditions on the orders as a satisfiability problem and asks a SAT solver for candidate tables. Then it tries to *straighten* a candidate: find angles and offsets for actual lines whose crossings occur in the required order. The straightening step uses heuristic SciPy minimization over order inequalities. A failure to straighten a table does not prove that the table is impossible for straight lines. Any promising straight-line result still needs an exact face recount. Our public repository can reconstruct a drawing and count faces, but does not include a SAT model or table-straightening solver.

Savchuk's published model already has optional variables for bounded segments without a neighboring triangle. It assumes every pair of lines crosses in a distinct point. A missing crossing for parallel lines needs a different encoding. He also [proposes extending the approach to even line counts and underused parallel/concurrent cases](https://arxiv.org/html/2507.07951v1). Adapting those ideas to 18 lines would build on this prior work.

## The upper bound of 94

Bartholdi, Blanc and Loisel's [published theorem](https://arxiv.org/html/0706.0723v1) gives a bound for *simple*, pairwise-intersecting arrangements of 18 lines, including pseudolines: `floor(18(18 - 7/3)/3) = 94`. [OEIS](https://oeis.org/A006066) lists 93 achieved and 94 as the reported upper bound for the 18-line problem. The theorem cannot be applied directly to our 93 drawing because three pairs of its lines are parallel. For a no-triple-point arrangement, a short perturbation argument suggests that rotating parallel lines by sufficiently small angles creates new crossings far away while leaving existing bounded triangular faces intact. This would extend that 94 ceiling to the no-triple-point case with parallel lines. This argument has not been formally checked or reviewed by a mathematician. Triple intersections need separate treatment.

The elementary segment count says that a hypothetical 94-face drawing with three parallel pairs would need `U = 282 - 3×94 = 0`. That is a necessary condition, not evidence that such a drawing exists. We have not established whether a drawing with parallel pairs can reach 94. The next search focuses on drawings where every pair crosses (94 would leave exactly six unused segments), while parallel and concurrent arrangements remain open cases. A specialist must review any proposed parallel-pair exclusion before it can be used in a proof. Proving 93 is the maximum requires ruling out 94 across all permitted classes. A finite unsuccessful search does not establish that result.

## Shared vertices and the fan

Multiple distinct lines may cross at the same point. The verifier allows that vertex and rejects duplicate lines. To see why traced triangle outlines do not always count as regions, take the 17 lines `y = i x` for `i = 0, ..., 16` through the origin and add `x = 1`. Selecting two of the rays and the transversal gives `17 choose 2 = 136` triangle outlines. Only the 16 formed by neighboring rays are undivided triangular faces. Both exact checkers return 16. The fan has 33 bounded line segments. Its 16 triangles have 48 side incidences, so some bounded segments border two triangles. The `U = E - 3T` shortcut assumes this sharing cannot happen and does not apply to the fan. Each added ray divides an older triangle rather than preserving it as an extra face.

Concurrency is a genuine possible tool, not an excluded case. [OEIS records a 14-line construction with 54 faces](https://oeis.org/A006066) that uses triple points. A rigorous 18-line upper bound would need to cover this legal class as well.

## Searching for 94 one crossing at a time

The included exact audit maps each of the three unused segments in the 93 drawing to its neighboring crossings. An arrangement with 94 faces and *every pair crossing* would leave exactly six of its 288 bounded segments unused. To get an all-crossing starting point, add 1 to the first coefficient of lines 1, 7 and 13 in the included 93 witness. Both counters still find 93 faces, and the segment audit finds nine unused segments. Eight ±1 versions of these three changes all stayed at 93. These are finite probes, not a search result above 93.

The wall-crossing search works on *straight-line drawings directly*. It starts from the all-crossing 93 witness produced by those three coefficient changes. A move holds one line's direction fixed and slides it just past the nearest crossing point of the other 17 lines, in either direction. In a drawing with no parallel lines and no triple points, that flips exactly one triangle: the moving line and the two lines through the crossed point each swap one neighboring pair in their crossing order. If several crossing points share the nearest offset, the move is rejected. The new offset is the simplest rational strictly between that crossing and the next one, which keeps coefficients small. Both exact checkers recount every drawing. The search expands the highest-scoring drawing first, keeps lower-scoring drawings so it can leave a local peak, and counts each crossing pattern once, identified by the order of crossings along every oriented line and the cyclic order of line directions. For example, sliding line 0 of the starting drawing to `[0, 2, -727]` crosses one point and gives 90 faces with 18 unused segments.

A pilot over 1,000 distinct crossing patterns found no 94, and neither did a follow-up over 20,000, which followed chains of up to 13 moves and never climbed back above 90. The starting 93 is a strict local peak for this move: all 24 of its distinct one-move neighbors have 90 faces. In every case the flipped triangle survives, the three triangles touching its corners become four-sided regions, and no new triangle appears. The 93 drawing packs its triangles corner to corner, so any single slide costs three faces. So any route from this drawing to 94 must pass through lower scores, take more than one move, or use a different move, such as rotating a line past a crossing point (which must also reject moves that make two lines parallel). These finite runs give no upper bound. A separate proof-oriented path could adapt Savchuk’s satisfiability encoding, with its optional missing-triangle variables, to rule out all-crossing 94-face tables. Such a claim would require a faithful model and checked unsatisfiability evidence, followed by an argument for parallel and concurrent cases.

## Why the remaining robots never halt

For the tape robot, the [known result `S(2)=6`](https://oeis.org/A060843) matches the six-step machine our checker found. Of 20,736 fully labeled two-state rule tables, 9,784 halt within 100 steps and 5,040 come with a repeating-configuration proof. The 100-step simulator leaves the remaining 5,912 unresolved. Two further exact certificates explain all of them.

For 2,896 tables, no halting rule can ever be read. Start with the rule for state A on a blank square. Any state that a reachable rule moves to, and any symbol that a reachable rule writes, can occur later, so add every such combination and repeat until nothing changes. The result contains every rule the machine can ever use. If it contains no halting rule, the machine never halts.

The other 3,016 are *record cycles*. At two moments the head stands farther right (or farther left) than ever before, in the same state. Everything beyond a record is still blank. If the tape over every square the head visits between those moments matches the tape at the second moment, shifted by the distance the head moved, then the second stretch reads the same symbols as the first one, shifted along the tape. It ends at a new record in the same state and leaves the same matching pattern, so by induction the robot runs forever. Every record cycle appears by step 8.

The certificate checker re-simulates each machine and re-derives every condition. No halting table receives a certificate. Our checks therefore account for all 20,736 tables and confirm that six steps is the longest halting run. This reproduces `S(2)=6` with checkable certificates; it is not a new result. We have not tried them on three-state machines, whose established maximum is 21 steps under the same convention. A head that sweeps back and forth across a growing block would not be a record cycle, so that behavior would need a new kind of certificate. A longer simulation is not a nonhalting proof.

## Reproducing the counts

Run these commands from the repository root with Python 3.10+:

```sh
python3 tools/segment_audit.py candidates/best/solution.json
python3 tools/segment_audit.py candidates/prior-art-93/solution.json
python3 -m tools.wall_crossing_pilot --budget 1000 --out wall-crossing-run
python3 -m tools.beaver_certificates --out beaver-certificates
python3 -m unittest tests.test_segment_audit tests.test_wall_crossing tests.test_beaver_certificates -v
```

The segment audit uses the two existing exact triangle counters and refuses the unused-segment formula at multiple intersections. The two search commands write their logs into a new directory and refuse to overwrite an existing one. The website does not call these tools, so it works offline without Python once downloaded.
