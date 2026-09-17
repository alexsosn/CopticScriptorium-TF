# Issue #16 — end-to-end converter regression and resource smoke plan

Status: research complete enough to begin RED-first implementation.

## Product boundary

Issue #16 proves that the **converter** works end to end on supported Coptic Scriptorium TT input. It does not independently certify Coptic Scriptorium annotations, metadata, licenses, scholarly identities, or corpus completeness.

A pinned upstream revision is only a reproducible large regression fixture.

## Current implementation inventory

The required stages already exist and have their own reviewed contracts:

1. `parse_source_tree(root, upstream_repository=..., upstream_commit=...)`
   - discovers supported direct `*_TT/*.tt` and `*_TT.zip` packages;
   - parses them deterministically into `DocumentModel` objects;
   - fails explicitly on unsupported package/member layouts.
2. `build_graph(documents)`
   - derives reviewed document relations by default;
   - builds and validates the deterministic TF-independent graph.
3. `write_graph(graph, destination)`
   - writes ordinary native Text-Fabric atomically;
   - uses native node/edge features, not JSON/XML structural blobs;
   - reload behavior is covered by #15.

There is currently **no single supported public conversion orchestration** and no direct converter CLI/module. `copticscriptorium_tf.__init__` still exports only parser/model APIs. Existing full-corpus research scripts manually chain stages.

## Measured resource constraint

Issue #26 records about 6.5 GiB peak RSS for the full pinned parse + graph path before TF writing. The old issue-14 census also builds the graph twice to prove reversed-input determinism and hard-codes historical corpus counts/classification totals.

Do not copy that machinery into #16. The #16 smoke path must:
- parse once;
- build one graph;
- write once;
- release no intentionally duplicated graph copy;
- cleanly reload the generated TF;
- measure wall time, high-water RSS and output size.

If a clean full run exceeds a practical runner/local memory envelope, record the measured converter failure and promote #26; do not reinterpret an OOM/resource failure as an upstream-data defect.

## Proposed thin converter API

Add `copticscriptorium_tf.converter` with a small orchestration API, initially:

```python
convert_source_tree(
    source_root,
    destination,
    *,
    upstream_repository,
    upstream_commit,
) -> ConversionResult
```

The orchestration should:
- reject/preserve an existing destination according to `write_graph`'s fail-closed contract;
- call the existing parser, graph builder and writer rather than duplicating their logic;
- return operational summary data useful to CLI/Agora integration (source records, slots/nodes/edges, phase timings, peak RSS, output path/size);
- not emit a certification report or encode historical expected corpus totals.

Expose a minimal module CLI through `python -m copticscriptorium_tf.converter` rather than adding packaging machinery in this ticket. A later packaging decision can add a console-script wrapper without changing converter semantics.

## RED-first gates

Before implementation, add tests that require the missing orchestration behavior:

1. **End-to-end fixture**
   - source tree with both direct and ZIP TT packages;
   - call one converter API;
   - native TF output exists and reloads with real `text-fabric==13.1.0`;
   - source document/slot counts equal the parser/graph result for that same fixture;
   - representative text, metadata, dependency/entity and translation access survives;
   - output contains no `*_json.tf` semantic features.

2. **Fail closed**
   - unsupported input shape raises an actionable converter error;
   - existing output destination is not overwritten;
   - failed conversion does not publish a misleading final TF directory.

3. **Operational summary**
   - reports counts and phase/resource measurements produced by this run;
   - contains no hard-coded expected upstream census or certification verdict.

4. **CLI smoke**
   - module CLI accepts source root, destination, repository/revision labels and optional summary output;
   - non-zero exit on conversion failure;
   - no network access is required by the converter itself.

Commit these tests first and observe RED because `copticscriptorium_tf.converter` does not yet exist.

## Full-corpus regression gate

After the thin orchestration path is green on fixtures, add one exact-head workflow that runs the same public converter path against `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`.

The gate should verify converter invariants only:
- conversion completes, or fails with a clearly attributable converter/resource error;
- native TF reloads through real Text-Fabric;
- no structural `*_json` features appear;
- output counts are internally consistent with the graph from that same run, not with a separately maintained historical census;
- a small set of representative generated features/relations/text formats is loadable;
- wall time, peak RSS and TF output bytes/files are reported.

The regression may record source/document/slot counts as observations for debugging, but changing upstream data is not itself a converter failure unless converter invariants break.

## CI/resource strategy

A complete upstream checkout is currently expensive and the parse/graph path is already near ordinary hosted-runner memory limits. Therefore:
- keep fast fixture tests in generic CI;
- run the full source smoke only in the issue-16 workflow while this ticket is active;
- do not build a second independent semantic model for comparison;
- if memory prevents a complete write/reload, route directly to #26 and optimize the production path rather than adding certification/audit infrastructure.

## First complete-source attempt: measured findings

Exact head `7a60f9b980c387740fdb921a6e34315dd1702e7b` reached the writer projection after a single parse + graph build but failed before TF publication with:

`line node 5934833 has no measured word locus; reopen schema gate`

The same run measured 7,144,964 KiB maximum RSS and about 3:03 wall time before the failure. This is useful resource evidence for #26, but the immediate #16 blocker is a layout projection edge case, not an OOM.

Research against the existing layout contract shows that a layout marker after the final word is a valid, positionable source event (#23). `_layout_segment()` currently represents such a final zero-width segment with empty `slot_ranges`, while Text-Fabric requires every non-slot node to participate in `oslots`. The intended loss-aware representation is therefore:
- keep `word` as the sole slot type;
- keep the exact zero-width source position in the existing boundary fields;
- keep the layout node's own text as the empty string;
- give the zero-width layout node a **technical locus on the adjacent real word slot** so it can be serialized through normal `oslots`;
- never render or otherwise borrow the technical anchor word's text.

This does not introduce a synthetic slot and preserves the previously reviewed own-text rendering rule for layout nodes. A minimal trailing-layout fixture must be RED before changing graph construction.

The same exact-head run also exposed a pre-existing deterministic-writer test weakness: Text-Fabric itself appends volatile `@dateWritten=<utcnow>` metadata to every `.tf` file, so two otherwise identical saves can differ when they cross a clock-second boundary. The writer must normalize only that generated volatile metadata line before publication, and the regression test must force different write times rather than rely on timing luck.

Additional adversarial findings to cover before finalization:
- an empty source tree should fail at the public converter boundary with an actionable message, not leak a lower-layer graph error;
- `python -m copticscriptorium_tf.converter` should not produce a `runpy` warning caused by eager package-level import of the same module;
- the complete-source smoke must load the native document-relation evidence companion edge features as well as the relation edges themselves;
- README status and local conversion instructions must describe the implemented converter instead of the old research-only state.

## Finalization gate

Research/plan → RED orchestration tests → minimal converter/API/CLI implementation → fast exact-head tests → full-corpus smoke/resource measurement → any required #26 fix → exact-head retest → logically independent adversarial review → merge #16.
