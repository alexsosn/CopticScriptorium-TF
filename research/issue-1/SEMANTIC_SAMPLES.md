# Issue #1 semantic source samples

Status: **sample evidence, not yet a corpus-wide authority decision**.

Research census commit: `3ac067f1709a0012daf39ea8da2fac79980176a5`.

Official upstream release immediately preceding that commit: `v6.3.0`, tag commit `d6332e37c7f92c737f51deb4f6e7ee872bfd603f`, published 2026-07-22. The research commit is two commits ahead of the release tag. GitHub compare reports one changed corpus file between the tag and research commit: `shenoute-errs/shenoute.errs_TT/shenoute.errs.XG336-343.tt`, whose metadata changes `people="-"` to `people="none"`. Final TF provenance therefore needs both a release label and an exact source commit; they are not interchangeable.

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

No sibling TEI artifact was observed at the top level. This invalidates any inventory algorithm that equates format presence with a `_FORMAT/` directory or calls a CoNLL-U document “missing TT” merely because TT members are hidden inside an archive.

The inventory therefore distinguishes:

1. format presence;
2. packaging (`directory` vs `archive`);
3. record-level visibility in the Git tree;
4. missing counterparts only among formats whose record members are actually visible.

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

In this sample TEI does not expose the UD dependency arcs or the entity identity layer in the same direct form as TT. It also does not expose the sampled Arabic translation layer.

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

CoNLL-U drops the full manuscript/layout/formatting structure and is therefore not suitable as the sole canonical source. Conversely, the sampled normalized UD FEATS/construction annotations are richer/more normalized than the literal attributes visible on corresponding TT tokens, so CoNLL-U cannot be discarded without a field-level parity check.

## Documentary sample: CPR 4.16

Paths sampled:

- `doc-papyri/doc.papyri_TT/cpr.4.16.tt`
- `doc-papyri/doc.papyri_TEI/cpr.4.16.xml`
- `doc-papyri/doc.papyri_CONLLU/cpr.4.16.conllu`

The TEI header records CTS identity, author, papyri.info source, annotation/translation responsibility, CC-BY 4.0 license, object type, repository/collection/inventory number, language and bibliography. The TT header carries corresponding document metadata plus annotation-quality and entity/identity fields. CoNLL-U supplies normalized UD morphology/dependencies and entity encoding but not the full codicological/layout metadata.

The same split of responsibilities seen in AP therefore also appears in a documentary corpus family.

## Bohairic sample: Jonah 1

Path: `bohairic-jonah/bohairic.jonah_TT/bohairic.Jonah_01.tt`

Observed differences from the Sahidic literary sample are data values, not a different TT grammar: Bohairic language, book/chapter metadata, digital-edition provenance, public-domain Coptic text plus CC-BY 4.0 annotations/files, parsing automatic, segmentation/tagging checked, entity/identity values `none`, and contextual LXX English translation. The same orig/norm groups and UD local-token/dependency attributes are present.

This supports one parser grammar across at least sampled Sahidic and Bohairic TT, while feature presence/quality must remain data-driven rather than assumed.

## Treebank copy vs source corpus: XH204-216

Source path: `shenoute-fox/shenoute.fox_TT/XH204-216.tt`

Treebank path: `coptic-treebank/coptic.treebank_TT/XH204-216.tt`

Upstream documentation describes treebank documents as identical to their source-corpus documents, but the two current TT blobs are not byte-identical:

- source blob SHA: `4a0fad1a7e116b3b17d3a8d1054ac56f7a4b249e`
- treebank blob SHA: `3f72359386e0dba64d9130c95e4516c4a38dd0e8`

The first metadata line already differs: the treebank copy includes `Arabic_translation="Philippe Zaher"`, while the sampled source-corpus copy does not. Both share the same scholarly CTS identity.

Consequences for issue #2:

- byte equality is insufficient as the definition of duplicate/identity;
- a corpus membership/export record and a scholarly document identity need separate representation;
- deduplication requires layer-aware comparison and an explicit preferred-source policy;
- provenance must retain which physical source copy supplied each merged field if fields differ.

