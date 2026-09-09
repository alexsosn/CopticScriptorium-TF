# Research: Coptic Scriptorium → Text-Fabric

## Scope and pinned evidence

Issue #1 establishes the source-authority contract for Coptic Scriptorium → Text-Fabric conversion. All corpus-wide measurements below are pinned to:

- upstream repository: `CopticScriptorium/corpora`;
- exact upstream commit: `3ac067f1709a0012daf39ea8da2fac79980176a5`;
- immediately preceding upstream release: `v6.3.0` (`d6332e37c7f92c737f51deb4f6e7ee872bfd603f`);
- upstream `meta.json` blob: `a0aa597fb413a63cb7b17f02570a4a5da166f45c`, 2,461,846 bytes.

The research revision is two commits ahead of `v6.3.0`, including a source metadata normalization. Generated TF provenance must therefore retain the immutable source commit as well as any human-facing release label.

The CI research workflow reruns deterministic source inventory, TT semantic census, strict CoNLL-U validation, TT↔CoNLL-U parity, `meta.json` reconciliation, relANNIS metadata reconciliation, PAULA package/metadata reconciliation, TEI census, and TEI↔TT coverage against that exact upstream revision. Generated JSON artifacts are the measurement authority; this document summarizes them.

## Corpus topology and packaging

The pinned tree contains 79 top-level corpus directories and 78 detected datasets. All 78 expose TT, CoNLL-U, PAULA and ANNIS package presence; 76 expose TEI.

Packaging is heterogeneous:

- TT: 561 directory files plus 2,067 members of aggregate ZIP packages;
- PAULA: 78 packages in the sparse research checkout; `bohairic.nt` and `bohairic.ot` use an observed one-level outer ZIP containing a single inner `*_PAULA.zip`;
- ANNIS: 77 packages with parseable metadata tables plus one configuration-only `bohairic.ot` package;
- TEI: 1,458 visible XML paths in 76 directory datasets.

Opaque packaging is never evidence that a source record is absent. Record counterpart claims are made only when identities are observable or a package is opened explicitly.

## Canonical TT document stream

The TT census contains 2,628 documents. Every document contains normalized-token markup and source dependency `xml:id`/`func`/`head` structure. Additional measured layers include:

- `orig` / `orig_group`: 1,490 documents;
- translations: 1,490 documents;
- Arabic translation markup: 96 documents;
- entities: 1,652 documents;
- entity identity/Wikification: 1,326 documents;
- page boundaries: 419 documents;
- column boundaries: 338 documents;
- line boundaries: 356 documents.

Layout boundaries can cross the rendered character content of linguistic tokens. Production conversion therefore needs an event/interval-aware representation; ordinary XML containment or one-token-per-line assumptions are unsafe.

TT metadata contains source anomalies that remain visible. Sixty-four documents contain duplicate metadata attribute names: 121 equal-value duplicate occurrences and six conflicting occurrences. The source-native metadata lexer preserves all literal values/conflicts rather than relying on XML overwrite behaviour.

## Strict CoNLL-U validation and parity

The pinned export contains 1,717 CoNLL-U documents, 1,565,983 basic-token rows and 485,106 multiword-token rows. No empty-node rows or enhanced-DEPS rows were observed.

Strict validation reports 19 structural errors across nine documents: ten non-positive basic token IDs, one malformed multiword ID (`0-2`), seven negative HEAD values and one dangling HEAD. Malformed documents remain in an error ledger and contribute no semantic supplementation.

CoNLL-U-specific enrichment coverage includes `Cxn/CxnElt` in 1,042 documents, `Morphs` in 1,419, `Orig` in 1,447, `OrigLang` in 1,452 and `Subject` in 13.

There are 1,717 paired TT/CoNLL-U identities. Of these, 227 CoNLL-U files are whitespace-only placeholders and nine are structurally invalid. The remaining **1,481 documents / 1,547,873 basic tokens** compare token-for-token with no token-count mismatch:

| Field | True differences | Present only in CoNLL-U | Present only in TT |
| --- | ---: | ---: | ---: |
| `norm` | 0 | 0 | 0 |
| lemma | 0 | 1 | 0 |
| fine POS / XPOS | 1 | 0 | 0 |
| dependency relation | 4,718 | 0 | 0 |
| dependency head | 0 | 54,747 | 0 |

