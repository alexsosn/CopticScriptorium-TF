# Issue #184, first bounded implementation: Arabic source tag identity

## Research (original pinned TT)
Coptic Scriptorium upstream commit `3ac067f1709a0012daf39ea8da2fac79980176a5` has two distinct source tags: `AP/apophthegmata.patrum_TT/AP.044.w670.temptation.tt` (8,865 bytes) includes three original `<arabic_translation arabic_translation=...>` openings; `AP/apophthegmata.patrum_TT/AP.054.daniel.04.tt` (9,088 bytes) includes five `<arabic arabic=...>` openings. Confirmed from actual upstream bytes without reproducing source Arabic text. Corpus-wide historic census has 3 and 1,595 openings respectively.

Current `parser.py` merges both spellings in a shared `arabic_stack` and `Translation` has only ordinal/text/locus. `_graph_core.py` emits common node type `arabic_translation`, correctly retaining word slots and text but losing original tag-name identity. No new slot or second non-slot node is justified; preserve original tag kind as a native scalar node feature `original_source_tag`.

## Plan/TDD
1. RED parser→graph→writer→clean Fabric test for both original tag spellings and separate normal English `translation`; reject forged alias. Keep original Arabic wording, slots and node IDs unchanged. No opaque sidecars.
2. Add optional original tag to `Translation` and `GraphNode` (default None for all preexisting constructors). Capture raw opening tag spelling on Arabic source stack, propagate into graph node, write `original_source_tag` as a native scalar TF feature on Arabic nodes. Existing English translation nodes are not relabeled; this records source evidence not inferred language equivalence.
3. Source-bound CI: independently check the two pinned original AP files against parsed Arabic source-kind counts, then clean TF reload and compare exact node counts/kinds and full original source SHA. Run complete pinned 2,628-record / 2,394,354-slot TF regression, preserve SBL/Horner/LXX candidate/CoNLL-U gates; assess resource usage.
4. Logically independent adversarial review on real original source content and TF graph feature, including absent vs empty Arabic text and mixed tag nesting/closings. Merge only after exact-head green CI and review.
5. Leave #184 open for the distinct secondary `morph.lang` and other core multi-attribute provenance research; don't claim comprehensive 101-tag losslessness.

This PR changes one native feature and the source model's optional provenance field, not grouping/segmentation.
