# Coptic full-build RSS checkpoints (#109)

The full corpus converter already records **peak** process resident memory via `resource.getrusage(RUSAGE_SELF).ru_maxrss`. That high-water statistic cannot identify which completed phase still holds memory or whether the phase released objects. The new `phase_memory_mb` field supplements, not replaces, `peak_rss_mb`.

## Metrics

Each named checkpoint contains two source-free quantities:

- `current_rss_mb`: instantaneous Linux `/proc/self/status` **VmRSS**, in MiB; `null` when unavailable/invalid. This is a sampled snapshot **after** the phase, not the phase's own maximum.
- `peak_rss_mb`: `ru_maxrss` high-water process resident memory, in MiB. On Linux this counter is KiB divided by 1024; on macOS the raw bytes are divided by 1024². It can remain high after objects are released. The existing `ConversionResult.peak_rss_mb` is unchanged.

Checkpoints: `after_parse` → `after_graph` → `after_release_source` (after deleting parser objects and collecting garbage) → `after_write` → `after_reload` (the existing `research/issue-16/full_converter_smoke.py` clean TF reloader).

High-water between checkpoints is monotonic; **neither metric proves which operation caused all allocations**, and `VmRSS` does not show short-lived peaks within a phase. Do not treat differences between separate GitHub-hosted runners as a controlled performance comparison or a proof of memory reduction. No tracing or profiling of restricted source text is performed.

## Gate and follow-up

Tests verify source-free numeric reporting, malformed/missing procfs fallback, native TT direct+ZIP parser/converter counts and TF reload. The issue120 workflow is reused on the specifically named profiling branch to rebuild and reload the **2,394,354-word / 2,628-document** pinned Coptic corpus and independently audit the original 2,747 SBL annotations, Coptic-owned bilateral NT wefts, and 904 Greek verse targets (2,301 candidates / 437 ambiguous / 8 unresolved / 1 edition-unavailable). No native source or corpus content is uploaded.

The target of issue #109 remains **under 5 GiB peak RSS**. Phase measurements should determine a separate RED-first scoped implementation optimization; adding instrumentation by itself does not achieve the goal.
