# Issue #89 — pilot two native TF modules for Coptic OT/LXX verse-address candidates

## Research and pinned provenance (2026-10-11)

- The production Coptic TT→Text-Fabric parser, graph and writer preserve every source record, source SHA-256 and exact word ordinal. Merged #71 preserved word-scoped verse labels plus 29 intra-word marker events; full pinned 2,628-record census was green. Merged #72 strictly resolves Coptic book/chapter/verse into only **reference-address candidates**, never text/word correspondences. Real Ruth 2 (23), Jonah 2 (11) and Bohairic Habakkuk 2 (20) resolved all 54 candidate addresses against pinned `CenterBLC/LXX` 1935, v1.0.1, Git `f32a98eddf7eb239aa73ab863d70381e416d5076`.
- `CATSS-TF` projects a stable shared alignment ID onto existing parent nodes instead of invalid cross-corpus TF edges. The CATSS LXX parent profile has 623,693 Greek word slots, 30,371 verse nodes, maxNode 685,732; mapping-critical Git blob fingerprints are in CATSS `lxx_schema.py`, including `otype.tf=2e6480116dfda09f20e8de7c5b9feefa76322a96`, `verse.tf=ff8766352d7aff530c6eec4f66366adcc691740e`.
- The Coptic corpus is version-pinned to `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`. On Coptic parent, `source_record_id`, `source_word_ordinal` and `source_sha256` can verify source correspondence. Parent native TF data must remain untouched; no user corpus redistribution.
- The Coptic source may use different verse numbering; **shared verse address ≠ validated textual equivalence**. Preserve this in status/metadata and don't project CATSS Greek word alignments onto Coptic.

## Plan / RED-first acceptance

1. RED tests verify: sample three real TT documents; Coptic generated native TF parent; actual immutable LXX TF parent; 54 references; both modules have only native scalar TF features, no warp files, no XML/JSON/TSV semantic sidecars. Attach Coptic reference ID to Coptic **word slots** (possibly multiple witnesses); LXX reference ID to LXX **verse** node and integer source-span count.
2. Build fail-closed pure projector over `DocumentModel` and two loaded parent TF APIs. Assert complete source-record SHA, word counts, ordinal uniqueness and `norm` surface parity against the **actual Coptic TF warp**, and strict fingerprint of the pinned LXX release plus count/profile. Check candidate tuple node identity via actual `T.nodeFromSection`; do not trust stale raw node integers.
3. Emit weft-only TF node feature files `coptic_lxx_ref_id.tf`, `coptic_lxx_ref_status.tf` on Coptic word slots and `coptic_lxx_ref_id.tf`, `coptic_lxx_source_span_count.tf` on LXX verse nodes with module/provenance metadata, via atomic no-clobber publication of a combined directory.
4. CI fetches pinned Coptic three source records and actual pinned CenterBLC/LXX TF 1935, runs RED unit tests and real module projection, reloads **parent + module** for each corpus and asserts 54 Greek references and 54 Coptic verse spans. No distribution of real derived corpus artifacts.
5. Adversarial cases: wrong Coptic provenance/word order, wrong LXX version/blob, existing output path, missing verse, contradictory reference, same Greek address from two witnesses, corrupt/missing TF feature; require no partial output.
6. Logically independent skeptical review only after exact-head CI; merge only once green.

## Next: beyond pilot

Full OT coverage and true verified versification crosswalk (including subverse/1:N), dual projected modules for the *entire* pinned corpus, and honest unresolved/ambiguous audit remain in #70. Pilot reference IDs are not word-by-word translation alignments.
