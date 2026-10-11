# Issue #110 — source-faithful language wrappers in native TF

## Research — source bytes and existing model (2026-10-11)
- Exact pinned `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`, `sahidica.mark/sahidica.mark_TT/Mark_02.tt`, Git blob `224415544df384cfa696e6d3c3210649d2e96b3b`: **77** opening `lang` wrappers: 61 exact literal `Greek`, 16 exact literal `Hebrew`; each matches a closing wrapper. The visible source excerpts place wrappers *inside* `norm` with visible Coptic characters inside the wrapper, sometimes inside entity annotations. `lang` identifies upstream scholarly annotation, **not** SBL Greek textual parallels, not a token's etymology verified by lexica, and not a Greek→Coptic word correspondence.
- Native SBL annotation parser already handles potentially crossing source spans, and explicitly retains opening/closing word/character positions + complete-word locus, with a single-word anchor for in-word-only annotations. Existing `SblAnnotation` positional carrier and graph `sbl_greek`/`sbl_apparatus` are suitable patterns but **SBL occurrence numbering must not change** if new `lang` is encountered earlier in document.
- Current parser silently ignores `<lang>` tags. Need conserve raw `lang` values/positions as **native nodes `lang`**; do not change the 2,394,354 word slots, section design, or SBL annotation identity.
- #110 requires a **complete 2,628-record scholarly wrapper census** before asserting global wrapper coverage; this PR covers the known real `lang` case while follow-up census remains open. It must not be advertised as all-wrapper completion.

## Research → plan → RED → implement → test → independent review
1. RED tests for a `<lang lang="Greek">` entirely within one Coptic norm (anchor with raw start/end character offsets), span across two complete words (native oslots), distinct literal `Hebrew` with SBL co-occurrence preserving independent old SBL ordinals, source empty vs missing attribute, malformed close/unclosed language wrapper, and native TF reload using `lang` nodes with `value` + standard positional features.
2. Reuse positional **source** carrier and existing source-annotation parsing logic, but keep SBL ordinal counter separate from `lang`; reject malformed occurrence instead of silently dropping it. `lang` is not Greek text: no SBL feature contamination, no synthetic slots, no text rewriting.
3. Add native `lang` non-slot nodes with `lang_span` vs `lang_anchor` render modes, exact source record identity + boundaries + literal. Negative graph validations reject forged positions and wrong source metadata.
4. Actual pinned Mark 2 workflow fetches **one** immutable TT file, verifies exact Git commit/blob, checks all 77 source tag occurrences (61 Greek / 16 Hebrew) against 77 native TF nodes, reloads TF and checks invariant SBL counts. Avoid distributing source text.
5. Exact PR-head CI, skeptical independent review of real provenance, parser crossings, graph position bounds and SBL ordinal identity. Merge only if green. Follow-up full census of other unknown wrapper tags remains #110; do not close #110 as completed yet.

## Definition of done for this bounded slice
- Zero silent loss of Mark 2 language occurrences in real native TF
- No new word slots / section hierarchy change / JSON XML blobs
- Exact-head CI real pinned Mark 2 green
- Logically independent adverse review and merge
