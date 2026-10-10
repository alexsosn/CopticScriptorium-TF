# Coptic ↔ Septuagint reference-candidate modules (pilot)

This is a **verse-reference address crosswalk**, not an assertion that two
manuscript passages represent identical text, share versification, or that
individual Coptic and Greek words translate each other.

The first implementation covers a source-verified pilot: Sahidic Ruth 2,
Sahidic Jonah 2, Bohairic Jonah 2, and Bohairic Habakkuk 2. Both Coptic Jonah
witnesses point to the same 11 Greek verse *addresses*, and the Greek module's
`coptic_lxx_source_span_count` records two witnesses at those addresses. The
actual real-parent integration test in `tests/live_issue89_dual_modules.py` is the executable recipe. It
checks out pinned source data in CI, converts the three Coptic TT documents to
native TF, loads the pinned LXX Greek TF parent, generates and reloads both
additive modules.

## Pinned parent versions

- Coptic source: `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`; source
  `source_record_id`, local word ordinal and exact document SHA-256 are
  checked against the loaded Coptic TF corpus before any feature is written.
- Greek source: `CenterBLC/LXX@f32a98eddf7eb239aa73ab863d70381e416d5076`,
  Rahlfs 1935 v1.0.1. All eight CATSS-TF mapping-critical feature Git-blob
  fingerprints and the TF parent slot/verse counts are checked. Replacing the
  corpus with another version using the same `book/chapter/verse` strings
  fails closed.

No source text or converted corpus is bundled into the software repository.

## Module feature model

| Module | Existing parent nodes | Native feature | Meaning |
| --- | --- | --- | --- |
| `coptic/` | Coptic word slots | `coptic_lxx_ref_id` | edition-qualified Greek verse *address* candidate |
| `coptic/` | Coptic word slots | `coptic_lxx_ref_status` | `reference_candidate`, `unresolved`, `ambiguous`, or `unclassified_corpus` |
| `lxx/` | LXX verse nodes | `coptic_lxx_ref_id` | shared address ID with mapped Coptic candidate words |
| `lxx/` | LXX verse nodes | `coptic_lxx_source_span_count` | number of candidate Coptic verse spans at this Greek address |

For Ruth 2:1 the stable join ID is `CenterBLC/LXX:1935:Ruth:2:1`.
Coptic and LXX **integer node identifiers are never joined directly**.
The two module directories contain ordinary `.tf` node features, without
`otype.tf`, `oslots.tf`, structural JSON/XML blobs, or sidecars.

The canonical parent corpora are *not modified*. Both new feature modules
are published atomically as one no-clobber bundle; the converter refuses
to publish if the source hash, reference status, target Greek verse node,
or version fingerprints disagree.

## API and loading

Given already parsed `DocumentModel` objects from the exact pinned Coptic
source and loaded Text-Fabric APIs of both pinned parent corpora:

```python
from pathlib import Path
from copticscriptorium_tf.lxx_modules import project_reference_modules

summary = project_reference_modules(
    documents,
    coptic_api=coptic_api,
    lxx_api=lxx_api,
    lxx_tf_dir=Path("/path/to/CenterBLC-LXX/tf/1935"),
    destination=Path("/path/to/generated/coptic-lxx-module-pair"),
)
```

Load the generated modules together with their respective parent warps.
This **does not** load the Greek module into the Coptic warp or vice versa:

```python
from tf.fabric import Fabric

coptic = Fabric(
    locations=[
        "/path/to/generated/coptic-tf",
        "/path/to/generated/coptic-lxx-module-pair/coptic",
    ],
    silent="deep",
).load("source_record_id norm coptic_lxx_ref_id coptic_lxx_ref_status")

greek = Fabric(
    locations=[
        "/path/to/CenterBLC-LXX/tf/1935",
        "/path/to/generated/coptic-lxx-module-pair/lxx",
    ],
    silent="deep",
).load("book verse coptic_lxx_ref_id coptic_lxx_source_span_count")
```

To find the Greek verse address candidate for a Coptic word, read
`coptic.F.coptic_lxx_ref_id.v(coptic_word_node)`, then locate the same string
on a Greek **verse** node via `greek.F.coptic_lxx_ref_id`. Multiple Coptic
witnesses can share an ID; `coptic_lxx_source_span_count` exposes their
multiplicity without encoding a list of foreign node IDs in any TF feature.

## What is not established

- The Coptic source warns that its OT versification can diverge from LXX;
  a matching chapter/verse number is a candidate until independently reviewed.
- Source records with conflicting CTS book/work metadata are `ambiguous`,
  not silently mapped; other OT books need source-family research and explicit
  Greek edition selection (Daniel, Tobit, etc.).
- Word-level Coptic↔Greek alignment and semantic translation judgments are a
  separate research task. The DSS↔BHSA consonantal matching heuristic cannot
  be reused directly across Coptic and Greek.
- An in-word verse marker remains a precisely positioned native event in
  CopticScriptorium-TF; the pilot does not invent a whole-token verse identity
  where source boundaries divide the token.

Track expansion and quality assessment in issue #70; pilot module construction
and exact source tests in issue #89.
