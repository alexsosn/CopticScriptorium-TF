# Local Text-Fabric web application

CopticScriptorium-TF includes a configuration-only app for the standard
Text-Fabric 13.1.0 browser. It reads the same native `.tf` files produced by
the converter; there is no second semantic store and no JSON/XML sidecar model.

## Launch

When CopticScriptorium-TF is installed from its wheel, the shortest path is:

```bash
copticscriptorium-tf-web /path/to/output-tf
```

The installed launcher locates the wheel-packaged corpus app configuration and
delegates normal serving to Text-Fabric 13.1.0's standard browser entry point.
It does not require a repository checkout and does not copy configuration or
semantic sidecars into the generated TF directory.

For a non-serving validation that loads the generated TF and constructs the
standard Flask browser application, use:

```bash
copticscriptorium-tf-web /path/to/output-tf --check
```

Standard Text-Fabric browser flags are passed through. For example,
`-noweb` starts the server without automatically opening a browser window.

For app development/debugging from a repository checkout, the equivalent raw
Text-Fabric command remains:

```bash
tf "app:$(pwd)/app" --locations=/path/to/output-tf --modules=.
```

The `--locations` argument points directly at the generated TF directory and
`--modules=.` tells Text-Fabric that the feature files are in that directory.
The app configuration deliberately has no remote corpus repository, so neither
launcher path fetches a prebuilt corpus.

## Navigation and text

The browser has one section level: a physical `document`, addressed by its
`source_record_id`, for example
`sahidica.nt/sahidica.nt:41_Mark_01`. This is distinct from
`scholarly_id`, which may be shared by multiple physical records.

The default format is `text-orig-full`, the writer's normalized Coptic word
text. When the source provides diplomatic/original surfaces, choose
`text-diplomatic-full` from the Text-Fabric format control. Both formats come
from native `otext.tf` metadata and ordinary scalar features emitted by the
writer.

## Features and graph relations

Document displays keep stable physical provenance visible by default:
`source_record_id`, `corpus`, `dataset`, `source_path`,
`source_sha256`, and `packaging`. Word displays show physical document
identity and source word ordinal. Node numbers and node types are enabled by
default so researchers can move directly between browser results and the
Text-Fabric Python API.

The browser loads the generated feature inventory rather than assuming every
valid source subset contains every optional annotation type. Available
`lemma`, `pos`, `func`, entity, translation, Arabic translation, metadata,
and layout features are therefore queryable when present. Query features are
shown with results.

Native edges such as `dependency_head`, `entity_head`, `same_scholarly`,
`documented_overlap`, and `witness`, including their valued evidence
features, remain ordinary Text-Fabric edge features and can be used in the
browser search interface. The app does not copy them into display-only scalar
fields.

A simple lexical search template is:

```text
word lemma=ⲉⲓⲣⲉ
```

Use feature names from the generated TF inventory; optional features naturally
depend on the selected source corpus.

## Direct API remains independent

The same generated directory can still be loaded without the app:

```python
from tf.fabric import Fabric

api = Fabric(locations=["/path/to/output-tf"], silent="deep").load(
    "lemma pos func dependency_head",
    silent="deep",
)
```

The browser configuration changes presentation defaults only. It does not
change node IDs, sections, text formats, graph edges, or conversion semantics.

## Scope

This local app is for freshly generated CopticScriptorium-TF artifacts. Agora
registration and automatic Context-Fabric/cfabric-mcp artifact discovery remain
separate integration work. The app presents annotations preserved by the
converter; it does not certify the scholarly correctness or completeness of
upstream Coptic Scriptorium data.
