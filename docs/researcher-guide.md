# Researcher guide

This guide describes a generated CopticScriptorium-TF corpus as a research
object. The shorter installation and loading path stays in the
[README](../README.md); runnable recipes live in
[examples/query_cookbook.py](../examples/query_cookbook.py), and the standard
Text-Fabric browser is documented in [docs/web-app.md](web-app.md).

CopticScriptorium-TF preserves and projects upstream Coptic Scriptorium
assertions into native Text-Fabric. It validates the converter's structural and
serialization behavior; it does not certify the scholarly correctness,
completeness, authorship, licensing interpretation, or editorial quality of
upstream annotations.

## Load a generated corpus

The cookbook provides a convenience loader that loads the features used by the
recipes plus available meta_* document features:

~~~python
from examples.query_cookbook import load_generated_tf

api = load_generated_tf("/path/to/output-tf")
~~~

For tighter memory control on a large corpus, use Fabric directly and request
only the features required by a task:

~~~python
from tf.fabric import Fabric

api = Fabric(locations=["/path/to/output-tf"], silent="deep").load(
    "norm lemma pos func source_record_id scholarly_id corpus dataset "
    "dependency_head entity_head documented_overlap witness",
    silent="deep",
)
~~~

Feature files are ordinary native TF files. Optional source annotations can be
absent from a selected corpus or subset; code should not assume that every
optional feature is present.

## Corpus model

The sole slot type is word. One source TT norm token becomes one word slot.
All other objects are non-slot nodes measured over word slots by native
oslots. A non-slot node can therefore be located in the Coptic word sequence
without a parallel JSON/XML structure.

| node type | research meaning |
| --- | --- |
| document | one preserved physical TT source record; the only TF section type |
| sentence | source sentence span |
| orig_group | grouping above one or more norm_group nodes |
| norm_group | normalized group; may contain orig children and/or direct words |
| orig | source original/diplomatic unit under a norm_group |
| page | physical-layout segment |
| column | physical-layout segment |
| line | physical-layout segment |
| entity | entity annotation spanning one or more words |
| translation | English translation segment with its own text |
| arabic_translation | Arabic translation segment with its own text |

The basic containment graph uses oslots for measured spans. Additional
structural edges preserve relationships that slot containment alone cannot
express:

- parent is child -> parent. It links orig -> norm_group,
  norm_group -> orig_group when applicable, and nested entity -> parent entity.
- direct_word is norm_group -> word for words that belong directly to the
  norm_group rather than through an orig child.

These directions matter when using E.parent.f(), E.direct_word.f(), or TF Search.

## Normalized and diplomatic text

The writer defines native TF text formats when the corresponding data exists:

~~~python
normalized = api.T.text(document, fmt="text-orig-full")
diplomatic = api.T.text(document, fmt="text-diplomatic-full")
~~~

text-orig-full is the normalized word rendering despite the historical TF
format name. text-diplomatic-full uses diplomatic/original source surfaces and
group boundaries reconstructed by the writer. Do not infer that the two strings
must have the same tokenization or characters.

orig, norm_group, and orig_group nodes can also have source value features.
Translation and layout nodes use their own text rather than borrowing the
Coptic text of their anchor span.

## Words, morphology, and source IDs

Useful word features include:

- source_record_id — owning physical record;
- source_word_ordinal — 1-based ordinal inside that record;
- source_id — upstream word identifier when supplied;
- norm — normalized Coptic form;
- lemma — upstream lemma;
- pos — upstream part-of-speech value;
- func — upstream syntactic/function or morphology-related value;
- source_text — source surface associated with the word;
- head_literal and dependency_head_ordinal — preserved source dependency
  evidence.

A missing optional feature value means that the converter has no value to
project for that node. It should not be interpreted as a negative scholarly
claim. If a feature has no values anywhere in a generated subset, its .tf file
may be absent entirely.

### Lexical and morphology searches

Text-Fabric 13.1.0 node-feature constraints can be used directly:

~~~python
lemma_hits = tuple(api.S.search("word lemma=ⲉⲓⲣⲉ", silent="deep"))
verb_dependents = tuple(
    api.S.search("word pos=V func=dep", silent="deep")
)
~~~

Each result is a tuple in search-template atom order. The equivalent reusable
recipes are lemma_hits() and morphology_hits() in the cookbook.

## Dependencies

dependency_head is a directed word -> word edge from the dependent to its head.
A source dependency_head_ordinal of 0 or None represents root/no resolved head;
the graph emits no dependency_head edge for that word.

A two-node TF Search query is therefore:

~~~python
query = """
dependent:word func=dep
head:word
dependent -dependency_head> head
"""
pairs = tuple(api.S.search(query, silent="deep"))
~~~

For a pair (dependent, head), E.dependency_head.f(dependent) contains head.
The cookbook's dependency_pairs() implements this query and makes the root
semantics explicit.

## Entities

An entity is a measured non-slot node. Its oslots span is the entity occurrence.
entity_class and identity preserve upstream annotation when present.
entity_head is directed entity -> head word. If entities are nested, parent is
directed child entity -> parent entity.

~~~python
query = """
entity:entity entity_class=person
head:word
entity -entity_head> head
"""
for entity, head in api.S.search(query, silent="deep"):
    span_words = tuple(api.L.d(entity, otype="word"))
~~~

The head must lie inside the entity's measured word span. The
entity_head_occurrences() cookbook recipe returns entity, head, and span
together.

## Translations

