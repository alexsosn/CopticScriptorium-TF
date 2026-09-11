# Research: Coptic Scriptorium → Text-Fabric

## Scope and pinned evidence

Issue #1 establishes the source-authority contract for Coptic Scriptorium → Text-Fabric conversion. All corpus-wide measurements below are pinned to:

- upstream repository: `CopticScriptorium/corpora`;
- exact upstream commit: `3ac067f1709a0012daf39ea8da2fac79980176a5`;
- immediately preceding upstream release: `v6.3.0` (`d6332e37c7f92c737f51deb4f6e7ee872bfd603f`);
- upstream `meta.json` blob: `a0aa597fb413a63cb7b17f02570a4a5da166f45c`, 2,461,846 bytes.

The research revision is two commits ahead of `v6.3.0`, including a source metadata normalization. Every local TF materialization must retain the immutable source repository/commit as provenance; a human-facing upstream release label may be retained in addition but does not replace the exact revision.

The CI research workflow reruns deterministic source inventory, TT semantic census, strict CoNLL-U validation, TT↔CoNLL-U parity, `meta.json` reconciliation, relANNIS metadata reconciliation, PAULA package/metadata reconciliation, TEI census, TEI↔TT coverage, and the issue #2 identity/overlap and preference audits against that exact upstream revision. Generated JSON artifacts are the measurement authority; this document summarizes them.

## Corpus topology and packaging

The pinned tree contains 79 top-level corpus directories and 78 detected datasets. All 78 expose TT, CoNLL-U, PAULA and ANNIS package presence; 76 expose TEI.

Packaging is heterogeneous:

- TT: 561 directory files plus 2,067 members of aggregate ZIP packages;
- CoNLL-U: 1,717 directory files plus 911 root-level members of `sahidic.ot/sahidic.ot_CONLLU.zip`;
- PAULA: 78 packages in the sparse research checkout; `bohairic.nt` and `bohairic.ot` use an observed one-level outer ZIP containing a single inner `*_PAULA.zip`;
- ANNIS: 77 packages with parseable metadata tables plus one configuration-only `bohairic.ot` package;
- TEI: 1,458 visible XML paths in 76 directory datasets.

Opaque packaging is never evidence that a source record is absent. Record counterpart claims are made only when identities are observable or a package is opened explicitly. The CoNLL-U audit therefore uses one shared source iterator for directory files and the measured archive layouts, so standalone validation and TT↔CoNLL-U parity see the same source set.

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

The pinned export contains **2,628 CoNLL-U documents**, 2,181,412 basic-token rows and 682,360 multiword-token rows. No empty-node rows or enhanced-DEPS rows were observed.

Strict validation reports **57 structural errors across 40 documents**: 38 multiword-token ranges reference one or more missing basic word IDs, ten non-positive basic token IDs are present, one malformed multiword ID (`0-2`) occurs, seven HEAD values are negative, and one HEAD is dangling. These defects include cases that a regex-only MWT check had previously missed; for example, `bohairic.nt/03_Luke_24` declares range `46-49` but the sentence ends after basic word 48. Malformed documents remain in an error ledger and contribute no semantic supplementation.

CoNLL-U-specific enrichment coverage includes `Cxn/CxnElt` in 1,746 documents, `Morphs` in 2,271, `Orig` in 2,335, `OrigLang` in 2,359 and `Subject` in 15.

All **2,628 TT identities have CoNLL-U counterparts**. Of these, 227 CoNLL-U files are whitespace-only placeholders and 40 are structurally invalid. The remaining **2,361 documents / 2,104,966 basic tokens** compare token-for-token with no token-count mismatch:

| Field | True semantic differences | Present only in CoNLL-U | Present only in TT | Serialization-equivalent raw differences |
| --- | ---: | ---: | ---: | ---: |
| `norm` | 0 | 0 | 0 | 4 |
| lemma | 0 | 1 | 0 | 4 |
| fine POS / XPOS | 1 | 0 | 0 | 0 |
| dependency relation | 4,902 | 0 | 0 | 0 |
| dependency head | 0 | 52,773 | 0 | 0 |

The four raw `norm` differences and the same four lemma differences are XML-entity serialization only: TT metadata/token parsing yields literal `<`/`>` while the CoNLL-U fields retain `&lt;`/`&gt;`. The audit preserves both literal values and raw mismatch counts while classifying these separately from semantic conflicts.

CoNLL-U HEAD IDs are normalized from sentence-local IDs to document token positions before comparison. Valid CoNLL-U can therefore supplement missing TT heads, while its normalized DEPREL layer must not overwrite TT `func`. There are no TT-only or CoNLL-U-only source identities after archive-packaged `sahidic.ot` is opened.

