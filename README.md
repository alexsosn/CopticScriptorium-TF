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
copticscriptorium-tf \
  /path/to/CopticScriptorium-corpora \
  /path/to/output-tf \
  --upstream-repository CopticScriptorium/corpora \
  --upstream-commit <exact-source-commit> \
  --summary /path/to/conversion-summary.json
```

The installed `copticscriptorium-tf` command delegates to the same reviewed CLI as `python -m copticscriptorium_tf.converter`; the module form remains supported as an equivalent fallback. Supported input discovery includes both direct `<corpus>/<dataset>_TT/*.tt` datasets and `<corpus>/<dataset>_TT.zip` packages. Directory TT datasets/records and `*_TT.zip` archive packages must be physical paths in the handed-off source tree; symlinked `*_TT` directories, `.tt` members, and archive packages (including dangling symlinks) are rejected rather than followed or silently ignored. The destination must not already exist. The repository/commit arguments record provenance for the local tree; conversion does not fetch data from the network.

`--upstream-commit` must be a full 40-hex SHA-1 or 64-hex SHA-256 commit ID. Symbolic refs and abbreviated hashes are rejected before source parsing; for an intentionally unversioned local tree, use the explicit `unversioned-local` sentinel. The converter validates identifier form locally and does not contact the repository to prove membership.

The JSON summary contains operational counts, phase timings, output size, peak process RSS where available, and source records missing a literal license metadata field. It is operational metadata and must use a fresh path outside the TF destination; the converter rejects summary paths that already exist (including symlinks) or are equal to/nested under the TF destination before conversion starts. It does not assign an aggregate license verdict and does not certify the corpus.

## Browse locally

The installed wheel includes the corpus-specific configuration for the standard
Text-Fabric web application. Point the installed launcher at any freshly
generated TF directory:

```bash
copticscriptorium-tf-web /path/to/output-tf
```

No repository checkout is needed at runtime. The browser uses the physical
`source_record_id` document sections and the native normalized/diplomatic text
formats emitted by the converter. See [the local web-app guide](docs/web-app.md)
for the non-serving `--check` mode, raw Text-Fabric development command,
navigation, feature/query behavior, and the app's local-only boundary.

From a source checkout, the equivalent development/debugging command remains
`tf "app:$(pwd)/app" --locations=/path/to/output-tf --modules=.`.

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

## Researcher guide and query cookbook

For the full corpus model, annotation semantics, provenance/citation guidance, missing-value rules, and reproducible research recipes, see [the researcher guide](docs/researcher-guide.md).

The importable [query cookbook](examples/query_cookbook.py) runs directly against generated native TF and includes Text-Fabric Search examples for lexical/morphological filtering, dependencies, entities, document identity/relations, translations, rendering, and provenance tracing.

For interactive exploration of the same generated artifact, see the [Text-Fabric web-app guide](docs/web-app.md).

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

CopticScriptorium-TF is registered as a **standalone materializer** in
[Agora](https://github.com/alexsosn/Agora) (merged Agora
[PR #198](https://github.com/alexsosn/Agora/pull/198)). Its registry plugin ID is
`copticscriptorium-tf`; the materializer ID is
`copticscriptorium-text-fabric`. The registry pins an exact reviewed source
commit rather than a mutable tag. Registration is at **community** verification
level and makes no claim about the scholarly quality or licensing eligibility
of upstream corpus content.

### Materialize a local TT tree via Agora

From a checkout of the Agora repository, with a supported Python runtime and
OS sandbox available, run:

```bash
python scripts/agora_install_materializer.py list
python scripts/agora_install_materializer.py install copticscriptorium-tf \
  --approve-code-execution

python scripts/agora_materialize_registered.py \
  --plugin copticscriptorium-tf \
  --materializer copticscriptorium-text-fabric \
  --source /path/to/CopticScriptorium-corpora \
  --output /path/to/agora-output \
  --sandbox required
```

The installation flag is an explicit decision to run the third-party
Python packaging/build code; listing and passive fetching do not approve it.
The materializer executes in the required network-denied OS sandbox after
source handoff. The destination must be absent or empty. Output lives in
`/path/to/agora-output/tf/` as ordinary native Text-Fabric feature files;
`conversion-summary.json` and `agora-materialization.json` in the output
root are operational/provenance sidecars, not TF semantic containers.

The local-source route above was tested end to end on an actual Agora
installation, including sandboxed conversion, clean Text-Fabric reload,
and Context-Fabric/cfabric-mcp search. The integration smoke uses a small
synthetic TT fixture; the separate full-corpus Text-Fabric regression
and measured footprint appear above.

### Import the generated TF into Context-Fabric

Use the Context-Fabric MCP server (Python 3.13) and invoke its public tools,
passing a path accessible **on the MCP server host**. In a local deployment,
after completing the command above:

```text
install_local_corpus(source="/path/to/agora-output/tf", name="Coptic Scriptorium")
prepare_corpus(resource_id="<returned-id>", source_mode="offline")
load_corpus(resource_id="<returned-id>", source_mode="offline",
            features=["norm", "lemma", "pos", "source_record_id"])
describe_corpus(corpus="<returned-logical_name>")
search(corpus="<returned-logical_name>", template="word", return_type="count")
```

Use the actual `id` returned by `install_local_corpus` and `logical_name`
returned by `load_corpus`. These examples are MCP tool invocations, not shell
commands. The imported TF is copied into Context-Fabric's evictable managed
cache: it can be queried and later unloaded/removed, but the original TF
directory should be retained. This is an **explicit materialize-then-import
workflow**; Agora does not yet connect these operations automatically. The
`install_local_corpus` tool reads server-local paths and should not be exposed
unauthenticated on a remote transport. See the
[Agora local-import guide](https://github.com/alexsosn/Agora/blob/main/wiki/guides/context-fabric-local-import.md)
for limits, lifecycle, and feature-module behavior.

### Automatic upstream acquisition: outstanding limitation

The manifest now opts in to Agora's proposed `sparse_patterns` Git acquisition
(`/*/*_TT/**` and `/*/*_TT.zip`), which downloads TT directory files and
TT ZIP archives at the same pinned upstream commit without deliberately
materializing other formats. The host support is under review in
[Agora PR #210](https://github.com/alexsosn/Agora/pull/210).
**This is only a declaration**: existing Agora registry installations remain
pinned to the earlier reviewed Coptic plugin commit until that registry pin is
updated after both PRs are approved. A full real-source automatic acquisition
and conversion has not yet passed, so use `--source` meanwhile.

The materializer manifest also declares immutable Git acquisition from
`CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`.
Running the registered materializer without `--source` selects that acquisition
strategy, but its full-corpus end-to-end path **has not yet passed**. A CI
attempt hit the bounded **120-second** Git fetch timeout with an early EOF
while acquiring the approximately 2.7 GiB repository; conversion was never
reached in that attempt. See
[Agora #205](https://github.com/alexsosn/Agora/issues/205) and
[CopticScriptorium-TF #17](https://github.com/alexsosn/CopticScriptorium-TF/issues/17)
for this remaining gate. For now, use an already acquired local TT source tree
with `--source` or the direct converter documented above; do not treat the
declared automatic acquisition as a verified working full-corpus route.

## Troubleshooting

If conversion reports `no supported TT source records`, check that the selected root contains direct `<corpus>/<dataset>_TT/*.tt` data or `<corpus>/<dataset>_TT.zip` archives. Unsupported nested layouts fail explicitly rather than being guessed.

If the destination already exists, choose a fresh output path. The direct converter refuses to overwrite an existing TF directory, and the Agora adapter requires the host-created staging directory to be empty before it creates its `tf/` child. Likewise, `--summary` must name a fresh non-symlink path outside the TF destination; existing summary files/directories are never overwritten, and any already-existing ancestor of a new summary path must be a directory.

For load failures, use the package-pinned `text-fabric==13.1.0` environment and load the generated directory itself. Feature names are ordinary `*.tf` filenames and can be inspected before deciding which subset to load.

For full-corpus conversion, allow materially more memory than the serialized ~619 MB output size: the measured reviewed run peaked at roughly 7.0 GiB RSS. Smaller source subsets require less, but no fixed scaling ratio is promised.

Converter errors describe input/serialization failures. They are not reclassified as claims that upstream Coptic Scriptorium scholarship is wrong.

## Development process

Active changes follow research/plan → RED tests → minimal implementation → exact-head tests → logically independent adversarial review. Historical census workflows are manually dispatchable; ordinary implementation PRs keep focused regression checks and product-relevant integration gates.

Current release-facing follow-ups are:

- #17 — complete bounded automatic upstream acquisition (Agora #205); the registered local-source and explicit Context-Fabric handoff paths already work;
- #18 — maintain tested installation, feature/query, and Agora instructions;
- #11 — parent first-usable-release epic.

## License

Software authored for this repository — converter code, utilities, tests, and software documentation — is licensed under the [MIT License](LICENSE). See [LICENSE_SCOPE.md](LICENSE_SCOPE.md) for the code/data boundary.

The MIT license does not apply to Coptic Scriptorium corpora, source texts, translations, annotations, metadata, or imported/generated data artifacts. Those retain the licenses and terms of their original corpora and sources.
