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

## Source paths and Agora

For local TT trees, the direct converter and Agora's registered
`copticscriptorium-tf` materializer produce the same native TF model.
[README: Agora integration](../README.md#agora-integration-status) gives the
reviewed local `--source` materialization command and the explicit
`install_local_corpus` → `prepare_corpus` → `load_corpus` handoff to
Context-Fabric/cfabric-mcp. The server must be able to read the generated
`tf/` directory locally. Bulk automatic Git acquisition remains an open
Agora #205 gate; do not treat its manifest declaration as a successful full
acquisition test.

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
| ed_line_n / ed_lb_n | numbered edition line annotations; preserve literal page/line numbering |
| ed_page_n / ed_pg_n | numbered edition page annotations, distinct from manuscript pagination |
| multiword | upstream TT grouping over existing normalized words; original Coptic word slots are unchanged |
| chapter_n / marcion_chapter_n / marcion_verse_n / petermann_chapter_n / petermann_verse_n | original source edition reference labels, never inferred canonical Bible alignments |
| hi_rend / note / gap_reason / supplied_reason / note_note / gap_unit / supplied_source / gap_quantity / gap_extent / supplied_evidence / unclear_reason / unclear | literal editorial witness annotation spans/anchors over existing Coptic word slots |
| gap / supplied / abbr | intervention/abbreviation wrappers with all original attributes in separate native scalar features |
| entity_head_tok / entity_text / entity_identity / persName_type / placeName_type / placeName_ref / roleName_type / rs_type / org_type | source-attested entity/name labels with literal values and positions; no automatically verified ontology equivalence |
| pb_coptic_id / p_n / p / p_source / pb_n / lb_nb | literal original page, paragraph and witness-provenance source tags, with positional span/anchor semantics |
| verse / verse_n_vid_n / verse_n_vname / v_id / vid__n / chapter_name / ed_chapter_n / chapter_2 / ch_n / chapter | original alternate biblical/CTS/source reference literal spans or anchors; no inferred canonical LXX equivalence |
| date_type / german / section_title / quote_ref / quote_type / gap_exent / hi / figDesc / figure / 18 other rare types | original low-frequency editorial/linguistic labels, preserving source attributes and span/anchor positions |
| verse_n_marker / vid_n_marker / verse_vid_marker | source reference marker inside an unsplit word, with exact character offset; not a whole-word verse membership |
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

### Source multiword groupings

A `multiword` node preserves the literal value of one upstream TT
`<multiword multiword="...">` annotation. It groups existing normalized Coptic
word slots; it does **not** add a single synthetic token or replace the
individual source word morphology, dependency edges, or CoNLL-U annotations.

~~~python
for node in api.F.otype.s("multiword")[:10]:
    print(
        api.F.source_record_id.v(node),
        api.F.source_ordinal.v(node),
        api.F.value.v(node),             # original grouped Coptic surface label
        api.F.render_mode.v(node),       # multiword_span / multiword_anchor
        tuple(api.E.oslots.s(node)),     # existing Coptic word slots
    )
~~~

`multiword_span` indicates fully covered words in the source annotation.
`multiword_anchor` denotes a positional source event for which complete-word
containment is not warranted; inspect the native start/end word and character
offsets rather than interpreting `oslots` as semantic membership. The
`value` can preserve original whitespace and must not be reconstructed by
blindly concatenating normalized words. Upstream word-level TT `func`,
`head_literal` and separate `ud_head` edges retain their own provenance;
a source `multiword` tag does not prove a UD `fixed` dependency.

The full source-data rationale and known limits are in
`research/issue-143/RESEARCH_PLAN.md`.

### Edition chapter and verse reference labels

The source labels `chapter_n`, `marcion_chapter_n`,
`marcion_verse_n`, `petermann_chapter_n` and
`petermann_verse_n` are preserved as five distinct **non-slot**
Text-Fabric node types. Each node stores the upstream edition literal
as `value`, an original `source_record_id`, source-opening `source_ordinal`,
and source word/character boundary features.

~~~python
for verse in api.F.otype.s("marcion_verse_n")[:10]:
    print(
        api.F.source_record_id.v(verse),
        api.F.value.v(verse),        # Marcion *edition's* original label
        api.F.render_mode.v(verse), # reference_span / reference_anchor
        tuple(api.E.oslots.s(verse)),
    )
~~~

A `reference_span` has measured wholly covered source Coptic norm
words. A `reference_anchor` is a positional association, **not**
claimed whole-word membership. Labels such as `chapter_n="148_postscript"`
and `chapter_n="0"` remain strings. Marcion and Petermann chapter/verse
numbers are parallel **source edition reference systems**, not evidence
of correspondence to canonical Coptic biblical books, the Greek New Testament,
or LXX verse numbers. Existing Coptic `verse_n`, `vid_n` and
`verse_vid` features remain separate. See
`research/issue-146/RESEARCH_PLAN.md`.

### Editorial witness tags and explicit source positions

Twelve source-only TT tags are preserved as native **non-slot** TF node
types: `hi_rend`, `note`, `gap_reason`, `supplied_reason`,
`note_note`, `gap_unit`, `supplied_source`, `gap_quantity`,
`gap_extent`, `supplied_evidence`, `unclear_reason`, `unclear`.
Each node retains its original decoded source attribute in `value`,
its `source_record_id`, independent `source_ordinal`, and precise
Coptic word-relative start/end character positions. These are **attested
editorial notes or qualifiers**, not reconstructed text, translations,
normalized tokens, or UD dependency decisions.

~~~python
for n in api.F.otype.s("hi_rend")[:5]:
    print(
        api.F.source_record_id.v(n),
        api.F.value.v(n),             # original rendition, e.g. "red"
        api.F.render_mode.v(n),       # editorial_span / editorial_anchor
        api.F.start_char.v(n),
        api.F.end_char.v(n),
        tuple(api.E.oslots.s(n)),
    )
~~~

`editorial_span` indicates one or more fully covered existing Coptic norm
words. `editorial_anchor` is only a positional association; it does not
assert entire-word membership. For instance, a single red character inside
a Coptic source word is a one-slot anchor with native character boundaries.
Crossed note/gap source tags are modeled by independent occurrence stacks,
not falsely normalized into one XML tree.

The TT `gap`, `supplied` and `abbr type` tags belong to a separate
multi-attribute source family; they are **not** the single-value editorial
source events above. Their individual attributes are preserved as native
scalar features (see next section), rather than flattened into `value`.
Research and source coverage assumptions: `research/issue-153/RESEARCH_PLAN.md`.

### Original multi-attribute gap, supplied and abbr wrappers

TT `gap`, `supplied` and `abbr` carry potentially more than one original
source attribute. Their node types are native **non-slot** TF annotations,
and their original source attribute values are materialized individually:

| Native node type | Original attribute keys / TF features |
| --- | --- |
| `gap` | `source_attr_gap_gap`, `source_attr_gap_extent`, `source_attr_gap_reason`, `source_attr_gap_unit` |
| `supplied` | `source_attr_supplied_supplied`, `source_attr_supplied_source`, `source_attr_supplied_reason` |
| `abbr` | `source_attr_abbr_type` |

~~~python
for n in api.F.otype.s("gap")[:5]:
    print(
        api.F.source_record_id.v(n),
        api.F.source_ordinal.v(n),
        api.F.render_mode.v(n),  # intervention_span / intervention_anchor
        api.F.source_attr_gap_extent.v(n),
        api.F.source_attr_gap_reason.v(n),
        api.F.source_attr_gap_unit.v(n),
        tuple(api.E.oslots.s(n)), # existing norm words only
    )
~~~

Feature absence means its original source tag omitted that key; it **does
not mean the key had an empty string literal**. A present empty value is
retained as an explicit TF node feature value. Source attribute metadata
records the original TT tag and attribute key. The convenient `value`
may use the main source `gap`/`supplied` label or `abbr type` where
available; query the named scalar attributes for authoritative provenance.
No abbreviation expansion, text restoration, Coptic token retokenization,
UD dependency or Greek/LXX mapping follows merely from these tags.

The original source constraints and coverage gates are in
`research/issue-156/RESEARCH_PLAN.md`.

### Original entity/name source labels

Nine original TT tags are preserved as **native non-slot Text-Fabric node
types**: `entity_head_tok`, `entity_text`, `entity_identity`,
`persName_type`, `placeName_type`, `placeName_ref`, `roleName_type`,
`rs_type` and `org_type`.

~~~python
for n in api.F.otype.s("placeName_ref")[:10]:
    print(
        api.F.source_record_id.v(n),
        api.F.source_ordinal.v(n),
        api.F.value.v(n),           # exact upstream ref, e.g. "paths:places:32"
        api.F.render_mode.v(n),     # entity_label_span / entity_label_anchor
        api.F.start_char.v(n),
        api.F.end_char.v(n),
        tuple(api.E.oslots.s(n)),
    )
~~~

A `entity_label_span` encloses complete original Coptic norm words;
`entity_label_anchor` denotes an exact source position inside or between
words. **Neither implies an ontology equivalence.** An upstream
`entity_identity="Sarah"` or `placeName_ref="paths:places:32"`
is preserved literally, not automatically resolved to Wikidata, an LXX
referent, or a verified scholarly authority. These nine original spans are
also **not conflated with existing interpreted `entity` nodes**: any
future association or head-word mapping requires demonstrable source
provenance, never coincident surface forms. Crossed original TT tags need
independent occurrence IDs rather than invented XML parent nesting.

Primary source witnesses and restrictions are in
`research/issue-159/RESEARCH_PLAN.md`.

### Original page, paragraph and witness-provenance markers

The original TT types `pb_coptic_id`, `p_n`, `p`, `p_source`,
`pb_n` and `lb_nb` are preserved as **six native non-slot TF node
types**, distinct from canonical book/chapter/verse or LXX mappings.
Every node retains its original `source_record_id`, `source_ordinal`,
decoded literal `value`, exact start/end word and word-relative character
positions.

~~~python
for n in api.F.otype.s("pb_coptic_id")[:5]:
    print(
        api.F.source_record_id.v(n),
        api.F.value.v(n),           # e.g. original Coptic page ID
        api.F.render_mode.v(n),     # document_span / document_anchor
        api.F.start_char.v(n),
        api.F.end_char.v(n),
        tuple(api.E.oslots.s(n)),
    )
~~~

A `document_span` is a whole-word source range; `document_anchor`
is only a positional marker. Literal Coptic combining characters, source
Roman paragraph IDs such as `I.1` and witness provenance `PATHS` are
not converted into invented integers, translations or authority links.
Source annotations can cross verse, translation, page, entity and norm
wrappers; no strict XML-tree nesting is assumed.

See `research/issue-162/RESEARCH_PLAN.md`. The separate original
`trans_horner` translation-specific family is not modeled in this batch.

### Alternate original biblical and CTS source references

Ten original TT source tag families are conserved as native non-slot TF nodes:
`verse`, `verse_n_vid_n`, `verse_n_vname`, `v_id`, `vid__n`,
`chapter_name`, `ed_chapter_n`, `chapter_2`, `ch_n`, and
`chapter`. These preserve **378** original source opening occurrences on
the pinned corpus. Original CTS labels and human-readable reference names
may overlap; the source is not asserting that they identify the same
canonical Greek or LXX passage.

~~~python
for n in api.F.otype.s("verse_n_vid_n")[:5]:
    print(
        api.F.source_record_id.v(n),
        api.F.source_ordinal.v(n),
        api.F.value.v(n),
        api.F.render_mode.v(n),    # alternate_reference_span / _anchor
        tuple(api.E.oslots.s(n)),
    )
~~~

`alternate_reference_span` means source markup covers whole canonical
Coptic norm words; `alternate_reference_anchor` preserves a source-only
position (including a fragment inside one word). Labels such as
`verse="1 Corinthians 14:1"`, `verse_n_vname="Jonah 1:1"`,
`v_id="urn:cts:copticLit:shenoute.abraham.monbya:21.8"` and
`vid__n` (two underscores) are kept *exactly* as original source types
and decoded values. They are not merged into the separate native
`verse_n`/`vid_n` reference evidence or an inferred LXX map.

Research and exact source-conservation contract:
`research/issue-166/RESEARCH_PLAN.md`.

### Original small editorial, linguistic and quotation source wrappers

Twenty-seven low-frequency source tags are modeled as **native non-slot TF
otypes**, preserving 308 original pinned TT opening events. These are
attested source values, not inferred textual interpretations. They include
`date_type`, `german`, `section_title`, `quote_ref`,
`quote_type`, `source_lang`, `figDesc`, `figure`, and
rare gap/typographic variants.

~~~python
for n in api.F.otype.s("quote_ref")[:5]:
    print(
        api.F.source_record_id.v(n),
        api.F.source_ordinal.v(n),
        api.F.value.v(n),       # original text, e.g. "Sal.72 , 22.23"
        api.F.render_mode.v(n), # residual_span / residual_anchor
        api.F.start_char.v(n),
        tuple(api.E.oslots.s(n)),
    )
~~~

Important literal source distinctions: `hi` has original TT
attribute `rend` (not `hi`), whereas other tags in this bounded
family have one matching source attribute. Original misspellings such as
`gap_exent`, `gap_reasaon`, and `gap_reasonn` remain **distinct**
otypes and are not silently merged into `gap_extent`/`gap_reason`.
German translations remain their own upstream source annotation family,
not Coptic words or an overwrite of existing `translation` nodes.
`quote_ref` and `quote_type` preserve the original quotation's label
and classification, not a verified biblical/LXX correspondence.

Midword `figDesc` and `figure` are `residual_anchor` positional
attestations, not claims that entire original Coptic words are figures.
Source research: `research/issue-172/RESEARCH_PLAN.md`.

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

### Edition line/page annotations (source-only)

The source `ed_line_n`, `ed_lb_n`, `ed_page_n` and `ed_pg_n`
wrappers are native **non-slot** TF node types. Their `value` is the upstream
literal (so `"0001"` stays `"0001"`), and `source_record_id` and
`source_ordinal` identify the physical TT occurrence. An `edition_span`
render mode means one or more **fully covered** Coptic words; an
`edition_anchor` mode means only a positional association can be justified,
with the exact source word/character bounds retained in `start_word_ordinal`,
`start_char`, `start_after_word_ordinal`, `end_word_ordinal`,
`end_char` and `end_after_word_ordinal`.

~~~python
edition_lines = api.F.otype.s("ed_line_n")
for n in edition_lines[:5]:
    print(
        api.F.source_record_id.v(n),
        api.F.value.v(n),             # edition's own literal
        api.F.render_mode.v(n),       # edition_span / edition_anchor
        api.F.start_char.v(n),        # None if opened between Coptic words
        api.F.end_char.v(n),
        tuple(api.E.oslots.s(n)),     # Coptic word span or positional anchor
    )
~~~

These are the edition's line/page labels, **not** the existing physical
manuscript `page/column/line` nodes, and not equivalent to Coptic biblical
verses or Greek LXX/NT references. Do not interpret an anchor as entire-word
coverage. On a partial corpus, a given edition node type or feature may be
absent. The source inventory and validation assumptions are documented in
`research/issue-140/RESEARCH_PLAN.md`.

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

## Supplemental UD layer from CoNLL-U

TT is the canonical source. When a record's CoNLL-U export validates and aligns
token-for-token and sentence-for-sentence with TT, its words also carry
separately named UD values. TT features are never overwritten or filled in.

- ud_lemma, ud_upos, ud_xpos, ud_deprel — CoNLL-U LEMMA, UPOS, XPOS, DEPREL;
- ud_head_ordinal — document-relative HEAD, where 0 means root;
- ud_head — word -> word edge for every non-root CoNLL-U head;
- ud_feat_<key> — one feature per FEATS key, for example ud_feat_pron_type
  (PronType) or ud_feat_number_psor (Number[psor]);
- ud_misc_<key> — one feature per MISC key (Orig, OrigLang, Morphs, Cxn,
  CxnElt, Entity, Subject), kept as literal source strings. CxnElt values
  begin with a sentence-local CoNLL-U word ID; Entity uses CoNLL-U bracket
  notation, while the entity nodes come from TT.

Each per-key feature records the literal UD key as sourceKey in its .tf header.

dependency_head contains TT heads only. On the pinned snapshot CoNLL-U adds
52,773 heads that TT lacks (1,146 of them roots); where both supply a head they
agree. Their relation labels differ on 4,902 words, so compare func and
ud_deprel rather than assuming one equals the other.

~~~python
infinitives = tuple(
    api.S.search("word ud_upos=VERB ud_feat_verb_form=Inf", silent="deep")
)
ud_pairs = tuple(api.S.search("""
dependent:word ud_deprel=obj
head:word
dependent -ud_head> head
""", silent="deep"))
~~~

Each document node records conllu_status: supplemented, missing (no CoNLL-U
counterpart), or the reason it was not used (placeholder, malformed_conllu,
unsupported_conllu_shape, token_alignment, invalid_utf8).
conllu_source_path and conllu_source_sha256 identify the CoNLL-U record
whenever one exists. On the pinned snapshot, 2,361 records are supplemented,
227 CoNLL-U files are whitespace-only placeholders and 40 are structurally
invalid. Words of those 267 records carry TT values only.

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

## Biblical source references and LXX alignment boundaries

Biblical TT sources may contain `verse_n`, `vid_n`, or `verse_vid` reference
markers. Their **literal source strings** are exposed as optional word features
of the same names. Absence means source evidence was not available for a given
word; it does not imply an inferred verse. A new `verse_n` explicitly resets
the preceding CTS/verse-label values rather than leaking them across a
reference boundary.

Some source-reference tags start *inside* a source `norm` after visible
characters. Such a word crosses the source reference boundary; it cannot
honestly have a single whole-word verse address. The converter preserves
these events as `verse_n_marker`, `vid_n_marker`, and
`verse_vid_marker` **native nodes** anchored by `oslots` to their containing
word; the literal marker is `label`, and `start_word_ordinal` /
`start_char` locate its exact original-text offset. A missing word-level
`verse_n` for such a word is deliberate. A source marker at the *start* of a
word can apply to that whole word.

```python
api = Fabric(locations=["/path/to/tf"], silent="deep").load(
    "source_record_id norm verse_n vid_n verse_vid "
    "label start_word_ordinal start_char", silent="deep"
)
word = 1
source_verse_literal = api.F.verse_n.v(word)
for node in api.F.otype.s("verse_n_marker"):
    print(api.F.source_record_id.v(node), api.F.label.v(node),
          api.F.start_word_ordinal.v(node), api.F.start_char.v(node))
```

These values are **source-local references**, not verified Greek
`CenterBLC/LXX` correspondences. Upstream explicitly warns that Coptic and
Septuagint versification may differ. A subsequent alignment layer must check
an edition-qualified LXX parent version, document its reference-mapping
evidence and exceptions, and leave unresolvable passages visible. TF node
integers cannot be used as cross-corpus edge targets.

## Look up Coptic witnesses from one LXX verse

For a generated **bilateral native TF module** bundle, you can query the
Greek parent verse and retrieve all Coptic source-record word runs associated
with the edition-qualified **reference-address candidate**:

~~~python
from tf.fabric import Fabric
from copticscriptorium_tf.lxx_query import find_coptic_witnesses
from copticscriptorium_tf.lxx_module import verify_coptic_module_parent
from copticscriptorium_tf.lxx_modules import validate_lxx_release

# Distinct parent warps and distinct additive native TF weft directories.
coptic_tf_dir = "/path/to/generated-coptic/tf"
lxx_tf_dir = "/path/to/pinned-CenterBLC-LXX/tf/1935"
weft_coptic_dir = "/path/to/generated-bilateral-modules/coptic"
weft_lxx_dir = "/path/to/generated-bilateral-modules/lxx"

# Validate both exact parent identities *before* interpreting candidate IDs.
verify_coptic_module_parent(weft_coptic_dir, coptic_tf_dir)
base_lxx = Fabric(locations=[lxx_tf_dir], silent="deep").load(
    "book chapter verse subverse word orig_order", silent="deep"
)
validate_lxx_release(lxx_tf_dir, base_lxx)

coptic = Fabric(
    locations=[coptic_tf_dir, weft_coptic_dir], silent="deep"
).load(
    "source_record_id source_word_ordinal verse_n "
    "coptic_lxx_ref_id coptic_lxx_ref_status", silent="deep"
)
lxx = Fabric(
    locations=[lxx_tf_dir, weft_lxx_dir], silent="deep"
).load(
    "book chapter verse subverse coptic_lxx_ref_id", silent="deep"
)

result = find_coptic_witnesses(coptic, lxx, "Ruth", 2, 1)
for witness in result.spans:
    print(witness.source_record_id, witness.source_word_ordinals, witness.status)
~~~

Every `word_nodes` value in the returned Coptic witness spans is local to
the **Coptic** warp; `result.lxx_node` belongs only to the Greek warp.
The shared string `CenterBLC/LXX:1935:Ruth:2:1` joins them safely.
Discontinuous Coptic runs, distinct source witnesses, and **adjacent distinct
source `verse_n` literals mapped to one LXX reference** remain separate.
Each returned `CopticWitnessSpan.source_verse_n` is the original Coptic
verse label, not an inferred Greek verse number. The source `verse_n`
feature must be loaded; the helper fails explicitly if it is missing or
malformed, rather than silently merging source verse boundaries. Repeated
opening verse tags with identical literals cannot be reconstructed from
word features alone (see the source marker-topology audit).
The source-locked Greek module contains `coptic_lxx_ref_id` but **does not**
provide `coptic_lxx_source_span_count`. The legacy two-module writer may
provide that optional count; in that case load the count feature explicitly,
and the helper validates its positive value. In the current source-locked
module, `result.declared_coptic_source_span_count is None` rather than a
fabricated count. Any declared count is a source **candidate span** count,
not a token count, lexically aligned word count, or scholarly verification.

The helper uses Text-Fabric's inverse feature index to avoid scanning every
Coptic word for each query. It returns `reference_candidate` and
`versification_candidate` statuses as they appear on the native weft, and
never upgrades them to verified Greek/Coptic passage equivalence.
Absent Greek verses, inconsistent edition IDs, corrupt candidate word
ordinals and missing weft features fail explicitly. The same numbered Coptic
and Greek verses can differ in content or numbering (see #70/#92/#108).

## Source language wrappers (Greek/Hebrew evidence)

The upstream TT `<lang lang="...">` annotation is preserved as an ordinary
native non-slot TF node of type `lang`. It carries the **literal upstream
language label** in `value` and native source positions in
`start_word_ordinal`, `start_char`, `start_after_word_ordinal`,
`end_word_ordinal`, `end_char`, and `end_after_word_ordinal`.
Use `render_mode=lang_span` for a complete-word locus and
`render_mode=lang_anchor` when oslots provides only a single-word positional
anchor. An anchor does *not* imply the whole Coptic word is language-tagged.
There are no extra word slots or serialized XML/JSON annotations.

On the exact pinned `sahidica.mark` Mark 2 TT source, 77 wrappers are present:
61 labeled `Greek` and 16 labeled `Hebrew`. The original SBL Greek NT
annotation nodes remain a separate model and retain their own original
occurrence numbering. The source language label does **not** certify a Greek
loanword, etymology, a corresponding SBL Greek NT word, or an LXX alignment.

~~~python
lang_nodes = api.F.otype.s("lang")
for node in lang_nodes:
    literal_label = api.F.value.v(node)
    mode = api.F.render_mode.v(node)
    source = api.F.source_record_id.v(node)
    words = api.L.d(node, otype="word")
~~~

This first slice does not claim completeness for *other* TT scholarly wrappers;
see issue #110 for the full source tag census.

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
