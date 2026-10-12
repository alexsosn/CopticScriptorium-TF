# Issue #159 — nine source entity/name-label wrapper families (8,827 events)

## Research (2026-10-12; exact current `main` and original TT)

The immutable upstream `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5` is already censused in `research/issue-118/tag_matrix.csv`. Nine source wrapper types remain missing as **independent queryable provenance**, even when `entity` itself exists:

| tag | opening count |
|---|---:|
| entity_head_tok | 3677 |
| entity_text | 3677 |
| entity_identity | 901 |
| persName_type | 245 |
| placeName_type | 140 |
| placeName_ref | 85 |
| roleName_type | 80 |
| rs_type | 18 |
| org_type | 4 |
| **total** | **8827** |

Real `life-aphou/life.aphou_TT/life.aphou.01.tt` has `persName_type="monk"` inside `norm`; `roleName_type="religious"` spanning grouping markup; `placeName_ref="paths:places:32"` crossed with `placeName_type="city_village"` inside a `norm`, and `org_type="ethnic"` inside an `entity`. `abraham/shenoute.abraham_TT/YA525-530.tt` uses `entity_identity="Sarah"` inside `lang="Hebrew"` and `norm`. `john.constantinople` has `entity_head_tok` and `entity_text` wrappers separately from `entity` attributes. An external paths reference is a literal, **not** a validated ontology mapping.

Parser currently uses opening-order `SblAnnotation` (one source literal plus exact start/end word/char positions) for SBL, language, token, edition, multiword, reference and editorial families. Independent per-tag stacks support interleaved/crossed closing tags; graph projects one native node per original wrapper without adding TF slots. Retain this consistent architecture: a new **single entity-label family**, not nine bespoke algorithms. DO NOT infer `entity` parent, identity equality, dereferenced ontology resource, Greek lemma or Coptic↔LXX correspondence.

## Research → RED plan → implement → tests → independent review

1. RED-first, structurally strict synthetic TT sources covering nine label kinds, token-internal values, crossed independent closes, case-sensitive exact source literals, nesting, adjacent/multiword spans, missing value/unclosed/orphan closes and two distinct overlapping `entity` mentions. Assert `DocumentModel.entity_label_annotations` retains all events in original opening order.
2. Add `ENTITY_LABEL_WRAPPER_TYPES` and one `entity_label_annotations` track. Parser records exact source value and positions using existing shared event stacks. Graph projects native non-slot `otype=<source tag>` and `render_mode=entity_label_span|entity_label_anchor` with correct slots and offsets. Adapt graph validation. No inferred `E.entity_*` links. No new TF word slots. Existing optional defaults remain compatible.
3. Writer uses existing `value`, `source_record_id`, `source_ordinal`, `start_word_ordinal/start_char/end_word_ordinal/end_char`, `render_mode` node-feature projection; verify actual native TF reload.
4. Real pinned witness sample (life-aphou, abraham; john-constantinople where available) and **complete pinned 2,628-record direct+ZIP audit**. Independently scan TT source opening counts vs newly parsed `entity_label_annotations`; assert exactly **8,827**, per-tag counts and 2,394,354 unchanged word slots for full conversion if feasible. Fail if source-loss or bad positions. No raw data artifacts or unauthorised text distribution. Reuse existing pinned checkout and full test infrastructure where possible.
5. Independent, skeptical review of **exact PR head** and genuine source/CI evidence; adversarially challenge false entity association, escaped values, crossed source spans, missing values, zero-locus, collisions and memory. Merge only all applicable CI green. Keep #118 open until other wrapper batches complete.

## Acceptance

- Native queryable TF nodes for all nine source wrapper kinds, original labels, exact boundaries, source-record provenance
- Actual source coverage reconciles to 8,827 source tag openings; all 2,628 source records parse and no word-slot changes
- No sidecars/blob features, synthetic word creation or unsupported ontology identification
- Exact-head CI + independent adversarial review + squash merge


## Rebase research / adversarial integration correction (2026-10-12)
- Issue #156's separately reviewed PR #157 was **already merged** at `f71886e12d86...` while this label work developed; it owns 4,647 original `gap/supplied/abbr` events, their independently typed native TF nodes and original source-attribute provenance. Its dispatch/import/validation edits overlap this branch textually, though the data are separate.
- The previous #160 real pinned source audit failed **not on the 8,827 labels** but because the three selected raw example documents include witness CTS references outside that three-document sample. The production full-corpus witness relation derivation must **remain fail-closed**; the isolated label-node smoke explicitly builds with `document_relations=()`, testing precisely source shape and native warp.
- This branch was recreated from the post-#157, post-#147 main and **three-way merged per source line**: both wrapper-family registrations, both parser opening/closing occurrence stacks, both document model fields, both graph node render states, both graph validations, existing intervention source-attribute projection, and all original tests. Old branch was not overwritten.
- Independent new RED tests reject forged kinds in `entity_label_annotations` on the source model and require an original `gap reason="lost"` and source `entity_identity="Sarah"` **within the same Coptic norm token** to survive native TF reload simultaneously. This surfaced the need to register entity-label instances in `_check_document`'s source-annotation validation loop as well as the graph's node validator.
- Full immutable 565-file / 2,628-record source scan is required to recheck exactly 8,827 labels and unchanged 2,394,354 word slots, plus the full streamed bilateral Coptic-LXX TF module gate that necessarily reruns on a changed warp. Do not merge on synthetic checks alone. Independently review source-attribute provenance and positional label integrity after CI.