translation and arabic_translation nodes are measured over Coptic word slots
but render their own text through own_text:

~~~python
english = [
    (node, api.T.text(node))
    for node in api.F.otype.s("translation")
]
arabic = [
    (node, api.T.text(node))
    for node in api.F.otype.s("arabic_translation")
]
~~~

The measured span says which Coptic words the translation annotates; api.T.text()
on the translation node returns the translation string itself. The cookbook
function translation_texts() returns both text and anchor span.

## Physical layout and token-internal boundaries

page, column, and line nodes are measured segments with their own source text.
Layout changes can occur between words or inside a source word. The writer
therefore keeps both a word locus and character-level boundary features:

- event_ordinal;
- start_word_ordinal and start_char for an event inside a word;
- start_after_word_ordinal for an inter-word event;
- end_word_ordinal and end_char;
- end_after_word_ordinal.

own_text on a layout node is the exact source-text segment between that event
and the next event of the same layout type. The word-slot locus is still the
native TF anchor. Character offsets refine that locus; they are not extra
synthetic slots.

## Physical and scholarly document identity

source_record_id is the physical identifier used as the TF section address:

~~~python
document = api.T.nodeFromSection(
    ("sahidica.nt/sahidica.nt:41_Mark_01",)
)
physical = api.F.source_record_id.v(document)
scholarly = api.F.scholarly_id.v(document)
~~~

scholarly_id is separate, usually derived from the source document_cts_urn.
Multiple physical records may carry the same scholarly_id. Do not use
scholarly_id as if it uniquely named a generated document.

Filter physical documents through ordinary TF Search:

~~~python
docs = tuple(
    api.S.search(
        "document corpus=sahidica.nt dataset=sahidica.nt/sahidica.nt",
        silent="deep",
    )
)
~~~

The cookbook functions document_hits() and document_identity() keep this
distinction visible.

## Relations between physical documents

The converter does not deduplicate or collapse related physical records.
Relations are native directed document -> document edges:

- same_scholarly — two physical records carry the same scholarly identity;
- documented_overlap — a reviewed collection-level overlap relation;
- witness — source witness metadata points to a scholarly identity, projected
  to the matching physical document(s).

Search them with the ordinary directed edge syntax from Text-Fabric 13.1.0:

~~~python
query = """
source:document
target:document
source -documented_overlap> target
"""
overlaps = tuple(api.S.search(query, silent="deep"))
~~~

The same pattern works for -same_scholarly> and -witness>. Separate valued edge
features preserve evidence rather than packing it into strings:

- same_scholarly_classification;
- documented_overlap_classification;
- documented_overlap_family;
- witness_literal;
- witness_target_scholarly_id.

The classifications describe converter-preserved/measured relation evidence;
they are not a preferred-edition ranking.

## Document metadata

Upstream document metadata becomes deterministic scalar node features.

For a safe lowercase ASCII key such as title, the primary value is meta_title.
Repeated values use occurrence features meta_title__2, meta_title__3, and so on.

Keys that would be unsafe, case-colliding, or ambiguous with that occurrence
namespace are encoded reversibly as UTF-8 hex after meta__hex_. For example,
the source key Title becomes meta__hex_5469746c65. A literal source key
title__2 is also hex-encoded, so it cannot collide with the second occurrence
of title.

This projection keeps each value queryable as a scalar TF feature. There is no
metadata JSON/XML blob containing the semantic structure.

## Provenance and citation

Each document carries:

- source_record_id — physical TT record identity;
- source_path — path in the handed-off source tree, including archive member
  notation for ZIP sources;
- source_sha256 — SHA-256 of the exact source record bytes;
- corpus and dataset;
- packaging — directory/archive source mode.

The TF feature metadata also records upstreamRepository and upstreamCommit.
The cookbook exposes these through trace_provenance():

~~~python
from examples.query_cookbook import trace_provenance

evidence = trace_provenance(api, word_or_node)
~~~

For a reproducible citation or analysis log, prefer the immutable source
revision plus physical source evidence: upstreamRepository, upstreamCommit,
source_record_id, source_path, and source_sha256. For word-level references,
also record source_id when available or source_word_ordinal.

Numeric TF node IDs are deterministic for the same ordered converted input, but
they are build-local graph addresses and can change when the selected corpus or
schema changes. They are useful in a saved analysis tied to one generated
artifact; they are weaker long-term citation identifiers than the physical
source/provenance fields above.

scholarly_id is useful for connecting source records that make the same
scholarly identity claim, but it does not replace source_record_id when citing
which physical TT record was analyzed.

## Running the cookbook

From a repository checkout:

~~~bash
python examples/query_cookbook.py /path/to/output-tf --lemma ⲉⲓⲣⲉ
python examples/query_cookbook.py /path/to/output-tf --pos V --func dep
~~~

The command-line mode prints JSON-friendly result tuples. For broader work,
import the functions and combine them with the standard F/E/L/T/S APIs.

The executable CI fixture asserts result shapes for lemma, POS/function,
dependency, entity span/head, English/Arabic translations, document filters,
physical/scholarly identity, same_scholarly/documented_overlap/witness,
normalized/diplomatic rendering, metadata encoding, group structure, layout
boundaries, and provenance tracing.

## Browser workflow

The standard Text-Fabric browser uses the same generated native TF artifact; see
[docs/web-app.md](web-app.md). Browser display configuration does not create a
second data model. Queries developed in the browser can be moved directly into
api.S.search() recipes and vice versa.