CoNLL-U HEAD IDs are normalized from sentence-local IDs to document token positions before comparison. Valid CoNLL-U can therefore supplement missing TT heads, while its normalized DEPREL layer must not overwrite TT `func`. There are 911 TT records without CoNLL-U counterparts, all in `sahidic.ot`; there are no CoNLL-U-only identities.

## `meta.json` reconciliation

Global `meta.json` contains 2,390 keys. All 2,628 TT copies reconcile case-insensitively to those keys, with no orphan TT records and no unused global records:

- 2,152 keys map to one TT copy;
- 238 keys map to two TT copies.

Physical source-copy identity and scholarly identity are therefore distinct concepts. Issue #2 owns overlap/preference semantics.

`meta.json` is useful normalized/global evidence, but it is not an unconditional overwrite source. TT may preserve HTML/PATHS values while `meta.json` stores normalized labels or identifiers. Literal anomalous keys such as `" segmentation"` and `"msItem_title "` also exist and must remain distinguishable from derived normalized forms.

## relANNIS metadata reconciliation

The 78 ANNIS source packages balance as 77 parseable metadata datasets plus one configuration-only `bohairic.ot` archive containing viewer/configuration assets but no corpus/document metadata tables.

The 77 parseable datasets contain 77 corpus nodes and 1,991 document nodes. Every relANNIS document matches `meta.json`; there are no relANNIS document orphans. The 507 `meta.json` keys without relANNIS documents all map to `bohairic.ot`, completely explaining the configuration-only gap.

relANNIS document values often differ textually from normalized `meta.json`, reinforcing non-destructive merge rules. Corpus-node annotations remain dataset-level provenance rather than values copied blindly to every document.

## PAULA corpus-wide audit and reconciliation

The PAULA audit opens all 78 pinned packages, including the one-level wrapper ZIPs used by Bohairic NT/OT, and parses 118,511 PAULA XML members with no package errors after the observed source shapes are modelled explicitly.

Publishing provenance shows that Coptic Scriptorium imports TT into Pepper/Salt, adds order relations, injects corpus metadata, and exports the same graph through PAULA and ANNIS. Corpus measurement is consistent with that derivation:

- PAULA contains metadata for all **2,628 document records**;
- PAULA document metadata exposes exactly the same **80 field names** observed in TT metadata;
- there are **0 document metadata field names unique to PAULA** and **0 TT document metadata field names absent from the PAULA vocabulary**;
- coverage differs only for three fields: `document_cts_urn` is present in 2,579 PAULA documents vs 2,628 TT documents, `next` in 285 vs 1,828, and `previous` in 267 vs 1,810;
- all other 77 document metadata fields have equal document-level occurrence counts;
- PAULA also contains 18 corpus-scope metadata types. Four (`Project`, `projects`, `verion_date`, `version_number`) are not TT document metadata fields and therefore remain dataset-level provenance rather than justification for a PAULA document parser.

Actual Coptic PAULA document metadata uses `featList` anchored to `xml:base="anno.xml"`; token-level features such as POS use mark/token bases. The audit treats `annoFeat` as annotation inventory, not metadata, and fails closed on unclassified/ambiguous package layouts.

The measured result supports using PAULA as reproducibility/corpus-metadata evidence without adding it to the production document-parser set.

## TEI corpus-wide audit and TT coverage

TEI is independently generated by the publishing pipeline rather than derived through Pepper, so it received a separate corpus-wide audit.

- 76 datasets contain 1,458 TEI paths;
- all 1,458 identities have TT counterparts, with 12 filename case variants and no TEI-only source identities;
- 73 TEI files are malformed XML (`mismatched tag`) across 17 top-level corpora; 1,385 parse successfully;
- all 1,385 parseable documents expose TEI header, CTS reference, license, language usage, repository metadata, sentence translation and word markup;
- 1,314 have morpheme elements;
- 8,822 words contain page/column/line layout boundaries inside `<w>`, independently confirming intersecting linguistic/layout segmentation;
- presence-level TEI↔TT comparison finds no TEI-only candidate for CTS, lemma, POS, translation, page, column or line data;
- the single measured TEI-only presence is `license` for `book.bartholomew_part3`, whose TT metadata lacks a license. This is additional evidence for issue #8, not permission to infer publication eligibility. The TEI files for Bartholomew parts 1 and 2 are themselves malformed.

