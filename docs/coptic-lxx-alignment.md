# Coptic ↔ LXX reference candidates in native Text-Fabric

This is a **candidate reference lookup**, **not** an assertion of matching
Coptic/Greek readings, a revised Septuagint verse edition, or bilingual
word-by-word alignment.

The prototype attaches source-local Coptic biblical references to
`CenterBLC/LXX` **1935**, release **v1.0.1**, pinned Git commit
`f32a98eddf7eb239aa73ab863d70381e416d5076`.
The Coptic source is `CopticScriptorium/corpora` pinned to
`3ac067f1709a0012daf39ea8da2fac79980176a5`.

## What exists and what has been tested

- Source `verse_n`, `vid_n`, `verse_vid` are optional *native Coptic
  word features* from issue #69. Source-reference boundaries inside an
  unsplit word are separate native position nodes with exact
  `start_word_ordinal/start_char` instead of dishonest whole-word labels.
- Issue #70 resolves reviewed source families (Sahidic Ruth and Jonah;
  Bohairic Habakkuk) only when `meta chapter`, source marker, available
  `verse_vid` and available CTS reference are consistent. An actual
  edition-pinned Greek `T.nodeFromSection((book,chapter,verse))` must
  resolve to a native `verse` node. This produces only
  `reference_candidate`, `ambiguous`, `unresolved`, or
  `unclassified_corpus`.
- Issue #73 creates **two additive weft-only TF modules**, leaving both
  corpora's native `otype`, `oslots` and text untouched. Three real Coptic
  documents (Ruth 2, Jonah 2, Bohairic Habakkuk 2) have 2,104 word slots,
  54 candidate reference addresses and 54 matching real LXX verse nodes.
  Full OT coverage has not been demonstrated.

## Features and cross-parent join

| Corpus/module | Node type | Features |
| --- | --- | --- |
| Coptic `modules/coptic` | `word` | `coptic_lxx_ref_id`, `coptic_lxx_ref_status`, `coptic_lxx_ref_evidence`, `coptic_lxx_ref_reason` |
| Greek `modules/lxx` | `verse` | `coptic_lxx_ref_id` |

A `coptic_lxx_ref_id` is a **stable address key** such as
`CenterBLC/LXX:1935:Ruth:2:1`. Multiple Coptic witnesses or overlapping
collections may share the same Greek verse key. This does not overwrite
their independent `source_record_id`/source provenance, and does not require
a Greek verse feature to store a lossy list of all Coptic witness IDs.

Example after modules have been materialized against the actual parent datasets:

```python
from pathlib import Path
from tf.fabric import Fabric
from copticscriptorium_tf.lxx_module import verify_coptic_module_parent

coptic_tf = Path("/path/to/generated-coptic/tf")
lxx_tf = Path("/path/to/CenterBLC-LXX/tf/1935")
pair = Path("/path/to/derived-coptic-lxx-modules")

# Check the *generated Coptic TF warp* fingerprint before overlaying the module.
# The source Git revision is NOT the TF parent release commit.
verify_coptic_module_parent(pair / "coptic", coptic_tf)

coptic = Fabric(
    locations=[str(coptic_tf), str(pair / "coptic")], silent="deep",
).load("source_record_id coptic_lxx_ref_id coptic_lxx_ref_status", silent="deep")
greek = Fabric(
    locations=[str(lxx_tf), str(pair / "lxx")], silent="deep",
).load("coptic_lxx_ref_id", silent="deep")

ref = "CenterBLC/LXX:1935:Ruth:2:1"
coptic_words = [
    w for w in coptic.F.otype.s("word")
    if coptic.F.coptic_lxx_ref_id.v(w) == ref
]
lxx_verse_nodes = [
    v for v in greek.F.otype.s("verse")
    if greek.F.coptic_lxx_ref_id.v(v) == ref
]
assert len(lxx_verse_nodes) == 1
# Each Coptic word still carries its own document's source_record_id.
```

The script `tests/live_issue73_dual_modules.py` is an executable source
for preparing this exact pilot with the pinned Coptic and Greek datasets.
It loads the full Greek TF parent, verifies mapping-critical Git blob
fingerprints and positive Coptic/Git revision IDs, materializes the two
weft-only modules, reloads both, and checks the shared-reference join.
The generated corpus and modules are intentionally **not redistributed**.

## Known limitations and next gates

Do **not** infer Greek/Coptic word identity from an equal verse address;
Coptic OT books may follow different verse divisions from Rahlfs LXX.
Greek `subverse` membership is a separate boundary layer. The current
pilot knows three source families; other biblical sources remain
`unclassified_corpus` until an explicit reviewed book/corpus map is
added. A future version needs a full coverage audit, explicit 1:N/N:1
versification crosswalks with provenance, confidence/status reporting,
and only then independently evaluated translated word alignment.

See [research issue #70](../research/issue-70/RESEARCH_PLAN.md) and
[issue #73 plan](../research/issue-73/RESEARCH_PLAN.md) for those gates.
