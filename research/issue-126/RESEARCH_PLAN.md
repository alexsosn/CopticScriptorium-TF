# Issue #126 — source-verified Mark 15:28 Greek NT edition absence

## Research (real immutable bytes, 2026-10-11)
- Pinned `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`, `sahidica.mark/sahidica.mark_TT/Mark_15.tt`, Git blob `15074a8734aea32078f3bafe107829284258fbd3` has document `book=Mark`, `chapter=15`, `document_cts_urn=urn:cts:copticLit:nt.mark.sahidica_ed:15` and explicit SBL Greek source provenance.
- Exact source has consecutive editor labels `verse_vid="41N 15:27"`, `verse_vid="41N 15:28"`, `verse_vid="41N 15:29"`. Mark15:28 opens with `verse_n="28"`, an SBL wrapper `sbl_greek="(missing in SBL)"`, then the `41N 15:28` reference. This is literal source editorial absence evidence; do not infer a Greek word sequence, a corrected Greek verse, or a superior variant.
- Read-only pinned Greek NT parent `alexsosn/sblgnt@4dd0207bda66133fdfa9740ff0aae7de61228700` is MorphGNT 6.12 Text-Fabric. Its verse inventory was previously audited by #117 and Mark15:28 does not exist. Maintain independent corpus ownership: no changes to `sblgnt`.
- Production `copticscriptorium_tf/nt_reference.py` already implements typed `edition_unavailable` for John7:53–8:11; Mark15:28 is missing from its explicit absence policy and therefore becomes generic `unresolved`. Refine only the **status** after all source identity, SBL provenance, CTS, book/chapter and editor-label consistency gates.
- Current pinned full source outputs: 2,628 Coptic TT records, 2,747 SBL occurrences, 2,301 `reference_candidate`, 437 `ambiguous`, 9 `unresolved`, 904 distinct mapped Greek NT verses. New expected distribution: 2,301 candidate, 437 ambiguous, 8 unresolved, 1 edition_unavailable, same 2,747 total and same 904 parent verses.

## Research→plan→RED→implement→test→independent review
1. RED tests: exact source Mark15:28 Coptic marker with missing Greek verse returns `edition_unavailable`, no `shared_id`, no target node, no fabricated lookup; preserve 15:27/29 candidates. Incorrect chapter/editor label, forged Git provenance, missing source provenance, wrong work and a random absent Greek verse remain `ambiguous`/`unclassified_source`/`unresolved` as appropriate.
2. Extend only the edition-absence policy for (`Mark`, 15, 28). Keep John excluded references unchanged. No source text or Greek verse repair.
3. Update full-corpus pinned expected status counts in `research/issue_120/full_nt_wefts.py` and exactly corresponding assertions. Run all unit tests on exact PR head.
4. Activate the existing 100m **full 2,394,354-word Coptic TF plus 2,747 source SBL and bilateral Greek NT native modules/independent reload** workflow for this PR branch, reusing one sparse pinned acquisition; do not claim full acceptance from a Mark-only fixture.
5. Separate logically independent adversarial review of changed code and actual original Coptic, Greek pinned release, native TF and full pipeline logs. Merge only exact-head green; retain unmatched/unmapped semantics.

## Non-goals
No semantic Greek/Coptic word alignment, no reconstructed/forged Mark15:28 target, no general Mark missing-verse heuristic, and no corpus redistribution.