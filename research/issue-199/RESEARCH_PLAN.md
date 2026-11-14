# Issue #199 — source-byte-locked Bohairic Psalm `verse_n=0` topology against LXX

## Research baseline and skeptical hypothesis (2026-11-15)
- Full real immutable Coptic corpus audit [#195](https://github.com/alexsosn/CopticScriptorium-TF/pull/195) artifact `issue194-pinned-tvtms-aggregate-report` (run `43651753680`, 2,628 TT docs / 1,574 conservative OT docs / 35,472 grouped OT verse refs) contains exactly **151** original `verse_n=0` tags in `bohairic.ot/bohairic.ot:19_Psalmi_001..151`, **2** in Bohairic Lamentations 1 and 5, none elsewhere in OT. Each Psalm zero tag is ordinal 1 and `source_word_starts_before=0` in the separate #108 raw-tag anomaly stream. This is not evidence of a wordless span; next marker must be inspected on the actual source bytes.
- Pinned Coptic TT Git `3ac067f1709a0012daf39ea8da2fac79980176a5` has `bohairic.ot/bohairic.ot_TT.zip`. Pinned real Greek `CenterBLC/LXX@f32a98eddf7eb239aa73ab863d70381e416d5076`, TF 1935; check Greek `Ps` verse/subverse nodes with existing feature-blob verifier.
- Public original witness catalog confirms exact CTS work `urn:cts:copticLit:ot.pss.bohairic_ed:01` and text license CC-BY-SA 4.0, e.g. https://data.copticscriptorium.org/texts/bohairicot/19_psalmi_01/ . LXX Psalm superscriptions may be numbered; under no circumstances assume source zero equals Greek verse 0, verse 1, or a matching translation.
- #194's 3,153 Psalms reference-group differences with English→Greek TVTMS describe differences between numbering schemes, **not** 3,153 proven Coptic errors. Fail closed on translating those into new mappings.

## Test-driven acceptance plan
1. RED: synthetic raw TT tests for empty vs nonempty span between `verse_n="0"` and next numbered marker, zero within Coptic token, malformed literal, no next marker, multiple zero tags, non-Psalm and wrong edition, zero after word, mismatched source SHA/commit.
2. GREEN: source-only `psalm_zero_boundary.py` classifier emitting strictly limited metadata: exact source ID + source sha256, original zero tag offset, word count before next verse marker, next original literal, Greek **address-exists** status (no bilingual text equivalence).
3. Focused live source/Greek acceptance: stream all **151 physical Bohairic Psalm records** from genuine pinned ZIP, assert ordinal 001..151, no silent omissions or duplicates, compare raw tag word counts with parsed `Word.verse_n` layer; check actual Greek verse nodes with `T.nodeFromSection` and CATSS identity checker. Add 2 Bohairic Lamentations negative-control documents from same ZIP. Keep output to aggregate counts and bounded examples, no Coptic/Greek text.
4. Source verdict: if all 0 spans are empty, identify harmless source scaffolding; if some have Coptic words, keep those explicitly unresolved and research verse-local Greek parallels before changing any TF references.
5. Independent adversarial review of *actual* files, strict source and Greek pins, tests, exact-head green CI, and no redistribution. Only merge if its actual result supports conclusion; keep #75/#108 open for broader alignments.

## Non-goals
- No automatic chapter renumbering, no T→Greek Greek verse-zero invention, no word-level translation alignment, no source text redistribution, no opaque JSON/XML semantic sidecar. This adds a read-only research/diagnostic source evidence path.
