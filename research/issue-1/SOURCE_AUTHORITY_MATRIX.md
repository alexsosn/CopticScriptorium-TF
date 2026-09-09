# Issue #1 — source authority matrix

Pinned upstream: `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`.

This matrix records the conversion contract established by corpus-wide inventory, semantic census and reconciliation audits. It does not define the final Text-Fabric graph schema; that belongs to issue #3.

| Semantic layer | Primary authority | Supplement / validation | Conflict policy |
| --- | --- | --- | --- |
| Physical source-record identity and provenance | TT source path + pinned upstream revision | `meta.json` basename mapping | preserve literal source identity; scholarly identity/dedup belongs to #2 |
| Per-copy document metadata | TT `<meta ...>` | `meta.json`, relANNIS and PAULA reconciliation evidence | never overwrite unequal TT values silently; PAULA adds no unique document field vocabulary and is less complete for three fields |
| Corpus-level metadata | relANNIS/PAULA corpus metadata | repository/corpus documentation | keep as dataset provenance; do not inject onto every document by default |
| Diplomatic/original surface | TT `orig_group` / `orig` stream | TEI presentation/diplomatic cross-check | TT remains production input; no required TEI-only layer was measured |
| Normalized groups/tokens | TT `norm_group` / `norm` | validated CoNLL-U | `norm` agrees on all 1,489,537 tokens in 1,450 valid comparable documents |
| Lemma | TT when present | valid CoNLL-U may supplement TT absence | one audited lemma exists only in CoNLL-U; zero true lemma conflicts |
| Fine POS / XPOS | TT source annotation | CoNLL-U conflict evidence | one true disagreement; no silent precedence switch |
| Basic dependency relation | TT `func` | CoNLL-U DEPREL as normalized/derived view | 4,423 true differences; preserve semantics separately rather than overwrite |
| Basic dependency head | TT `head` when present | valid CoNLL-U HEAD may supplement TT omissions | 52,257 heads exist only in CoNLL-U; zero true head conflicts after strict validation |
| UD FEATS | validated CoNLL-U | none measured as equivalent TT layer | import only from structurally valid CoNLL-U |
| UD/MISC construction annotations (`Cxn`, `CxnElt`) | validated CoNLL-U | none measured as literal TT equivalent | CoNLL-U-only enrichment; present in 1,042 documents |
| `Morphs` and related MISC enrichment | validated CoNLL-U | TT segmentation remains source segmentation authority | preserve provenance; never use enrichment to rewrite TT segmentation |
| Entity span/class/head/identity | TT | CoNLL-U MISC validation/enrichment evidence | TT retains the richer source-native entity/identity stream |
| Page/column/line and formatting | TT event stream | TEI cross-check | TEI independently confirms layout can split words; use overlap-aware representation |
| Translation / secondary translation | TT | TEI/CoNLL-U/ANNIS comparison evidence | preserve source attribution and separate translation layers |
| Annotation quality (`segmentation`, `tagging`, `parsing`, `entities`, `identities`) | per-copy TT metadata | `meta.json`, relANNIS and PAULA evidence | quality is provenance, not destructive preference |
| Redundancy / witness relation | TT metadata | global metadata evidence | retain boolean and explicit witness relations; #2 owns identity policy |
| License | per-copy TT evidence + reviewed release policy | `meta.json`, relANNIS, PAULA, TEI and upstream documentation | preserve literal evidence; missing/ambiguous is fail-closed; #8 owns release policy |

## Measured CoNLL-U parity boundary

At the pinned revision:

- 2,628 TT documents are inventoried;
- 1,717 CoNLL-U paths pair with TT source-record identities;
- 227 paired CoNLL-U files are whitespace-only placeholders;
- strict CoNLL-U validation reports 57 structural errors across 40 documents; those documents are excluded from semantic supplementation/parity;
- 1,450 valid equal-token-count pairs compare over 1,489,537 basic tokens;
- there are no token-count mismatches among valid pairs;
- 911 TT records in `sahidic.ot` have no CoNLL-U counterpart; no CoNLL-U-only identities are observed.

The shared ID validator used by both the standalone CoNLL-U census and TT↔CoNLL-U parity enforces consecutive basic IDs, valid/non-overlapping MWT ranges that actually cover existing basic words, sentence-initial `0.1` empty nodes when present, sequential empty-node suffixes and sentence-local dependency targets. This prevents an invalid document from being rejected by one audit yet entering supplementation through another.

## Global and corpus metadata boundary

`meta.json` contains 2,390 keys and reconciles to all 2,628 TT copies: 2,152 keys have one TT copy and 238 have two. No TT or `meta.json` identity is orphaned.

ANNIS package accounting finds 78 source packages: 77 parseable metadata datasets and one configuration-only `bohairic.ot` archive. The 77 datasets contain 1,991 document nodes and 77 corpus nodes; every relANNIS document matches `meta.json`. The 507 global keys not represented as relANNIS documents all map to `bohairic.ot`, explaining that format asymmetry completely.

PAULA package accounting also covers all 78 packages and all 2,628 document records. Identity-level reconciliation matches all 2,628 PAULA document records to all 2,628 TT records, with no PAULA-only or TT-only identities; 11 pairs differ only by filename case and both literal forms are retained. Document-scope PAULA metadata has the exact same 80 field names as TT metadata, with no PAULA-only or TT-only field names. Coverage is lower in PAULA only for `document_cts_urn` (2,579 vs 2,628), `next` (285 vs 1,828), and `previous` (267 vs 1,810); the other 77 fields have equal occurrence counts. PAULA additionally exposes 18 corpus-scope types, retained as dataset provenance.

## TEI validation boundary

TEI contains 1,458 records in 76 datasets, all paired with TT. Seventy-three TEI files are malformed XML, leaving 1,385 parseable documents. Presence-level parity finds no TEI-only CTS, lemma, POS, translation, page, column or line layer. The sole checked TEI-only presence is a license for `book.bartholomew_part3`, which is handed to #8 rather than used as an implicit publication rule.

The converter therefore starts from TT as the source-native document stream, supplements only from structurally valid CoNLL-U, uses `meta.json` as global normalization/reference evidence, keeps relANNIS/PAULA corpus metadata at dataset scope, and treats TEI as measured diplomatic/presentation evidence. PAULA and TEI become production parsers only if later graph/schema research demonstrates a concrete semantic requirement unavailable from this narrower authority set.
