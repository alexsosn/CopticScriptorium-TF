# Issue #54 research and plan

## Research

The source parser distinguishes supported inputs lexically before checking their
filesystem type:

- `root_path.rglob("*_TT")` collects every matching path. Symlinks are rejected,
  but a non-directory candidate currently reaches `if not directory.is_dir():
  continue` and silently disappears.
- inside a valid dataset, every lexical `.tt` path is collected. Symlinks are
  rejected, but a non-regular candidate currently reaches `if not path.is_file():
  continue` and silently disappears.
- `root_path.rglob("*_TT.zip")` now rejects symlinks (#52), but a non-regular
  physical candidate is handed to `zipfile.ZipFile`, producing a generic lower-level
  error rather than an explicit source-shape failure.

This matters for completeness: if other valid records are present, silently skipped
supported-looking inputs can let conversion succeed with a partial corpus. The
parser already follows a fail-closed policy for malformed supported layouts and
symlinks, so wrong filesystem types should follow the same policy.

The narrow rule is: after the dedicated symlink checks, a lexical supported
candidate must have its required physical type. Unrelated paths remain outside
discovery and are ignored.

## Plan

1. RED: put a regular file at `<corpus>/<dataset>_TT` alongside a valid dataset;
   require a deterministic dataset-type error instead of partial success.
2. RED: put a directory named `record.tt` inside a valid `*_TT` directory
   alongside a valid record; require a deterministic record-type error.
3. RED: put a directory at `<corpus>/<dataset>_TT.zip`; require a deterministic
   archive-type error before `ZipFile`.
4. Keep an unrelated non-TT directory/file in the same source root and show it does
   not become a candidate.
5. Implement only the three type guards, preserving symlink checks first.
6. Run exact-head research/parser/graph/writer/Agora/console-command CI and the
   pinned real Coptic directory/ZIP source slice.
7. Freeze the head and perform a logically independent adversarial review grounded
   in RED logs, parser ordering, valid-input controls, and real-corpus regressions.

## Non-goals

No support for special files/devices, no symlink following, and no valid TT/ZIP
semantic changes.
