# Issue #48 research and plan

## Research

The current writer performs a freshness preflight and later publishes with
`staging.rename(target)`. Python documents that on Unix, renaming one directory
onto an existing empty directory silently replaces the destination, while on Windows
an existing destination makes `os.rename()` fail. Therefore the current preflight +
rename sequence has a TOCTOU no-clobber gap on Unix.

The kernel/platform primitives that match the contract are:

- Linux: `renameat2(..., RENAME_NOREPLACE)`, which atomically refuses an existing
  destination. Filesystem support is required; unsupported cases must fail closed.
- macOS: `renamex_np(..., RENAME_EXCL)`, the platform exclusive-rename primitive.
- Windows: `os.rename()` already fails when the destination exists.

Python 3.12 does not expose Linux `RENAME_NOREPLACE` or macOS `RENAME_EXCL`
directly, so the smallest dependency-free implementation is a private
platform-specific publisher using `ctypes`. Unknown/unsupported platforms or
filesystems must raise rather than fall back to clobber-capable POSIX rename.

Authoritative references:
- https://man7.org/linux/man-pages/man2/renameat2.2.html
- https://developer.apple.com/documentation/foundation/urlresourcevalues/volumesupportsexclusiverenaming
- https://docs.python.org/3/library/os.html#os.rename

## Plan

1. RED: exercise publication on the real Linux CI filesystem with a staging
   directory and competing empty-directory, file, and symlink destinations created
   after preflight; require each competing object to remain untouched.
2. RED integration: force a competing destination to appear immediately before
   writer publication and require `write_graph()` to fail without replacing it.
   Also require Windows non-replacing dispatch and fail-closed unknown-platform behavior.
3. Implement a private atomic no-clobber directory publisher:
   Linux `renameat2(RENAME_NOREPLACE)`; macOS `renamex_np(RENAME_EXCL)`;
   Windows `os.rename()`; all unsupported cases fail closed.
4. Preserve the existing early occupied/dangling-symlink check and TF staging cleanup.
5. Run issue-15 writer tests, pinned real Coptic directory/ZIP slice, full triggered CI,
   then freeze the head.
6. Perform a logically independent adversarial review against code, platform branches,
   actual Linux filesystem behavior, and the pinned real corpus writer regression.

## Non-goals

No process-wide locking, resume protocol, TF schema change, summary-path change, or
new runtime dependency.
