# Issue #75 — audited book×family source-coverage matrix

## Research
The reviewed full pinned scope census PR #76 merged at `6f3a19b840658c73ce5665e6756f2579c1afd039`. Its immutable real CI job 114242624844 found precisely 2,628 TT source records and 78 source families across 565 sparse Git blobs; candidate classes: 1,574 OT, 615 NT, 439 undetermined. This classification is source-evidence only. Pilot bilateral Coptic/LXX TF modules in PR #74 resolve only 54 verse *reference-address candidates*, not textual equivalence, for real Ruth 2/Jonah 2/Bohairic Habakkuk 2.

The present census aggregates separate `cts_work_counts` and `literal_book_counts` per source family but lacks a **joint work/reference profile**, obscuring whether a given book is identified by CTS, `meta book`, or neither. `sahidic.ot_TT.zip` and `bohairic.ot_TT.zip` contain multiple works and must not be treated as single books.

Pinned target `CenterBLC/LXX@f32a98eddf7eb239aa73ab863d70381e416d5076` (CATSS-TF LXX 1935) has 57 books, 30,371 verses including a subverse layer; book aliases and versification cannot be guessed solely from filenames.

## Plan / RED → implement → live CI → independent review
1. Add RED tests to `tests/test_issue75_ot_inventory.py` for multi-work OT ZIPs, direct OT without CTS, unidentified OT records, and NT exclusion. Require deterministic `source_work_profiles` per family, carrying *source literal* work key, **mutually exclusive** CTS/book/no-work evidence category, chapter label counts, verse marker counts, source record count, scope statuses and bounded path examples. Same raw record counted exactly once in one profile.
2. Implement per-record joint census without retaining raw texts, serializing source text, calling a Greek parent, or claiming LXX alignment. A CTS work is a source literal, **not** a CenterBLC book code. Preserve `meta book` as additional raw evidence even where CTS is chosen for grouping.
3. Add exact-head CI script to extract and print compact OT candidate family/work breakdown in the existing real pinned source inventory workflow. Still upload only metadata JSON; don't embed source text.
4. Verify exact parent revision and 565/2,628 record invariants. On real data, report category totals and missing chapter information per work, and select a batch for further researched canonical LXX aliases and divergences (not one PR per verse).
5. Independently adversarially review per-work grouping for double counting, absent/malformed CTS, false-positive biblical scope, zip identity collisions, version provenance, deterministic output, licensing and archived record leakage before merge.

## Not in scope
No full Coptic→LXX verse equivalence, no Greek/Coptic token alignment, no Greek cross-warp node IDs embedded in source TF, no inferred canonical book names without inspection.
