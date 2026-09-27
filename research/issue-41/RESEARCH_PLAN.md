# Issue #41 research and plan

## Research

Issue #37 protects the summary target itself: an existing file, directory, or symlink is
rejected before conversion. A fresh-looking child path can still be impossible to
create when one of its ancestors is an existing non-directory.

Examples:

- `/tmp/existing-file/conversion-summary.json`
- `/tmp/dangling-link/reports/conversion-summary.json`

The current preflight checks only the final summary path. Conversion can therefore
parse, build, and publish the native TF dataset before `_write_summary()` reaches
`path.parent.mkdir(parents=True, exist_ok=True)` and fails. The command returns
failure even though the corpus has already been published.

The check can remain non-mutating: walk from `summary.parent` toward the filesystem
root until the nearest existing path or symlink is found. That ancestor must be a
directory. An existing symlink to a directory is acceptable; issue #35's resolved
containment check already prevents such a parent from routing the summary into the TF
destination.

## Plan

1. RED: existing regular-file ancestor and dangling-symlink ancestor both fail before
   `convert_source_tree()` can start.
2. RED/happy path: missing nested parent directories under an existing directory remain
   valid and are created after successful conversion.
3. Add a small non-mutating ancestor preflight to `_validate_summary_path()`.
4. Preserve issue #35 containment and #37 occupied-target behavior unchanged.
5. Document the early parent-path failure.
6. Run exact-head CI and independent adversarial review.

## Non-goals

This does not attempt permission probing, directory reservation, or cross-process
locking. Those would either mutate the filesystem during preflight or still be racy.
