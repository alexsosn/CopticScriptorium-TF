# #135 — Research / plan / RED-first native token wrapper conservation

## Pinned upstream evidence

At immutable `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`, full source CI run `38143780565` job `114482850578` scans **565** Git TT blobs / **2,628** physical records / **6,621,410** opening tags. Five wrapper kinds are inside `norm` on *all* occurrences: `morph` (78,265), `norm_func` (20,011), `norm_head` (17,713), `norm_xml:id` (20,011), `norm_new_sent` (860). Total 136,860. The source census is baseline evidence, not proof of TF conversion.

The real `AP/apophthegmata.patrum_TT/AP.001.n135.mother.tt` contains `morph` spans crossing `lang` wrappers and an `lb_n` event inside a morph. `proclus-homilies/proclus.homilies_TT/proclus.23.nativity.tt` has `norm_new_sent`, `norm_head`, `norm_func`, and `norm_xml:id` opening and closing in **crossed orders**; strict XML tree behavior destroys/source-rejects these tags. Their textual span is positional source evidence, even when the scalar key repeats `norm` metadata.

## Research decisions

- Use one bounded family of native positional, non-slot TF nodes. Each type has a distinct `otype`; one shared `SblAnnotation` source-occurrence structure (new field `token_annotations`), one global source-local token annotation ordinal sequence, per-kind stacks; neither older SBL nor `lang` occurrence IDs may change.
- Only accept these five annotations *inside an open source `norm`*. Emit the source literal `value` with exact word and character boundaries measured in **visible decoded Coptic characters**, not raw TT offsets. Literal empty stays distinct from absent. Preserve non-nested/crossed closures, requiring matching per-kind opening; incomplete unclosed wrappers fail closed. Forbid a wrapper spanning multiple `norm` tokens.
- Treat partial-word wrappers as `token_annotation_anchor` with a single original word oslot and explicit start/end. Do not pretend a subtoken is a whole word or mint an extra slot. The source `morph` value is an annotation literal; actual diplomatic character text can differ due to editorial marks/layout.
- Emit per-kind nodes through existing graph loop; preserve `source_ordinal` + provenance + `value`, `start_char`, `end_char`, source word offsets. `sbl_verse_n` remains specific to SBL.
- Source-to-TF contract: word slots 2,394,354; physical records 2,628; `lang` 110,148; SBL 1,652 + 1,095; token nodes by type above. One complete sparse source checkout shared with existing full converter in `issue69-full-verse-census` CI job. No distributed corpus.
- Combine with forward-ported CoNLL-U #133 by stacking this branch on its tested head; after #133 merges, rebase/retarget to main. #134 is an independent source inventory.

## Gates

1. RED commit: tests covering crossed closure order, overlapping `lang/morph`, source literal and offsets, exact render anchor, malformed/orphan/unclosed/outside norm, empty literal semantics, native TF reload, preserved SBL occurrence IDs, word slot counts.
2. GREEN: minimal changes to model/parser/graph, no new sidecars.
3. Test: focused unit and pinned real AP/Proclus fixtures; all 2,628 documents on single full source job; exact pinned node counts and reader parity.
4. Skeptical independent code/data review before merge; no logical leap to lexical segmentation or Greek equivalence.
