# Issue #1 — source authority matrix

Pinned upstream: `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`.

This matrix records the conversion contract established by corpus-wide inventory and parity audits. It does not define the final Text-Fabric graph schema; that belongs to issue #3.

| Semantic layer | Primary authority | Supplement/fallback | Conflict policy |
| --- | --- | --- | --- |
| Source record identity and source-relative provenance | physical TT source record + pinned upstream revision | `meta.json` basename mapping | preserve literal source path/name; identity/dedup policy deferred to #2 |
| Document metadata as attached to a specific corpus copy | TT `<meta ...>` | `meta.json` as global normalized/reference metadata | never overwrite a TT value silently; record disagreement and missing-on-one-side fields |
| Corpus-level metadata not attached to an individual TT document | relANNIS/PAULA or other upstream corpus metadata as needed | repository/corpus metadata | preserve as dataset-level provenance; do not inject blindly into every document |
| Diplomatic/original surface | TT `orig_group` / `orig` stream | TEI for presentation-oriented cross-checks | TT is canonical parser input unless a later measured gap proves a TEI-only semantic layer is needed |
| Normalized groups/tokens | TT `norm_group` / `norm` | CoNLL-U validation | token `norm` agrees on all 1,563,143 tokens in the 1,488 valid paired documents audited |
| Lemma | TT when present | CoNLL-U if TT value is absent and the CoNLL-U document passes structural validation | one audited CoNLL-U lemma fills a TT absence; no true lemma conflict in valid paired documents |
| Fine POS / XPOS | TT | CoNLL-U as conflict evidence | one true POS disagreement exists; no silent precedence switch |
| Basic dependency relation | TT `func` preserves source annotation | CoNLL-U UD-normalized DEPREL is a distinct derived/normalized view | 4,856 true relation differences; preserve both if downstream schema exposes both semantics |
| Basic dependency head | TT `head` when present | valid CoNLL-U HEAD can supplement TT omissions | 55,564 audited heads exist only in CoNLL-U; 7 true head disagreements; local IDs must be resolved to document token targets before TF serialization |
| UD FEATS | CoNLL-U | none measured in TT | CoNLL-U-only enrichment; import only from structurally valid CoNLL-U |
| UD/MISC construction annotations (`Cxn`, `CxnElt`) | CoNLL-U | none measured in TT | CoNLL-U-only enrichment; present in 1,042 documents at pinned revision |
| `Morphs` and related CoNLL-U MISC enrichment | CoNLL-U | TT segmentation remains source segmentation authority | preserve provenance and do not use it to rewrite TT segmentation |
| Entity span/class/head/identity | TT | CoNLL-U MISC may be used only as validation/enrichment evidence | TT contains the richer source-native entity/identity stream and crossing structure |
| Layout: page/column/line and formatting | TT event stream | TEI for cross-checking/documentation | layout can cross token rendering, so conversion requires overlap-aware event handling rather than ordinary XML containment assumptions |
| Translation and secondary translation | TT | TEI / corpus exports only if a measured TT omission is established | preserve source attribution and language/translation metadata |
| Annotation quality (`segmentation`, `tagging`, `parsing`, `entities`, `identities`) | per-copy TT metadata | `meta.json` reference/normalization | quality values are provenance, never destructive preference rules |
| Redundancy/parallel witness marker | TT metadata | global metadata as evidence | no automatic deduplication; #2 owns identity/overlap policy |
| License | per-copy source metadata plus reviewed release policy | normalized `meta.json` label and upstream corpus documentation | preserve literal evidence; missing/unknown is fail-closed for publication; mixed-license release policy is separate work |

## Corpus-wide parity boundary

At the pinned revision:

- 2,628 TT documents were inventoried.
- 1,717 CoNLL-U paths have matching TT source-record identities.
- 227 matching CoNLL-U files are whitespace-only placeholders, all in the aggregate Sahidica NT packaging observed by the audit.
- structurally invalid CoNLL-U documents are excluded from semantic parity and reported explicitly rather than parsed permissively;
- the remaining structurally valid, equal-token-count pairs are compared token by token;
- all TT-only records in the current TT↔CoNLL-U identity comparison are from `sahidic.ot`, where 911 TT documents lack visible CoNLL-U counterparts at this revision.

The canonical converter therefore uses TT as its source-native document stream and treats CoNLL-U as a validated supplementary authority for UD-normalized/enrichment fields. `meta.json` is a global metadata reference and normalization layer, not an unconditional overwrite source. TEI/PAULA/relANNIS remain evidence and corpus-level metadata sources; adding a second production parser requires a concrete field that TT plus validated CoNLL-U plus `meta.json` cannot preserve.
