# Issue #95 — primary-source audit of Coptic ↔ Greek Zechariah versification

## Research (2026-10-11)

Complete technical candidate projection already works: reviewed PR #83 performed one
full pinned 2,628-record native Coptic TF → two native weft-only modules, 21,120
distinct pinned LXX verse-address candidates, all Coptic slots status-labelled.
Reviewed PR #90 performed a 4-source, 65-witness-span / 54-Greek-verse dual-module
pilot and preserved overlapping Sahidic/Bohairic Jonah witnesses. These are
only *reference-address* matching results; they are not textual equivalence.

The genuinely scholarly follow-on #75/#92/#70 is edition-/versification-aware
mapping. The full source/target audit (#81) flagged Zechariah 1:18–21 as
unresolved in CenterBLC/LXX 1935 and an existing #75 comment recorded external
evidence that MT-style Zech 1:18 (four horns) is LXX-style Zech 2:1.
The warning in source Coptic OT metadata explicitly notes numbering may differ
from Septuagint. The source family has *two* CTS work spellings
`ot.zach`/`ot.zech`, and there may be multiple Coptic editions.
Therefore blindly applying a 1→2 chapter shift is unjustified.

Pinned targets:
- `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`;
- `CenterBLC/LXX@f32a98eddf7eb239aa73ab863d70381e416d5076`,
  TF 1935 (same exact parent as CATSS-TF), native `book/chapter/verse`.

## Plan / RED → source evidence → review

1. RED tests require extraction based on **exact CTS work** and bounded
   chapter+verse windows, not broad filename matching. Report source record ID,
   exact edition/CTS metadata, raw verse/CTS/label markers and their source
   statuses; detect conflicting/missing evidence instead of repairing it.
2. Implement a narrowly scoped diagnostic that reads only the *two* pinned OT
   ZIPs, never exports raw source files or generated data; checks exact Greek
   parent mapping-critical Git blob fingerprints and real TF verse nodes;
   reports bounded anonymized/short Coptic and LXX evidence around the chapter
   transition and unresolvable source references. Print maximum ~5 Greek words
   and ~50 characters of source text per focused verse; no full text release.
3. CI pins both upstream Git commits and tests script against actual source.
   The diagnostic intentionally does **not** assert that matching passages
   are equivalent; it only proves provenance and provides inspectable evidence
   for an independent scholarly decision.
4. Independent adversarial review of actual output examines which source
   edition/witness uses which numbering; only **after** this introduce one
   versioned *edition-qualified* crosswalk batch (1:N allowed), negative
   control tests and native TF metadata. No fabricated auto-shift.
5. Keep parent #70/#75/#92 open until real source/target correspondence
   adjudicated; do not promote numeric `reference_candidate` statuses.

## Gates

- [x] Prior technical pipeline, source and Greek parent researched
- [ ] RED source-work/verse focus tests
- [ ] Pinned primary-source diagnostic CI
- [ ] Review actual source/Gk snippets and numbering discrepancy
- [ ] Independent skeptical exact-head PR review
- [ ] Then separate edition-qualified crosswalk change if justified
