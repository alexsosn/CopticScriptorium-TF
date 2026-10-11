# Coptic-owned Greek NT reference-candidate resolver (#113)

The alignment owner is **`alexsosn/CopticScriptorium-TF` only**. `alexsosn/sblgnt` remains a standalone, read-only, pinned Greek NT corpus and source-reference dependency. No Coptic mapping tables, application logic, or generated alignment modules belong in the Greek NT repository. A future Greek-facing TF *weft* can be generated and distributed by the Coptic project without modifying the Greek parent.

## Source research
An independent pinned Coptic `sahidica.mark/Mark_02.tt` contains source Greek and critical apparatus attributes plus `book=Mark`, `chapter=2`, a Coptic CTS document address, word-level `verse_n`, full verse `vid_n=urn:cts:copticLit:nt.mark.sahidica_ed:2.n` and an editor reference `verse_vid=41N 2:n`. Pinned `sahidica.1corinthians/1Cor_02.tt` uses `book=1Cor`, `nt.1cor` and `46N 2:n`. An independent `coptic-treebank` physical Mark copy must remain distinct. The source's `Greek_source` attributes cite **SBL Greek New Testament (c)2010**, not word/edition equality to MorphGNT 6.12 (2024 source).

## Policy and code
`copticscriptorium_tf/nt_reference.py` resolves one `sbl_greek` or `sbl_apparatus` source occurrence at a time, preserving exact physical record and ordinal and identifying only **reviewed NT source families**. Coptic word-span markers, document CTS and editor labels must independently agree. Anything contradictory is `ambiguous`; absent or position-only source values remain `unresolved`; missing/untrusted provenance or unreviewed books stay `unclassified_source`. Successful lookup requires an actual pinned `sblgnt` TF verse node and yields a stable *edition-qualified reference ID*; the Greek parent node number exists only in process, never as a foreign TF integer edge.

Known Faithlife SBLGNT v1.2 verse additions John 7:53–8:11 are absent from MorphGNT 6.12. Such Greek morphologized nodes must not be invented. The explicit missing-address policy is tested but does not authorize classification of hypothetical or unreviewed Coptic John sources. All source references are **candidate addresses only, not certified text similarity, textual identity or word alignment**.

## Research → RED → test
The RED-first suite tests Mark, 1Cor, missing source provenance, contradictory CTS/word references, unsupported book source, zero-span Greek annotation, wrong source SHA, invalid Greek node IDs, and arbitrary Greek strings that should not affect address-candidate status. The real-data pilot checks pinned Mark 2, 1 Corinthians 2, and independent treebank Mark 2 sources against the exact independently pinned 27-book Greek Text-Fabric parent `alexsosn/sblgnt@4dd0207bda66133fdfa9740ff0aae7de61228700`, then reports candidate/ambiguous/unresolved counts only.

Next ticket phase: after real-data audit, design native bilateral **weft-only** TF feature modules and parent-feature hash checks, with all generation and tests implemented in this Coptic repository. Do not modify or publish the Greek corpus or restricted Coptic source text. If real data contradicts the resolver, revise only on documented evidence and re-run TDD and independent adversarial review.

## Complete source-candidate conservation gate

`copticscriptorium_tf/nt_reference_audit.py` independently accounts for every physical TT source record (directory or ZIP). Its source-kind/order identity check is independent of target selection; a Greek verse candidate additionally requires the pinned Greek TF's reverse section to exactly equal the proposed `(book, chapter, verse)`. It rejects duplicate physical source IDs, unexpected/missing annotations, edition ID mismatch, phantom foreign target IDs on unresolved records and unknown disposition types.

`tests/live_issue113_all_source_audit.py` streams all **2,628** pinned TT physical records, parsing only **48** records with SBL annotation wrappers. It requires an exact **1,652 sbl_greek + 1,095 sbl_apparatus** source inventory and reports each of `reference_candidate`, `ambiguous`, `unresolved`, `edition_unavailable` and `unclassified_source` without inferring successful resolution for all rows. The output contains bounded physical source coordinates, status and reason only; it does not contain Greek passages, Coptic text, full words, foreign TF integer node IDs or generated corpora.

The full-source gate runs in the existing NT pilot job to share the pinned checkout and Greek TF dependency. It is a source-to-reference **coverage check**, not yet a native bilateral TF module. New node features will be authored in CopticScriptorium-TF only, never in the independent Greek NT repository.
