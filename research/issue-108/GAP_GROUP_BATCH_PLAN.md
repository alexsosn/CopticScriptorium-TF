# Issue #108 — batch source-locked OT verse-gap evidence

## Research (2026-10-11, inspected main code and merged CI)
- Existing `CopticOtVerseAnomalyBatch` collects each abnormal source `verse_n` marker with exact physical `source_record_id`, source SHA-256, edition/CTS work, chapter, marker ordinal, tag offset and word-start position. After real pinned `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5` vs `CenterBLC/LXX@f32a98eddf7eb239aa73ab863d70381e416d5076` CI, the verified 1,574 OT-candidate documents have **309 positive-number jump occurrences** and **153 source-zero occurrences**. These are source-numbering events, not necessarily absent Greek/Coptic passages.
- PR #123 source-locked these individual anomaly rows and queried each *missing intermediate* LXX verse address plus subverse count where possible; #125 split literal types; #141 grouped all 153 source-zero events by immutable physical record/edition/chapter. **309 numeric gap events have no equivalent research-facing witness/edition batch summary** or trustworthy aggregate of how many intervening addresses exist in LXX. Existing `cases` is correct but costly to adjudicate one event at a time.
- `inspect_greek` only probes target addresses when source book/chapter is known and gap is bounded (<=256 missing numbers). It records only *address* and *subverse count*. A present Greek address does **not** show that Coptic is missing the verse, nor prove Greek/Coptic textual correspondence. Preserve all ambiguous/unknown statuses.
- Avoid extra remote acquisition and duplicate full tests: extend existing `issue80-lxx-coverage.yml` with one RED-focused test and added assertions in the existing pinned 565-blob/2,628-record full-run, rather than a new expensive CI job.

## Research → plan → RED → implementation → exact-head CI → independent skeptical review
1. RED tests demand `gapped_source_groups` with physical source ID + SHA256 + CTS work + edition + chapter + target LXX book; each source event retains source ordinal, tag offset, preceding word starts, previous/current literal positive integers, precisely recorded skipped-number count and bounded list of Greek lookup evidence.
2. Group losslessly and deterministically, independent of source ingestion order. Reject inconsistent group identity and duplicate event ordinals instead of overwriting them. Preserve the original `cases` schema, zero grouping and full source annotations.
3. Provide `gapped_work_edition_counts`, `gapped_source_record_count`, `gapped_intermediate_address_status_counts` (number of *per-event* Greek presence/absence probes), and explicit `not_checked`/unclassified/too-large non-inferable cases. Make Greek status counts descriptive of *addresses only*, not reconstructed verses.
4. Real full pinned CI: prove **309 gap events** are present in groups and grouped source-record count agrees; all intervening Greek address probes reconcile exactly to the explicit per-event evidence; never silently drop >256-case ranges or project unproven correspondence. Retain no raw Coptic/Greek text or derived corpora.
5. Independent adversarial review of actual diff + pinned CI aggregate output before merge, emphasizing source edition isolation, never asserting equivalence, invalid type/error handling, failure atomicity and determinism.
6. Full #108 remains open for substantive scholarly adjudication and evidence-backed crosswalk; no single-verse PR proliferation.

## Scope
This is a single batch that makes all **309** existing source-gap cases auditable. It does **not** invent LXX alignment evidence, add word slots, create new corpus copies, assign passage equivalence, or close Coptic #70/#75/#92/#108.

## Independent adversarial review finding (pre-CI)
The legacy human-readable aggregate key `work|edition` is **not injective**:
a missing CTS work and a literal source value `<missing>` can display under
the same key, and a literal work/edition containing `|` can also collide.
Preserve `gapped_work_edition_groups` with separately typed nullable
`source_cts_work` and `source_edition` as the authoritative grouping, tested
against these adversarial cases. Keep `gapped_work_edition_counts` only as a
backward-friendly **display aggregate**; never use it to deduplicate edition
identities or drive alignment decisions. The full pinned CI reconciles the
structured counts as well as the display counts against all 309 events.
