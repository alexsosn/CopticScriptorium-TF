# Issue #149 continuation — source-local evidence around ten OT edition-ambiguous verse jumps

## Primary evidence and motivation

The 2026-10-11 real native CenterBLC/LXX run on PR #150 (now merged as `8e63b31a0afdee4890474f3861976d02a2722ba5`) checked 140 Greek verse addresses across Dan/DanTh, TobBA/TobS, Sus/SusTh and Bel/BelTh. 125 exist and 15 do not. All ten exact source gaps remain `unresolved_edition` because numerical-address presence does not establish Coptic-to-Greek reading/edition identity. Exact source event identity lives in `research/issue-149/pinned-ambiguous-gaps.json` (seven physical TT SHA-256 hashes and ten marker ordinals), independently grounded in the full pinned 2,628-record Coptic upstream CI census `38165316273`.

The next **non-duplicative research batch** reopens the *actual pinned Coptic TT source bytes*, only `sahidic.ot/sahidic.ot_TT.zip` (rather than all 565 upstream blobs), to count original Coptic `norm` word starts between the flanking `verse_n` tags, check source chapter/CTS/editorial metadata and record whether source metadata literally *mentions* recognized Greek edition terminology. It does **not** choose a Greek tradition, infer missing text, or distribute source excerpts.

## Plan / research → RED → implementation → CI → independent review

1. RED-first source-context tests require fail-closed full TT source SHA, marker ordinal and prior/current verse label validation, exact reset at `chapter_n` boundaries, positive **word counts** between flanking markers, deterministic ordering and no fabricated certainty from edition-name mentions.
2. Implement a bounded pure source-markup scanner (`TAG_RE` / existing strict attribute scanner), using no Coptic text/lemma output, plus an explicit seven-record ZIP-only runner which refuses duplicate/missing archive members. Evidence includes source record ID and SHA, event ordinal/verse labels, original word-start count in immediately preceding source verse and optional editorial source-key presence; note any Greek edition name *mentioned*, never claim it is the base Greek text.
3. Add separate CI on exact converter head, sparse checkout only `sahidic.ot_TT.zip` at upstream `3ac067f1709a0012daf39ea8da2fac79980176a5`; independently cross-check 7 real members and all ten prior source events from the verified immutable fixture. CI prints **metadata only** (no raw corpus words/translations).
4. Adversarial review checks whether an apparent gap is merely missing numbering while source words continue, whether raw metadata states an edition or only a translation used for an English gloss, completeness of expected events, and no edition promotion.
5. Keep issue #149 and parent LXX alignment #70 OPEN. Later compare actual Coptic readings against the two Greek editions with expert/lexical evidence. Never promote `unresolved_edition` on references or metadata-name mentions alone.

## Acceptance
- [ ] 7 expected original TT byte hashes verified on upstream ZIP and all 10 real source events matched at original marker positions
- [ ] bounded source word counts/metadata only, no copyrighted source text in generated artifacts
- [ ] exact-head CI and independent skeptical review before merge
- [ ] no native alignment change or premature source edition selection
