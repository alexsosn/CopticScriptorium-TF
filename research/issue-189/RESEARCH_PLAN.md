# Issue #189: preserve exactly 284 original morph.lang attributes

## Research
The pinned original TT source at `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`, independently counted by merged source census PR #186 / run 39453660227, contains 78,265 `<morph>` source openings and exactly **284** `lang` attributes on those openings. First attested source physical members are Sahidic OT ZIP Genesis 1, 5, 17. The separate nested `<lang>` tag has its own source evidence and must not be conflated with these attributes. Existing parser stores SblAnnotation source_attributes for interventions only, so `morph.lang` source value is lost.

## RED-first and implementation
1. RED parser→graph→writer→Fabric contract (including original `morph.lang` empty/present/absent, crossing nested `<lang>` with different label, exact source ordinal/character position and only 1 word slot). RED on existing implementation because annotation source attrs are empty and feature missing.
2. Allow only `morph` source opener keys `morph` and optional `lang`, preserving their exact original decoded strings in SblAnnotation source_attributes; all other original token wrapper types stay unchanged. Keep source `morph` value and positions. Extend both model-stage and graph-stage validation narrowly. Add sparse native `source_attr_morph_lang` via existing typed source attr writer loop; present empty string distinguished from absence. Do not add slots or separate label nodes.
3. Independently scan all 565 original TT Git blobs including ZIP members, verify exactly 284 `lang` attrs in original `morph` openings, and compare each attested source record's original attr literal, native `morph` source ordinal, original `value`, byte SHA and the regular `lang` nodes if present. Compare after exact full native build 2,628 records / 2,394,354 slots. No original TT words in CI logs/artifacts. Full CoNLL-U, Horner, LXX checks, resources.
4. Logically independent skeptical source/code/diff and actual CI review on exact final head; merge only after all applicable gates green. Keep #184 open for other source attr gaps.

No generic sidecar, no broad serializer, no inferred Greek/Coptic lexical equivalence. Scope is 284 original attested labels on existing source morph annotations.
