# Reproduced 93-face construction

These 18 exact integer line equations form 93 triangular faces according to both local exact-arithmetic checkers. Their complete supporting-line sets agree. This is a reproduction of prior art attributed to Johannes Bader, reconstructed from Pavlo Savchuk's LineOrder drawing. It is not our discovery, a new record, a Lean proof or an Autolab evaluation.

## Representation and limits

Each `[a,b,c]` in `solution.json` means `a*x + b*y + c = 0`. The file is 1,064 bytes. The largest coefficient magnitude is 736,030,939, below the hill's 10^30 limit. There are three parallel pairs, indexed from zero: `(0,1)`, `(6,7)` and `(12,13)`. No triple of lines is concurrent. Consequently this candidate is outside the pairwise-intersecting model of the primary 94 upper-bound theorem currently cited by the campaign. No unconditional hill ceiling is asserted here.

## Source and changes

The source is [Pavlo Savchuk's LineOrder 18-line drawing at commit 2631b879](https://raw.githubusercontent.com/zegalur/line-order/2631b8793eb351be2ad6b8a91b7194eeb67e25bb/gallery/imgs/kobon_18_93tri_lines.svg), whose caption credits Johannes Bader for the construction. The [2025 paper, Figure 5](https://arxiv.org/html/2507.07951v1) supplies the literature reference. The drawing comes from Pavlo Savchuk's LineOrder project, whose pinned README declares **CC BY 4.0**, copyright attribution Pavlo Savchuk 2024–2025. See the saved README and `provenance.json` for evidence. Preserve this credit and the indication of modifications when reusing these files. This private repository makes no external-release grant.

We extracted the SVG's 18 line endpoints, ignoring its filled triangle paths and count caption. The decimal endpoint strings were parsed as exact fractions. We rounded slopes and intercepts to six decimal places on the better-conditioned axis, then reduced the resulting coefficients to primitive integers. This creates a new exact coordinate representation of the published example. It does not assert equality with unpublished original coordinates or identical topology. Both checkers then recounted the resulting geometry from scratch.

## Reproduction

From the repository root, with standard-library Python 3.10+:

```sh
PYTHONPATH=. python3 tools/reconstruct_prior_art_93.py evidence/prior-art-93/source/kobon_18_93tri_lines.svg
python3 -c "from kobon.verify import verify_file; print(verify_file('candidates/prior-art-93/solution.json')['score'])"
python3 -m unittest tests.test_prior_art -v
```

`evidence/prior-art-93/verification.json` records all 93 supporting triples. `geometry.json` gives their exact rational vertices and positive areas. These are computational certificates for subsequent formalization, not kernel-checked proofs. `candidates/best/` remains the original 76-face search result.
