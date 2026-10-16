# Math You Can Touch

Two hands-on math playgrounds. Move a fence and watch triangular yards appear and disappear. Give a tiny tape robot four rules, predict whether it will stop, then follow each step.

Both run in a modern browser with JavaScript enabled, with no account or installation. You can also download the repository and use them offline.

## Play online

- [Move the fences](https://qsimeon.github.io/math-you-can-touch/fences.html): drag or rotate a fence, then inspect which triangular yards appear.
- [Program the tape robot](https://qsimeon.github.io/math-you-can-touch/beaver.html): edit four rules, predict an outcome, and follow every step.
- [Read the experiment story](https://qsimeon.github.io/math-you-can-touch/): see the geometry and the saved search results together.

## Run offline

Download this repository and open `site/fences.html`, `site/beaver.html`, or `site/index.html` in a modern browser. The 2D demos use local SVG and HTML assets. No account, network connection, rendering library, or GPU is needed. JavaScript is required for interaction.

For browsers that restrict local files, run this from the repository root and visit the printed loopback address:

```sh
python3 -m http.server 8000 --bind 127.0.0.1 --directory site
```

### Quick tour

1. Open the fence playground. Drag a fence to slide it, or drag its red turn handle to rotate it around the center dot. You can also use the Slide and Turn buttons. The count updates after a valid move. Undo brings the previous drawing back.
2. Choose Explore 93 yards to edit a copy of Bader’s published construction, reconstructed from Pavlo Savchuk’s LineOrder drawing. Click a shaded yard or use Previous yard and Next yard to see its three fences. The separate slider loads 41 saved positions. Pan, zoom and Zoom to yard change only the view.
3. Open the robot. Predict its outcome, step through the six-step example, then change a rule. A halt, a complete configuration repeated up to translation, and an unresolved 100-step cutoff have separate outcomes.

## Verified examples

The playgrounds' 18-line examples have 16, 76 and 93 triangular faces. The `candidates` folder adds two more 93-face drawings from the crossing-pattern search: Bader's pattern redrawn with coefficients no larger than 42, and a different 93 with coefficients no larger than 70. Each line is represented by exact integer coefficients `[a,b,c]` for `a*x+b*y+c=0`. Two independently implemented Python methods agree on the complete sets of faces. The browser uses integer arithmetic, with regression checks against both Python methods.

The 93-face example reproduces Johannes Bader’s published construction from Pavlo Savchuk’s LineOrder drawing. It has three parallel pairs and no triple intersections. It is not a new result or a proof of optimality. The experiment story reports four bounded search-run summaries totaling 6,000 changes, with no reported count above 93. The detailed per-change logs are not included in this repository, so this is a limited search result, not independently replayable evidence of a broader claim.

The robot uses two states, two symbols, an initially blank infinite tape, a left or right move on every step and a 100-step limit. All 20,736 fully labeled transition tables were checked. The saved experiment reports 9,784 halts, 5,040 translation-cycle witnesses and 5,912 unresolved tables. The longest observed halting run takes six steps and leaves four ones. The cross-language test recomputes these totals and compares all 20,736 tables across the three simulators. The 100-step simulator leaves those 5,912 tables unresolved. A separate certificate checker, `tools/beaver_certificates.py`, proves that each of them never halts and certifies no halting table, so the repository's own checks confirm six steps as the longest halting run. That reproduces the known value [S(2) = 6](https://oeis.org/A060843), also listed by [MathWorld](https://mathworld.wolfram.com/BusyBeaver.html). The [research notes](docs/RESEARCH.md#certificates-for-the-remaining-robots) explain both certificates. Six-state Busy Beaver research is separate.

These examples let you inspect what computation establishes: a drawing can achieve a count, a robot can halt, and a repeated configuration can show why it never will. We have not proved a maximum for the fence problem. The standard two-state result settles the robot’s maximum separately from our 100-step checker.

## The gap and the crossing-pattern search

Our original search used three random seeds, with a fresh small-coefficient drawing at the start and every 200 proposals, for 1,200 proposals per seed. Its best drawing had 76 triangular regions. Bader’s earlier drawing has a coordinated threefold pattern and reaches 93. An exact audit finds 58 bounded line segments unused by triangles in our 76 drawing and only three in the reconstructed 93. These numbers measure the difference between saved drawings. The [research notes](docs/RESEARCH.md) explain Savchuk’s later crossing-order search and the 94-face question. They also describe our search of every crossing pattern with SAT solvers, programs that decide whether a list of true-or-false conditions can all hold at once. That search proved, with an independently checked proof, that no drawing with the threefold symmetry of Bader’s 93 has 94 triangles when every pair of lines crosses and no three meet. It also found the second 93. Without the symmetry restriction, the search gave no answer in two hours, so whether any 18-line drawing reaches 94 remains open.

Multiple distinct lines may meet at one point. A 17-line fan through one point with an eighteenth line crossing its rays traces 136 triangle outlines but forms just 16 undivided triangular regions. The crossing point is legal. The larger outlines do not count because other lines divide them.

## Run the checks

The arithmetic checks use Python 3.10+ and its standard library. Run from the repository root:

```sh
python3 -c "from kobon.verify import verify_file; r=verify_file('candidates/prior-art-93/solution.json'); print(r['score'], r['verification'])"
python3 tools/segment_audit.py candidates/prior-art-93/solution.json
python3 -m unittest tests.test_io tests.test_geometry tests.test_oracle tests.test_agreement tests.test_prior_art tests.test_learning_data tests.test_busybeaver tests.test_segment_audit tests.test_wall_crossing tests.test_beaver_certificates tests.test_kobon_sat -v
```

The first command should print `93 two local exact-arithmetic algorithms agree`. The segment audit should report three unused bounded segments. The test command includes a bounded enumeration test. The SAT and straightening tests need `python-sat`, `numpy` and `scipy`, and they are skipped when those packages are missing. `tests.test_prior_art` reconstructs the witness from the included drawing and verifies its source identity.

Optional cross-language and browser checks require an already-installed Bun executable, the Python Playwright package and its Chromium browser. They are test dependencies only. These commands do not install anything:

```sh
python3 -m unittest tests.test_fence_geometry tests.test_beaver_browser_core tests.test_fence_browser -v
```

The optional tests compare all saved fence frames with both Python checkers and all 20,736 robot tables with two Python simulators. They also exercise edits, undo, reset, saved-frame labels, mobile layouts and 2D face selection.

## Repository contents

| Folder | Purpose |
| --- | --- |
| `site/` | Offline 2D pages, exact saved geometry and editable tape rules. |
| `kobon/` | Input validation and the two exact geometry checkers. |
| `busybeaver/` | Two simulators and bounded enumeration helpers. |
| `candidates/` | The five exact line arrangements and their provenance. |
| `tools/` | Reconstruction of the published drawing, the exact segment audit, the wall-crossing search, the robot certificates, the SAT search of crossing patterns, the straightener, the comparison with Bader’s 93 and the wiring-diagram drawer. |
| `docs/` | Research explanation, candidate algorithm and the concurrency example. |
| `tests/` | Arithmetic, cross-language and browser regression checks. |
| `evidence/prior-art-93/` | The original drawing, upstream attribution record and exact certificates. |

The upstream README is an unmodified attribution and license record. Its examples and relative image links describe the separate LineOrder project, not this repository.

## Attribution and reuse

Johannes Bader is credited for the 93-triangle construction. Pavlo Savchuk supplied the drawing through [LineOrder](https://github.com/zegalur/line-order/blob/2631b8793eb351be2ad6b8a91b7194eeb67e25bb/README.md). Its pinned README declares [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), copyright Pavlo Savchuk 2024–2025. His [2025 paper](https://arxiv.org/html/2507.07951v1) describes the later crossing-order method. It does not document how Bader found the 93-face construction. [The construction README](candidates/prior-art-93/README.md) records the exact source, deterministic rounding changes and license declaration.

The upstream license applies to its respective material. No license for the newly written project code is granted here.
