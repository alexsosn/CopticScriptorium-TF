# Issue #184 — quantify original TT attribute-key occurrences (research only)

## Known pinned source facts
- Immutable `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`; existing source census `research/issue-118/tag_matrix.csv`: exactly 565 TT Git blobs / 2,628 physical original records (including ZIP) / 6,621,410 original opening tags, 101 kinds.
- `morph` has 78,265 openings and the key union `morph;lang`. The old published matrix cannot tell whether the extra `lang` occurs once or thousands of times, or which original source file contains it.
- Current parser `TOKEN_WRAPPER_TYPES` records exact original `morph` main literal/value and start/end positional evidence, but does not record `source_attributes` for token kinds; `lang` on the *same morph opening* would be unrepresented. Standalone nested `<lang lang="Greek">` is a separate native annotation and must not be confused with it.
- Original `norm`, `entity`, `verse_n`, `norm_group`, `meta` have multiple original attribute names; some map to existing native features and may be semantic aliases. Need empirical counts before schema additions. Arabic source tag distinction was resolved by merged #185.

## Research → RED → implementation → independent review
1. RED-first focused test on existing source census `audit_tt` expecting a *watched* `morph.lang` original-opening source record sample and independent `(tag,attribute)` counters without original corpus text. First RED head intentionally fails because `watched_examples` is absent.
2. Extend the **existing, already-running pinned full source census**, not introduce a new scanner/framework or second Git checkout. It already collects `by_tag_attr` counter for each parsed TT opener and processes directory/ZIP; report counts for all observed attribute keys on selected `morph`, `norm`, `entity`, `verse_n`, `norm_group`, `meta` kinds and at most 3 physical source IDs for `morph.lang`. Never emit literal values/Arabic/Coptic words.
3. Run exact pinned source workflow on PR head and focused/all repository tests. Inspect original `morph.lang` occurrence count and source record IDs; only then decide whether to introduce native `source_attr_morph_lang` under its own RED-first original source parity ticket/commit or to document an intentional exclusion. Preserve source ordering and existing `lang` nodes.
4. Logically independent skeptical review of scope, no source leakage, immutable source/count provenance and green CI before merging. This PR makes **no** converter/writer/schema changes; its counts do not prove all original attribute values are preserved.
5. Keep #184 OPEN for subsequent value-level TF conservation; do not create a broad generic attribute serializer unless data demonstrate need.

Resource cost: reuse source audit `issue69-complete-pinned-verse-census` instead of a second expensive checkout. Existing full corpus CI might rerun because census script is part of its workflow; no additional job or downloaded corpus is introduced.
