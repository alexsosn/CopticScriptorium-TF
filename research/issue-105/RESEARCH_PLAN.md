# #105 — Full source verse-marker topology audit

## Research (pinned sources, 2026-10-11)

The existing `lxx_coverage.py` loads exactly 2,628 immutable TT records, streams their `DocumentModel` one at a time into Coptic→LXX reference grouping, and emits source-work/family/status totals. Its full-pinned run has already verified 29 token-internal verse markers and the exact target CenterBLC/LXX Git-blob profile. The [#100] full paired native TF module re-run resulted in 2,394,354 Coptic words, including 1,071,829 numerical-address reference candidates, 344 source-edition-qualified candidate words, and a large unresolved/unclassified remainder. Shared addresses are NOT confirmed textual alignment.

`resolve_coptic_lxx_references` groups consecutive *word features* by the literal `verse_n`. This can collapse two consecutive distinct source occurrences of `<verse_n verse_n="1">` with the same value, and cannot see a zero-word-start interval (not necessarily textually empty, because a marker may split a norm) marker. A source verse decrease or numbering gap is not automatically an error: witnesses may be fragmentary or annotated differently. The exact original SGML-like text is already available on each `DocumentModel.source_text` during the streaming audit; source text must not be saved to report artifacts. No new source acquisition or semantic sidecars needed.

## RED → implementation → live real-data tests → independent skeptical review

1. RED-first one-pass pure source marker scanner covering consecutive duplicate, decreasing, gapped, zero-word, malformed/un-numbered verse tags. Anchor only *opening* `verse_n` tags; count intervening *opening* `norm` tokens. Closing tags must not be confused with a new verse. Count and deterministically retain max 3 distinct physical source IDs per category independent of traversal order. No source strings or text payload escape.
2. Integrate the scanner with existing `CopticLxxCoverageAudit.add` so the *same* real pinned 2,628-source/CenterBLC LXX job produces topology counts with status partition unchanged. Source marker literal results are not silently promoted to verified LXX equivalence. Preserve v1 report schema or explicitly version it if consumers break.
3. Have the full existing pinned `issue80-lxx-coverage` workflow trigger from the new scanner and test paths (no redundant new full-acquisition workflow); assert observed 73,844 opening `verse_n` tags match the independently measured pinned source census and 29 precisely positioned events are retained.
4. Use actual bounded source-record IDs to reproduce any suspicious cases, evaluate whether resolver merges semantically distinct reference spans, then file targeted corrective work if needed rather than introducing speculative remapping.
5. Logically independent adversarial exact-head review of source scanner semantics, abort conditions, privacy/no raw text, coverage counts, edge cases and CI data. Merge only once live full pinned run is green.

## Current gates
- [x] Research and plan
- [ ] RED-first unit tests
- [ ] Pure scan + streaming accumulator
- [ ] Genuine pinned complete corpus + LXX acceptance
- [ ] Independent skeptical exact-head review
- [ ] Merge
