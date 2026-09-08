# Research: Coptic Scriptorium → Text-Fabric

## Scope and pinned evidence

Issue #1 establishes the source-of-truth contract for Coptic Scriptorium → Text-Fabric conversion. The corpus-wide measurements in this document are pinned to:

- upstream repository: `CopticScriptorium/corpora`;
- upstream commit: `3ac067f1709a0012daf39ea8da2fac79980176a5`;
- upstream `meta.json` blob: `a0aa597fb413a63cb7b17f02570a4a5da166f45c`, 2,461,846 bytes.

The research workflow runs deterministic inventory, TT semantic census, CoNLL-U feature/validity census, TT↔CoNLL-U parity, and `meta.json` reconciliation against that exact revision. The detailed field decision is in `research/issue-1/SOURCE_AUTHORITY_MATRIX.md`; licensing evidence is in `research/issue-1/LICENSE_FINDINGS.md`.

## Corpus topology

The pinned source contains 79 top-level corpus directories and 78 detected corpus datasets. All 78 expose TT, CoNLL-U, PAULA and relANNIS packaging; 76 expose TEI. Packaging is not uniform: some large datasets expose TT or CoNLL-U as archives rather than visible per-record directories, so absence from GitHub code search or a directory listing is not evidence that a representation is absent.

The inventory found no zero-byte Git blobs at the pinned revision. Record-counterpart claims are made only where the representation is actually visible; opaque archives are classified as archives rather than guessed to contain or omit particular records.

## Canonical document stream

Upstream states that TreeTagger SGML (`*.tt`) generally contains the most complete document annotation, and corpus-wide research supports using TT as the source-native document stream.

The TT census contains 2,628 documents:

- 2,067 read from archive packaging;
- 561 read from visible TT directories;
- every TT document contains normalized-token markup and dependency `xml:id`/`func`/`head` structure;
- 1,490 contain `orig`/`orig_group`, `translation`, and the richer source stream associated with manually/recurrently represented documents;
- 1,652 contain entity markup; 1,326 contain entity identity/Wikification data;
- layout evidence occurs independently of token structure: page markup in 419 documents, column markup in 338, and line markup in 356.

A layout boundary can occur inside the rendered character content of a normalized linguistic token. The production parser therefore needs an event/stack or interval-aware model; ordinary XML containment assumptions and line-oriented parsing are unsafe.

TT metadata also has source anomalies that must remain visible. Sixty-four TT documents have duplicate metadata attribute names; six duplicate occurrences contain conflicting values rather than identical repetition. A source-native metadata lexer therefore preserves duplicate values and conflict evidence instead of relying on an XML parser that would reject or overwrite them.

## TT ↔ CoNLL-U identity and parity

There are 1,717 CoNLL-U source paths with matching TT source-record identities. CoNLL-U is not a complete replacement for TT:

- 911 additional TT records in `sahidic.ot` have no visible CoNLL-U counterpart at the pinned revision;
- 227 matching CoNLL-U files are whitespace-only placeholders in the aggregate Sahidica NT packaging and contain no semantic token stream;
- basic CoNLL-U validity checking finds 18 dependency-format errors across nine source files, including token ID `0`, negative HEAD values, and a dangling HEAD; invalid CoNLL-U sources are classified and excluded from semantic merge/parity rather than parsed permissively.

For structurally valid equal-token-count pairs, parity is measured token by token after resolving TT `xml:id`/`head` references and CoNLL-U sentence-local HEAD IDs to document token positions. The previously measured valid corpus showed complete normalized-token agreement and the following shared-field pattern:

- `norm`: no differences;
- lemma: one CoNLL-U value where TT is absent, no true lemma conflict;
- XPOS/fine POS: one true disagreement;
- dependency relation: thousands of true differences, demonstrating that CoNLL-U DEPREL is a normalized/derived syntactic view rather than a byte-equivalent copy of TT `func`;
- dependency head: most mismatches are CoNLL-U heads supplementing TT tokens with no explicit TT head, plus a very small number of true head disagreements.

The exact final counts are emitted by the pinned `cross-format-audit.json` artifact and must be treated as generated evidence rather than hand-maintained release constants.

## CoNLL-U-only enrichments

CoNLL-U remains important as a supplementary source after structural validation. At the pinned revision the census contains 1,565,983 basic token rows and 485,107 multiword-token rows. No enhanced-DEPS or empty-node rows were observed.

UD FEATS are widespread: all 1,490 non-placeholder documents counted before invalid-source exclusion contain core morphological feature coverage. CoNLL-U MISC also contains enrichments not measured as literal TT equivalents, including:

- `Cxn` / `CxnElt` in 1,042 documents;
- `Morphs` in 1,419 documents;
- `Orig` in 1,447 documents;
- `OrigLang` in 1,452 documents;
- `Subject` in 13 documents.

Therefore CoNLL-U is a validated supplementary authority for UD morphology/construction/enrichment features. It must not rewrite TT segmentation, original surface, layout, entity semantics, or per-copy metadata.

## `meta.json` reconciliation and metadata merge policy

Global `meta.json` contains 2,390 record keys. All 2,628 TT copies reconcile case-insensitively to those keys with no orphan TT records and no unused `meta.json` records:

- 2,152 global keys map to one TT copy;
- 238 global keys map to two TT copies.

