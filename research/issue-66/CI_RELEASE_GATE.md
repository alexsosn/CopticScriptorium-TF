# #66 release workflow repair (2026-10-11)

## Research

The original PR #67 (head 5b43eda) green real full-corpus CoNLL-U job 114003929246 in run 37984752829 was keyed to `github.event.pull_request.head.ref == 'feat/issue66-conllu-supplement'`. The current forward-port [PR #133](https://github.com/alexsosn/CopticScriptorium-TF/pull/133) on fresh main (head a63d5e2) passed its `conllu-wiring-unit` job but run **38146188014** explicitly marks `conllu-full-corpus-parity` as **skipped**. No valid exact-head 2,361/227/40 / 2,104,966-word release gate has run on the rebased language/SBL/verse version. Do not merge on old PR's evidence.

## RED → GREEN repair

RED `tests/test_issue66_ci_scope.py` requires the complete job on *all* pull requests changing the CoNLL-U converter, model/parser/graph/writer, test files or workflow itself. Workflow-level `pull_request.paths` filters unrelated PRs; `workflow_dispatch` remains available for manual complete parity. Remove the stale branch-name `if` from `conllu-full-corpus-parity`. On a relevant PR, every job (unit and full) must run on the same exact PR head, and the existing `needs: conllu-wiring-unit` gate remains intact.

## Tests/acceptance

New exact-head run must pass focused tests, full immutable pinned CoNLL-U/TT source checkout, full native TF reload and independent reader parity; the separate existing full source 2,628-document language/SBL check also must stay green. No corpus redistribution. Adversarial review re-examines full job status; skip is **not green**.
