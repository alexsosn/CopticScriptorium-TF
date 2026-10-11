# Issue #149 — one batch: alternative Greek edition address probes for 10 ambiguous Coptic OT gaps

## Evidence and fixed scope (2026-10-11)

Retrieved real GitHub Actions artifact `issue80-coptic-lxx-reference-coverage` (70,398-byte compressed ZIP, 1,090,500-byte JSON), from successful pinned full-corpus run [38165316273](https://github.com/alexsosn/CopticScriptorium-TF/actions/runs/38165316273), job `114546559963` on PR #145 head `8b02a2507b48b9e4f93ba5c1559d47cd69e4edfe`; now merged by squash at `b49d3ef500866a295368cd66a23311526f360aae`.

The source is `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`; all 565 TT Git blobs and 2,628 physical TT records were checked. Of 309 OT numeric-gap events, 299 are Greek-address crosschecked (795 per-event Greek intermediate addresses present, 108 absent), **10** have `greek_status=source_reference_unclassified`. The ten have **50** missing intermediate source verse numbers, five physical source records? Actually seven physical records: Daniel 4/5/10 (3), Tobit 4/5 (2), Susanna 1 (1), Bel 1 (1). Preserve distinct marker ordinals even for same physical record.

Source work counts: `ot.dan` 6, `ot.tob` 2, `ot.sus` 1, `ot.bel` 1. All are Sahidic `coptot`, unlike the existing separately reviewed Bohairic Zechariah crosswalk.

The immutable Greek target `CenterBLC/LXX@f32a98eddf7eb239aa73ab863d70381e416d5076` (TF 1935 v1.0.1) contains alternative Greek edition books as recorded in CATSS-TF's pinned LXX schema:
- `ot.dan`: `Dan`, `DanTh`;
- `ot.tob`: `TobBA`, `TobS`;
- `ot.sus`: `Sus`, `SusTh`;
- `ot.bel`: `Bel`, `BelTh`.

No current source witness evidence justifies selecting one of these variants. An apparent numeric match under either Greek book is **not** proof of textual affinity or source versification agreement.

## Research → plan → RED → implement → test → independent skeptical review

1. Commit an **aggregate-only**, non-semantic research fixture with exact 10 source record IDs, real TT SHA256, CTS work, source chapter, marker ordinal, preceding/current numbered markers and bounded missing numbers. Not source text, translations, lexical forms, generated TF or scholarly semantic sidecars.
2. RED tests verify all four variant pairs, exact ten events/seven records/50 internal source numbers, fail-closed provenance, no accidental duplicate event or unreviewed source work, and that even one variant having a Greek address (vs its competitor missing it) does **not** automatically select that edition.
3. Implement pure, typed **address-only** dual-variant probe. For each source event check the previous/current Greek verse address and each missing intermediate address independently under *both* alternatives. Optionally report native Greek subverse counts; missing addresses remain recorded. Edition status always `unresolved_edition` until human/editorial evidence exists.
4. CI test against real `CenterBLC/LXX` pinned TF 1935. Reuse existing `validate_lxx_release` checks for actual mapping-critical Git-blob fingerprints; never substitute static toy Greek node IDs in a live claim. No full Coptic source download in this PR: exact source IDs/hashes originate from **already successful full pinned artifact**. This prevents another 15-minute duplicate full corpus pull.
5. Independent adversarial review final exact head with primary data, all checked target addresses and safeguards against treating book variants as interchangeable. Merge only after required workflows GREEN.
6. Separate subsequent research with actual Coptic and Greek textual/edition content before any positive `versification_candidate` or TF module change. This audit is not a mapping and **does not** close #149/#108/#70.

## Acceptance
- [ ] Ten exact source gap events from seven source records; all 50 missing numbered markers retained.
- [ ] Both relevant Greek edition variants checked for each event, real Greek verse-node existence and any subverses, with ambiguity explicitly preserved.
- [ ] No fabricated Coptic↔Greek passage/word equivalence, no raw corpus files distributed, no cross-warp integer edges, no new TF annotation based on mere address existence.
- [ ] RED-focused tests, exact-head real Greek CI, logically independent skeptical review.
