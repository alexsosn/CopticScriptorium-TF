# Issue #1 semantic source samples

Status: **sample evidence supporting the corpus-wide authority decision**.

Research census commit: `3ac067f1709a0012daf39ea8da2fac79980176a5`.

Official upstream release immediately preceding that commit: `v6.3.0`, tag commit `d6332e37c7f92c737f51deb4f6e7ee872bfd603f`, published 2026-07-22. The research commit is two commits ahead of the release tag. GitHub compare reports one changed corpus file between the tag and research commit: `shenoute-errs/shenoute.errs_TT/shenoute.errs.XG336-343.tt`, whose metadata changes `people="-"` to `people="none"`. TF provenance therefore needs both a release label and an exact source commit; they are not interchangeable.

The hand-inspected samples below were used to formulate hypotheses. Final source authority is determined by the corpus-wide machine-generated audits summarized in `research.md` and `SOURCE_AUTHORITY_MATRIX.md`; sample observations do not override those measurements.

## Source-shape evidence

### AP / `apophthegmata.patrum`

Observed sibling exports:

- `_ANNIS/`
- `_CONLLU/`
- `_PAULA/`
- `_TEI/`
- `_TT/`

The PAULA directory is not a one-file-per-document XML directory in the observed AP snapshot: it contains `apophthegmata.patrum_PAULA.zip`. ANNIS is corpus-oriented relational data plus `ExtData` rather than a set of document files.

### `sahidica.nt`

This corpus uses a different physical packaging:

- `sahidica.nt_ANNIS.zip`
- `sahidica.nt_PAULA.zip`
- `sahidica.nt_TT.zip`
- `sahidica.nt_CONLLU/`

No sibling TEI artifact was observed at the top level. The final inventory therefore distinguishes format presence, directory/archive packaging, record-level visibility and actual missing counterparts instead of inferring one from another.

### `bohairic.ot`

Corpus-wide relANNIS inspection established a distinct package shape: `bohairic.ot_ANNIS.zip` contains ANNIS configuration/visualization assets (`annis.version`, `resolver_vis_map.annis`, `corpus.properties`, CSS/fonts and related files) but no `corpus.annis`/`corpus_annotation.annis` or legacy `.tab` metadata tables.

The final relANNIS census records this package explicitly as metadata-unavailable rather than silently skipping it or inventing a third metadata layout. Its 507 `meta.json` identities exactly account for the 507 global metadata records not represented by the 77 parseable relANNIS metadata datasets.

## Paired sample: AP.004.poemen.65

### TT

Path: `AP/apophthegmata.patrum_TT/AP.004.poemen.65.tt`

Observed in one stream:

- dense document metadata, including CTS URN, per-document license, annotation-quality fields, manuscript/repository data, `redundant`, PATHS links, version metadata, translations and source attribution;
- `orig_group → norm_group → orig → norm` structure;
- normalized token local IDs (`u1`, `u2`, ...), `head`, `func`, `pos`, `lemma`, normalized form and sentence-start markers;
- entity spans, entity class, entity head token and identity where supplied;
- page/column/line/chapter/verse markers;
- translations and an Arabic translation layer;
- language and highlighting/rendition markers.

A line boundary can split the rendered character content of one normalized token. The TT serialization therefore cannot be treated as ordinary well-nested XML or as one-token-per-line input.

### TEI

Path: `AP/apophthegmata.patrum_TEI/AP.004.poemen.65.xml`

Observed strengths:

- rich `teiHeader` manuscript/source/responsibility/license metadata;
- CTS-ref title;
- EpiDoc-style diplomatic hierarchy and layout markers;
- sentence-level English translations;
- words with lemma and fine POS;
- morpheme elements;
- language and rendition/highlight spans.

In this sample TEI does not expose UD dependency arcs or the entity identity layer in the same direct form as TT, and it does not expose the sampled Arabic translation layer. No corpus-wide evidence in issue #1 demonstrated a required TEI-only semantic field, so TEI remains validation/presentation evidence rather than a mandatory second production token parser.

### CoNLL-U

Path: `AP/apophthegmata.patrum_CONLLU/AP.004.poemen.65.conllu`

Observed strengths:

