# Research: Coptic Scriptorium → Text-Fabric

## Scope and pinned evidence

Issue #1 establishes the source-authority contract for Coptic Scriptorium → Text-Fabric conversion. All corpus-wide measurements below are pinned to:

- upstream repository: `CopticScriptorium/corpora`;
- exact upstream commit: `3ac067f1709a0012daf39ea8da2fac79980176a5`;
- immediately preceding upstream release: `v6.3.0` (`d6332e37c7f92c737f51deb4f6e7ee872bfd603f`);
- upstream `meta.json` blob: `a0aa597fb413a63cb7b17f02570a4a5da166f45c`, 2,461,846 bytes.

The exact commit matters in addition to the release label: the research revision is two commits ahead of `v6.3.0`, including a source metadata normalization. Generated TF provenance must therefore retain the immutable source commit as well as any human-facing release label.

The CI research workflow runs deterministic source inventory, TT semantic census, strict CoNLL-U structural validation, TT↔CoNLL-U parity, `meta.json` reconciliation, and relANNIS metadata reconciliation against that exact upstream revision. The generated JSON artifacts are the authoritative measurements; prose summarizes them.

## Corpus topology and packaging

The pinned tree contains 79 top-level corpus directories and 78 detected corpus datasets. All 78 expose TT, CoNLL-U, PAULA and ANNIS packaging; 76 expose TEI.

Packaging is heterogeneous. TT is read from 561 visible files and 2,067 members of aggregate ZIP packages. ANNIS has 78 source packages, of which 77 contain parseable corpus/document metadata tables and one (`bohairic.ot/bohairic.ot_ANNIS.zip`) contains ANNIS configuration/viewer assets but no corpus metadata tables. That package is recorded explicitly as `configuration_only`; it is not silently treated as a metadata dataset.

Opaque packaging is never evidence that a source record is missing. Record-level counterpart claims are made only where record identities are observable or where the audit explicitly opens the package.

## Canonical TT document stream

Upstream describes TreeTagger SGML (`*.tt`) as generally carrying the most complete document annotation, and the corpus-wide census supports using TT as the source-native document stream.

The TT census contains 2,628 documents. Every document contains normalized-token markup and the source dependency `xml:id`/`func`/`head` structure. Additional measured layers include:

- `orig` / `orig_group`: 1,490 documents;
- translations: 1,490 documents;
- Arabic translation markup: 96 documents;
- entities: 1,652 documents;
- entity identity/Wikification: 1,326 documents;
- page boundaries: 419 documents;
- column boundaries: 338 documents;
- line boundaries: 356 documents.

Layout boundaries can cross the rendered character content of linguistic tokens. Production conversion therefore needs an event/interval-aware representation; ordinary XML containment or one-token-per-line assumptions are unsafe.

TT metadata also contains source anomalies that must remain visible. Sixty-four documents contain duplicate metadata attribute names. There are 121 equal-value duplicate occurrences and six conflicting duplicate occurrences. The source-native metadata lexer preserves those values and conflict evidence rather than accepting XML-parser rejection or silent last-value overwrite.

## Strict CoNLL-U validation

The pinned export contains 1,717 CoNLL-U documents, 1,565,983 basic-token rows and 485,106 multiword-token rows. No empty-node rows or enhanced-DEPS rows were observed.

Strict structural validation reports 19 errors across nine documents:

- ten non-positive basic token IDs;
- one malformed multiword-token ID (`0-2`);
- seven negative HEAD values;
- one dangling HEAD reference.

Malformed documents are retained in the error ledger and excluded from semantic supplementation/parity. They are not repaired heuristically.

CoNLL-U-specific enrichments remain substantial. Document coverage includes:

- `Cxn` / `CxnElt`: 1,042 documents;
- `Morphs`: 1,419 documents;
- `Orig`: 1,447 documents;
- `OrigLang`: 1,452 documents;
- `Subject`: 13 documents.

Core UD FEATS are present throughout the 1,490 non-placeholder documents, with individual feature families varying by applicability.

## TT ↔ CoNLL-U parity

There are 1,717 paired TT/CoNLL-U source identities. Of these, 227 CoNLL-U files are whitespace-only placeholders and nine CoNLL-U documents are structurally invalid. The remaining **1,481 documents / 1,547,873 basic tokens** compare successfully token-for-token with no token-count mismatch.

Measured shared-field results:

| Field | True differences | Present only in CoNLL-U | Present only in TT |
| --- | ---: | ---: | ---: |
| `norm` | 0 | 0 | 0 |
| lemma | 0 | 1 | 0 |
| fine POS / XPOS | 1 | 0 | 0 |
| dependency relation | 4,718 | 0 | 0 |
| dependency head | 0 | 54,747 | 0 |

CoNLL-U HEAD IDs are resolved sentence-locally and normalized to document token positions before comparison. The absence of true head conflicts after strict validation is evidence for using valid CoNLL-U heads to supplement missing TT heads. The 4,718 relation differences show that CoNLL-U DEPREL is a normalized/derived syntactic view and must not overwrite TT `func` as though the fields were equivalent.

