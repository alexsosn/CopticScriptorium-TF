# Issue #118 — full-source TT source tag conservation matrix

## Immutable research baseline

Use GitHub Actions run [38143780565](https://github.com/alexsosn/CopticScriptorium-TF/actions/runs/38143780565), job **114482850578**, stage `tests/live_issue110_wrapper_census.py`, checked out `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`: 565 TT Git blobs, 2,628 physical TT records, 6,621,410 opening tag occurrences, 101 source tag types. Source snapshot includes directory records and ZIP members. The raw scanner labels 18 types `modeled`, 82 `unknown_unmodeled`, and one `requires_modeling` (`note`). Those labels are **inventory heuristics**, not proven source-to-native-feature parity or guaranteed semantic loss.

## RED gate / plan

1. First commit a failing `tests/test_issue118_tag_matrix.py` contract for exactly 101 unique types, total 6,621,410 opening tags, status distribution and well-formed source-inventory counts. Run on baseline before adding CSV to get FileNotFoundError.
2. Transcribe **every** per-tag row from the real pinned CI JSON into an open, sortable `tag_matrix.csv` with original source occurrence count, collections, token-inside count, empty/duplicate attribute signals, attribute names and bounded source record examples. Do not package any text or word literals. Add a **provisional** batching family for review; never silently convert `unknown_unmodeled` to modeled.
3. The matrix is a review scaffold. For each unmodeled family, inspect sample TT data against current parser/model/writer. Only after ruling out existing fields decide `intentionally_not_modeled` versus `requires_modeling`; distinguish source stand-off annotations, duplicates, nested wrappers and genuine unique semantics. Build a shared typed positional event architecture where needed.
4. For subsequent schema batches: add RED parser/graph/writer tests before production; compare pinned source offsets, explicit empty values, overlapping ranges, and closed/open sequences; run full 2,628-document / 2,394,354-slot TF reload with all `lang` and SBL nodes unchanged. Require a logically independent adversarial review for each PR.

## This research slice

No converter changes, corpus output, lexical alignment or annotation reinterpretation. Keep #118 open until semantic decisions and source-faithful native TF models are implemented. The 101-type CSV count comes from the upstream raw TT source, not generated TF.
