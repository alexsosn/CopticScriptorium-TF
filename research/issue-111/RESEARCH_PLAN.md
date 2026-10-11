# #111: Bohairic Zechariah 2:7–13 / LXX 2:11–17 evidence batch

## Sources and falsifiable research hypothesis
- Source corpus exact `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`, `bohairic.ot/bohairic.ot_TT.zip` physical `38_Zacharias_02.tt`, original chapter2 SHA256 `6521b293392498f22cddd432bfe2bc0a89ef4a244010040a5b8c3d45a5382028`, exact `urn:cts:copticLit:ot.zach.bohairic_ed:02`.
- Target `CenterBLC/LXX@f32a98eddf7eb239aa73ab863d70381e416d5076` TF 1935; all eight release-critical Git blob fingerprints must match CATSS-TF.
- Earlier actual data-supported candidates already give Bohairic source 2:1–6 → Greek 2:5–10. The remainder 2:7+ is intentionally `ambiguous`; wrongly treating matching same-number addresses as verified would be worse than a missing link.
- Public-domain Brenton Zechariah chapter2 7–13 and Greek LXX/Rahlfs chapter2 11–17 suggest **seven separate possible shifts**: source 2:7..13 → Greek 2:11..17. The *source edition English translation* may be derived from Brenton and misaligned; it is **not independent Coptic→Greek lexical evidence**. Check actual Coptic word spans/CTS/English verse-local annotation availability and the pinned Greek word nodes before changing the map. Do not apply a global +4 rule or extrapolate to another edition/chapter.

## Distinguishing themes (not equivalence certification)
Source English 2:7–13: (7) Sion/Babylon, (8) nations/apple of eye, (9) hand/spoil, (10) rejoice/Sion, (11) many nations/dwell, (12) Judah/Jerusalem, (13) flesh/clouds. Against actual pinned Greek target 2:11–17 respectively, compare Greek root anchors Σιών/Βαβυλών, κόρη/ὀφθαλμός, χείρ/σκῦλα, θύγατερ/Σιών, ἔθνη/κατασκηνόω, Ἰούδα/Ἰερουσαλήμ, σάρξ/νεφέλαι. Same-number Greek 2:7–13 is the negative control.

## Research → plan → RED → implementation → CI → review
1. Add **live bounded diagnostic** that opens one exact Coptic TT ZIP member, verifies SHA and CTS, derives seven raw source verse spans and verse-local English annotations using existing parser; verifies actual Greek parent version and `T.nodeFromSection(("Zech",2,v))` for both shifted and same-number candidates. Measure motif matches for each verse; emit at most 7 structured rows with counts and motif scores, without reproducing text.
2. If any span is missing, source English mismatches, unexpected Greek numbering/subverses or same-number comparison is not discriminating, stop and document the actual difference. No change to real mapping unless evidence warrants it.
3. RED-first pure tests extend the versioned source-byte-gated chapter2 policy by **one batch** to 2:7..13, with exact expected 2:11..17, wrong SHA and CTS, alternate Sahidic, and source 2:14+ negative controls.
4. Extend the existing scoped source rule (not seven per-verse PRs) only after live evidence; keep status `versification_candidate`, preserve source/Greek provenance, no text equivalence claim. Update old negative tests and researcher guide to reflect actual reviewed range.
5. Gate exact-head subset CI AND full pinned Coptic↔LXX all-corpus native TF module and coverage CI; ensure all 2,394,354 Coptic slot statuses remain partitioned. Logically independent skeptical final PR review then merge; keep parents #97/#70 open.

## Anti-overclaim
A valid Greek verse address + correlated Brenton verse-local motif is still only a **source-edition-specific reference candidate**, not translation proof or Coptic/Greek word alignment. Edition pin, SHA, per-verse evidence and human-checkable reason/status must survive.
