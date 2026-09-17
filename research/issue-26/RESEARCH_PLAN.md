# Issue #26 research plan — reduce full-corpus converter peak memory

## Goal
Reduce complete supported-source conversion peak RSS from the exact #16 baseline (~11,075.7 MiB) to a practical local envelope without changing converter semantics.

This work optimizes the converter. It does not certify, reinterpret, deduplicate, or selectively rewrite upstream data.

## Exact baseline
Pinned upstream: `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`.

PR #28 exact-head full conversion/reload:
- source records: 2,628
- word slots: 2,394,354
- non-slot nodes: 3,854,785
- graph edges: 2,505,872
- TF output: 130 files / 618,769,322 bytes
- parse: ~93.1 s
- graph: ~68.6 s
- write: ~103.9 s
- clean reload: ~173.0 s
- process peak RSS: **11,075.7 MiB** (`/usr/bin/time`: 11,341,560 KiB)

Earlier parser+graph census peaked around 6.5 GiB, so TF projection/save/reload adds substantial high-water memory beyond graph construction.

## Research questions, in order

### R1 — parser model object overhead
`model.py` uses frozen dataclasses without `slots=True`, while graph records already use slotted dataclasses. The full parser model contains millions of `Word`, `Orig`, `NormGroup`, `OrigGroup`, `Sentence`, `LayoutEvent`, `Entity`, and `Translation` instances. Measure a minimal representation-only change first.

Hypothesis: adding `slots=True` to immutable source-model dataclasses materially reduces parse/graph overlap with no semantic changes.

Gate:
- RED contract proves high-cardinality source-model records currently expose per-instance `__dict__`;
- implementation adds slots only, no field/order/type changes;
- all parser/graph/writer/converter tests stay green;
- full-source exact-input run measures new peak RSS before any larger change.

### R2 — parser → graph lifetime overlap
The public converter currently holds the complete parser model through `build_graph()`, and only deletes it after the complete graph exists. Determine whether graph construction can release document-local source structures earlier without changing deterministic ordering/relations.

Do not stream prematurely: relation derivation currently needs corpus-wide document identity/metadata. First separate small document-level relation evidence from large word/group payloads if measurements justify it.

### R3 — writer projection duplication
`writer._project()` materializes full `node_features` and `edge_features` dict/set structures in addition to the complete graph before `Fabric.save()`.

Measure whether this is the dominant post-graph increase. Look for simple reductions first:
- avoid redundant temporary sets/lists where TF accepts equivalent structures;
- release graph components no longer needed before save if safe;
- avoid simultaneous duplicate representations of slot loci / feature values.

### R4 — Text-Fabric save/reload high water
If R1–R3 do not get below the practical envelope, measure `Fabric.save()` and clean `Fabric.load()` separately. Do not redesign the converter around undocumented TF internals without evidence.

The #16 regression can keep reload as an integration gate even if ordinary conversion itself does not reload output.

## TDD and measurement discipline
For each implementation slice:
1. record the narrow hypothesis;
2. add a RED regression/representation contract before production change;
3. make the smallest production change;
4. run focused + repository exact-head tests;
5. run the same pinned full-source conversion measurement;
6. compare semantics/output and peak RSS with the baseline;
7. conduct a logically independent adversarial review before finalizing the PR.

## Acceptance target
Initial practical target: **<8 GiB peak RSS** on the same GitHub runner/pinned input, with lower preferred if reachable through simple representation/lifetime changes.

A change is only useful if it preserves:
- word-slot cardinality and source ordering;
- native TF node/edge/text semantics;
- deterministic fixture output bytes;
- clean TF reload and representative queries;
- direct + archive-packaged TT support;
- no hidden structural JSON/XML containers;
- no synthetic slots.

## Explicit non-goals
- corpus correctness/certification;
- independent semantic re-audit;
- changing document identity policy to save memory;
- selective materialization before measurements require it;
- caching/release/provenance frameworks;
- optimizing historical research census workflows inside this ticket (#10 owns CI cleanup).