No corpus-wide evidence demonstrates a required TEI-only semantic layer for the production graph. TEI therefore remains diplomatic/presentation validation evidence; malformed files are explicitly ledgered rather than silently skipped.

## Metadata merge contract

1. Per-copy TT `<meta ...>` is authoritative for metadata attached to that physical source record.
2. `meta.json` is global/reference normalization evidence and may fill an absence only under an explicit field policy.
3. relANNIS/PAULA corpus metadata is dataset-level provenance unless a reviewed design maps a field to documents.
4. PAULA document metadata is derived/redundant evidence and is demonstrably less complete for three TT metadata fields; it does not displace TT.
5. Unequal values present on multiple sides are recorded, never silently overwritten.
6. Literal source values and normalized forms remain separately recoverable.
7. Missing metadata has a deterministic identity ledger containing field, physical source, corpus and CTS URN where available.

The missing-metadata ledger identifies three TT records without `license`: `book.bartholomew` parts 1–3. Publication is fail-closed pending issue #8.

## Source authority contract

The production converter should start with the smallest measured parser set:

- **TT:** canonical source-native document stream for original/normalized segmentation, per-copy metadata, layout, translations, entities/identities, source POS/lemma, source dependency relations/heads and annotation-quality provenance.
- **Validated CoNLL-U:** supplementary authority for UD FEATS, construction/MISC enrichments, normalized dependency relations, and dependency heads absent from TT. Structurally invalid documents contribute no semantic enrichment.
- **`meta.json`:** global metadata index/reference and normalization evidence, never a blind replacement for TT metadata.
- **relANNIS/PAULA:** measured corpus-level/provenance evidence. PAULA document metadata adds no unique field vocabulary and has lower coverage for three fields; relANNIS/PAULA therefore do not become production document parsers from issue #1.
- **TEI:** measured diplomatic/presentation cross-check. All TEI identities pair to TT; no required TEI-only semantic layer was found, and 73 TEI files are malformed XML. A production TEI parser should be introduced only from a later measured requirement.

Issue #3 may widen this parser set only from measured need, with a new research/TDD gate.

## Identity and overlap boundary

Upstream contains treebank copies of source-corpus documents, individual biblical-book corpora overlapping aggregate collections and parallel witnesses marked `redundant="yes"`. Sampled copies can share scholarly CTS identity while differing in metadata; an observed redundant record also carries an explicit `witness` CTS relation.

Issue #2 therefore owns release-stable source identity, scholarly identity, alternate-analysis classification, witness relations, filtering and preferred-analysis policy. Issue #1 discards none of these physical records.

## Licensing boundary

The TT census contains 17 literal license strings, including CC-BY, BY-SA 3.0/4.0, 11 BY-NC-SA 4.0 documents, Sahidica/Wells academic-use terms, public-domain-text-plus-CC-BY-annotations formulations and malformed/ambiguous string variants. At least four records combine a BY-SA URL with visible text `CC-BY 4.0`; URL and label cannot be normalized independently without conflict handling.

Three `book.bartholomew` records have no TT `license` attribute. TEI supplies a license only for part 3 among the three, while parts 1 and 2 are malformed TEI. Generated data cannot safely receive one blanket data license. Issue #8 owns license-family normalization, source-term resolution, distribution filtering and the machine-readable attribution/provenance manifest.

## Follow-up queue

- #2 — document identity, overlap, redundancy, witnesses and release-stable addressing;
- #3 — Text-Fabric graph model for segmentation, syntax, entities, layout and translations;
- #5 — autonomous-agent coordination protocol;
- #8 — mixed-license release policy and attribution manifest.

Production converter implementation should be derived from the independently reviewed outputs of #1–#3 rather than from an unreviewed graph schema.
