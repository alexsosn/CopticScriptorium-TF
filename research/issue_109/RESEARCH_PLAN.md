# Issue #109 — exact-source phase RSS profiling before optimization

## Research

- Existing `convert_source_tree` executes all 2,628 TT source models → 2.394M slots / 3.86M nodes graph → TF writer in one Python process, then `research/issue-16/full_converter_smoke.py` loads TF anew in the **same process**. Current operational summary records phase time and `ru_maxrss` but only **one overall peak**; #109 cannot attribute the peak to parse, graph construction, graph+parser overlap, TF writing, or fresh reload.
- Source graph and model objects are already frozen `@dataclass(slots=True)`. Blind "add slots" or broad string interning is not a justified optimization. The converter already deletes parsed source model before writing and calls `gc.collect()`.
- Previous pinned exact-head #128 [full-run 38143323705](https://github.com/alexsosn/CopticScriptorium-TF/actions/runs/38143323705) observed full converter+reload **7m39.54s and 7,485,092 KiB process peak RSS**, projection 29.68s / 5,672,256 KiB; no paired same-run control. #122 had 5m09s at a similar RSS; do **not** claim a speed improvement/regression due to this noise.
- On Linux, `/proc/self/status` exposes instantaneous `VmRSS`, whereas `resource.getrusage(RUSAGE_SELF).ru_maxrss` is the process high-water mark. They measure different quantities. Never mislabel one as the other or interpret high-water as an instantaneous sample. Non-Linux fallback should report `null`, not zero or an invented number.

## Research → RED → implement → test → adversarial review

1. RED-first tests assert exact phase keys, high-water monotonicity and current RSS sampling, safe `None` fallback if `/proc` missing/malformed, no filesystem/source text in metric payloads, dataclass serializability, and preservation of the old operational summary. Include an end-to-end small TT synthetic corpus smoke.
2. Add no-dependency, low-overhead per-phase RSS snapshots to converter: after parse, after graph, after releasing source objects/GC, after TF write. Record `instantaneous_rss_mb` and `high_water_rss_mb` separately and optionally high-water-increase-from-last-sample. Keep original `peak_rss_mb` unchanged. Add after-reload checkpoint to the existing full converter smoke report. Avoid `tracemalloc` on the large 2.4M-slot path.
3. Verify unchanged converter counts/graph/TF output and no extra source data or generated corpus published. Run original #120 full pinned corpus+complete SBL parity+native bilateral weft check (2,301/437/8/1, 904 Greek verse nodes), once on exact head. Collect source-free snapshots and `/usr/bin/time -v`, not corpus contents.
4. Conduct logically independent adversarial review of code, Linux RSS parser, false-zero cases, comparative phase data and actual native full corpus. Only merge when all exact-head applicable CI passes. Use phase evidence to open a **separate targeted optimization** under #109 with measured bottleneck, instead of claiming profiling itself reduces peak below 5GiB.

## Boundaries

All code stays in `CopticScriptorium-TF`, Greek NT repo read-only. No semantic features removed; the original 2,747 SBL source annotations remain preserved. No full generated TF redistributed.