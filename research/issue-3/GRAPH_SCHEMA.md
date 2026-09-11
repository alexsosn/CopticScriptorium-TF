# Issue #3 — measured Text-Fabric graph schema ADR

Status: proposed for issue #3 final review

Pinned upstream: `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`

This ADR defines the intermediate graph contract that issue #11 may implement. It does not implement a converter or Text-Fabric writer.

## Evidence summary

The exact-head graph-shape audit measures 2,628 TT document streams containing:

- 2,394,354 normalized `norm` tokens;
- 1,565,993 `orig` segments;
- 1,105,458 `norm_group` nodes;
- 736,574 `orig_group` nodes;
- 78,993 sentence starts;
- 3,294 page, 3,291 column and 47,933 line markers;
- 13,015 token-internal layout crossings affecting 12,307 tokens, with 535 tokens crossed more than once and a maximum of seven crossings in one token;
- 256,677 entities, all non-empty and all source heads resolved, including 78,243 nested entities;
- 52,346 English translation nodes in 1,490 documents;
- 1,598 Arabic translation nodes in 96 documents.

Every document containing tokens has a source sentence start and no token occurs before the first sentence start.

The group hierarchy is not one universal four-step chain. All 736,574 `orig_group` nodes have exactly one `norm_group`; every `orig` has exactly one `norm`; but 368,884 `norm_group` nodes have no `orig_group`, `norm_group` may contain 0–11 `orig` nodes, and 828,361 `norm` tokens occur directly under `norm_group` rather than `orig`.

English translation has four measured zero-token textual loci. Arabic translation has one measured zero-token locus (`shenoute.night.BV278-282`, literal `بواسطة شنودة`). These are independently positioned textual annotations and cannot borrow a neighbouring word slot.

Chapter/verse/video markers are heterogeneous rather than universal navigation: chapter markers occur in 426 documents, verse markers in 2,571 and video markers in 206.

## ADR 1 — slot type

**Decision:** each TT `norm` is one semantic `word` slot.

Reasons:

- lemma, POS and source dependencies already live on `norm`;
- validated CoNLL-U aligns to this unit;
- entity heads target this unit;
- ordinary TF linguistic queries remain direct;
- character/source-piece slots would multiply slot count and move linguistic features to non-slot nodes;
- layout crossings can be represented losslessly without splitting a word slot.

A single source `norm` is never split into multiple semantic word slots solely because a page/column/line boundary crosses its rendered text.

The literal source-local `xml:id` remains a word feature for provenance/navigation inside the source document, but it is not a global TF node ID.

## ADR 2 — synthetic slots

Semantic and synthetic slots are distinct.

A textual annotation with a real word locus uses those word slots. An independently positioned textual annotation with zero word coverage receives exactly one surface-less synthetic slot placed in source order. The synthetic slot:

- has no source-word ID;
- has no fabricated visible Coptic surface;
- belongs to exactly one physical document;
- is not absorbed into a sentence node;
- exists only to preserve TF sequence position for the zero-span textual object.

This rule applies to both `translation` and `arabic_translation`. The pinned corpus currently requires five such loci in these two measured families: four English and one Arabic.

An empty literal translation that still has a real word locus does not receive a synthetic slot merely because its text feature is empty.

Non-textual graph objects may use a documented technical anchor only when serialization requires it. Such an anchor must render as `none` or the node's own text, never the neighbouring anchor slot's semantic text.

## ADR 3 — linguistic grouping nodes

Preserve the source distinctions as ordinary non-slot nodes:

- `orig_group`
- `norm_group`
- `orig`
- `word` (`norm`, slot)

The graph must preserve measured parent/containment relationships instead of synthesizing an invariant `orig_group -> norm_group -> orig -> norm` chain. In particular:

- standalone `norm_group` is valid;
- direct `norm` under `norm_group` is valid;
- a `norm_group` with zero `orig` children is valid;
- one `norm_group` may relate to multiple `orig` nodes.

Literal normalized and diplomatic/original strings remain separately reconstructable.

## ADR 4 — sentence nodes and sections

**Universal Text-Fabric section hierarchy:** `document` only.

Each physical source record from issue #2 becomes one `document` node with a unique section address derived from its deterministic `source_record_id`. Repeated scholarly CTS IDs remain ordinary features and never collapse document sections.

`sentence` is an ordinary node, not a universal section level. The corpus evidence nevertheless supports complete sentence partitioning of semantic word slots: every token stream has a first source sentence start and no token occurs before it. Every word slot must therefore belong to exactly one sentence node.

Sentence nodes may expose deterministic document-local ordinals/helper addresses, but `nodeFromSection()`-style universal navigation must not require sentence, chapter, verse or video semantics.

Chapter, verse and video/source-reference markers remain source features/nodes for corpus-specific queries.

## ADR 5 — layout representation

Page, column and line are ordinary layout nodes. Layout may intersect linguistic token content and therefore cannot be represented solely as conventional containment spans over whole word slots.

A layout node whose boundary falls inside a word must retain:

- the relevant word slot locus;
- exact token-relative character offset(s) for start/end boundaries;
- the literal source layout label;
- its own diplomatic text needed to reconstruct the layout span;
- `render_mode="own_text"`.

There are 13,015 measured token-internal boundary events, and some words contain multiple crossings. The materializer must preserve all events in source order. It must not duplicate, truncate or split the semantic word slot.

Default normalized word rendering must not acquire line/page whitespace merely because diplomatic layout exists. Diplomatic rendering is a separately named text format.

## ADR 6 — syntax

For each word slot:

