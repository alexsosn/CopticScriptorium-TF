# Issue #52 research and plan

## Research

Issue #46 hardened direct-directory sources by rejecting symlinked `*_TT`
directories and symlinked `.tt` records before reading their targets. Archive
discovery still uses:

`for archive_path in sorted(root_path.rglob("*_TT.zip"), ...):`
followed directly by `zipfile.ZipFile(archive_path)`.

Opening a live symlink follows its target, so an archive physically outside the
handed-off root can contribute bytes while every generated `source_path` remains
lexically rooted at the in-tree symlink. A dangling archive symlink is also a
lexical source candidate and currently reaches `ZipFile`, producing a generic
filesystem failure instead of the explicit source-boundary rejection used for
directory inputs.

The narrow fix is to reject the archive path itself when `is_symlink()` before
opening it. This requires no target resolution and does not alter ZIP member
semantics or physical archive parsing.

## Plan

1. RED: create a valid physical `*_TT.zip` outside the source root and expose it
   through an in-tree symlink; require explicit rejection before any archive bytes
   are parsed.
2. RED: create a dangling `*_TT.zip` symlink and require the same deterministic
   rejection.
3. Keep a physical ZIP package as a control and verify the existing archive
   `source_record_id`, packaging, and source-path semantics.
4. Implement the smallest parser guard: reject `archive_path.is_symlink()`
   before `zipfile.ZipFile(...)`.
5. Update direct-use documentation so directory datasets/records and archive
   packages all state the physical handed-off-path boundary.
6. Run exact-head research/parser/graph/writer/Agora/console-command CI and the
   pinned real Coptic directory/ZIP writer slice.
7. Freeze the head and perform a logically independent adversarial review grounded
   in the final parser diff, RED evidence, physical-ZIP control, and real-corpus
   regressions.

## Non-goals

No archive extraction, symlink materialization, ZIP member-layout change, or
general filesystem sandbox.
