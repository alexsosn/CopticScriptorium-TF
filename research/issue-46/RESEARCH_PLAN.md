# Issue #46 research and plan

## Research

`parse_source_tree()` discovers directory members with `item.is_file()` and reads
them with `item.read_bytes()`. Both follow a live symlink. Consequently a path that
is lexically below `<corpus>/<dataset>_TT` can contribute bytes from outside the
handed-off tree while provenance records only the lexical in-tree path.

A dangling `.tt` symlink is currently ignored because `is_file()` is false, which
is also undesirable: the supported source shape silently changes depending on target
availability. ZIP members do not have this filesystem escape.

The narrow contract is to reject TT symlink members themselves. This does not need
`resolve()` or target inspection and therefore does not read/follow the target.
Physical regular files retain existing behavior.

## Plan

1. RED: create live and dangling `.tt` symlinks under a valid `*_TT` directory;
   require both to raise before parsing, and prove an external live target is not
   accepted as an in-tree record.
2. Keep ordinary physical-file parsing covered as a control.
3. Implement a deterministic directory-member scan that identifies TT candidates by
   lexical suffix, rejects `is_symlink()`, then accepts physical files.
4. Document the physical-file source boundary.
5. Run exact-head unit/parser/Agora regressions and all triggered CI.
6. Freeze the head and independently review symlink-to-file, dangling symlink,
   non-TT symlinks, nested layout, ZIP behavior, and provenance implications.

## Non-goals

No symlink materialization, general sandbox, or ZIP semantic change.