- stable sentence records within the export;
- normalized sentence text and English sentence translation;
- multiword-token rows corresponding to bound groups;
- lemma, UPOS, fine XPOS;
- normalized UD morphological FEATS;
- HEAD/DEPREL;
- original-form residue, entity spans/identities, original language and morph decomposition in MISC;
- construction (`Cxn`/`CxnElt`) annotations on some tokens.

The corpus-wide parity audit confirmed the sample hypothesis: CoNLL-U is not a replacement for TT, but structurally valid CoNLL-U contributes measured supplementary UD morphology, construction/MISC enrichment and some dependency heads absent from TT.

## Documentary sample: CPR 4.16

Paths sampled:

- `doc-papyri/doc.papyri_TT/cpr.4.16.tt`
- `doc-papyri/doc.papyri_TEI/cpr.4.16.xml`
- `doc-papyri/doc.papyri_CONLLU/cpr.4.16.conllu`

The TEI header records CTS identity, author, papyri.info source, annotation/translation responsibility, CC-BY 4.0 license, object type, repository/collection/inventory number, language and bibliography. The TT header carries corresponding document metadata plus annotation-quality and entity/identity fields. CoNLL-U supplies normalized UD morphology/dependencies and entity encoding but not the full codicological/layout metadata.

This sample supports the same division of responsibilities measured corpus-wide.

## Bohairic sample: Jonah 1

Path: `bohairic-jonah/bohairic.jonah_TT/bohairic.Jonah_01.tt`

Observed differences from the Sahidic literary sample are data values rather than a different TT grammar: Bohairic language, book/chapter metadata, digital-edition provenance, public-domain Coptic text plus CC-BY 4.0 annotations/files, parsing automatic, segmentation/tagging checked, entity/identity values `none`, and contextual LXX English translation. The same orig/norm groups and UD local-token/dependency attributes are present.

The corpus-wide TT census did not require a dialect-specific parser grammar.

## Treebank copy vs source corpus: XH204-216

Source path: `shenoute-fox/shenoute.fox_TT/XH204-216.tt`

Treebank path: `coptic-treebank/coptic.treebank_TT/XH204-216.tt`

Upstream documentation describes treebank documents as identical to their source-corpus documents, but the two current TT blobs are not byte-identical:

- source blob SHA: `4a0fad1a7e116b3b17d3a8d1054ac56f7a4b249e`;
- treebank blob SHA: `3f72359386e0dba64d9130c95e4516c4a38dd0e8`.

The treebank copy includes `Arabic_translation="Philippe Zaher"` while the sampled source-corpus copy does not, even though both share the same scholarly CTS identity. Corpus-wide `meta.json` reconciliation later measured 238 global identities with two TT copies, confirming that physical source copy and scholarly document identity must remain distinct. Issue #2 owns deduplication/preference semantics.

## Parallel witness sample: Abraham Our Father XL93-94

Path: `abraham/shenoute.abraham_TT/XL93-94.tt`

Observed metadata includes `redundant="yes"`, CTS identity `urn:cts:copticLit:shenoute.abraham.monbxl:23-24`, and a `witness` relation to `urn:cts:copticLit:shenoute.abraham.monbya:21-27`, which is present as `YA535-540.tt`.

`redundant=yes` is therefore not a sufficient identity model. The explicit witness relation is scholarly data to preserve; issue #2 owns its final graph/selection semantics.

## Translation-delivery wording

The v6.3.0 release text says Arabic translations are available in ANNIS, while pinned TT samples visibly contain Arabic translation metadata/content as well. Issue #1 therefore does not encode an “ANNIS-only Arabic” assumption from release prose. TT remains the source-native translation stream unless a later graph-model requirement demonstrates a concrete missing layer.

## Final sample-to-census conclusion

The samples motivated the corpus-wide tests, and those tests establish the operative contract:

- TT is the canonical source-native document stream;
- structurally validated CoNLL-U is a supplementary authority for measured UD-normalized/enrichment fields;
- `meta.json` is global/reference metadata, not a blind overwrite source;
- relANNIS provides measurable corpus/document metadata where its tables are present, with config-only packaging recorded explicitly;
- TEI and PAULA remain evidence/cross-check sources unless later work demonstrates a required field unavailable from the narrower parser set;
- source copies, normalized metadata, derived views and scholarly identities retain separate provenance.

The remaining work after issue #1 is design/implementation work in #2, #3, #5 and #8 plus the independent adversarial review of this exact final research head.