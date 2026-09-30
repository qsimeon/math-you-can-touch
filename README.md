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

### A five-minute visit

1. Open the fence playground. Drag a fence to slide it, or drag its red turn handle to rotate it around the center dot. You can also use the Slide and Turn buttons. The count updates after a valid move. Undo brings the previous drawing back.
2. Choose Explore 93 yards to edit a copy of Bader’s published construction, reconstructed from Pavlo Savchuk’s LineOrder drawing. Click a shaded yard or use Previous yard and Next yard to see its three fences. The separate slider loads 41 saved positions. Pan, zoom and Zoom to yard change only the view.
3. Open the robot. Predict its outcome, step through the six-step example, then change a rule. A halt, a complete configuration repeated up to translation, and an unresolved 100-step cutoff have separate outcomes.

## What the examples establish

The 18-line examples have 16, 76 and 93 triangular faces. Each line is represented by exact integer coefficients `[a,b,c]` for `a*x+b*y+c=0`. Two independently implemented Python methods agree on the complete sets of faces. The browser uses integer arithmetic, with regression checks against both Python methods.

The 93-face example reproduces Johannes Bader’s published construction from Pavlo Savchuk’s LineOrder drawing. It has three parallel pairs and no triple intersections. It is not a new result or a proof of optimality. The experiment story reports four bounded search-run summaries totaling 6,000 changes, with no reported count above 93. The detailed per-change logs are not included in this repository, so this is a limited search result, not independently replayable evidence of a broader claim.

The robot uses two states, two symbols, an initially blank infinite tape, a left or right move on every step and a 100-step limit. All 20,736 fully labeled transition tables were checked. The saved experiment reports 9,784 halts, 5,040 translation-cycle witnesses and 5,912 unresolved tables. The longest observed halting run takes six steps and leaves four ones. The cross-language test recomputes these totals and compares all 20,736 tables across the three simulators. Those 5,912 tables remain unresolved by this checker. For this standard model, [OEIS records S(2) = 6](https://oeis.org/A060843), and [MathWorld lists the same result](https://mathworld.wolfram.com/BusyBeaver.html), so the theorem separately implies that they never halt. This experiment does not prove that theorem. Six-state Busy Beaver research is separate.

These examples let you inspect what computation establishes: a drawing can achieve a count, a robot can halt, and a repeated configuration can show why it never will. We have not proved a maximum for the fence problem. The standard two-state result settles the robot’s maximum separately from our 100-step checker.

## Run the checks

The arithmetic checks use Python 3.10+ and its standard library. Run from the repository root:

```sh
python3 -c "from kobon.verify import verify_file; r=verify_file('candidates/prior-art-93/solution.json'); print(r['score'], r['verification'])"
python3 -m unittest tests.test_io tests.test_geometry tests.test_oracle tests.test_agreement tests.test_prior_art tests.test_learning_data tests.test_busybeaver -v
```

The first command should print `93 two local exact-arithmetic algorithms agree`. The second includes a bounded enumeration test. `tests.test_prior_art` reconstructs the witness from the included drawing and verifies its source identity.

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
| `candidates/` | The three exact line arrangements and retained provenance. |
| `tools/` | Deterministic reconstruction of the published drawing. |
| `tests/` | Arithmetic, cross-language and browser regression checks. |
| `evidence/prior-art-93/` | The original drawing, upstream attribution record and exact certificates. |

The upstream README is an unmodified attribution and license record. Its examples and relative image links describe the separate LineOrder project, not this repository.

## Attribution and reuse

Johannes Bader is credited for the 93-triangle construction. Pavlo Savchuk supplied the drawing through [LineOrder](https://arxiv.org/html/2507.07951v1). The pinned upstream README declares CC BY 4.0, copyright Pavlo Savchuk 2024–2025. [The construction README](candidates/prior-art-93/README.md) records the exact source, deterministic rounding changes and license declaration.

The upstream license applies to its respective material. No license for the newly written project code is granted here.
