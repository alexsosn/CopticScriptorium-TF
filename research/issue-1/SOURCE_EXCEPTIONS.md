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

The shared strict validator reports **57 structural errors across 40 CoNLL-U documents**. By error occurrence: 38 multiword-token ranges reference one or more missing basic word IDs, ten basic token IDs are non-positive, one multiword ID is malformed (`0-2`), seven HEAD values are negative, and one HEAD is dangling.

The machine-generated audit retains every line-specific occurrence. The affected documents and their first recorded structural failure are:
- `bohairic-life-isaac/bohairic.life.isaac_CONLLU/bohairic.life.isaac03.conllu` — MWT `1-3` references missing basic word IDs (line 1998);
- `bohairic.nt/bohairic.nt_CONLLU/03_Luke_24.conllu` — MWT `46-49` references missing basic word IDs (line 1808);
- `bohairic.nt/bohairic.nt_CONLLU/04_John_08.conllu` — MWT `29-31` references missing basic word IDs (line 403);
- `bohairic.nt/bohairic.nt_CONLLU/05_Acts_24.conllu` — MWT `1-2` references missing basic word IDs (line 267);
- `bohairic.nt/bohairic.nt_CONLLU/05_Acts_25.conllu` — MWT `48-50` references missing basic word IDs (line 316);
- `bohairic.nt/bohairic.nt_CONLLU/19_Hebrews_12.conllu` — MWT `14-16` references missing basic word IDs (line 609);
- `bohairic.nt/bohairic.nt_CONLLU/27_Revelation_10.conllu` — MWT `39-42` references missing basic word IDs (line 354);
- `bohairic.nt/bohairic.nt_CONLLU/27_Revelation_18.conllu` — MWT `42-43` references missing basic word IDs (line 1291);
- `bohairic.ot/bohairic.ot_CONLLU/01_Genesis_09.conllu` — MWT `14-15` references missing basic word IDs (line 318);
- `bohairic.ot/bohairic.ot_CONLLU/01_Genesis_22.conllu` — MWT `41-44` references missing basic word IDs (line 648);
- `bohairic.ot/bohairic.ot_CONLLU/01_Genesis_24.conllu` — MWT `37-39` references missing basic word IDs (line 2956);
- `bohairic.ot/bohairic.ot_CONLLU/01_Genesis_30.conllu` — MWT `45-46` references missing basic word IDs (line 1525);
- `bohairic.ot/bohairic.ot_CONLLU/02_Exodus_05.conllu` — MWT `46-47` references missing basic word IDs (line 546);
- `bohairic.ot/bohairic.ot_CONLLU/02_Exodus_36.conllu` — MWT `47-48` references missing basic word IDs (line 400);
- `bohairic.ot/bohairic.ot_CONLLU/02_Exodus_39.conllu` — MWT `26-28` references missing basic word IDs (line 184);
- `bohairic.ot/bohairic.ot_CONLLU/02_Exodus_40.conllu` — MWT `31-33` references missing basic word IDs (line 612);
- `bohairic.ot/bohairic.ot_CONLLU/03_Leviticus_27.conllu` — MWT `29-30` references missing basic word IDs (line 1011);
- `bohairic.ot/bohairic.ot_CONLLU/04_Numeri_01.conllu` — MWT `16-19` references missing basic word IDs (line 1372);
- `bohairic.ot/bohairic.ot_CONLLU/04_Numeri_03.conllu` — MWT `20-22` references missing basic word IDs (line 1287);
- `bohairic.ot/bohairic.ot_CONLLU/04_Numeri_08.conllu` — MWT `17-18` references missing basic word IDs (line 1232);
- `bohairic.ot/bohairic.ot_CONLLU/04_Numeri_11.conllu` — MWT `65-66` references missing basic word IDs (line 1398);
- `bohairic.ot/bohairic.ot_CONLLU/05_Deuteronomium_13.conllu` — MWT `50-51` references missing basic word IDs (line 940);
- `bohairic.ot/bohairic.ot_CONLLU/05_Deuteronomium_17.conllu` — MWT `14-15` references missing basic word IDs (line 702);
- `bohairic.ot/bohairic.ot_CONLLU/05_Deuteronomium_19.conllu` — MWT `51-52` references missing basic word IDs (line 938);
- `bohairic.ot/bohairic.ot_CONLLU/18_Iob_11.conllu` — MWT `10-12` references missing basic word IDs (line 17);
- `bohairic.ot/bohairic.ot_CONLLU/19_Psalmi_102.conllu` — MWT `17-19` references missing basic word IDs (line 485);
- `bohairic.ot/bohairic.ot_CONLLU/24_Ieremias_24.conllu` — MWT `51-53` references missing basic word IDs (line 71);
- `book-bartholomew/book.bartholomew_CONLLU/book.bartholomew_part1.conllu` — basic token ID `0` (line 6341);
- `book-bartholomew/book.bartholomew_CONLLU/book.bartholomew_part2.conllu` — basic token ID `0` (line 933);
- `helias/helias_CONLLU/helias_martyrdom_part1.conllu` — basic token ID `0` (line 289);
- `helias/helias_CONLLU/helias_martyrdom_part4.conllu` — MWT `34-37` references missing basic word IDs (line 1068);
- `john-constantinople/john.constantinople_CONLLU/penitence.01.conllu` — MWT `2-5` references missing basic word IDs (line 7595);
- `life-hilaria/life.hilaria_CONLLU/life.hilaria.bnf132frg2.conllu` — malformed row ID `0-2` (line 198);
- `life-marina/life.marina_CONLLU/life.marina.HC_giron.conllu` — basic token ID `0` (line 542);
- `mercurius/mercurius_CONLLU/martyrdom.mercurius.conllu` — MWT `38-39` references missing basic word IDs (line 5135);
- `sahidica.nt/sahidica.nt_CONLLU/41_Mark_01.conllu` — dangling HEAD `32` (line 431);
- `sahidica.nt/sahidica.nt_CONLLU/41_Mark_07.conllu` — basic token ID `0` (line 632);
- `sahidica.nt/sahidica.nt_CONLLU/41_Mark_09.conllu` — basic token ID `0` (line 428);
- `theodosius-alexandria/theodosius.alexandria_CONLLU/Encomium_Michael_BL_OR_7021_part2.conllu` — MWT `73-75` references missing basic word IDs (line 1635);
- `theodosius-alexandria/theodosius.alexandria_CONLLU/Encomium_Michael_BL_OR_7021_part3.conllu` — MWT `8-10` references missing basic word IDs (line 1130);

