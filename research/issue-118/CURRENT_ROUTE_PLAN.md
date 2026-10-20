# Issue #118 — current 101-tag source-to-native **route** reconciliation

## Primary evidence and limits
- Immutable pinned raw source inventory remains `research/issue-118/tag_matrix.csv`: source `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`, 565 TT Git blobs, 2,628 physical TT records, 6,621,410 original opening tags across exactly 101 tag names. Its `baseline_status` column is **historical** from prior to #135–#173 and must not be rewritten.
- Current code (post #176 and #181) declares 83 disjoint source annotation otypes across 11 groups via `model.py`, consumes them through the positional `parser.py` tracks and constructs native nodes in `_graph_core.py`; 18 other raw tags take core word/structural/layout/translation/reference routes.
- This is a **type-dispatch audit**, not source literal/attribute parity for all 6.6 million tags. In particular, original matrix lists additional keys for `morph` (`lang;morph`), `norm`, `entity`, `verse_n`, `norm_group`, and `meta`. Parser captures `source_attributes` selectively for `gap/supplied/abbr`. These require separate grounded original-value comparisons, not a declaration that every attribute is preserved.
- A code-level type name being routed to native TF does not assert a token is Greek or that edition reference labels prove textual alignment to LXX.

## RED → GREEN → tests → independent review
1. Introduce `tests/test_issue118_current_native_routes.py` requiring a new *separate* 101-row `current_native_type_routes.csv` table. Baseline RED fails on absence of that table, leaving immutable historical census untouched.
2. Generate the table directly from the immutable source rows plus current model wrapper families and an explicitly reviewed 18-type core mapping. Include source opening counts, original attributes, native target or feature, family, and attribute-review status for each tag. All rows explicitly say `code_dispatch_not_complete_parity`.
3. Checks guarantee exact set equality, 83/18 disjoint partition, original count/provenance agreement, concrete parser core layout route and writer feature names, and do not convert a potential extra-attribute gap to a false conservation claim. No production schema change, no downstream fake chapter/verse/Greek equivalence.
4. Run focused + standard full tests on exact PR head; validate using real prior whole-corpus source/TF counts. Logically independent adversarial review should inspect current parser/graph/writer and the original matrix, especially the extra source attribute cases. Merge only on green applicable checks and review.
5. Follow-up: add a separately scoped source-backed issue to quantify additional original TT source attribute occurrences (including archive members), build RED source-to-native attribute parity and repair if true losses are verified. Keep #118 open until attribute/offset/value parity is independently evidenced.

No 9 GiB full corpus regeneration needed for a read-only research audit; original pinned corpus integrity already checked on real full CI and this branch does not change converter behavior.
