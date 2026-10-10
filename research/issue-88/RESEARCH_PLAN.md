# Issue #88 — make expensive pinned writer test use exactly its 3 TT source blobs

## Research (2026-10-10)
The existing `.github/workflows/issue15-writer.yml` runs on every PR and push to main, including pure docs changes. Its separate `pinned-real-source-slice` job checks out the **entire** immutable `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5` (real upstream Git tree ~1.9 GB tracked raw source). That CI job actually calls `research/issue-15/writer_slice.py` which reads precisely the following three pinned files:
- `sahidica.mark/sahidica.mark_TT/Mark_01.tt`
- `sahidica.mark/sahidica.mark_TT/Mark_02.tt`
- `sahidica.nt/sahidica.nt_TT.zip` (member `41_Mark_01.tt`).
The existing converter/Agora integrations and sparse-Git workflows in this repo and Agora prove pinned Git sparse materialization of such paths works; no reason to fetch the unrelated ANNIS/PAULA/TT files.

## RED TDD → implement → live CI → independent review
1. Add test `tests/test_issue88_writer_sparse_ci.py` first; it reads the **real** writer workflow and requires `filter: blob:none`, `sparse-checkout-cone-mode: false`, exactly those three sparse path declarations plus required-file assertions in the actual job. Before implementation these fail.
2. Change only writer fixture `actions/checkout@v4` to partial Git + non-cone sparse patterns, using exact immutable Git SHA already pinned; add explicit post-checkout existence validation for all 3 inputs. Preserve existing full real-`writer_slice.py` source/TF regression and only upload its operational JSON, not the source.
3. Include a native source shape/path validation; do not accidentally omit ZIP or widen selection. No changes to corpus features, output format, or license handling.
4. GitHub Actions writer pinned-real-source-slice on exact head must succeed, with absent-file failure tests (RED static fixture gate) and all relevant unit tests green. Report observed CI runtime/footprint honestly; don't invent performance metric.
5. Independent skeptical code/real-run review, focusing on whether partial clone actually hydrates only the selected blobs and compatibility with future GitHub checkout behavior. CI workflow trigger gating is a **separate follow-up** if source checkout remains expensive; do not skip regressions just to make CI green.

## Scope
This is a CI/data-access bottleneck, not a change to source semantics or the Coptic↔LXX alignment.
