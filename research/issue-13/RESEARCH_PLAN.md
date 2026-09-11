# Issue #13 — deterministic source parser and TF-independent model

Pinned upstream: `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`

Settled inputs: source authority #1, identity/overlap #2, graph schema #3 / merged PR #12.

## Goal

Implement the smallest deterministic production source layer that reads the supported Coptic Scriptorium inputs and preserves their reviewed semantics in a Text-Fabric-independent intermediate model. This ticket does not assign TF node IDs and does not write TF files.

## Package boundary

Create a small `copticscriptorium_tf` package with three explicit responsibilities:

1. `sources` — deterministic discovery/read of direct and archive-packaged supported records with strict UTF-8 and immutable provenance;
2. `model` — plain dataclasses/value objects describing one physical document, words/groups/original segments, sentences, layout boundary events, entities, translations, metadata, provenance, and source exceptions;
3. `parser` — event-driven TT parser plus separately invoked validated CoNLL-U supplementation.

TT parsing must not depend on Text-Fabric. The normalized model must be serializable/comparable in tests without TF installed.

## Canonical TT parse contract

TT is overlapping SGML rather than XML. Parse it as ordered source events with independent state for linguistic groups, current word, entities/translations and layout.

For every physical TT record preserve:

- `source_record_id`, corpus/dataset, literal record name, direct/archive source path, raw SHA-256 and pinned upstream revision;
- literal metadata values without inventing missing fields; duplicate/conflicting metadata remains explicit source evidence;
- `orig_group`, `norm_group`, `orig`, and `norm` objects and their measured source relationships without forcing a four-level tree;
- every `norm` in source order as one model word, with literal `xml:id`, norm/lemma/POS/func/head evidence;
- source sentences from `new_sent=true`; no synthetic sentence start;
- dependency heads resolved in a second pass against document-local source IDs; unresolved/cross-document targets are explicit failures;
- entity class/identity/head plus ordered word locus. When an entity opens inside an already-open `norm`, that current word belongs to its locus before later word starts are counted. On the pinned corpus the resolved head must lie inside this corrected locus;
- English and Arabic translations as own-text annotations plus ordered word locus. A translation opening inside an already-open `norm` inherits that current word;
- page/column/line boundary events in source order, including token-relative character offsets when a boundary occurs inside an open word; words are never split by layout;
- exact literal source values needed for later rendering/provenance.

A genuinely zero-word textual locus or valid entity head outside the corrected entity locus is not part of the reviewed pinned schema. Surface it explicitly and block graph construction pending a focused schema gate.

## Source discovery and failures

Supported TT packaging is exactly the measured #1 contract: direct `corpus/dataset_TT/*.tt` and dataset `*_TT.zip` archive members. Unsupported archive layouts fail closed.

All source text decodes strict UTF-8. Malformed syntax, duplicate local token IDs, unresolved dependency/entity targets, impossible group closes/opens, and unsupported measured-shape violations are not silently repaired.

Whitespace/empty records and known malformed supplemental CoNLL-U inputs remain explicit ledger/failure results according to #1 rather than becoming empty successful documents.

Deterministic ordering is by physical source identity, never filesystem enumeration order.

## CoNLL-U supplementation boundary

CoNLL-U is supplementary, not a second canonical parser. Reuse the reviewed #1 structural validation/packaging semantics rather than inventing a new relaxed parser.

For a structurally valid matching document, supplementation may attach only the reviewed CoNLL-U-derived fields (UD FEATS, construction/MISC enrichment, normalized dependency relation/head where explicitly named separately). It must:

- require identity/token cardinality alignment;
- preserve TT source values separately;
- never overwrite TT `func`/head/lemma/POS silently;
- classify placeholders and structurally invalid files as non-supplementing source exceptions;
- fail closed on ambiguous identity or token alignment.

Implementation can initially expose supplementation as a separate function over a parsed TT document plus validated CoNLL-U record; graph construction decides later which supplemental fields become graph features.

## Intermediate model invariants

The model must make the following independently testable before TF exists:

- one model word per source `norm`, in exact source order;
- every word belongs to one physical document and one source-derived sentence;
- source-local IDs remain literal and resolved relations use model word ordinals/references, not future TF IDs;
- grouping relations are explicit and preserve direct `norm_group -> norm`, no-`orig`, and multi-`orig` shapes;
- layout events preserve kind/value/source order/current-word locus/character offset;
- entity and translation loci inherit an already-open current word correctly;
- normalized and diplomatic/original values remain separately reconstructable;
- provenance and literal metadata survive round-trip through the model;
- no field in the model is a TF node number.

## RED-first test plan

Before implementation, tests must cover at least:

1. ordinary `orig_group -> norm_group -> orig -> norm` with metadata and dependency root/head;
2. direct `norm_group -> norm`, no-`orig`, and multi-`orig` group shapes;
3. sentence start/partition and unresolved dependency target;
4. one and multiple page/column/line boundaries inside an open `norm`, with exact token-relative offsets and no word split;
5. nested entities and entity opening inside current `norm`; resolved head must be in corrected locus; unresolved/outside-locus head fails explicitly;
6. English and Arabic translation before a word and inside a current word, preserving own text and loci;
7. missing optional metadata without fabricated values; duplicate/conflicting metadata evidence preserved;
8. direct and archive TT packaging, strict UTF-8, unsupported archive layout, deterministic ordering and provenance hash/path;
9. CoNLL-U valid supplement vs placeholder/malformed/token-drift inputs, with TT values not overwritten;
10. deterministic model serialization/comparison and proof that model contains no TF IDs.

## Corpus gate

After focused GREEN tests, add an exact-head pinned workflow that parses all 2,628 TT physical records and emits a machine-readable parser report. At minimum compare parser counts with reviewed #3 evidence:

- 2,628 documents;
- 2,394,354 words / TT `norm` tokens;
- source sentence coverage;
- 13,015 token-internal layout crossings;
- 256,677 entities with zero unresolved/outside-corrected-span heads;
- 52,346 English and 1,598 Arabic translations with zero zero-word loci;
- deterministic source ordering and provenance coverage.

The parser corpus gate must not derive its expected totals from the parser output itself.

## Exit gate

Focused RED→GREEN history → full relevant tests → exact-head pinned parser census → logically independent adversarial review of issue #13 + exact diff + generated report. Any code-changing review fix invalidates that review.
