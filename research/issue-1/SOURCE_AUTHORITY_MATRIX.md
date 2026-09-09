# Issue #1 — source authority matrix

Pinned upstream: `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`.

This matrix records the conversion contract established by corpus-wide inventory, semantic census and reconciliation audits. It does not define the final Text-Fabric graph schema; that belongs to issue #3.

| Semantic layer | Primary authority | Supplement / validation | Conflict policy |
| --- | --- | --- | --- |
| Physical source-record identity and provenance | TT source path + pinned upstream revision | `meta.json` basename mapping | preserve literal source identity; scholarly identity/dedup belongs to #2 |
| Per-copy document metadata | TT `<meta ...>` | `meta.json` normalized/reference values; relANNIS comparison evidence | never overwrite unequal TT values silently; retain missing/conflict ledgers |
| Corpus-level metadata | relANNIS/PAULA corpus metadata | repository/corpus documentation | keep as dataset provenance; do not inject onto every document by default |
| Diplomatic/original surface | TT `orig_group` / `orig` stream | TEI presentation/diplomatic cross-check | TT remains production input unless a measured TEI-only requirement emerges |
| Normalized groups/tokens | TT `norm_group` / `norm` | validated CoNLL-U | `norm` agrees on all 1,547,873 tokens in 1,481 valid comparable documents |
| Lemma | TT when present | valid CoNLL-U may supplement TT absence | one audited lemma exists only in CoNLL-U; zero true lemma conflicts |
| Fine POS / XPOS | TT source annotation | CoNLL-U conflict evidence | one true disagreement; no silent precedence switch |
| Basic dependency relation | TT `func` | CoNLL-U DEPREL as normalized/derived view | 4,718 true differences; preserve semantics separately rather than overwrite |
| Basic dependency head | TT `head` when present | valid CoNLL-U HEAD may supplement TT omissions | 54,747 heads exist only in CoNLL-U; zero true head conflicts after strict validation |
| UD FEATS | validated CoNLL-U | none measured as equivalent TT layer | import only from structurally valid CoNLL-U |
| UD/MISC construction annotations (`Cxn`, `CxnElt`) | validated CoNLL-U | none measured as literal TT equivalent | CoNLL-U-only enrichment; present in 1,042 documents |
| `Morphs` and related MISC enrichment | validated CoNLL-U | TT segmentation remains source segmentation authority | preserve provenance; never use enrichment to rewrite TT segmentation |
| Entity span/class/head/identity | TT | CoNLL-U MISC validation/enrichment evidence | TT retains the richer source-native entity/identity stream |
| Page/column/line and formatting | TT event stream | TEI cross-check | layout can cross token rendering; use overlap-aware representation |
| Translation / secondary translation | TT | TEI/CoNLL-U/ANNIS comparison evidence | preserve source attribution and separate translation layers |
| Annotation quality (`segmentation`, `tagging`, `parsing`, `entities`, `identities`) | per-copy TT metadata | `meta.json` / relANNIS reference evidence | quality is provenance, not destructive preference |
| Redundancy / witness relation | TT metadata | global metadata evidence | retain boolean and explicit witness relations; #2 owns identity policy |
| License | per-copy TT evidence + reviewed release policy | normalized `meta.json`, relANNIS and upstream documentation | preserve literal evidence; missing/ambiguous is fail-closed; #8 owns release policy |

## Measured parity boundary

At the pinned revision:

- 2,628 TT documents are inventoried.
- 1,717 CoNLL-U paths pair with TT source-record identities.
- 227 paired CoNLL-U files are whitespace-only placeholders.
- strict CoNLL-U validation reports 19 structural errors across nine documents; those documents are excluded from semantic supplementation/parity.
- 1,481 valid equal-token-count pairs compare over 1,547,873 basic tokens.
- there are no token-count mismatches among valid pairs.
- 911 TT records in `sahidic.ot` have no CoNLL-U counterpart; no CoNLL-U-only identities are observed.

## Metadata boundary

`meta.json` contains 2,390 keys and reconciles to all 2,628 TT copies: 2,152 keys have one TT copy and 238 have two. No TT or `meta.json` identity is orphaned.

ANNIS package accounting finds 78 source packages: 77 parseable metadata datasets and one configuration-only `bohairic.ot` archive without corpus/document metadata tables. The 77 parseable datasets contain 1,991 document nodes and 77 corpus nodes; every relANNIS document matches `meta.json`. The 507 `meta.json` keys not represented as relANNIS documents all map to `bohairic.ot`, fully explaining the configuration-only package gap.

The converter therefore starts from TT as the source-native document stream, supplements only from structurally valid CoNLL-U, uses `meta.json` as global normalization/reference evidence, and keeps relANNIS/PAULA corpus metadata at dataset scope. TEI remains a measured cross-check unless issue #3 demonstrates a semantic requirement that the smaller production parser set cannot preserve.
