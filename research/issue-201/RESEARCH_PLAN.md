# Issue #201 — Coptic Psalm zero-to-one boundary ↔ exact Greek 1–2 (research plan)

## Sources and initial findings (15 Nov 2026)
- Pinned corpus `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`: exact `bohairic.ot/bohairic.ot_TT.zip`, 151 Psalm zero source spans = **1,313 Coptic word slots**. 151/151 are nonempty, #199/#200. Six physical controls: Psalm 1 (1 word), 3 (16), 17 (59), 51 (42), 149 (1), 151 (11); source document SHA-256 recorded in [#201](https://github.com/alexsosn/CopticScriptorium-TF/issues/201).
- Greek TF `CenterBLC/LXX@f32a98eddf7eb239aa73ab863d70381e416d5076` (Text-Fabric 1935) has `@fmt:text-orig-full={word}`, `@sectionTypes=book,chapter,verse`, 30,371 Greek verse nodes. Need independently query `L.d(verse, otype='word')` and `F.word.v` for Greek verses 1–2, including original `orig_order`.
- Published primary display [Coptic Scriptorium Bohairic Ps17](https://data.copticscriptorium.org/texts/bohairicot/19_psalmi_17/) shows the final source-zero phrase `ⲟⲩⲟϩ ⲡⲉϫⲁϥ` ('and he said'), while [Greek Rahlfs Ps17:1–2](https://www.die-bibel.de/bibel/LXX/PSA.17) places `καὶ εἶπεν` at Greek 17:2, *after* a Greek 17:1 superscription ending with Saul. This is a **cross-verse** hypothesis, not a certified bilingual word alignment.
- Psalm 1 source zero rendered as literal ellipsis `...`, a placeholder, whereas Greek 1:1 opens `Μακάριος ἀνήρ`: negative control. Psalm 149 source zero is `ⲁⲗⲗⲏⲗⲟⲩⲓⲁ`, which may correspond to the very first word `Ἀλληλούϊα` of Greek 149:1 (split within a verse). Psalm 151 opening appears as a more substantial title; do not treat every psalm equally.
- Greek titles 3 and 51 need exact native word-verse boundary checks; no blanket 0→1 and 1→2 is justified.

## Scoped development decision
1. Introduce a read-only **six-case primary-source boundary diagnostic** rather than an unverified new TF mapping. Accept only those six physically SHA-locked Bohairic source records and the exact pinned Greek parent, validating native verse nodes, source word marker boundaries and original Greek word order. Observations are *structural hypotheses*; never convert candidate references or assign bilingual word alignments.
2. **RED-first** test: literal Psalm1 `...` placeholder (must not count as lexical match); Psalm17 source-zero final phrase and Greek17:2 initial `καὶ εἶπεν` (cross-verse); Psalm149 `ⲁⲗⲗⲏⲗⲟⲩⲓⲁ` vs Greek149:1 `ἀλληλούϊα` (within-Greek-verse), unknown cases 3/51/151, forged TT SHA and fake Greek parent, Greek reversed/or missing first-2 words, bogus candidate equal-number references, no source-origin loss.
3. On exact real pinned CI, emit bounded, textual-data-free case evidence: 0/1 source word counts, Greek verse1/2 word counts, Boolean occurrence/position of the *curated short lexical anchors* (not raw text), source/parent sha and chapter. For 17 and 149, test exact source word form/position and Greek form/position, with accents stripped/Unicode NFC. Positive only as `candidate_cross_verse` / `candidate_within_verse` until expert collation; 1 is `editorial_placeholder`, other cases remain `needs_collation`.
4. Keep #75/#108 open; follow-up could design native typed edge and source word ordinal interval only after evidence of 1:N/N:1 Greek correspondence. Add source-relevant researcher guide, no licensed text or new semantic sidecars.
5. Independent adversarial review on real source labels, pinned TF Greek word feature and exact-head CI before merging PR.

## Acceptance / stop gates
- Six physical TT hash controls and Greek section/word/native node structural checks; stable statuses and bounded counts on genuine corpus. No Coptic/Greek words beyond curated minuscule anchor checks emitted; case-level exact source provenance retained.
- Any mismatch blocks CI. No crosswalk change until lexical evidence is sufficient; no default shift.
- RED-first test committed before production code. Exact-head real CI + separate skeptical review before squash merge.
