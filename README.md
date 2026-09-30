# Math You Can Touch

An offline playground for triangular regions made by straight lines and a two-state tape robot. Start with four fences, change one, and watch the triangular faces change. Then program the robot and inspect each read, write, move and state change.

## Open the playgrounds

Clone or download this repository, then open `site/fences.html` in a modern browser. Open `site/beaver.html` for the robot or `site/index.html` for the experiment story. All runtime assets are included. No account, network access or installation is needed. Both demos are 2D. They use SVG and HTML, with no rendering library or GPU requirement. JavaScript is required for interaction.

For browsers that restrict local files, run this from the repository root and visit the printed loopback address:

```sh
python3 -m http.server 8000 --bind 127.0.0.1 --directory site
```

### A five-minute visit

1. Open the fence playground. Choose a fence, drag its round handle, or use the Slide and Rotate buttons. The exact triangular-face count updates after a valid move. Undo restores the previous arrangement.
2. Load the published 93-face construction. It is an editable copy of prior art. The separate saved-frame slider loads 41 previously checked positions. Pan, zoom and Focus face change only the view.
3. Open the robot. Predict its outcome, step through the six-step example, then change a rule. A halt, a complete configuration repeated up to translation, and an unresolved 100-step cutoff have separate outcomes.

## What the examples establish

The 18-line examples have 16, 76 and 93 triangular faces. Each line is represented by exact integer coefficients `[a,b,c]` for `a*x+b*y+c=0`. Two independently implemented Python methods agree on the complete sets of faces. The browser uses integer arithmetic, with regression checks against both Python methods.

The 93-face example reproduces a published construction attributed to Johannes Bader. It has three parallel pairs and no triple intersections. It is not a new result or a proof of optimality. The story summarizes a 6,000-change search that did not improve 93. This repository verifies the saved constructions but does not reproduce that search.

The robot uses two states, two symbols, an initially blank infinite tape and a 100-step limit. All 20,736 fully labeled transition tables were checked. The saved experiment reports 9,784 halts, 5,040 translation-cycle witnesses and 5,912 unresolved tables. The longest observed halting run takes six steps and leaves four ones. The cross-language test recomputes these totals and compares all 20,736 tables across the three simulators. Unresolved cases prevent this experiment from proving a maximum. Six-state Busy Beaver research is separate.

There is no new mathematical record, completed Lean geometric proof or official Autolab evaluation in this project.

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
