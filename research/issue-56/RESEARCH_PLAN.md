# Issue #56 research and plan

## Research

`parse_source_tree()` treats each lexically valid physical `*_TT` directory and
`*_TT.zip` package as a supported dataset container, but only appends records to
the global `pending` list. There is currently no per-container cardinality check.

Consequently an empty supported container, or one containing only unrelated non-TT
files, contributes zero records and disappears. If another container is valid, the
converter cannot distinguish this from a source tree in which the empty dataset never
existed and can publish a partial corpus successfully.

This is different from malformed TT members. A nested `.tt` directory member or
unsupported archive TT member already raises while scanning; those specific layout
errors should remain authoritative. The cardinality check belongs only after a
container's complete supported-member scan succeeds.

The narrow contract is therefore: every discovered, type-valid, non-symlink supported
dataset container must contribute at least one supported TT record.

## Plan

1. RED: create one valid dataset plus one empty physical `*_TT` directory and
   require a deterministic empty-dataset error rather than partial success.
2. RED: create one valid dataset plus one physical `*_TT.zip` containing no TT
   members and require a deterministic empty-archive error.
3. Control: non-TT files alongside at least one valid TT record/member do not make
   the container invalid.
4. Preserve existing malformed nested TT-member errors by checking emptiness only
   after the normal member scan.
5. Implement per-container record counters without changing global ordering,
   source-record identity, parsing, graph, or TF semantics.
6. Run exact-head parser/research/graph/writer/Agora/console CI and the pinned real
   Coptic directory/ZIP writer slice.
7. Freeze the head and perform a logically independent adversarial review grounded
   in RED logs, member-scan ordering, controls, and the real pinned source.

## Non-goals

No corpus-directory completeness policy beyond discovered supported containers, no
new record types, and no changes to TT semantics or native TF projection.