Several documents contain additional errors beyond the representative first failure above. In particular, the previous regex-only MWT handling had missed real ranges whose numeric surface was syntactically plausible but whose endpoint word did not exist in the sentence. For example, `bohairic.nt/bohairic.nt_CONLLU/03_Luke_24.conllu` declares `46-49` although the sentence ends at basic word 48.

Classification: malformed/non-standard supplementary source. TT remains source-native authority. These CoNLL-U documents are excluded from semantic supplementation/parity and are never repaired heuristically. The standalone CoNLL-U audit and TT↔CoNLL-U parity audit share the same sentence-ID validator so an invalid document cannot pass through one path after failing the other.
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

PAULA document metadata covers all 2,628 records. Identity-level reconciliation matches all 2,628 PAULA document identities to all 2,628 TT document identities, with no PAULA-only or TT-only records. Eleven pairs differ only in filename case; both literal spellings remain recorded.

PAULA exposes the same 80 field names as TT metadata, but three fields have lower occurrence counts in PAULA:

- `document_cts_urn`: 2,579 PAULA vs 2,628 TT;
- `next`: 285 PAULA vs 1,828 TT;
- `previous`: 267 PAULA vs 1,810 TT.

The other 77 field counts match TT exactly.

Classification: identity-complete but lossy derived document-metadata serialization for these fields. PAULA is validation/corpus-provenance evidence, not a replacement for TT per-copy metadata.

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
