# Issue #187 — exact original entity.text TT source attribute

## Primary research and bounds
- Original pinned `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5` physical `doc-papyri/doc.papyri_TT/cpr.31.14.tt`: exactly **12 <entity> openings**, each with original keys `head_tok;text;entity` (independent direct source check, 2026-10-20). Do not log/copy Coptic original values.
- `parser.py` discards the `text` key when processing a core `<entity>` opening but preserves `head_tok`, entity class/identity and word locus. `Entity` internal dataclass has no source-literal field; core `GraphNode` already has native `source_attributes` and the TF writer already supports sparse original attribute features for `gap/supplied/abbr`.
- The existing native `<entity_text>` positional source annotation type is separate from an attribute on core `<entity>`. Do not add a fake node/slot or infer equivalence with normalized Coptic text.

## Research → RED → implement → actual original TF → independent adversarial review
1. RED-first parser/graph/native Fabric tests for an original `entity.text` attribute with HTML entities, an explicitly empty original attribute, and absent attribute. The original attribute must round-trip as source evidence without modifying text rendering, entity head/class/locus, original node IDs or Coptic word slots. Assert standalone `<entity_text>` retains distinct native kind.
2. Implement optional `Entity.source_text_literal` (None absent, empty string present) and propagate to **only** `entity` core GraphNode `source_attributes` with key `text`. Add `source_attr_entity_text` using existing native writer source-attribute feature mechanism; do not serialize opaque original XML/JSON. Reject forged keys in graph validation.
3. Pin `doc-papyri/doc.papyri_TT/cpr.31.14.tt` independently in the *existing* immutable sparse TT full corpus workflow: raw regex/attr scan checks 12 original `entity.text` values and opening order; parser must match decoded originals; after complete native TF build/reload independently compare `source_attr_entity_text`, preserved source SHA and exact `entity`/word loci. Keep copyrighted literals out of log.
4. Exact-head research tests and full 2,628 physical TT records / 2,394,354 slots native TF reload; unchanged lang, SBL, Horner, LXX candidates and CoNLL-U. Record peak RSS/disk.
5. Separate logically independent adversarial review on primary source/parity and edge cases before merging. Keep broader #184 open for `morph.lang` / core attribute issues even if this scoped repair passes.

This is user-facing provenance detail inside researcher-queryable native TF, not a new code framework. No new materializer or bulk semantic inference.
