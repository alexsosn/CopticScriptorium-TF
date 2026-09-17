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

## R1 result — parser record slots
The RED representation contract proved all eleven immutable source-model record classes allocated normal instance dictionaries. They were changed mechanically to `@dataclass(frozen=True, slots=True)` with no field or parser changes.

Exact-head full-source run `cf91c103fb1ea6e1a9cd949a99f1e899ed96cfb4`:
- all converter/reload invariants passed with the same 2,628 documents, 2,394,354 slots, 3,854,785 nodes, 2,505,872 edges, 130 TF files and 618,769,322 output bytes;
- parse ~94.2 s, graph ~67.6 s, write ~104.4 s, reload ~176.2 s;
- peak RSS **11,009.4 MiB** (`/usr/bin/time`: 11,273,604 KiB).

Delta from baseline: only about **66.4 MiB / 0.6%**. Keep the low-risk representation improvement, but R1 is not the dominant end-to-end peak and does not approach the <8 GiB target.

## Research questions, in order

### R1 — parser model object overhead — measured, insufficient
Completed above. No further parser-record representation work is justified before larger measured peaks are addressed.

### R2 — parser → graph lifetime overlap
The public converter currently holds the complete parser model through `build_graph()`, and only deletes it after the complete graph exists. This may matter for the graph-phase peak, but the end-to-end high-water remains ~11 GiB after R1, so it is not the next target unless writer work fails to reduce the dominant peak.

Do not stream prematurely: relation derivation currently needs corpus-wide document identity/metadata. First separate small document-level relation evidence from large word/group payloads only if later measurements justify it.

### R3 — writer projection duplication — next slice
`writer._project()` currently materializes every node feature and every edge feature at once, including millions of `otype` entries and millions of per-node `oslots` target sets, while the complete `Graph` remains live. Only after this monolithic projection exists does `Fabric.save()` begin serializing features.

Pinned Text-Fabric 13.1.0 source review (`annotation/text-fabric@v13.1.0`) shows:
- `Fabric.save()` accepts dictionaries of node/edge features and serializes each feature independently through `Data.save()`;
- each `Data.save()` writes its supplied feature data directly; Text-Fabric does not first clone the entire node/edge feature collection into another all-features representation;
- therefore our simultaneous all-feature `_project()` is avoidable retention;
- repeated `Fabric.save()` calls can preserve the same staging directory and atomic final publication while allowing completed feature batches to be released before projecting the next one.

Next hypothesis: **incremental native-TF projection/save materially reduces peak RSS by preventing `Graph + all projected features` from coexisting.**

Planned gate:
- RED memory-shape contract requires the writer to expose bounded feature batches instead of one monolithic projection/save call;
- keep `otype` + `oslots` together as the warp batch so Text-Fabric performs its normal warp validation;
- project remaining node/edge features in small independent batches and save them immediately;
- preserve ordinary documented Text-Fabric input shapes (node dicts; edge dicts of sets/dicts), avoiding undocumented tuple tricks;
- preserve the existing staging-directory atomicity: any failed batch leaves no final destination;
- preserve deterministic bytes, feature inventory, metadata headers, otext formats, and clean reload semantics;
- rerun the same full-source measurement before considering R2 or more invasive serialization changes.

### R4 — Text-Fabric save/reload high water
If R3 does not get below the practical envelope, measure `Fabric.save()` and clean `Fabric.load()` more deeply. Note that the #16 converter-reported peak is captured before the separate smoke-test reload, and it already matches the whole-process high-water closely; clean reload is therefore not the observed ~11 GiB peak driver.

Do not redesign around undocumented Text-Fabric internals without evidence.

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
