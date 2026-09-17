# Issue #15 — research and implementation plan

Status: implementation in progress on PR #27. Finalization still requires RED-first native-TF regression tests, exact-head CI, and a logically independent adversarial review.

## Product boundary

This ticket builds a reliable Coptic Scriptorium TT → native Text-Fabric writer. The project owns converter correctness and usability; it does **not** certify the scholarly correctness, completeness, licensing, or corpus design of upstream Coptic Scriptorium data.

- Base: merged #14 graph (PR #25, squash `123dfab86e9d31f0d9a3a2853a154fcc86d6bd44`).
- Reproducible real-source regression fixture: `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`.
- The pinned revision is a stable test input, not a certification target.
- Output is user-local TF. No generated corpus artifacts are committed here.
- Agora acquisition is #17; end-to-end full-corpus regression/resource smoke testing is #16; memory optimization is #26.

## Text-Fabric API contract

`text-fabric==13.1.0` is the supported CI version for this ticket.

Use `tf.core.fabric.Fabric.save` with:
- `nodeFeatures`: scalar `str|int` values;
- `edgeFeatures`: unvalued target sets or valued scalar target maps;
- `metaData`: feature metadata plus `otext` configuration.

Preserve #14 IDs: all word slots first, then non-slot nodes, with `oslots` mapping every non-slot node to its measured word locus. Use ordinary TF primitives; do not invent a secondary serialized data model inside feature values.

## Native-TF projection rules

1. **No structured blobs in semantic features.** No `*_json`, JSON object/array strings, raw TT/XML document blobs, or JSON-valued relation evidence.
2. `otype` / `oslots` are the structural backbone. Every graph word remains exactly one TF slot; no synthetic slots are introduced.
3. Source scalar fields become ordinary typed node features.
4. Document metadata becomes deterministic native scalar features. Feature-name normalization must be transparent, TF-safe, deterministic, and collision-checked. Repeated metadata values must remain lossless without JSON containers.
5. Structural relationships become native edge features. In particular, direct word membership is an edge, not a serialized list.
6. Document-relation evidence is split into ordinary valued edge features as needed (`classification`, `family`, witness literal, target scholarly identity) rather than packed into JSON.
7. `section_address` is not serialized as a list: the document section is represented by `otext.sectionTypes=document` and `sectionFeatures=source_record_id`.
8. Normalized, diplomatic/original, translation, Arabic translation, and layout rendering remain distinct and use TF text formats / own-text features.
9. Literal upstream strings may contain markup-like text (for example an HTML link in metadata). Preserving such a source literal is allowed; generating a serialized XML/JSON container is not.
10. Save atomically and fail before publishing a partial final dataset.

## Repeated metadata representation

TF node features are scalar. For repeated metadata attributes, use deterministic occurrence feature names rather than a container value:
- first/effective value: `meta_<key>`;
- repeated source occurrences: `meta_<key>__2`, `meta_<key>__3`, ... in source order.

The feature-name encoder must reject collisions after normalization instead of silently merging distinct source keys. This keeps the representation native, lossless, simple, and directly inspectable without adding a new metadata-node graph layer.

## RED-first regression gate for the native-TF refactor

Before removing the existing blob representation, tests must require:

- no generated semantic feature name ends in `_json`;
- no writer-generated node/edge value is a JSON object/array container;
- document metadata is available as native `meta_*` scalar features, including repeated occurrences;
- metadata-name collisions fail explicitly;
- direct group→word membership is queryable as an unvalued edge feature;
- `documented_overlap` evidence is available through separate native valued edge features;
- `witness` relation, witness literal, and target scholarly identity are separately queryable native edge features;
- no `section_address_json` feature exists; section lookup still works;
- save/reload with real TF preserves slots, text formats, dependency/entity edges, document relations, and deterministic output bytes.

Commit the tests first and observe failure against the current blob-based writer. Then implement the smallest projection change that satisfies them.

## CI policy

Focused #15 CI installs real Text-Fabric and runs the writer tests plus a bounded real-source save/reload regression.

The repository-wide unit-test job must install dependencies needed by tests it discovers. Historical corpus-research audit jobs are not a release gate for converter changes; broad upstream certification work should not block #15.

## Finalization gate

Research/plan update → RED native-TF regression commit → implementation → exact-head focused + repository tests → bounded real-source regression → logically independent adversarial review of the final exact head → merge #15.

The adversarial review must specifically challenge metadata feature-name collisions, repeated metadata loss, relation-evidence loss, accidental JSON/XML container reintroduction, TF reload behavior, and deterministic serialization.