## `meta.json` reconciliation

Global `meta.json` contains 2,390 keys. All 2,628 TT copies reconcile case-insensitively to those keys, with no orphan TT records and no unused global records:

- 2,152 keys map to one TT copy;
- 238 keys map to two TT copies.

Physical source-copy identity and scholarly identity are therefore distinct concepts. Issue #2 measures the overlap/preference semantics directly below.

`meta.json` is useful normalized/global evidence, but it is not an unconditional overwrite source. TT may preserve HTML/PATHS values while `meta.json` stores normalized labels or identifiers. Literal anomalous keys such as `" segmentation"` and `"msItem_title "` also exist and must remain distinguishable from derived normalized forms.

## relANNIS metadata reconciliation

The 78 ANNIS source packages balance as 77 parseable metadata datasets plus one configuration-only `bohairic.ot` archive containing viewer/configuration assets but no corpus/document metadata tables.

The 77 parseable datasets contain 77 corpus nodes and 1,991 document nodes. Every relANNIS document matches `meta.json`; there are no relANNIS document orphans. The 507 `meta.json` keys without relANNIS documents all map to `bohairic.ot`, completely explaining the configuration-only gap.

relANNIS document values often differ textually from normalized `meta.json`, reinforcing non-destructive merge rules. Corpus-node annotations remain dataset-level provenance rather than values copied blindly to every document.

## PAULA corpus-wide audit and reconciliation

The PAULA audit opens all 78 pinned packages, including the one-level wrapper ZIPs used by Bohairic NT/OT, and parses 118,511 PAULA XML members with no package errors after the observed source shapes are modelled explicitly.

Publishing provenance shows that Coptic Scriptorium imports TT into Pepper/Salt, adds order relations, injects corpus metadata, and exports the same graph through PAULA and ANNIS. Corpus measurement is consistent with that derivation:

- PAULA contains metadata for all **2,628 document records**;
- identity-level reconciliation matches all **2,628 PAULA records to 2,628 TT records**, with **0 PAULA-only** and **0 TT-only** identities; 11 pairs differ only by filename case and retain both literal spellings;
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
- the single measured TEI-only presence is `license` for `book.bartholomew_part3`, whose TT metadata lacks a license. This is additional source-license evidence that the local materializer should report; it is not a reason to infer a blanket license. The TEI files for Bartholomew parts 1 and 2 are themselves malformed.

No corpus-wide evidence demonstrates a required TEI-only semantic layer for the production graph. TEI therefore remains diplomatic/presentation validation evidence; malformed files are explicitly ledgered rather than silently skipped.

## Metadata merge contract

1. Per-copy TT `<meta ...>` is authoritative for metadata attached to that physical source record.
2. `meta.json` is global/reference normalization evidence and may fill an absence only under an explicit field policy.
3. relANNIS/PAULA corpus metadata is dataset-level provenance unless a reviewed design maps a field to documents.
4. PAULA document metadata is derived/redundant evidence and is demonstrably less complete for three TT metadata fields; it does not displace TT.
5. Unequal values present on multiple sides are recorded, never silently overwritten.
6. Literal source values and normalized forms remain separately recoverable.
7. Missing metadata has a deterministic identity ledger containing field, physical source, corpus and CTS URN where available.

The missing-metadata ledger identifies three TT records without `license`: `book.bartholomew` parts 1–3. The local materializer must report unresolved/missing license evidence and must not assign a blanket data license. Public redistribution policy is deferred in #8 and does not block local conversion.

## Source authority contract

The local converter/materializer should start with the smallest measured parser set:

- **TT:** canonical source-native document stream for original/normalized segmentation, per-copy metadata, layout, translations, entities/identities, source POS/lemma, source dependency relations/heads and annotation-quality provenance.
- **Validated CoNLL-U:** supplementary authority for UD FEATS, construction/MISC enrichments, normalized dependency relations, and dependency heads absent from TT. Structurally invalid documents contribute no semantic enrichment.
- **`meta.json`:** global metadata index/reference and normalization evidence, never a blind replacement for TT metadata.
- **relANNIS/PAULA:** measured corpus-level/provenance evidence. PAULA document metadata adds no unique field vocabulary and has lower coverage for three fields; relANNIS/PAULA therefore do not become production document parsers from issue #1.
- **TEI:** measured diplomatic/presentation cross-check. All TEI identities pair to TT; no required TEI-only semantic layer was found, and 73 TEI files are malformed XML. A production TEI parser should be introduced only from a later measured requirement.

