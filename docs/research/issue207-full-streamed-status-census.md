# Issue #207 — reconcile pinned streamed Coptic–LXX status census

## Research (original pinned evidence)

The full native streamed two-weft test `tests/live_issue82_full_modules.py` remains on the historical post-Zechariah baseline: `versification_candidate=549` and `ambiguous=52`. This test reopens original Coptic and Greek Text-Fabric parents, regenerates both native overlays, checks 2,394,354 word slots and cross-parent ID parity, then checks the status census.

- **Observed RED**: [PR #198 full streamed workflow 43697967320](https://github.com/alexsosn/CopticScriptorium-TF/actions/runs/43697967320) actually generated/reloaded native modules before raising `ValueError: pinned post-crosswalk source-status coverage drift: versification=549, ambiguous=152`. The +100 ambiguous slots correspond to the three *original* Bohairic Psalms' source verse1 spans corrected by merged #203/#204 (41+31+28 words).
- **Subsequent source-locked correction**: merged #205/#206 guards *source verse2* spans of the same three Psalms (18+17+33 = 68 original TT words). The [real 2,628-document Coptic + Greek TF audit, run 43699229832](https://github.com/alexsosn/CopticScriptorium-TF/actions/runs/43699229832), on merged #206's exact head, reports `ot_word_statuses.ambiguous=220`, `versification_candidate=549`, and 21,120 distinct candidate Greek addresses.
- **Arithmetic and scope**: 52 historical ambiguous + 100 verified source verse1 + 68 verified source verse2 = **220** pinned ambiguous word slots. These are candidate-address status changes only. Original Coptic word slots, document positions, TT SHA and Greek native warp are unaffected. No Greek verse alignment should be reconstructed or guessed.

## Plan and strict invariants

Update **only** the stale expected ambiguous word-slot count (52 → 220) and its adjacent explanatory comment in the full streamed *test*, retaining `versification_candidate == 549`, all other full-corpus conservation checks, source IDs, bilingual TF native overlays, and independent positive/negative guards.

The original real failing full streamed job is the RED observation. A new full streamed job on this exact head must go GREEN on the actual source and native TF modules. The cheap test suite and syntax must remain GREEN. The final independent review must compare the complete patch with the verified upstream full corpus counts and reject any weakening of data guards.

No converter, corpus semantics, source pin, wheel, package, workflow trigger, or broad alignment policy change. No publication of licensed corpus material.
