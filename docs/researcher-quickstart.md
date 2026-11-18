# Researcher quickstart: a local Coptic corpus and first query

This guide is for a researcher starting from a checkout of
[CopticScriptorium-TF](https://github.com/alexsosn/CopticScriptorium-TF)
and a *locally available* Coptic Scriptorium TT source tree. It provides a
repeatable path from actual original TT bytes to a native Text-Fabric query.
For full schema details, see the [researcher guide](researcher-guide.md).

## 1. Install the converter

Use **Python 3.12**. From the CopticScriptorium-TF source checkout:

```bash
python -m pip install .
copticscriptorium-tf --help
```

The package installs Text-Fabric 13.1.0 and a SHA-256-locked published
`tf-build` wheel. The initial dependency installation requires network
access. The conversion itself never downloads source texts.

## 2. Convert a local original TT dataset

Your source tree must contain at least one physical file under
`<corpus>/<dataset>_TT/*.tt` or one
`<corpus>/<dataset>_TT.zip` archive. You may start with a small original
TT subset instead of the entire collection. Set the output and summary to
**two fresh paths**. The source commit below is the reviewed *upstream*
Coptic corpus Git revision, not the converter's version:

```bash
copticscriptorium-tf \
  /path/to/CopticScriptorium-corpora \
  /path/to/output-tf \
  --upstream-repository CopticScriptorium/corpora \
  --upstream-commit 3ac067f1709a0012daf39ea8da2fac79980176a5 \
  --summary /path/to/conversion-summary.json
```

Use that commit only if your local tree really is from the pinned upstream
revision. For a deliberately edited or otherwise unversioned local source,
use `--upstream-commit unversioned-local` rather than claiming a Git pin
you cannot substantiate. Existing output directories are never overwritten.
The separate JSON summary is operational metadata, not a corpus-data
feature or a substitute for the native `.tf` files.

## 3. Explore in the browser

Start the installed local Text-Fabric browser:

```bash
copticscriptorium-tf-web /path/to/output-tf
```

You may first validate it without serving a site:

```bash
copticscriptorium-tf-web /path/to/output-tf --check
```

In the browser's Text-Fabric search field, try:

```text
word lemma=ⲉⲓⲣⲉ
```

The result count depends on which original works you supplied: zero results
in a narrow corpus do not imply the converter failed. Search the available
`norm`, `lemma`, `pos` and other native features in your own data.
Both a **source-attested POS query** and a **source-attested Coptic Unicode
lemma query** are covered by the installed real-source HTTP regression test,
not merely the generic `word` query. The test chooses its lemma from original
pinned Coptic TT rather than assuming a given word occurs in every dataset.

## 4. Ask a question with the native Text-Fabric API

The following query chooses a POS value actually present in *your* converted
source and checks the Text-Fabric inverted index against Text-Fabric Search.
It will not guess a Coptic word that might be absent from the chosen edition.

```python
import re
from tf.fabric import Fabric

api = Fabric(locations=["/path/to/output-tf"], silent="deep").load(
    "norm lemma pos source_record_id source_word_ordinal", silent="deep"
)
if not api:
    raise RuntimeError("Could not load generated Text-Fabric")

pos = next(
    (
        value for w in api.F.otype.s("word")
        if (value := api.F.pos.v(w))
        and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", value)
    ),
    None,
)
if pos is None:
    raise RuntimeError("The selected source has no simple POS value")

query = f"word pos={pos}"
hits = tuple(api.S.search(query, silent="deep"))
assert hits and len(hits) == len(api.F.pos.s(pos))
print("Query:", query, "matches:", len(hits))
for (word,) in hits[:5]:
    print(api.F.source_record_id.v(word),
          api.F.source_word_ordinal.v(word),
          api.F.norm.v(word), api.F.lemma.v(word))
```

These results are native Coptic words, retaining physical source IDs.
Normalized forms, POS and lemmas are **upstream annotations**. Do not assume
that one physical source record is the same as one critical-edition work.
See the [query cookbook](../examples/query_cookbook.py) for dependency
relations, entity queries, original/normalized text, translations and source
provenance.

## 5. Optional: acquire the entire pinned source through Agora

If you do not have a local TT tree, the already registered Agora materializer
can acquire the reviewed Git snapshot automatically. Run these from an
**Agora** repository checkout with its supported sandbox/runtime:

```bash
python scripts/agora_install_materializer.py install copticscriptorium-tf \
  --approve-code-execution

python scripts/agora_materialize_registered.py \
  --plugin copticscriptorium-tf \
  --materializer copticscriptorium-text-fabric \
  --output /path/to/agora-output \
  --sandbox required
```

The resulting Text-Fabric files are in `/path/to/agora-output/tf`; substitute
that path in the browser or Python example above **in an environment where
the Coptic package and Text-Fabric are installed**. The complete original
2,628-source-record acquisition and conversion was tested by the registered
Agora integration in [PR #215](https://github.com/alexsosn/Agora/pull/215).
This is a resource-heavy path: pinned historical runs have measured peak
process **memory** above 7 GiB for TT-only and above 8 GiB with CoNLL-U,
not counting all concurrent host processes. Budget substantially more memory
and disk space than the roughly 669–795 MB of output TF files.

Context-Fabric/cfabric-mcp **does not import the corpus automatically** just
because Agora produced it. Use the explicit `install_local_corpus`,
`prepare_corpus`, `load_corpus` and `search` operations in the
[README Agora section](../README.md#agora-integration-status). The MCP server
must be able to access that native TF path on its own host.

## Interpretation and release scope

Coptic-to-LXX and Greek-NT module features are **reference candidates**,
not validated Greek/Coptic translation alignments or word equivalences.
For bilingual work consult the [Coptic–LXX module guide](coptic-lxx-alignment.md)
and its source-qualified ambiguities before interpreting a shared verse ID.

The converter and browser have real-source regression coverage, but
independent autonomous-agent exploratory research usability acceptance
is tracked separately in [issue #177](https://github.com/alexsosn/CopticScriptorium-TF/issues/177).
Neither this software's MIT licence nor its generated output grants permission
to redistribute the upstream Coptic Scriptorium corpus.
