# Source-attested 1 Corinthians 14 Greek NT verse addresses

## Evidence and narrowly reviewed exception

Original pinned physical Coptic TT: `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`, `sahidica.1corinthians/sahidica.1corinthians_TT/1Cor_14.tt`. It contains **40 original `<verse>` values** formatted as `1 Corinthians 14:1` through `1 Corinthians 14:40`, and **40 separate `<verse_vid>` editorial values** formatted as `46N 14:1` through `46N 14:40`. It has no `verse_n` or `vid_n`, which is why the previous strict resolver marked **all 40 `sbl_greek` and 21 `sbl_apparatus` physical occurrences as ambiguous**. Original document CTS, chapter, work, physical source and Greek edition attribution corroborate the book and chapter. The pinned independent Greek NT TF parent is read-only.

The code never fabricates `verse_n`. Its second, **read-only** scanner processes literal TT opening/closing verse labels and records which labels enclose each *complete original Coptic word slot*. For an SBL source annotation to qualify, all its original complete-word slots must share **one exact human-readable + editor-label pair** with matching book, chapter and verse. Labels opening/closing inside a word, conflicting word spans, altered source bytes/SHA256, duplicate label attributes and invalid word ordinals fail closed; another chapter or source family cannot use this exception.

This is a **source-grounded Greek NT verse-address candidate**, not correspondence between Coptic words and the source Greek words embedded in the SBL apparatus. The source's Greek SBL wrappers remain on existing **native Coptic SBL nodes**. The independent Greek parent keeps its own native `verse` nodes; no Greek token nodes, changed Text-Fabric warp or foreign node IDs are created. The code and generated TF wefts remain exclusively in `CopticScriptorium-TF`.

## Explicit pinned data acceptance

| Resolution status | Previous | Expected after source-specific recovery |
| --- | ---: | ---: |
| `reference_candidate` | 2,301 | 2,362 |
| `ambiguous` | 437 | 376 |
| `unresolved` | 8 | 8 |
| `edition_unavailable` | 1 | 1 |
| **Original SBL annotations** | **2,747** | **2,747** |
| **Distinct Greek parent verse addresses** | **904** | **944** |

Independent raw TT tag/witness scan shows the 40 original Greek and 21 original apparatus SBL occurrences are each encompassed by one matching pair; exact pinned parser+Greek parent validation must independently verify all **61** before the baseline is accepted. Subsequent full native TF acceptance must rebuild all 2,628 source documents, preserve 2,394,354 Coptic word slots and all 2,747 original SBL annotations, generate both Coptic-owned additive native wefts and independently reload both. Any discrepancy blocks merge rather than promoting uncertain references.

**Unchanged:** Mark1, Mark10/11 and 1Cor10 have absent, crossed or insufficient independently concordant source-level verse labels. They are still ambiguous. Mark15:28 remains `edition_unavailable` because the pinned Greek edition has no verse node there. No Coptic or Greek copyrighted corpus is redistributed; the CI output contains only coordinates/counts and local temporary TF data.