This is consistent with the repository's documented duplicate/convenience-corpus topology and is one reason `meta.json` cardinality must not be mistaken for TT source-record cardinality.

`meta.json` is useful as a normalized/global metadata reference, but it is not an unconditional overwrite source. Many raw mismatches are representational: for example TT often stores a full HTML license or PATHS link while `meta.json` stores the normalized label/identifier. There are also asymmetric or malformed metadata field names in the global index, including literal keys such as `" segmentation"` and `"msItem_title "`. Those spellings are source evidence and must not be silently trimmed into another field.

Merge contract:

1. per-copy TT `<meta ...>` is authoritative for metadata attached to that specific source record;
2. `meta.json` supplies global/reference normalization and can fill a TT absence only under an explicitly defined field policy;
3. a value present on both sides is never silently overwritten when unequal;
4. literal source values and normalized values should remain distinguishable where normalization is useful;
5. corpus-level metadata found only in PAULA/relANNIS is dataset provenance and should not automatically be copied onto every document.

## Source-format authority summary

The production converter should begin with the smallest set of parsers that preserves measured semantics:

- **TT:** canonical source-native document stream for original/normalized segmentation, document metadata, layout, translations, entities/identities, source POS/lemma, source dependency relations/heads and annotation quality;
- **validated CoNLL-U:** supplementary authority for UD FEATS, construction/MISC enrichments, normalized dependency views, and heads absent from TT;
- **`meta.json`:** global metadata index/reference and normalized metadata evidence, never a blind replacement for TT metadata;
- **TEI:** presentation/diplomatic cross-check evidence; a production TEI parser should be added only if later research demonstrates a semantic field not preservable from TT plus validated CoNLL-U plus metadata;
- **PAULA/relANNIS:** corpus-level metadata/evidence; not required as a second token parser unless a concrete unique semantic layer is demonstrated.

This keeps production parsing narrower while retaining a measured escape hatch: if graph-model research in #3 identifies a required field with no authority in TT/validated CoNLL-U/`meta.json`, the missing representation must be researched and tested before adding another parser.

## Annotation quality metadata

TT exposes quality levels for segmentation, tagging, parsing, entities and identities, including `automatic`, `checked`, `gold`, and layer-specific `none`. These values are provenance and user-selectable quality information. They are not destructive preference rules: a gold/treebank copy does not authorize silently deleting an alternate upstream analysis.

## Duplicate, overlap and parallel-witness semantics

The upstream README identifies multiple overlap classes:

1. `coptic-treebank` repeats gold treebanked documents also present in source corpora;
2. individual biblical-book corpora overlap large automatically annotated Sahidic OT/NT collections and can contain different, generally more accurate analyses;
3. parallel witnesses can be marked `redundant="yes"` while remaining textually distinct.

Issue #2 owns stable scholarly identity, release-scoped source identity, duplicate/alternate-analysis classification, filtering semantics and preferred-analysis selection. Issue #1 therefore preserves copies and evidence rather than deduplicating them.

## Licensing and redistribution

The measured TT license census is heterogeneous. It includes CC-BY material, BY-SA 3.0/4.0, 11 BY-NC-SA 4.0 documents, Sahidica/Wells academic-use terms, public-domain-text-plus-CC-BY-annotations formulations, and several malformed textual variants of otherwise recognizable license strings. Three TT documents have no `license` attribute at the pinned revision.

A generated corpus cannot safely receive one blanket data license. Missing/unknown license metadata is fail-closed for publication until resolved. Converter code licensing is separate from generated-data distribution. Follow-up #8 owns the research/design/TDD work for normalized license families, redistribution compatibility, record filtering and a machine-readable attribution/provenance manifest.

## Lessons from previous TF converter projects

### Pseudepigrapha-TF

Practices retained here:

- pin an immutable upstream revision and source hashes;
- preserve literal source identifiers plus deterministic technical addressing;
- test real Text-Fabric behavior rather than only an internal graph;
- make technical-anchor rendering explicit;
- require raw-source → generated-TF semantic parity;
- validate corpus-scale invariants with indexed/linear algorithms;
- discover real-source exceptions in pinned CI, then add a failing synthetic fixture before adding support.

### TLHdig-TF

Failure modes explicitly guarded against:

- XML well-formedness cannot prove structure conservation;
- repairs/normalizations requiring philological decisions cannot hide inside parser cleanup;
- coverage needs a balancing ledger: input = converted + explicitly classified exclusions;
- human-facing section labels are not unique source identity;
- known-loss allowlists are regression guards, not evidence of zero defects;
- release artifacts must be immutable and provenance-bound;
- measured reports, not hand-maintained prose, are authoritative for corpus counts.

### ORACC-TF

Autonomous-development practices retained here:

- reconcile issue/PR/claim state before implementation;
- keep one canonical PR per active task;
- test the exact PR head;
- invalidate review after any implementation change;
- keep implementation reasoning and final adversarial review logically independent.

Issue #5 decides the minimal coordination machinery appropriate for this repository.

## Remaining design queue

- #2: document identity, overlap, redundancy and release-stable addressing;
- #3: Text-Fabric graph model for segmentation, syntax, entities, layout and translations;
- #5: autonomous-agent coordination protocol;
- #8: mixed-license release policy and machine-readable attribution manifest.

Production converter tickets should be derived from the reviewed outputs of #1–#3 rather than pre-created against an unreviewed graph schema.
