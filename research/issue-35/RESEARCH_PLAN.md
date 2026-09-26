# Issue #35 research and plan

## Observed behavior

The direct converter CLI accepts an optional `--summary` path. `main()` first calls
`convert_source_tree(..., destination)`, which publishes the native TF directory, and
only afterwards calls `_write_summary(args.summary, result)`.

`_write_summary()` creates the summary parent directory and writes JSON without
checking its relationship to the TF destination. Consequently a caller can request
`--summary <destination>/conversion-summary.json` and inject a non-TF sidecar into
the native TF dataset.

This is an artifact-boundary bug rather than a corpus-model gap: the JSON contains
operational counts/timings, not semantic corpus data.

The Agora adapter has a different, intentional layout. Agora owns an existing staging
root and writes native TF to `output/tf/` while its operational summary is the sibling
`output/conversion-summary.json`. That contract must remain unchanged.

## Plan

1. Add a RED regression around direct CLI argument handling proving that a summary
   equal to or nested below the destination is rejected before conversion.
2. Keep ordinary external summaries working.
3. Add a small path-boundary preflight in the direct CLI before calling
   `convert_source_tree`; do not alter the writer or Agora adapter.
4. Document that `--summary` is operational metadata outside the TF dataset.
5. Run focused and repository CI, then perform a logically independent review of the
   exact PR head.