- preserve literal TT `xml:id`;
- preserve TT `func` as the source dependency-relation feature;
- represent a non-root TT head as a `dependency_head` edge from word slot to word slot;
- represent root status explicitly through the source relation/root feature rather than fabricating a global root node.

CoNLL-U-derived normalized relations, heads, UD FEATS and construction/MISC enrichments remain separately named supplemental features/edges according to issue #1. They never overwrite TT source values.

## ADR 7 — entities

Each source entity becomes an ordinary `entity` node spanning its measured word slots. Preserve:

- source entity class;
- literal identity/Wikification value where present;
- source head-token reference;
- an `entity_head` edge from entity node to its head word slot.

The head must lie within the entity span. The pinned corpus contains no empty entity and no missing/unresolved entity head, but the materializer must fail closed if a later source revision violates those invariants.

Nested entities are allowed and common (78,243 measured cases); the representation must not assume entity spans form a flat partition.

## ADR 8 — translations

`translation` and `arabic_translation` are distinct textual annotation node types with literal own-text features and source loci.

If a translation covers words, its node is anchored by those word slots. If its measured token coverage is zero, it receives the synthetic-slot treatment in ADR 2. Translation literal text is never injected into the Coptic word-slot surface.

Node-specific rendering uses the translation's own literal text, not descendant/anchor Coptic text.

## ADR 9 — documents, union topology and overlap

The default materialization is one logical union corpus, inherited from issue #2.

Each `document` node preserves at minimum:

- `source_record_id` (physical source-copy identity and section address);
- corpus/dataset membership;
- literal `document_cts_urn` where usable;
- exact source provenance/revision;
- license and annotation-quality metadata according to issues #1/#8;
- issue-2 overlap/redundancy/witness classifications as non-destructive features/edges.

Corpus-specific access is a view/query over document features. No graph-layer deduplication removes treebank copies, alternate analyses, book-vs-aggregate records or witnesses.

For Context-Fabric/cfabric-mcp discovery, the minimal corpus-view surface is therefore document-level `corpus`, `dataset`, `source_record_id`, scholarly identity and overlap/redundancy features; it does not require duplicate TF artifacts per source corpus.

## Node/edge/feature matrix

| Graph object | TF role | Core source/features | Relations |
| --- | --- | --- | --- |
| `word` | semantic slot | `norm`, lemma, POS, literal TT `xml:id`, TT `func`, source provenance | `dependency_head` to word |
| synthetic slot | surface-less slot | source-order position, no source word/surface | anchors one independently positioned zero-span textual node |
| `document` | non-slot section node | `source_record_id`, corpus, dataset, CTS, metadata, quality, license/provenance | overlap/witness relations; spans all document slots |
| `sentence` | non-slot | document-local ordinal/source start | spans exactly its word slots |
| `orig` | non-slot | diplomatic/original literal | source grouping relation to word |
| `norm_group` | non-slot | literal group value/provenance | source group relations to `orig` and/or direct words |
| `orig_group` | non-slot | literal group value/provenance | source relation to `norm_group` |
| `page`/`column`/`line` | non-slot layout | label, diplomatic text, token-relative offsets | source-order/locus relation to words |
| `entity` | non-slot span | class, identity, literal head reference | `entity_head` to word; word-span locus |
| `translation` | non-slot textual | literal English text, source position | word locus or one synthetic slot when zero-span |
| `arabic_translation` | non-slot textual | literal Arabic text, source position | word locus or one synthetic slot when zero-span |

Writer finalization must assign every non-slot `otype` a TF-safe contiguous node-ID range. Literal upstream identifiers stay available as features even when technical IDs differ.

## Rendering contract

Named text formats must make semantics explicit:

- normalized/default word format: normalized Coptic word surface only;
- diplomatic/original formats: reconstruct source original/layout text using explicit original/layout information;
- layout node rendering: own diplomatic text when word-internal boundaries occur;
- translation rendering: own literal translation text;
- synthetic slots: render no visible surface;
- non-textual technical-anchor nodes: render no anchor text unless an explicitly named own-text format exists.

A successful TF `T.text()` call is not evidence of correct text. #11 must test normalized, diplomatic, layout and translation formats independently.

## Acceptance contract for issue #11

The production materializer must be RED-first tested against at least these invariants:

1. one TT `norm` produces exactly one semantic word slot;
2. every semantic word slot belongs to exactly one physical document and exactly one sentence;
3. repeated scholarly CTS IDs produce distinct document nodes/section addresses;
4. direct `norm_group -> norm`, standalone `norm_group`, multi-`orig` groups and ordinary `orig -> norm` are all preserved without invented hierarchy;
5. dependency and entity-head edges target semantic word slots and resolve only within the source document;
6. page/column/line crossings preserve exact token-relative positions without splitting or duplicating words;
7. multiple internal layout crossings in one word survive in source order;
8. nested entities remain separately queryable;
9. translation/Arabic translation text never becomes Coptic slot surface;
10. each zero-token English/Arabic translation gets a surface-less synthetic slot at its source position and cannot borrow a neighbouring word;
11. synthetic slots never belong to sentence nodes or expose fabricated visible text;
12. technical anchors cannot render unrelated anchor text;
13. universal section types remain document-only; chapter/verse/video remain optional source structures;
14. union-corpus materialization preserves all physical source records and issue-2 overlap/witness relations;
15. non-slot node types serialize in contiguous TF-safe ranges;
16. literal source IDs/provenance remain recoverable after write/reload;
17. normalized and diplomatic text reconstruction are independently checked against source material rather than against the converter's own intermediate representation.

Any later requirement that changes slot type, introduces a new zero-span textual family, or promotes another structure into universal sections requires a new measured research/TDD gate rather than an ad-hoc writer exception.
