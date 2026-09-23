# CopticScriptorium-TF

CopticScriptorium-TF converts supported local Coptic Scriptorium TT sources into ordinary native [Text-Fabric](https://annotation.github.io/text-fabric/tf/index.html).

The converter preserves physical source documents, word slots, linguistic/grouping structure, layout boundaries, entities, English and Arabic translations, document relations, source metadata, and provenance. Structural relationships are native TF node/edge features; generated semantic features do not hide JSON/XML containers.

The complete pinned Coptic Scriptorium source tree has been converted and cleanly reloaded with the supported Text-Fabric version. This project validates converter behavior; it does not certify the scholarly correctness, completeness, licensing eligibility, or editorial quality of upstream Coptic Scriptorium data.

## Install and convert

Python 3.12 is required. From a checkout of this repository:

```bash
python -m pip install .
```

Convert a local Coptic Scriptorium source checkout:

```bash
python -m copticscriptorium_tf.converter \
  /path/to/CopticScriptorium-corpora \
  /path/to/output-tf \
  --upstream-repository CopticScriptorium/corpora \
  --upstream-commit <exact-source-commit> \
  --summary /path/to/conversion-summary.json
```

Supported input discovery includes both direct `<corpus>/<dataset>_TT/*.tt` datasets and `<corpus>/<dataset>_TT.zip` packages. The destination must not already exist. The repository/commit arguments record provenance for the local tree; conversion does not fetch data from the network.

The JSON summary contains operational counts, phase timings, output size, peak process RSS where available, and source records missing a literal license metadata field. It does not assign an aggregate license verdict and does not certify the corpus.

## Load and query

Load only the features needed for a task:

```python
from tf.fabric import Fabric

api = Fabric(locations=["/path/to/output-tf"], silent="deep").load(
    "norm lemma pos func source_record_id scholarly_id corpus dataset "
    "entity_class identity own_text "
    "dependency_head entity_head same_scholarly documented_overlap witness",
    silent="deep",
)
if not api:
    raise RuntimeError("Text-Fabric failed to load")
```

A physical TT record is the TF section unit. Resolve one by its stable `source_record_id`:

```python
document = api.T.nodeFromSection(("sahidica.nt/sahidica.nt:41_Mark_01",))

physical_id = api.F.source_record_id.v(document)
scholarly_id = api.F.scholarly_id.v(document)
corpus = api.F.corpus.v(document)
dataset = api.F.dataset.v(document)
```

`source_record_id` identifies the preserved physical source record. `scholarly_id` is a separate scholarly identifier, usually the source `document_cts_urn`, when present. Multiple physical records may therefore carry the same scholarly identity.

Normalized and diplomatic/original rendering use native TF text formats:

```python
normalized = api.T.text(document, fmt="text-orig-full")
diplomatic = api.T.text(document, fmt="text-diplomatic-full")
```

Word slots expose lexical and syntactic annotation directly:

```python
for word in api.F.otype.s("word"):
    lemma = api.F.lemma.v(word)
    pos = api.F.pos.v(word)
    func = api.F.func.v(word)

    # Outgoing dependency edge: dependent word -> head word.
    heads = tuple(api.E.dependency_head.f(word))
```

Entities are ordinary non-slot nodes with a native edge to the head word:

```python
for entity in api.F.otype.s("entity"):
    entity_class = api.F.entity_class.v(entity)
    identity = api.F.identity.v(entity)
    head_words = tuple(api.E.entity_head.f(entity))
```

English and Arabic translations are nodes with their own text:

```python
english = [api.T.text(n) for n in api.F.otype.s("translation")]
arabic = [api.T.text(n) for n in api.F.otype.s("arabic_translation")]
```

Document-level relations remain explicit rather than collapsing records:

```python
same_identity_records = tuple(api.E.same_scholarly.f(document))
documented_overlaps = tuple(api.E.documented_overlap.f(document))
witness_targets = tuple(api.E.witness.f(document))
```

The relation evidence is available in separate valued edge features such as `same_scholarly_classification`, `documented_overlap_classification`, `documented_overlap_family`, `witness_literal`, and `witness_target_scholarly_id`.

## Native TF model

The sole slot type is `word`. Non-slot node types are:

- `document`, `sentence`;
- `orig_group`, `norm_group`, `orig`;
- `page`, `column`, `line`;
- `entity`;
- `translation`, `arabic_translation`.

Frequently useful node/slot features include `source_record_id`, `source_word_ordinal`, `source_id`, `norm`, `lemma`, `pos`, `func`, `source_text`, `scholarly_id`, `corpus`, `dataset`, `source_path`, `source_sha256`, `packaging`, `entity_class`, `identity`, and `own_text`. Document metadata is projected as deterministic scalar `meta_*` features, including occurrence-suffixed features when a source metadata attribute is repeated.

Native edge features include `parent`, `direct_word`, `dependency_head`, `entity_head`, `same_scholarly`, `documented_overlap`, and `witness`, plus the valued relation-evidence features listed above.

Available text formats depend on the source content. The writer emits `text-orig-full` for normalized word text, `text-diplomatic-full` when diplomatic/original surfaces exist, and node-default own-text formats for translations and layout nodes.

## Measured full-corpus footprint

On the pinned upstream snapshot `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`, the reviewed full-source regression produced:

- 2,628 physical source records;
- 2,394,354 word slots;
- 3,854,785 non-slot nodes;
- 2,505,872 graph edges;
- 130 TF files totaling 618,769,322 bytes;
- 7,157.1 MiB peak process RSS;
- about 7m47s for the GitHub Actions smoke including conversion and clean reload.

These are reproducible measurements for that pinned source revision and CI environment, not fixed corpus invariants or hardware-independent performance guarantees. The earlier implementation peaked at 11,075.7 MiB; issue #26 reduced the retained-memory high-water mark while preserving output semantics.

## Agora integration status

The repository contains `agora.materializer.json` plus the offline `copticscriptorium_tf.agora` adapter. It has been validated against Agora's v1 materializer schema and exercised through Agora's real network-denied Bubblewrap host on synthetic TT input. The adapter supports both Agora-acquired Git input and user-local source directories, writes TF under the host-owned `tf/` output child, and records a stable `conversion-summary.json`.

CopticScriptorium-TF is **not yet canonically registered** in Agora, and automatic handoff of a materialized local artifact into Context-Fabric/cfabric-mcp is still an upstream post-1.0 boundary. Issue #17 remains open for those cross-repository gates. The presence of the manifest in this repository should therefore not be read as a released Agora catalog entry.

## Troubleshooting

If conversion reports `no supported TT source records`, check that the selected root contains direct `<corpus>/<dataset>_TT/*.tt` data or `<corpus>/<dataset>_TT.zip` archives. Unsupported nested layouts fail explicitly rather than being guessed.

If the destination already exists, choose a fresh output path. The direct converter refuses to overwrite an existing TF directory, and the Agora adapter requires the host-created staging directory to be empty before it creates its `tf/` child.

For load failures, use the package-pinned `text-fabric==13.1.0` environment and load the generated directory itself. Feature names are ordinary `*.tf` filenames and can be inspected before deciding which subset to load.

For full-corpus conversion, allow materially more memory than the serialized ~619 MB output size: the measured reviewed run peaked at roughly 7.0 GiB RSS. Smaller source subsets require less, but no fixed scaling ratio is promised.

Converter errors describe input/serialization failures. They are not reclassified as claims that upstream Coptic Scriptorium scholarship is wrong.

## Development process

Active changes follow research/plan → RED tests → minimal implementation → exact-head tests → logically independent adversarial review. Historical census workflows are manually dispatchable; ordinary implementation PRs keep focused regression checks and product-relevant integration gates.

Current release-facing follow-ups are:

- #17 — canonical Agora registration and the intended Context-Fabric/cfabric-mcp handoff;
- #18 — this user-facing documentation, finalized once #17's cross-repository path is available;
- #11 — parent first-usable-release epic.

## License

Software authored for this repository — converter code, utilities, tests, and software documentation — is licensed under the [MIT License](LICENSE). See [LICENSE_SCOPE.md](LICENSE_SCOPE.md) for the code/data boundary.

The MIT license does not apply to Coptic Scriptorium corpora, source texts, translations, annotations, metadata, or imported/generated data artifacts. Those retain the licenses and terms of their original corpora and sources.
