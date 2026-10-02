# Issue #46 research and plan

## Research

`parse_source_tree()` discovers directory members with `item.is_file()` and reads
them with `item.read_bytes()`. Both follow a live symlink. Consequently a path that
is lexically below `<corpus>/<dataset>_TT` can contribute bytes from outside the
handed-off tree while provenance records only the lexical in-tree path.

A dangling `.tt` symlink is currently ignored because `is_file()` is false, which
is also undesirable: the supported source shape silently changes depending on target
availability. ZIP members do not have this filesystem escape.

The same boundary applies to a symlinked `*_TT` dataset directory: accepting it can
move the entire discovered dataset outside the handed-off tree. The narrow contract
is therefore to reject both TT dataset-directory symlinks and TT record symlinks.
This does not need `resolve()` or target inspection and therefore does not read/follow
the target. Physical directories/files retain existing behavior.

## Plan

1. RED: create live and dangling `.tt` symlinks under a valid `*_TT` directory;
   require both to raise before parsing, and prove an external live target is not
   accepted as an in-tree record. Also cover a `*_TT` directory symlink to an
   external dataset.
2. Keep ordinary physical-file parsing covered as a control.
3. Implement deterministic dataset/member scans that reject relevant symlinks before
   accepting physical directories/files.
4. Document the physical-file source boundary.
5. Run exact-head unit/parser/Agora regressions and all triggered CI.
6. Freeze the head and independently review symlink-to-file, dangling symlink,
   non-TT symlinks, nested layout, ZIP behavior, and provenance implications.

## Non-goals

No symlink materialization, general sandbox, or ZIP semantic change.