There are 911 TT records with no CoNLL-U counterpart, all in `sahidic.ot`; there are no CoNLL-U-only source identities.

## `meta.json` reconciliation

Global `meta.json` contains 2,390 record keys. All 2,628 TT copies reconcile case-insensitively to those keys, with no orphan TT records and no unused `meta.json` records:

- 2,152 keys map to one TT copy;
- 238 keys map to two TT copies.

This confirms that `meta.json` identity cardinality and physical TT source-copy cardinality are different concepts. Issue #2 owns the scholarly identity/overlap model; issue #1 preserves both.

`meta.json` is useful as normalized/global metadata evidence, but it is not an unconditional overwrite source. Raw mismatches are often representational: TT may preserve an HTML license or PATHS link while `meta.json` stores a normalized label/identifier. The global index also contains literal anomalous keys such as `" segmentation"` and `"msItem_title "`. Literal source evidence and normalized values must remain distinguishable.

## relANNIS metadata reconciliation

The 78 ANNIS source packages balance as follows:

- 74 directory-packaged metadata datasets;
- 3 archive-packaged metadata datasets;
- 1 configuration-only archive (`bohairic.ot`) with no corpus/document metadata tables.

The 77 parseable metadata datasets contain 77 corpus nodes and 1,991 document nodes. All 1,991 relANNIS documents match `meta.json`; there are no relANNIS document orphans. There are 507 `meta.json` keys without a relANNIS document, and all 507 map to `bohairic.ot` TT records from the single configuration-only ANNIS package. No second unexplained metadata-coverage gap remains.

relANNIS document metadata disagrees textually with normalized `meta.json` for many fields, especially license/source/translation values, and also exposes encoded/asymmetric field names. This reinforces the non-destructive merge policy rather than creating a new precedence rule. Corpus-node annotations include corpus/project/language/version/license/source information and remain dataset-level provenance rather than values to copy blindly onto every document.

## Metadata merge contract

1. Per-copy TT `<meta ...>` is authoritative for metadata attached to that physical source record.
2. `meta.json` is global/reference normalization evidence and may fill an absence only under an explicit field policy.
3. relANNIS/PAULA corpus metadata is dataset-level provenance unless a later design explicitly maps a field to documents.
4. Unequal values present on multiple sides are recorded, never silently overwritten.
5. Literal source values and normalized forms remain separately recoverable.
6. Missing metadata has a deterministic identity ledger containing field, physical source, corpus, and CTS URN where available.

The missing-metadata ledger identifies three TT records without a `license` attribute; all are `book.bartholomew` parts 1–3. Publication of those records is fail-closed pending issue #8.

## Source authority contract

The production converter should start with the smallest measured parser set:

- **TT:** canonical source-native document stream for original/normalized segmentation, per-copy metadata, layout, translations, entities/identities, source POS/lemma, source dependency relations/heads and annotation-quality provenance.
- **Validated CoNLL-U:** supplementary authority for UD FEATS, construction/MISC enrichments, normalized dependency relations, and dependency heads absent from TT. Structurally invalid documents contribute no semantic enrichment.
- **`meta.json`:** global metadata index/reference and normalization evidence, never a blind replacement for TT metadata.
- **relANNIS/PAULA:** corpus-level metadata/evidence. relANNIS is measured directly for issue #1; its document-level values do not displace per-copy TT metadata.
- **TEI:** diplomatic/presentation cross-check evidence. A production TEI parser should be added only if graph/schema research demonstrates a required semantic layer that TT + validated CoNLL-U + metadata cannot preserve.

Issue #3 may widen this parser set only from measured need, with a new research/TDD gate.

## Identity and overlap boundary

Upstream contains several distinct overlap relationships: treebank copies of source-corpus documents, individual biblical-book corpora overlapping aggregate collections, and parallel witnesses marked `redundant="yes"`. Sampled treebank/source copies can share scholarly CTS identity while differing in metadata, and an observed `redundant=yes` record also carries an explicit `witness` CTS relation.

Issue #2 therefore owns release-stable source identity, scholarly identity, alternate-analysis classification, witness relations, filtering and preferred-analysis policy. Issue #1 does not deduplicate physical source records.

## Licensing boundary

The TT census contains 17 literal license strings, including CC-BY, BY-SA 3.0/4.0, 11 BY-NC-SA 4.0 documents, Sahidica/Wells academic-use terms, public-domain-text-plus-CC-BY-annotations formulations and malformed/ambiguous string variants. At least four records combine a BY-SA URL with visible text `CC-BY 4.0`; URL and label therefore cannot be normalized independently without conflict handling.

Three `book.bartholomew` records have no TT `license` attribute. Generated data cannot safely receive one blanket data license. Issue #8 owns license-family normalization, source-term resolution, distribution filtering and the machine-readable attribution/provenance manifest.

## Follow-up queue

- #2 — document identity, overlap, redundancy, witnesses and release-stable addressing;
- #3 — Text-Fabric graph model for segmentation, syntax, entities, layout and translations;
- #5 — autonomous-agent coordination protocol;
- #8 — mixed-license release policy and attribution manifest.

Production converter implementation should be derived from the reviewed outputs of #1–#3 rather than from an unreviewed graph schema.
