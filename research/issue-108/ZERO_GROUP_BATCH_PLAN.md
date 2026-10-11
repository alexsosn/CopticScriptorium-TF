# Issue #108 — batch provenance for 153 source verse-zero events

## Research (2026-10-11; actual code and verified pinned full-source CI)

Existing source-only `CopticOtVerseAnomalyBatch` from merged PRs #123/#125 retains every anomalous raw TT marker as a row (source record, SHA256, CTS work, edition, chapter, exact event ordinal, unicode-character tag offset, preceding word-start count, literal, previous verse). Existing pinned source+Greek regression `issue80-lxx-coverage.yml` produced **2,628 physical TT records**, including 1,574 OT candidates. Among 462 anomalous OT `verse_n` occurrences, exactly **309 positive-number gaps** and **153 invalid/nonpositive markers** were observed; the #125 per-literal subtype census found all 153 were syntactically zero-literals, not missing attributes. No scholarly interpretation can be inferred from zero.

Missing research-facing ergonomic surface: `report()['cases']` is event-by-event, and `by_work_edition_kind` aggregates all anomalies but **cannot identify which source records, chapters and witness editions have clustered verse-zero events**, nor compare non-Psalm negative controls as a batch without custom ad hoc grouping. No new LXX mapping should be published before this source evidence is grouped, reviewed with edition conventions and Greek verse/subverse profile.

## Plan → RED tests → implementation → real corpus gate → independent review

1. RED-first `tests/test_issue108_zero_grouping.py` requires `zero_literal_source_groups` generated entirely from existing exact anomalous source rows. Key by **physical source record ID + SHA256 + CTS work + edition + chapter**, not book/verse alone, so duplicate witnesses and chapters cannot be collapsed. Preserve exact event positions, preceding Coptic word-start counts and literal strings. Include *all* work families, not only Psalms; a Jonah/Exodus fixture is a negative control.
2. Group only `invalid_literal_class == zero_literal` events, sorted deterministically independent of source ingestion order. No corpus text, reconstructed readings, English translation, Greek lexical evidence, or blind `verse_zero → Greek Psalm superscription` inference. Store event IDs as compact data and counts; keep existing `cases` output backward-compatible.
3. In the existing full `issue80` pinned-source + pinned Greek CI, assert group/event conservation equals 153; log group counts by source CTS work/edition and examples without Coptic lexical text. **No second full upstream download in this PR.**
4. Independently challenge grouped-event identity (source SHA conflicts, chapter mixing), invalid/absent distinction, whether repeated source events could disappear, and whether a Coptic source zero is accidentally presented as a known LXX target verse. Inspect actual full-run logs before merge.
5. Later separate editorial crosswalk phase: compare prioritized grouped cases against primary Coptic manuscript/edition metadata and Greek verse/subverse evidence. Review 1:N decisions in batches, never one PR per marker. Maintain #108 and #70 open until those source/Greek adjudications exist.

## Acceptance

- 153 exact pinned OT source verse-zero marker events preserved in bounded and unambiguous record/chapter/edition grouping;
- all source identities and positions retained, non-Psalm records not silently excluded;
- no Greek passage mapping inferred;
- exact-head full pinned run + independently skeptical final review before merge.
