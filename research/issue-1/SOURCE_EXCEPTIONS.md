# Issue #1 — source exception ledger

Pinned upstream: `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`.

This ledger classifies source shapes discovered by corpus-scale research. Production conversion must balance every input record against converted output or an explicit source classification; none of these cases authorizes a silent skip.

## Packaging asymmetry

- TT is directory-packaged for some datasets and ZIP-packaged for others: 561 TT documents are read from visible directories and 2,067 from archives.
- CoNLL-U, PAULA and ANNIS packaging also varies by corpus.
- Opaque archive packaging is not evidence that a particular record is missing.

Classification: valid source packaging. Transport must open the supported package or report that record-level semantics are unavailable.

## One-level Bohairic PAULA wrapper ZIPs

`bohairic.nt/bohairic.nt_PAULA.zip` and `bohairic.ot/bohairic.ot_PAULA.zip` are outer wrapper archives containing one inner `*_PAULA.zip`; the PAULA XML lives in that inner archive. Corpus-wide PAULA accounting succeeds only after opening this measured one-level wrapper shape.

Classification: valid source packaging. The research reader accepts exactly one recognized inner PAULA ZIP when the outer archive contains no PAULA XML. Multiple candidate inner archives, unrelated ZIPs, deeper wrappers or wrappers with no XML remain unsupported/fail-closed rather than being searched heuristically.

## Configuration-only Bohairic ANNIS package

ANNIS source-package accounting finds 78 packages. Seventy-seven contain parseable corpus/document metadata tables. `bohairic.ot/bohairic.ot_ANNIS.zip` contains ANNIS configuration/visualization assets (`annis.version`, `resolver_vis_map.annis`, `corpus.properties`, CSS/fonts and related files) but no `corpus.annis` / `corpus_annotation.annis` or legacy `.tab` metadata pair.

The package is emitted as dataset `bohairic.ot/bohairic.ot`, classification `configuration_only`, with no relANNIS metadata availability. The 507 `meta.json` keys not represented by a relANNIS document all map to `bohairic.ot` TT records, so this package explains the complete relANNIS document-coverage gap.

Classification: valid format asymmetry, explicitly ledgered. Arbitrary archives with no recognized metadata pair still fail; incomplete, duplicate or ambiguous metadata-table layouts are hard errors.

## TT-only CoNLL-U identities

The TT↔CoNLL-U identity audit finds 911 TT source records in `sahidic.ot` with no matching CoNLL-U record. No CoNLL-U-only source identities are observed.

Classification: valid format asymmetry. TT conversion proceeds; CoNLL-U-only enrichments remain absent rather than fabricated.

## Whitespace-only CoNLL-U placeholders

There are 227 paired CoNLL-U paths whose content is whitespace-only, in aggregate Sahidica NT packaging.

Classification: valid empty supplementary representation, not token-count drift. TT remains convertible and no CoNLL-U enrichment is merged.

## Structurally invalid CoNLL-U

The strict validator reports 19 structural errors across nine CoNLL-U documents:

- `book-bartholomew/book.bartholomew_CONLLU/book.bartholomew_part1.conllu` — basic token ID `0`;
- `book-bartholomew/book.bartholomew_CONLLU/book.bartholomew_part2.conllu` — basic token ID `0`;
- `helias/helias_CONLLU/helias_martyrdom_part1.conllu` — basic token ID `0`;
- `helias/helias_CONLLU/helias_martyrdom_part4.conllu` — basic token ID `0`;
- `life-hilaria/life.hilaria_CONLLU/life.hilaria.bnf132frg2.conllu` — malformed multiword ID `0-2` plus basic token ID `0`;
- `life-marina/life.marina_CONLLU/life.marina.HC_giron.conllu` — basic token ID `0`;
- `sahidica.nt/sahidica.nt_CONLLU/41_Mark_01.conllu` — one dangling HEAD and seven negative HEAD values;
- `sahidica.nt/sahidica.nt_CONLLU/41_Mark_07.conllu` — basic token ID `0`;
- `sahidica.nt/sahidica.nt_CONLLU/41_Mark_09.conllu` — three basic token ID `0` occurrences.

