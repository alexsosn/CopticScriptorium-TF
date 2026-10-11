# #143 — source `multiword` as native non-slot grouping (research / RED gate)

Immute upstream: `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`. Census `research/issue-118/tag_matrix.csv` from full 2,628-doc source runner: 35,148 multiword opening tags, 78 corpora collections, 0 openings inside norm. This is an independent source count, not proof of 35,148 nonempty valid spans.

Actual source examples:
- AP mother TT: 3 multiword wrappers `ⲧⲱⲟⲩⲛ ϩⲁ`, `ϩⲉ ⲉ`, `ⲧⲱⲟⲩⲛ ϩⲁ`. One crosses source `lb_n` boundary between first and second canonical norm; two words and two potentially different dependency functions stay distinct.
- Pistis Sophia Postscript TT: `ⲉⲓ ⲉⲃⲟⲗ` wraps independent root and advmod Coptic words, 1 wrapper.
- Bohairic Lausiac 01 TT: 18 multiword wrappers, e.g. `ⲉⲃⲏⲗ ⲉ` across two orig_group/norm_group nodes, with TT function fixed on some but not all examples. No automatic syntactic relation inference.

Architecture planned:
- one new native TF otype `multiword`, preserving source literal `multiword="..."` unchanged and explicit character/word offsets, unique source opening ordinal per physical source record, `source_record_id`, `multiword_span` for proven fully covered words, `multiword_anchor` only for partial/zero-locus source events with an explicit one-word positional anchor. Distinguish source surface literal from normalized corpus `norm`; no new Coptic slot, no segmentation or canonical TT/UD head override.
- one dedicated `multiword_annotations` occurrence track (reusing common position schema), not mixing IDs of SBL, lang, token, edition or layout. Independent multiword stack handles potential nested groups and crossing with unrelated wrappers. Missing opening/closing/required source `multiword` key fails closed; present empty literal stays distinct from absent.
- **Research hold:** perform full pinned raw opener/closer and span-size census before approving one-word/zero-word policies; preserve unusual source evidence, avoid guess that every wrapper encloses exactly 2 words.
- RED tests first: split across orig groups and `lb_n` preserving two slots, source value with spaces, independent Coptic TT heads, full TF clean reload, empty vs absent, orphan/unclosed, overlapping edition wrappers, duplicate/nested ordinal behavior. Incorporate sampled real source parity.
- Full native CI on combined #142 + #139 baseline requires 35,148 `multiword` nodes, unchanged 2,628 documents, 2,394,354 slots, edition 43,735, token 136,860, lang 110,148, 2,747 SBL and CoNLL-U UD heads. Read raw source sample parity independently from parser; output native TF count from clean reload. Full source checkout reused once.
- Separate logically independent adversarial review of actual source TT examples, graph code, and exact-head CI before merge. No Coptic-to-Greek/LXX mappings or new JSON sidecars.

PR #142 is parent source-annotation work until it merges; keep this branch stacked and draft. Parent epic #118 stays open.
