# Issue #14 — research and implementation plan

Parent: #11. Dependencies: merged #13 parser/model, merged #3 graph ADR, issue #2 identity/overlap policy.

## Research gate

Broad corpus/schema research is closed by #1–#3. Reopen research only for a concrete source shape that the merged parser exposes but the reviewed graph ADR cannot represent.

Verify before implementation:

1. `DocumentModel` is the only semantic input; graph construction does not reread source files or write TF.
2. Every source `Word` becomes exactly one graph slot; no synthetic slots exist on the pinned revision.
3. Group/entity/translation containment follows parser ordinals and indices exactly.
4. Dependency and entity-head targets are document-local; invalid/outside-span targets fail closed.
5. Layout uses ordered events: inter-word positions come from `after_word_ordinal`; token-internal positions retain `word_ordinal` and `char_offset` without splitting slots.
6. Physical records stay distinct even with repeated scholarly IDs. Cross-document overlap/witness relations are explicit inputs, not deduplication.
7. IDs are deterministic: globally contiguous word slots first, then one contiguous range per non-slot `otype` in fixed order.
8. Output is writer-neutral so #15 can serialize it without recomputing semantics.

## RED-first implementation plan

Add focused tests before production graph code for one-word/one-slot cardinality, exact document/sentence membership, repeated CTS identity, source grouping shapes, dependency/entity locality, nested entities, English/Arabic translation loci and own text, ordered layout crossings, deterministic IDs/ranges, zero-word textual rejection, and explicit overlap/witness edges.

Then create `copticscriptorium_tf.graph` with immutable slot/node/edge/result records and `build_graph()`. Build in two passes: assign deterministic word slots/document-local lookup tables, then materialize non-slot nodes and resolve edges. Add an independent `validate_graph()` that rechecks construction invariants before return.

## Pinned-source gate

Add an issue-14 workflow that runs focused tests, checks out `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`, parses the complete TT corpus, builds the graph twice, checks deterministic counts/digest, verifies exactly 2,394,354 word slots, zero synthetic slots, no validation errors, and contiguous non-slot ranges, and uploads only a compact graph census artifact.

## Review gate

After exact-head CI is green, perform a logically independent adversarial review against #14 and the #3 ADR, explicitly trying to falsify locality, containment, deterministic-ID, layout-boundary, and zero-span assumptions. Any code-changing fix restarts exact-head CI and review.

## Non-goals

TF serialization/text formats, Agora integration, publication/release certification, speculative synthetic slots, physical-record deduplication, or reopening settled source-authority decisions.
