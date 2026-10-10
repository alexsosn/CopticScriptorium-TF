# Issue #73 — additive dual TF modules for Coptic→LXX reference candidates

## Research (2026-10-10)

- ETCBC/dss/alignment first locates Hebrew biblical passages by book/chapter/verse, then estimates consonantal word correspondences. Its separate DSS `parallels/tf/sim.tf` is not BHSA alignment.
- CATSS-TF `src/catss_tf/tf_schema.py::write_tf_module` uses standalone **weft-only** TF features attached to each parent node ID within its own warp. Shared stable IDs support cross-corpus joins without illegal cross-warp edges or new alignment nodes.
- Confirmed immutable Greek parent: `CenterBLC/LXX@f32a98eddf7eb239aa73ab863d70381e416d5076`, v1.0.1, TF 1935: 623,693 word slots, 685,732 total nodes, 30,371 verse nodes. Git blob SHA fingerprints of mapping-critical `otype`, `oslots`, `book`, `chapter`, `verse`, `subverse` available in CATSS-TF LXX profile. Check them independently rather than accepting counts alone.
- Immutable Coptic source `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`. Issue #69 full TT census: 2,628 source records, 73,844 `verse_n` occurrences, 29 in-word marker events preserved as explicit nodes; no fake unique verse assigned to those words. Issue #70 verified 54 verse-reference **address candidates** across real Ruth 2 (23), Jonah 2 (11), Bohairic Habakkuk 2 (20) using real Greek parent.
- Source references sometimes disagree in versification with Greek LXX. A matching verse address does **not** certify passage correspondence or bilingual word identity.

## RED/plan/implementation/acceptance

1. RED tests require a single approved version-pinned input pair; genuine parent word/verse node lookup (never arithmetic), multiple source witnesses share one Greek verse node without ambiguous assignment, collisions and missing source words fail closed, ambiguous/unresolved remain Coptic queryable with no affirmative shared ID.
2. Project `coptic_lxx_ref_id` shared on Coptic words and Greek verse nodes. Project Coptic `coptic_lxx_ref_status`, `coptic_lxx_ref_evidence` and `coptic_lxx_ref_reason` on relevant words. Greek reference node has one shared key regardless of #Coptic witnesses. Namespaced features must not collide with CATSS. No use of cross-warp integer edges.
3. Write two native **weft-only** TF modules under one atomically published output root, source and Greek parent release metadata in headers, no semantic sidecars or XML/JSON. Do not upload source or generated corpora.
4. CI: actual Ruth/Jonah/Habakkuk + pinned `CenterBLC/LXX`; build tiny generated Coptic parent TF and both modules; load both through Text-Fabric multi-module reader; cross-join by shared ID and query native features; validate all 54 candidates, Greek verse node count =54 and Coptic word membership; ensure no false claims of textual equivalence.
5. Independent adversarial review on exact head, then merge after dependency #69/#70 resolved. Broader full-OT coverage and versification exception policy remain separate higher gates.

## Non-goals

This first module release does not prove verse equivalence, map Greek/Coptic individual words, or claim full-OT coverage. The status is explicitly `reference_candidate`. A full scholarly alignment requires reviewable versification changes and source coverage audits.
