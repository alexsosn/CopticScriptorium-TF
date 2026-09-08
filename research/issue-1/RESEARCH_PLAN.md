# Issue #1 research plan — source formats and canonical conversion contract

Pinned upstream repository: `CopticScriptorium/corpora`

Pinned upstream commit: `3ac067f1709a0012daf39ea8da2fac79980176a5` (master at the start of this research cycle; commit date 2026-07-27)

## Question

Which upstream representation is authoritative for each semantic layer needed by CopticScriptorium-TF, and how can those layers be combined reproducibly without silently preferring a lossy or stale export?

## Method

The research is split into two independent kinds of evidence.

### A. Corpus-wide structural inventory

Use the Git tree at the pinned commit rather than GitHub code-search counts. Code search omits large/unindexed files and therefore cannot be used as a record census.

Inventory must record:

- every top-level corpus directory;
- every format directory ending in `_TT`, `_CONLLU`, `_TEI`, `_PAULA`, `_ANNIS`;
- source-record paths/stems in record-oriented formats;
- zero-byte blobs and unexpected extensions;
- missing format counterparts by source-record stem where comparison is meaningful;
- `meta.json` presence, blob SHA, and byte size;
- format-directory and record counts by corpus;
- source blob SHA/size for all record-oriented files so the report is pinned and reproducible.

Do not infer that a file is absent merely because GitHub code search does not return it.

### B. Semantic parity/authority sampling

Compare the same document across formats in several corpus families, at minimum:

1. literary/monastic Sahidic (`AP`);
2. documentary papyri (`doc-papyri`);
3. biblical Sahidic material with known overlap;
4. Bohairic material;
5. a gold treebank copy and its source-corpus counterpart;
6. a `redundant="yes"` parallel-witness case;
7. a document with entities/identities;
8. a document where layout boundaries cross normalized-token rendering.

For each paired document, compare the presence and semantics of:

- corpus/document metadata and CTS identity;
- per-document license and annotation-quality metadata;
- original/diplomatic surface;
- normalized groups and normalized tokens;
- `orig_group → norm_group → orig → norm` relationships;
- lemma and fine POS;
- UD morphology where present;
- dependency head/relation/root and sentence boundaries;
- entity span, head, class, and identity/Wikification;
- page/column/line/verse/chapter/layout boundaries;
- text formatting/highlighting/language spans;
- translations and secondary translations;
- manuscript/repository/bibliography metadata;
- redundancy/parallel/overlap indicators.

## Initial evidence already established

### Upstream topology

The root tree contains many corpus directories plus a root `meta.json` blob. At the pinned commit `meta.json` has blob SHA `a0aa597fb413a63cb7b17f02570a4a5da166f45c` and size 2,461,846 bytes.

A representative corpus (`AP`) contains sibling format directories for ANNiS, CoNLL-U, PAULA, TEI, and TreeTagger SGML.

### Paired document: AP.004.poemen.65

The paired AP document already shows that the formats are not interchangeable:

- `*.tt` carries a dense document-level metadata record including annotation-quality fields, license, CTS URN, redundant flag, manuscript/source metadata, named people/places, PATHS links, version metadata, and multiple translation/source fields.
- `*.tt` preserves original groups, normalized groups, original surface segments, normalized token/morpheme records, local token IDs, dependency heads/relations, entities, entity heads/identities, translations, and page/column/line structure in one stream.
- TEI preserves rich diplomatic/layout markup, manuscript description, responsibility/license metadata, word/lemma/POS structure, morpheme markup, language/highlight markup, and sentence translations. It does not expose the sampled UD dependency arcs or entity/identity layer in the same way.
- CoNLL-U is convenient for sentence segmentation, UD dependency heads/relations, UD morphological features, multiword-token/bound-group spans, normalized token text, original-form residue, and entity encoding in MISC. It drops the full manuscript/layout/formatting structure and is therefore unsuitable as the sole canonical source.
- A line boundary can occur inside the rendered character content of one linguistic token in TT/TEI. Layout and linguistic segmentation therefore have intersecting spans and cannot be reduced safely to one ordinary XML-style containment tree.

These observations are sample evidence only; corpus-wide authority is not declared until the inventory and conflict measurements are complete.

## Hypotheses to test, not assumptions

1. TT is the most appropriate primary annotation stream because upstream describes it as generally the most complete representation and the paired sample confirms it contains layers missing from CoNLL-U/TEI.
2. PAULA and/or relANNIS may be required for corpus-level metadata, but their field-level contribution and disagreement rate must be measured.
3. `meta.json` may be the most efficient document-metadata index, but it must be checked against TT/PAULA/ANNIS for missing fields, stale values, duplicate identities, and license/quality disagreements.
4. CoNLL-U may contain UD feature normalization or construction annotations not represented literally in TT, so it should be compared as a possible supplementary authority for UD-specific fields rather than discarded as a convenience export.
5. TEI may be the clearest authority for diplomatic rendering and layout/formatting details, but TT may preserve equivalent information in a non-nested stream. Exact parity must be measured before introducing a second parser solely for presentation markup.

## Failure classification

Every source-record anomaly found by the inventory must be classified as one of:

- valid record with all expected counterparts;
- valid record with intentional format asymmetry;
- valid metadata-only/non-textual record;
- duplicate copy / alternate analysis / parallel witness (identity policy deferred to #2);
- malformed source requiring explicit handling;
- empty source;
- unsupported source shape;
- license-restricted distribution case;
- unexplained missing counterpart (research blocker/defect until resolved).

No category may be implemented as a silent skip.

## Reproducibility deliverables

- `research/issue-1/inventory.py`: deterministic inventory over a Git Trees API JSON response or local checkout; network transport is kept outside the pure analysis core.
- tests for format classification, record-stem matching, zero-byte detection, and deterministic report ordering;
- machine-readable inventory JSON produced from the pinned tree;
- source-format/feature authority matrix;
- measured conflict report from paired documents;
- update to root `research.md` with the reviewed canonical-input recommendation and metadata merge policy.

## Gates

1. Research plan reviewed against issue #1.
2. RED-first tests for the inventory tool.
3. Implement inventory tool.
4. Run on the pinned upstream tree and inspect exceptions.
5. Perform semantic pair comparisons and conflict measurements.
6. Write canonical-input/merge recommendation.
7. Logically independent adversarial review of the research evidence and recommendation.
8. Merge only if #1 acceptance criteria are met; no production converter code in this ticket.