Issue #3 may widen this parser set only from measured need, with a new research/TDD gate.

## Identity, overlap, redundancy, and preference policy

Issue #2 measures identity independently from format counterpart matching. The pinned TT corpus has **2,628 physical source records and 2,520 valid literal scholarly CTS identities**. Every physical record has a usable `document_cts_urn` on this revision; there are no missing, malformed, or conflicting scholarly IDs. Of the 2,520 CTS identities, 2,412 occur once and **108 occur twice**.

The 108 duplicate-CTS groups are heterogeneous:

- 91 are byte-identical;
- one is a core-identical source variant: raw TT differs while original/normalized text and linguistic analysis agree;
- 15 contain alternate linguistic analyses of the same text;
- one has textual divergence.

Accordingly, neither CTS equality nor convenience-treebank membership is a deduplication instruction. `coptic-treebank` participates in 86 duplicate groups and spans all four measured classes; `bohairic-treebank` contributes 22 byte-identical pairs on this revision. All physical records remain stored/addressable by default.

The biblical book↔aggregate overlaps documented upstream form a separate relation because the paired records have different literal CTS identities. All 36 documented pairs are present: 16 Mark, 16 1 Corinthians and four Ruth. Nineteen pairs are alternate analyses and 17 are textually divergent; none are byte/core-identical. No filename/CTS-similarity heuristic is permitted to infer additional relations.

`redundant=yes` is another independent axis. Eighteen records are marked redundant, one without a witness value. There are **111 witness-bearing records** overall: 28 values are pure CTS and 83 are free text. Five free-text values also contain embedded CTS URNs. Across all witness metadata the audit extracts **35 CTS targets from 33 relations, and all 35 resolve** to known scholarly identities on the pinned corpus. The literal witness string is retained separately from extracted target relations.

Identity fingerprints are classification evidence, not public identifiers: raw TT SHA-256, original/normalized text fingerprints, and analysis fingerprints are recomputed for each pinned source revision. Public identity remains split between source-revision-scoped source record identity (dataset + literal record path, bound to upstream repository/commit/hash) and literal scholarly CTS identity.

Default local materialization is one logical union TF corpus preserving every physical source record. Corpus/dataset membership stays queryable, so corpus-specific use does not require separately maintained TF artifacts. An explicit future corpus-selection option may materialize a subset for resource reasons, but it must use the same identity/schema contract and may not deduplicate overlaps silently.

User-facing selection is non-destructive. The `all` view preserves every physical record. `nonredundant` hides only literal `redundant=yes` records from that view. A `source-preferred` view is evidence-backed only for the 92 duplicate groups that are byte/core-identical and contain exactly one convenience-treebank copy plus one source copy; the 16 alternate/textually divergent groups remain multi-valued. `best-parsing` has **zero unique winners** on this revision: all 108 duplicate groups tie on parsing quality (104 gold/gold, four automatic/automatic), so deterministic ordering of tied source IDs must not be represented as a scholarly preference.

The detailed ADR and machine-testable invariants live in `research/issue-2/IDENTITY_POLICY.md`. Issue #3 and materializer #11 may consume these identity levels and relations, but neither may collapse them.

## Licensing boundary for local materialization

The TT census contains 17 literal license strings, including CC-BY, BY-SA 3.0/4.0, 11 BY-NC-SA 4.0 documents, Sahidica/Wells academic-use terms, public-domain-text-plus-CC-BY-annotations formulations and malformed/ambiguous string variants. At least four records combine a BY-SA URL with visible text `CC-BY 4.0`; URL and label cannot be normalized independently without conflict handling.

Three `book.bartholomew` records have no TT `license` attribute. TEI supplies a license only for part 3 among the three, while parts 1 and 2 are malformed TEI. The converter/materializer must preserve literal per-record license evidence, report missing/unresolved evidence, and avoid claiming one blanket data license for the locally generated output.

A full aggregate redistribution/publication policy is not required for the current product path. Issue #8 is closed as deferred/not planned and should be reopened only if this project later decides to distribute prebuilt generated TF data.

## Follow-up queue

- #3 — Text-Fabric graph model for the union local corpus: segmentation, syntax, entities, layout, translations, identity/overlap relations and corpus views;
- #11 — Agora-compatible local Coptic Scriptorium → Text-Fabric materializer, after #2 and #3 are reviewed;
- #5 — autonomous-agent coordination protocol;
- #8 — deferred public redistribution policy, not a local-materialization blocker.

Converter/materializer implementation should be derived from the independently reviewed outputs of #1–#3. The current target is reproducible local generation from original sources, not publication of prebuilt TF corpora.