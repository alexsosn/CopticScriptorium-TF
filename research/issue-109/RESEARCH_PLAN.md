# Issue #109 — Measure real TF peak memory by conversion phase

## Research evidence (2026-10-11)
- Pinned CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5, Ubuntu 24.04 / Python 3.12 / text-fabric==13.1.0.
- Source-only complete TT + native reload successful 38151223197 / 114504923562: 2,628 documents, 2,394,354 source word slots, 136,860 five-family token nodes, 110,148 language nodes, RSS peak **7,564.33 MiB** / **7,745,872 KiB**. This is the comparison baseline for the same TT-only workload.
- With CoNLL-U, older exact-head job 38147515330 / 114497412774: 2,104,966 enriched words, 2,034,751 UD edges, RSS peak **8,353.44 MiB** and 356.189 s convert. The two workloads are *not directly comparable*.
- The converter currently deletes parsed DocumentModel instances after Graph construction and incremental writer saves at most one ordinary TF feature batch. GraphSlot, GraphNode and source records already use frozen slotted dataclasses. No evidence yet that interning provenance or changing node representation would reduce the actual peak enough to justify a semantic-risky refactor.
- Its phase performance report lists parse, graph and write elapsed time, but **only whole-process high-water RSS**; Linux /proc/self/status VmRSS permits cheap phase-boundary *live RSS* without generating additional large in-memory snapshots.

## Implementation plan
1. RED tests enforce an **opt-in** callback API (start, parsed, graph_built, models_released, writer_complete), no retained model/graph references, no semantic change with profiling enabled, exact TF feature bytes preserved, unknown-platform null RSS (never invented measurements).
2. GREEN: add optional `phase_probe` to converter and `--profile-memory` to existing `research/issue-16/full_converter_smoke.py`; capture wall-time, current RSS, lifetime high-water RSS, and optionally `VmSize` at each boundary; append post-reload point in the runner only. No extra packages, long-lived tracemalloc, background thread, corpus export, or default-output schema changes.
3. Piggyback on **same pinned full native source checkout** job; require returned JSON to contain the six ordered phases, strictly nonnegative numeric measurements when Linux, and match source revision/node/word-slot invariants. Capture full native exact-head CI log with this measurement before recommending any optimization.
4. Independent adversarial review checks that the profiler does not extend object lifetimes, that `VmRSS` is live RSS and `ru_maxrss` a high-water mark, that reporter latency does not misrepresent whole-phase peak, and that extra memory sampling does not weaken TT/CoNLL-U/word-slot source gates.

## Interpretation constraints
- Boundary samples alone **cannot locate transients within a phase**. Whole-process high-water peaks identify whether any transient occurred; a later bounded sampling design can refine the largest identified phase.
- Never claim the memory target (<5 GiB) or time target (<6min) met based only on instrumentation. #109 remains open until measured optimization verified with comparable workloads and unchanged TF features.