## Parallel witness sample: Abraham Our Father XL93-94

Path: `abraham/shenoute.abraham_TT/XL93-94.tt`

Observed metadata:

- `redundant="yes"`;
- document CTS URN `urn:cts:copticLit:shenoute.abraham.monbxl:23-24`;
- `witness="urn:cts:copticLit:shenoute.abraham.monbya:21-27"`;
- `previous` and `next` also point at that CTS URN in this record;
- gold segmentation/tagging/parsing/entities/identities;
- deprecated CTS URN retained separately.

The referenced witness is present as `abraham/shenoute.abraham_TT/YA535-540.tt` with CTS URN `urn:cts:copticLit:shenoute.abraham.monbya:21-27`.

`redundant=yes` is therefore not a sufficient identity model by itself. At least one observed record supplies an explicit inter-witness scholarly relation that should be preserved.

## Translation-layer conflict to measure

The v6.3.0 release text says Arabic translations are currently available in ANNIS. Current TT samples also visibly contain Arabic translation metadata/content (for example AP.004 and multiple AP records). This may reflect wording about a specific public interface, a post-export difference, or multiple delivery paths. Do not encode an “ANNIS-only Arabic” rule from release prose; measure the actual pinned artifacts.

## Preliminary authority matrix

| Layer | TT sample | CoNLL-U sample | TEI sample | PAULA / ANNIS | Current research stance |
|---|---|---|---|---|---|
| Document CTS identity | yes | document id, not full header parity checked | yes | metadata present in ANNIS | compare; likely TT/metadata merge |
| Per-document license | yes | not full header | yes | expected metadata | TT/TEI/metadata parity check |
| Annotation quality | yes | not sampled as full doc metadata | not sampled | ANNIS corpus annotation contains fields | TT + metadata parity check |
| Original/diplomatic text | yes | residue in MISC | yes, rich rendering | not yet inspected inside PAULA archive | TT/TEI parity check |
| Normalized groups/tokens | yes | yes | word/phrase representation, not same normalization layer | not yet inspected | TT primary candidate |
| Lemma/fine POS | yes | yes | yes | likely | compare |
| UD HEAD/DEPREL | yes | yes | not in sampled TEI | ANNIS likely graph export | TT primary candidate, CoNLL-U verifier |
| Normalized UD FEATS | limited literal attrs in sample | rich | not in sampled TEI | not yet measured | CoNLL-U supplementary candidate |
| Entity span/class/head/identity | yes | MISC encoding | not in sampled TEI | ANNIS likely | TT primary candidate |
| Layout/page/column/line | yes | no full structure | yes | not yet measured | TT/TEI parity check |
| Highlight/language spans | yes | reduced MISC | yes | not yet measured | TT/TEI parity check |
| English translation | yes | sentence text_en | yes | likely | compare alignment |
| Arabic translation | yes in sampled TT | not sampled | absent in sampled TEI | release says ANNIS delivery | measure actual artifacts |
| Corpus-level metadata | upstream README says incomplete | incomplete | document-oriented | upstream README says PAULA/relANNIS | PAULA/ANNIS/meta required candidate |

## Licensing boundary already established from upstream documentation

The repository is not governed by one uniform data license. Upstream documentation lists the normal CC-BY 3.0/4.0 case and major exceptions including:

- Sahidica New Testament specific license;
- Canons of Apa Johannes under CC-BY-SA 3.0;
- Sahidic Old Testament under CC-BY-SA 4.0;
- per-file licensing metadata.

The converter must carry per-document/per-source license provenance and the release process must not replace it with one repository-level license label.

## Remaining before source authority can be finalized

- complete machine-generated inventory from the pinned tree, including archive packaging;
- inspect archive contents for record-level coverage where needed;
- measure TT ↔ CoNLL-U UD field parity beyond hand samples;
- measure TT ↔ TEI diplomatic/layout parity;
- inspect PAULA and ANNIS metadata contents systematically and compare them with TT/meta.json;
- quantify metadata conflicts rather than choose precedence by convenience;
- classify every missing/opaque/empty/malformed source shape;
- independent adversarial review of the final authority/merge recommendation.
