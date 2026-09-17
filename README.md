# CopticScriptorium-TF

A pre-alpha converter from Coptic Scriptorium TT sources to ordinary native [Text-Fabric](https://annotation.github.io/text-fabric/tf/index.html).

The converter preserves physical source documents, one TT `norm` as one `word` slot, linguistic/grouping structure, layout boundaries, entities, translations, document relations, source metadata, and source provenance. Structural relationships are represented with normal TF node/edge features; generated semantic features do not hide internal JSON/XML containers.

## Current status

The source parser, deterministic graph builder, native TF writer, and end-to-end local converter are implemented. Current release work is validating the complete upstream corpus and reducing full-corpus resource usage before calling the converter practically ready for broad local use.

The first complete-source #16 run reached TF writing with about 7.1 GB maximum RSS before exposing a trailing-layout edge case. Memory reduction is tracked separately in #26; the converter is therefore still **pre-alpha** and full-corpus conversion should currently be treated as memory-heavy.

This repository converts local source data. It does not download Coptic Scriptorium data itself and does not certify the scholarly correctness or completeness of upstream corpora.

## Local conversion

Use Python 3.12 with the supported Text-Fabric version:

```bash
python -m pip install 'text-fabric==13.1.0'
```

From the repository root, convert a local Coptic Scriptorium source checkout:

```bash
python -m copticscriptorium_tf.converter \
  /path/to/CopticScriptorium-corpora \
  /path/to/output-tf \
  --upstream-repository CopticScriptorium/corpora \
  --upstream-commit <exact-source-commit> \
  --summary /path/to/conversion-summary.json
```

The input tree may contain supported direct `*_TT/*.tt` datasets and `*_TT.zip` packages. The destination must not already exist; conversion fails closed rather than overwriting it. The repository/commit arguments are provenance labels for the local source tree and do not trigger network access.

The JSON summary is operational only: source-document, slot/node/edge and output-file counts, phase timings, output size, and peak process RSS where the platform exposes it. It is not a corpus-certification report.

Generated TF can then be loaded with normal Text-Fabric APIs, for example:

```python
from tf.fabric import Fabric

api = Fabric(locations=["/path/to/output-tf"], silent="deep").load(
    "norm lemma pos source_record_id dependency_head entity_head",
    silent="deep",
)
```

## Native TF model

The current model uses:

- `word` as the sole slot type;
- `document` as the TF section level, keyed by physical `source_record_id`;
- `oslots` for node loci;
- scalar node features for lexical, source, layout, translation, provenance, and document metadata values;
- native `parent`, `direct_word`, `dependency_head`, `entity_head`, `same_scholarly`, `documented_overlap`, and `witness` edges;
- separate valued edge features for document-relation evidence;
- normalized and diplomatic text formats plus own-text rendering for translations/layout nodes.

Repeated metadata attributes are preserved as deterministic scalar occurrence features rather than serialized arrays. Literal source metadata may itself contain markup-like text; that literal content is preserved as data and is not used as a hidden structural encoding.

## Development process

The `research/` directory contains measured source investigations and schema decisions that preceded implementation. Active converter changes follow research/plan → RED tests → implementation → exact-head tests → independent adversarial review.

Important active follow-ups include:

- #16 — complete-source end-to-end converter/reload regression;
- #26 — reduce full-corpus peak memory for practical local use;
- #17 — later Agora integration/distribution work.

Historical research scripts and pinned-source regression fixtures are evidence for converter decisions; they are not release-certification machinery.

## License

Software authored for this repository — including converter code, utility scripts, tests, and supporting software documentation — is licensed under the [MIT License](LICENSE). See [LICENSE_SCOPE.md](LICENSE_SCOPE.md) for the explicit code/data boundary.

The MIT license does **not** apply to Coptic Scriptorium corpora, source texts, translations, annotations, metadata, or imported/generated data artifacts. Those retain the licenses and terms of their original corpora and sources, and corpus/document-level provenance should preserve the applicable upstream licensing information.
