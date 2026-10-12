# Issue #168 — fail-closed embedded source chapter boundary in Coptic↔LXX candidate resolver

## Research (2026-10-12)
- The current source parser and graph preserve TT `chapter_n` source-positioned reference annotations independently from the document metadata `chapter`; its `SblAnnotation` records `kind/value/start_word_ordinal/start_char/start_after_word_ordinal`. The producer's only word slots remain TT `norm` and all source evidence must survive unchanged.
- The version-pinned Coptic OT ↔ Greek resolver in `lxx_reference.py` currently uses `metadata["chapter"]` for **every** Coptic verse group; `_group_words` groups adjacent words solely by their `verse_n` literal. If source `chapter_n=3` begins between two groups both labelled `verse_n=1` while `meta chapter=2`, this could falsely fuse them and assign second-chapter words to LXX 2:1.
- Existing full pinned source audit: 1,574 OT-candidate records; no duplicate/backward positive OT verse labels, but 2,834 chapter-reset events in other/undetermined families. A synthetic future-variant regression is warranted; **not proof of a current pinned false alignment**. Coptic source/Greek LXX differences remain address candidates, not translation equivalence.

## Plan / explicit gates
1. RED-first tests for two physically different chapters sharing a verse number, missing/invalid chapter labels, same-chapter boundaries, token-internal source chapter marker, and Marcion chapter wrappers (do not treat as canonical Bible chapters).
2. Split verse groups conservatively at native TT `chapter_n` event starts (including before first word); no new token/node or silent numbering remap. Verify all groups before a changed chapter still match as candidates. If any chapter marker with a different/non-numeric value is active for a group, mark `ambiguous` and refrain from calling LXX lookup; if the marker intersects a verse group in the middle of a word, mark that group ambiguous.
3. Run all relevant exact-head unit and pinned actual Coptic/LXX integration workflows. If real full-corpus status metrics change, determine whether source evidence justifies change before merge.
4. Independently adversarially review actual final diff, source sample and CI logs. Close #168 only after all gates pass.

No foreign TF node edges, no source data redistribution, no claim of content equivalence.
