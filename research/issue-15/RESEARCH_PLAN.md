# Issue #15 — research and implementation plan

Status: research/plan gate; implementation and merge are NOT authorized until RED tests and a real TF environment are in place.

## Inputs and scope

- Base: merged #14 graph (PR #25, squash `123dfab86e9d31f0d9a3a2853a154fcc86d6bd44`); follow merged #3 graph/rendering ADR and #2 identity policy.
- Exact source corpus for integration: `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`.
- Measured #14 graph: 2,394,354 word slots, 3,854,785 non-slot nodes, 2,505,872 edges; process `ru_maxrss` 6491.2 MiB before writing. Track writer memory in #26; this high-water mark is not graph-only retained size.
- Output is a user-local TF corpus; no generated data committed to this repository and no Agora acquisition in this ticket.

## External API research, checked 2026-09-16

PyPI `text-fabric` currently lists 13.1.0 (2026-01-15) as current stable release; pin exactly 13.1.0 for CI/reproducible writer tests until deliberately updated. [PyPI](https://pypi.org/project/text-fabric/).

Official [`tf.core.fabric.Fabric.save`](https://annotation.github.io/text-fabric/tf/core/fabric.html) takes `nodeFeatures` (feature -> {node_id: str|int}), `edgeFeatures` (feature -> {source_id: set(target_ids) or {target_id: str|int}}) and `metaData` (feature metadata). Metadata needs correct `valueType` for int features and `edgeValues=True` for valued edges. `otext` is a *metadata-only* feature and must not appear in nodeFeatures/edgeFeatures. Crucial: TF validates `otype`/`oslots`: non-slot nodes must appear in oslots, and `otype` must establish one contiguous initial slot type.

Official [TF datamodel](https://annotation.github.io/text-fabric/tf/about/datamodel.html): IDs are consecutive with all slots first; non-slot oslots map to their word slots. Preserve #14 global IDs without implicit renumbering. Use `Fabric.save` for this fixed-graph projection, not `CV.walk` unless tests prove identical IDs/relations.

Official [Text API](https://annotation.github.io/text-fabric/tf/core/text.html): `otext` specifies `sectionTypes` and matching `sectionFeatures`; only `document` is universal. Formats can target node types with `type#` and default per-type formats (`translation-default`, `arabic_translation-default`, layout-defaults) can prevent T.text(node) from silently rendering its Coptic anchor slots. An explicit normalized document format should descend to word slots. Do not assume `T.text()` success proves diplomatic correctness.

## Source-to-TF projection and required research checks

1. Inspect all Graph/GraphSlot/GraphNode/GraphEdge fields and design a **named, typed feature matrix**, preserving literal source fields, provenance, metadata duplicates and document relations without reserved-name collisions. Store structured variable-length metadata in deterministic JSON string features where TF scalar values cannot represent it; document exact decoding. Do not overwrite TT features with CoNLL-U supplements.
2. `otype`: exactly one `word` slot for every graph slot, followed by graph node `otype` as-is. `oslots`: graph non-slot `slot_ranges` -> sorted set of IDs; do not silently borrow neighbouring slots for an empty source locus. **Research gate:** measure zero-slot nodes by type over pinned graph *before* assuming TF can save them; if a valid zero-locus object exists, reopen focused schema research rather than fabricated anchors.
3. Separate valueless directed edge features `dependency_head`, `entity_head`, `same_scholarly`, `documented_overlap`, `witness`; edge classification/family/literal evidence needs a documented lossless representation (valued edge or parallel scalar features) and reload tests. Verify duplicate physical target semantics, not just counts.
4. `otext`: `sectionTypes=document`, `sectionFeatures=source_record_id`; ensure literal source IDs and repeated scholarly CTS values do not collide in `nodeFromSection()`.
5. Format contract: default normalized Coptic uses `norm` from word slots; English/Arabic translation and layout nodes render **own text** using type-specific defaults and explicitly targeted formats. Diplomatic/original output must be compared with independent TT `orig`/word source evidence, including direct norm-group words, multiple orig siblings and token-internal crossings; do not present a slot-only approximation as source parity.
6. Preserve exact upstream revision, record path, raw source digest, metadata/quality/license *evidence*; do not invent a blanket corpus license.
7. Runtime: avoid eager duplicate dictionaries/sets for all ~6.25m nodes if unnecessary; measure peak RSS, runtime and generated output. Issue #26 covers memory improvements; #16 owns independent full-corpus source parity.

## TDD gate (RED before writer code)

Create focused fixture tests using real `text-fabric==13.1.0`, `tempfile.TemporaryDirectory`, and `Fabric(locations=...).load(...)` (verify supported constructor/arguments in CI) that assert:

- saved `otype`/`oslots` exists and reloads, one source norm per slot, no synthetic slots, full document/sentence ownership;
- duplicate scholarly identity with distinct physical source IDs round-trips through `T.nodeFromSection((literal_source_record_id,))`;
- all node types and scalar features/metadata survive, including missing vs empty values and metadata duplicates;
- dependency/entity head and overlap/witness edge directions/values survive, including corrected entity span;
- `T.text(document, fmt=normalized)` excludes layout and translation own text; `T.text(translation)` and `T.text(arabic_translation)` return own literal text; `T.text(layout)` returns layout own text, not Coptic anchor text;
- diplomatic format for direct words/multi-orig/layout crossing has source-checked expected output independent of intermediate graph helper;
- malformed/empty loci fail explicitly if unsupported, and saving must not leave a misleading partially successful final output;
- independent builds produce deterministic `.tf` bytes/feature names and successful fresh-process reload.

Commit failing tests in a separate RED commit, with CI showing the expected failure because the writer entry point is absent. Only then implement a minimal writer, run focused+relevant suite, pinned real-source slice, and exact-head independent adversarial review. Full graph source-independent parity remains #16.

## Gate ordering

Research → this committed plan → RED test commit and observed failure → production implementation → real TF integration and slice CI → independent adversarial exact-head review → merge #15; any code-changing commit restarts CI/review.
