# Issue #126 — Edition-qualified Mark 15:28 noncandidate classification

## Research evidence and boundaries
- Original Coptic TT pinned source: `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`, physical record `sahidica.mark/sahidica.mark:Mark_15`, SBL kind `sbl_greek`, ordinal 43. Source `book=Mark`, `chapter=15`, `document_cts_urn=urn:cts:copticLit:nt.mark.sahidica_ed:15`, original verse `verse_n=28`, editor `verse_vid=41N 15:28`; source reference provenance points to historical SBL GNT.
- The actual separately pinned `alexsosn/sblgnt@4dd0207bda66133fdfa9740ff0aae7de61228700` `tf/2022` parent has 7,927 Greek verse nodes and lookup lacks Mark 15:28. Mark 15:27 and 15:29 are expected to be present and are asserted against native TF in real-data tests.
- #124 complete source census isolated precisely **one** `parent_verse_unavailable` occurrence at this Mark 15:28 source; the full #120 native TF/weft baseline before this ticket was 2,301 candidates, 437 ambiguous, 9 unresolved. No source/Greek corpus text is redistributed. The Greek NT parent is read-only.

## Research → plan → RED → implementation → tests → adversarial review
1. RED-first independent unit tests for correct Mark15:28 `edition_unavailable`, zero Greek node/ref, Mark15:27/29 still candidates, malformed/wrong source work/chapter/versification cannot enter the special branch, and incomplete Coptic word spans remain unresolved. Preserve John 7:53–8:11 exclusions.
2. Extend explicit missing-Greek-verse edition inventory with exactly `('Mark', 15, 28)`, with no source text/word correspondence and no Greek repo change. Keep reference matching fail-closed and source-attestation rules unchanged.
3. RED/full baseline updates must preserve all 2,747 original SBL annotations. Require 2,301 candidates, 437 ambiguous, **8 unresolved**, **1 edition_unavailable**; 904 Greek verse nodes and 2,301 Greek occurrence counts remain unchanged.
4. Exact pinned Mark15 real-data smoke verifies original SBL occurrence ordinal 43 and source markers, native Greek parent `Mark 15:27` and `Mark 15:29` present and `Mark 15:28` absent, and no foreign target ID for 15:28.
5. Run complete pinned 2,628-document / 2,394,354-slot Coptic native TF build and SBL source parity, source-to-Greek verse resolver, bilateral Coptic-owned weft generation and separate TF native reload using existing issue120 workflow, extended only for issue126 branch. Publish source-free counts and resource measurements only.
6. Submit PR to independent adversarial skeptical review after exact-head CI; accept merge only when ALL applicable checks are green. Scope is status refinement only; source anomalies (#117), licensing and peak-memory (#109) stay separate.

## Non-goals
- No regeneration of Greek NT corpus, no cross-warp node IDs, no Greek/Coptic word-level alignment. No fabricated verses, no source data release.
