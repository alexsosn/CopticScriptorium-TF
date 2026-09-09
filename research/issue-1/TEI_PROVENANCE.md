# Issue #1 — TEI provenance and corpus-wide evidence

Pinned corpus revision: `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`.

Independent adversarial review of PR #7 found that TEI, like PAULA, had been represented mainly by samples. Unlike PAULA, TEI cannot be covered by the Pepper derivation argument: the public publishing pipeline requests TEI directly from GitDox with the `scriptorium_tei` or `scriptorium_tei_p` stylesheet, while TT is requested separately as `tt_sgml`. A separate corpus-wide gate was therefore required.

## Corpus-wide topology and identity

The pinned source contains:

- 76 datasets with TEI;
- 1,458 TEI XML paths;
- no TEI representation for `sahidic.ot/sahidic.ot` or `sahidica.nt/sahidica.nt`;
- all 1,458 TEI source identities paired to TT identities;
- no TEI-only source identities and no TT-only identities inside the 76 TEI datasets;
- 12 AP pairs whose filenames differ only by case.

TT archive packaging is opened during pairing, so Bohairic TT records are not falsely reported absent merely because their TEI counterparts are visible directories.

## Parseability and feature census

Seventy-three TEI files fail XML parsing with `mismatched tag` errors across 17 top-level corpora. The full generated error ledger records every source path and parse position. The other 1,385 files parse as TEI.

All 1,385 parseable documents contain:

- `teiHeader`;
- a CTS-bearing title reference;
- license metadata;
- language usage;
- repository metadata;
- sentence translation markup;
- word markup.

Morpheme elements are present in 1,314 parseable documents. Layout coverage includes page breaks in 377 documents, column breaks in 301 and line breaks in 313. Across the parseable corpus, **8,822 words contain page/column/line markup inside `<w>`**, independently confirming that diplomatic layout and linguistic segmentation intersect.

## TEI ↔ TT presence reconciliation

For the semantic families checked by the issue #1 authority decision, TEI contributes no unique presence for:

- CTS identity;
- lemma;
- fine POS;
- translation;
- page boundaries;
- column boundaries;
- line boundaries.

The single measured TEI-only presence is `license` in `book.bartholomew_part3`. TT metadata lacks `license` for Bartholomew parts 1–3; TEI parts 1 and 2 are among the malformed files, while part 3 parses and carries license evidence. This is passed to issue #8 and does not authorize a default license for the other records or publication without policy review.

## Authority conclusion

TEI remains useful diplomatic/presentation and independent validation evidence. Corpus-wide measurement found no required TEI-only semantic layer for the planned production graph, while 73 files are not XML-parseable at the pinned revision. TT retains the source-native event stream for document conversion; a TEI production parser should be introduced only if later graph/schema research identifies a concrete requirement unavailable from TT + validated CoNLL-U + reviewed metadata sources.
