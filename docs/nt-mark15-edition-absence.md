# Mark 15:28 — explicit Greek NT edition absence (#126)

## Verified source and parent distinction
The pinned TT record `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`, physical `sahidica.mark/sahidica.mark:Mark_15`, contains the original **43rd** SBL annotation of kind `sbl_greek` at Coptic **Mark 15:28**; the original source `verse_n` and editorial `verse_vid=41N 15:28` agree with the document's `nt.mark` CTS/book/chapter metadata.

The pinned read-only Greek NT Text-Fabric `alexsosn/sblgnt@4dd0207bda66133fdfa9740ff0aae7de61228700` has **no Greek verse node for Mark 15:28**, while its `Mark 15:27` and `Mark 15:29` verse nodes are present. The source passage is not discarded: its original Coptic `sbl_greek` TF node and text/position remain unchanged. Only its address-resolution status is refined from generic `unresolved` to `edition_unavailable`. No Greek verse or Greek/Coptic word correspondence is invented.

## Exact source-conservation baseline

| Status | Prior full native TF gate | New gate |
| --- | ---: | ---: |
| `reference_candidate` | 2,301 | 2,301 |
| `ambiguous` | 437 | 437 |
| `unresolved` | 9 | 8 |
| `edition_unavailable` | 0 | 1 |
| Total original SBL annotation nodes | 2,747 | 2,747 |
| Distinct Greek NT target verses | 904 | 904 |

The full Coptic-owned TF weft projects `coptic_nt_ref_status=edition_unavailable` on that *existing original* Coptic SBL node, with **no** `coptic_nt_ref_id` value. The Greek-side weft remains unchanged in reference-address meaning and target inventory. This is a *textual edition coverage observation*, not proof that the Coptic reading is identical to any Greek edition.

## Verification
RED-first `tests/test_issue126_mark15_edition.py` rejects widened rules, forged source provenance, conflicting editorial labels, or false classification of neighboring verses and incomplete Coptic word spans. `tests/live_issue126_mark15.py` checks actual original TT ordinal, source markers, exact Greek TF parent feature proofs, and parent verse absence/presence, without emitting corpus contents. The existing full issue120 acceptance workflow is reused, now also triggered by the issue126 PR branch: rebuild all 2,628 original TT records/2,394,354 Coptic word slots; independently verify all 2,747 source annotations; generate both native Coptic-owned wefts and perform separate Text-Fabric reload/count reconciliation. License review is still required before distributing any complete corpus.

**Boundary:** All alignment and diagnostics remain within `CopticScriptorium-TF`. The Greek NT repository and its warp/feature data remain unchanged, read-only parents.