Classification: malformed/non-standard supplementary source. TT remains source-native authority. These CoNLL-U documents are excluded from semantic supplementation/parity and are never repaired heuristically.

## Malformed TEI exports

The pinned TEI audit finds 1,458 TEI paths. Seventy-three fail XML parsing with `mismatched tag` errors, spread across 17 top-level corpora; 1,385 parse successfully. The full machine-generated TEI error ledger records every path and parse position. All 1,458 TEI identities still have TT counterparts, so malformed TEI does not imply loss of a source record.

Two of the malformed TEI files are `book.bartholomew_part1.xml` and `book.bartholomew_part2.xml`; part 3 parses and contains a license while its TT metadata does not.

Classification: malformed supplementary/presentation export. No TEI file is silently repaired or used as production authority merely because its TT counterpart exists. The Bartholomew part-3 license is evidence for #8, not an inferred corpus default.

## Duplicate TT metadata attributes

Sixty-four TT documents contain repeated metadata names: 121 equal-value extra occurrences and six conflicting occurrences. Conflicts are observed for `people` and `places`; a duplicated `segmentation` attribute is equal-valued.

Classification: malformed XML but source-readable SGML-like metadata. The source lexer preserves all literal values and emits conflict evidence; production metadata policy may not silently choose one duplicate value.

## Global `meta.json` field-shape anomalies

The global metadata index contains literal field names with leading/trailing whitespace, including `" segmentation"` and `"msItem_title "`, as well as percent-encoded/dotted PATHS field variants observed across exports. Many values are normalized versions of TT HTML links.

Classification: source normalization/quality anomaly. Exact keys and literal values remain provenance; normalization must be explicit and tested rather than implemented with unconditional trimming/overwrite.

## PAULA document metadata coverage asymmetry

PAULA document metadata covers all 2,628 records and exposes the same 80 field names as TT metadata, but three fields have lower occurrence counts in PAULA:

- `document_cts_urn`: 2,579 PAULA vs 2,628 TT;
- `next`: 285 PAULA vs 1,828 TT;
- `previous`: 267 PAULA vs 1,810 TT.

The other 77 field counts match TT exactly.

Classification: lossy derived document-metadata serialization for these fields. PAULA is validation/corpus-provenance evidence, not a replacement for TT per-copy metadata.

## Missing TT license metadata

The generated missing-metadata ledger identifies exactly three TT records without `license`:

- `book-bartholomew/book.bartholomew_TT/book.bartholomew_part1.tt` — `urn:cts:copticLit:misc.blbartholomew.budge_ed:3-11`;
- `book-bartholomew/book.bartholomew_TT/book.bartholomew_part2.tt` — `urn:cts:copticLit:misc.blbartholomew.budge_ed:12-19`;
- `book-bartholomew/book.bartholomew_TT/book.bartholomew_part3.tt` — `urn:cts:copticLit:misc.blbartholomew.budge_ed:20-25`.

Classification: unresolved redistribution metadata. Local conversion/validation may preserve the records with missing-license provenance; publication is fail-closed until #8 resolves source terms.

## License-string ambiguity

The TT census contains 17 literal license strings. At least four records use a BY-SA 4.0 URL while the visible label says `CC-BY 4.0`, in addition to malformed HTML variants and corpus-specific/custom terms.

Classification: normalization conflict. A release normalizer must evaluate literal label, target URL and surrounding scope together and preserve an explicit unresolved/conflict state when they disagree.

## Duplicate / alternate scholarly records

`meta.json` contains 2,390 keys while TT contains 2,628 source copies. Reconciliation is complete: 2,152 keys map to one TT copy and 238 keys map to two. Upstream also documents treebank duplicates, individual biblical-book vs aggregate analyses and `redundant="yes"` parallel witnesses.

Classification: valid scholarly overlap, not a parser duplicate. Issue #1 discards none of these records. Identity/preference/filter semantics belong to #2.

## Release regression rule

These counts and paths describe the pinned revision, not permanent allowlists. Every newer upstream revision must rerun inventory, semantic, structural-validity and reconciliation audits. New, removed or changed exceptions require research classification before a release gate can call the source contract satisfied.
