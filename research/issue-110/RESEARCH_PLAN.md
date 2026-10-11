# Issue #110 — source-faithful language wrappers in native TF

## Research — source bytes and existing model (2026-10-11)
- Exact pinned `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`, `sahidica.mark/sahidica.mark_TT/Mark_02.tt`, Git blob `224415544df384cfa696e6d3c3210649d2e96b3b`: **77** opening `lang` wrappers: 61 exact literal `Greek`, 16 exact literal `Hebrew`; each matches a closing wrapper. The visible source excerpts place wrappers *inside* `norm` with visible Coptic characters inside the wrapper, sometimes inside entity annotations. `lang` identifies upstream scholarly annotation, **not** SBL Greek textual parallels, not a token's etymology verified by lexica, and not a Greek→Coptic word correspondence.
- Native SBL annotation parser already handles potentially crossing source spans, and explicitly retains opening/closing word/character positions + complete-word locus, with a single-word anchor for in-word-only annotations. Existing `SblAnnotation` positional carrier and graph `sbl_greek`/`sbl_apparatus` are suitable patterns but **SBL occurrence numbering must not change** if new `lang` is encountered earlier in document.
- Current parser silently ignores `<lang>` tags. Need conserve raw `lang` values/positions as **native nodes `lang`**; do not change the 2,394,354 word slots, section design, or SBL annotation identity.
- Actual exact-head 2,628-record full raw source census passed: GitHub CI `38131788620`, job `114447455606`. Across 565 immutable TT Git blobs there are **6,621,410 opening tags**: 101 tag types, **83 not mapped** by the source conservation inventory. The raw upstream has **110,148 lang labels** across 77 collections (77 in real Mark 2). Most frequent unmodeled wrappers: `morph` 78,265; `ed_line_n` 42,189; `multiword` 35,148; `norm_func` 20,011. Source counts alone cannot establish semantic loss or validate a global TF projection. Batch the remaining modeling by annotation family, not one PR per tag; detailed follow-up #118.
- This PR covers `lang` occurrence conservation and emits source inventory counts for other tags; it cannot honestly close #110's remaining full conservation task.

## Research → plan → RED → implement → test → independent review
1. RED tests for a `<lang lang="Greek">` entirely within one Coptic norm (anchor with raw start/end character offsets), span across two complete words (native oslots), distinct literal `Hebrew` with SBL co-occurrence preserving independent old SBL ordinals, source empty vs missing attribute, malformed close/unclosed language wrapper, and native TF reload using `lang` nodes with `value` + standard positional features.
2. Reuse positional **source** carrier and existing source-annotation parsing logic, but keep SBL ordinal counter separate from `lang`; reject malformed occurrence instead of silently dropping it. `lang` is not Greek text: no SBL feature contamination, no synthetic slots, no text rewriting.
3. Add native `lang` non-slot nodes with `lang_span` vs `lang_anchor` render modes, exact source record identity + boundaries + literal. Negative graph validations reject forged positions and wrong source metadata.
4. Actual pinned Mark 2 workflow fetches **one** immutable TT file, verifies exact Git commit/blob, checks all 77 source tag occurrences (61 Greek / 16 Hebrew) against 77 native TF nodes, reloads TF and checks invariant SBL counts. Avoid distributing source text.
5. Run native Text-Fabric **full corpus** build and clean reload on the **same** pinned sparse Git checkout already used by source/census CI; assert `2,394,354` word slots, `2,628` document nodes, `110,148` native lang nodes, and `1,652+1,095` SBL nodes; report memory/time. This is the actual schema-migration gate.
6. Exact PR-head CI, skeptical independent review of real provenance, parser crossings, full native graph integrity and SBL ordinal identity. Merge only if all green; keep #110 open and batch other tag families under #118.

## Definition of done for this bounded slice
- Zero silent loss of Mark 2 language occurrences in real native TF
- No new word slots / section hierarchy change / JSON XML blobs
- Exact-head CI real pinned Mark 2 green
- Logically independent adverse review and merge

## Follow-up real CI failure / RED gate (2026-10-11)
- Exact PR head ba6a2e773a514bc9726453bbe07be0374aac1c45: source census and real Mark tests passed, but GitHub Actions run 38132112506/job 114448411135 failed at full native TF writer/reload after 183 seconds with `full converter smoke failed: No module named 'tf'`.
- Root cause: `.github/workflows/issue69-full-verse-census.yml` upgraded its purely source-based audit into a full-conversion gate but omitted the project's declared `text-fabric==13.1.0` dependency. Other workflows install it, but independent jobs do not share Python packages.
- RED-first `tests/test_issue110_full_census_dependencies.py` requires pinned installation to precede the actual full converter command; fix the workflow alone, preserve exact-source sparse checkout and no corpus upload.
- Rerun exact-head census+native TF CI and check that 2,394,354 slots/2,628 physical documents/110,148 `lang` source nodes actually match independently measured corpus data. Merge only after independent adversarial review, including possible `main` merge conflicts.
