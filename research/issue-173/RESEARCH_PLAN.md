# Issue 173: Horner translation source witness

Immutable upstream CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5.

Independent actual Git blob research: original trans_horner opening/closing pairs occur 162 in pistis.sophia_book_1_part1.tt, 136 in part2, 87 in part3 = 385 total. Original trans_horner values are an alternative ENGLISH Horner witness, not Greek biblical references. First parallel source `translation` and `trans_horner` original text differ. Independent physical norm-word range comparisons found 376/385 Horner events with exactly the same word boundaries as some original translation, 379 contained, SIX not contained. Do not force equivalence edges or overwrite native translation nodes.

RED tests require distinct parallel translation/Horner literal text and distinct source node count, source opening ordinal and source word/char span, midnorm positional anchor, crossed closures and malformed/orphan source rejection; no extra Coptic slots/UD-head changes and genuine native TF clean reload.

GREEN append one native non-slot trans_horner type, original literal/source record/opening ordinal/source word+char offsets and horner_span/horner_anchor, no opaque sidecar and no inference.

Independent raw TT byte scanner validates every 385 original source events in all 2628 original plain and ZIP source records against reloaded native TF: kind, original attribute, original decoded English literal, original opening ordinal, start/end completed Coptic norm-word boundaries. Exact per-file counts and nested primary original translation differences. Share one pinned conversion with all previous source gates, 2394354 Coptic slots and full CoNLL-U parity. Fresh adversarial review after all exact-head green.

Branch is stacked on draft PR 174 to avoid parallel full source CI. Parent issue 118 remains open.