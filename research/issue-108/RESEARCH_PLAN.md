# Issue #108 — bounded, source-identifiable OT marker-anomaly batch

## Research verified against current main (2026-10-11)
Merged #107 reconciled a full immutable 2,628-record Coptic TT census and reported **309 source positive-number gap events and 153 missing/nonpositive source verse literals** restricted to 1,574 OT-candidate physical records. No duplicate or descending OT labels. These are *source marker events*, not 309 absent Coptic readings nor 309 confirmed Septuagint mismatches. Real examples: `bohairic.ot/bohairic.ot:02_Exodus_25` (gap), `bohairic.ot/bohairic.ot:19_Psalmi_001` (unnumbered/invalid). Hebrew DSS/BHSA precedent: first stabilize reference anchoring; word-level matches require separate evidence.

Source `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`. Greek `CenterBLC/LXX@f32a98eddf7eb239aa73ab863d70381e416d5076`, v1.0.1, TF 1935, checked by CATSS-TF Git blob fingerprints. Existing `VerseMarkerTopologyAudit` counts events, but keeps only **3 source record ID examples per category** — insufficient to batch-review all anomalies, original literals and Greek address evidence. We must avoid silently interpreting Psalms verse 0 as a superscription, numeric gaps as lost manuscript lines, or same-number verse as identical Greek text.

## RED→plan→implement→real data→independent review
1. RED-first tests for exact source tag-event coordinates (ordinal, character offset, Coptic word-start count), literal raw `verse_n`, previous/current numeric labels, missing intermediate numbers for gaps, source-byte SHA-256, physical record ID / family / OT CTS work / source edition, chapter reset, invalid marker versus absent marker, and non-OT exclusion.
2. Add deterministic `CopticOtVerseAnomalyBatch` accumulating **only affected OT anomalies** (bounded by observed pinned count, not full text or word models). Validate source pin & SHA; all unique marker-event identities. Preserve empty literal string distinctly from absent `verse_n` attribute. Do not export source Coptic text or translations.
3. Add pinned LXX section lookup for **missing intermediate verse addresses** and inspect their actual `subverse` nodes separately. Status: `lxx_address_present` / `lxx_address_absent` / `source_reference_unclassified`; these are observed Greek reference *addresses*, not bilingual proof. For unnumbered markers, target remains `not_inferable` without a new independently sourced crosswalk.
4. Integrate this into the already-existing `issue80` full TT→LXX streaming CI, preserving the 2,628-record / 2.394M-slot accounting; add aggregate-only JSON rows for all 462 anomalies. Assert counts against #107 (309 and 153). Reuse one full sparse checkout instead of one CI/PR per verse. Test test-fixture, exact real LXX source blob identity, aggregate artifact without source passages.
5. Separate genuinely independent adversarial review of exact final head and real CI logs; no mappings/verse shifts until candidate cases individually supported by real source/edition evidence. Parent #108 stays OPEN as batch philological assessment is still needed.

## Acceptance
- [ ] All 462 events identifiable by exact TT byte hash and source-tag location
- [ ] LXX verse/subverse lookup attempted only for determinable gaps; unknown cases remain clearly unresolved
- [ ] CI/coverage counts reconciled; no raw TT text, no new semantic sidecars or invented correspondence
- [ ] Independent adversarial review before any merge

## Follow-up batch: distinguish 153 invalid/unnumbered source literals

**Research:** #123 merged the exact-source enumeration of all 309 positive-label
jumps and 153 absent/nonpositive OT `verse_n` events, checked against the
immutable Coptic source and pinned CenterBLC/LXX verse/subverse index. Its
original single `missing_or_nonpositive_literal` category preserved literal
evidence but conflated importantly different syntactic source conditions.
A source `verse_n="0"` must not be called a missing attribute or
presumed to mean a Psalm superscription; a bare `<verse_n>` likewise
must not be parsed as verse zero. Source labels are not Greek verses.

**RED first:** `tests/test_issue108_ot_anomaly_batch.py` adds synthetic,
adversarial literal forms: `0`, `00`, `-3`, empty, text, Unicode numeral,
and absent attribute, alongside a legitimate positive-number gap. Requires
exact event-level class and reconciliation to total invalid events, never
probes a Greek address for any invalid class.

**Implementation:** append backward-compatible
`invalid_literal_class` to the bounded source-event metadata (null for
`gapped`), and `invalid_literal_classes` counters to the aggregate
source-anomaly report. Categories are `zero_literal`, `empty_literal`,
`missing_attribute`, `signed_nonpositive_literal`, and
`nondecimal_literal`. These are source **syntax classifications**, not
guesses about editorial meaning. No Greek content, Coptic lexical forms,
source text, or per-word identity is added to the artifact.

**Real gate:** existing `issue80` full Git-pinned Coptic/LXX CI reuses the
same 565-file/2,628-record source, validates sum of exact invalid-class
counters equals **153**, and still independently verifies 309 numeric gaps,
all 462 rows, original source SHA and source-tag offsets. Log the observed
class partition without hard-coding an invented distribution. Preserve
2,394,354 Coptic slots and source book/edition boundaries. Review
the new exact-head code and live log logically independently before merge.

**Deferred:** Philological classifications (e.g. Psalm superscription vs
lacuna vs alternate versification) require explicit edition evidence and
negative controls; no candidate LXX address added in this PR.
