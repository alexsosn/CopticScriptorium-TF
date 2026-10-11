# Source SBL Greek and apparatus annotations (issue #91)

## Evidence and non-XML nesting
The pinned Coptic SCRIPTORIUM TT source `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`, especially `sahidica.mark/sahidica.mark_TT/Mark_02.tt`, includes independently valued `sbl_greek` and `sbl_apparatus` wrappers. Their closing tags can cross: an apparatus tag opens before a Greek tag, but **closes before the Greek tag**. Treating these as strict XML parent-child nodes would give false hierarchy or reject legitimate source evidence. The source attributes preserve Unicode Greek, critical signs, and trailing whitespace. `Greek_source` on the physical document carries provenance, which is **not** an assertion of identity to a specific modern Greek TF parent or even the post-2023 Faithlife edition.

## Native TF model
`word` remains the sole slot type. Each physical source occurrence is a separate native `sbl_greek` or `sbl_apparatus` node, with its **original exact decoded source attribute value** stored in `F.value`, unique per-document occurrence ordinal in `F.source_ordinal`, source record ID in `F.source_record_id`, and literal active Coptic verse in `F.sbl_verse_n` when provided. Do not replicate Greek passages on every Coptic word.

Each occurrence additionally carries `start_after_word_ordinal`, `end_after_word_ordinal` and optional `start_word_ordinal`, `start_char`, `end_word_ordinal`, `end_char`. The before/after positions permit recovering source-occurrence boundaries without assuming verse correspondence. When an annotation encloses whole Coptic words, `oslots` projects those word slots and `render_mode=sbl_span`. When it falls inside a word or between words, `oslots` anchors it to a single adjacent word and **`render_mode=sbl_anchor` explicitly disclaims whole-word ownership**. No synthetic slots, cross-warp integer IDs, JSON/XML semantic blobs, or word-level Greek/Coptic alignments are emitted.

## Query example

```python
from tf.fabric import Fabric
api = Fabric(locations=['/path/to/Coptic-TF'], silent='deep').load(
    'value source_record_id source_ordinal sbl_verse_n render_mode '
    'start_word_ordinal start_char start_after_word_ordinal '
    'end_word_ordinal end_char end_after_word_ordinal', silent='deep')
for node in api.F.otype.s('sbl_greek'):
    text = api.F.value.v(node)  # original Greek source-annotation value
    owner = api.F.source_record_id.v(node)
    mode = api.F.render_mode.v(node)
    positions = (api.F.start_after_word_ordinal.v(node), api.F.end_after_word_ordinal.v(node))
    coptic_slots_or_anchor = tuple(api.L.d(node, otype='word'))
```

Use the paired `sbl_apparatus` source occurrences, and preserve each physical record separately even if Mark is duplicated between collection datasets. A source annotation does **not** license corpus redistribution; the pinned Mark Coptic source metadata explicitly restricts Coptic text to academic use, and SBLGNT editorial versions have distinct provenance.

## Research → RED → tests and release limits
RED tests cover genuine crossed SGML wrapper closure, Unicode and trailing whitespace, source verse scope, duplicate occurrences, present-empty vs absent annotations, in-word offsets, zero-length anchors, malformed/unclosed tags, graph validation and clean native TF reload. A pinned Mark 2/16 live test exercises real sources. The requested comprehensive 2,628-record SBL annotation census, ZIP/directory parity and full-output corpus smoke remain separate required gates before considering #91 fully closed. Do not claim that this automatically creates Coptic ↔ SBLGNT verse alignment.
