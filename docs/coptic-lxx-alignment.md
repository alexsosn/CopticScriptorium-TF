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
- Issue #70 first resolved a source-evidenced Ruth/Jonah/Habakkuk pilot.
  The subsequently audited broader Coptic OT coverage uses reviewed family
  identity **and exact source CTS work evidence** (not guessed book titles)
  to resolve available book/chapter/verse references. The pinned Greek
  `T.nodeFromSection((book,chapter,verse))` must point to an actual native
  LXX `verse`. The resolver does not assign Greek targets for conflicting,
  missing, edition-ambiguous, NT, or undetermined source references. All
  affected Coptic words retain explicit `reference_candidate`, `ambiguous`,
  `unresolved`, or `unclassified_corpus` status rather than disappearing.
- Issue #73 creates **two additive weft-only TF modules**, leaving both
  corpora's native `otype`, `oslots` and text untouched. Three real Coptic
  documents (Ruth 2, Jonah 2, Bohairic Habakkuk 2) have 2,104 word slots,
  54 candidate reference addresses and 54 matching real LXX verse nodes.
  Full OT coverage has not been demonstrated in the pilot. The separate
  issue #82 streaming acceptance covers the complete pinned 2,628 TT-record
  corpus, producing both additive modules without retaining all Coptic
  documents and a 2.4-million-entry slot dictionary. In the live full-source
  run, 21,120 distinct LXX verse addresses received a candidate ID,
  1,072,234 Coptic word slots were marked as reference candidates, and all
  2,394,354 Coptic slots had an explicit status. These are address
  correspondences only, **not** verified Greek/Coptic textual alignments.
  The full-pinned run [38080479109](https://github.com/alexsosn/CopticScriptorium-TF/actions/runs/38080479109)
  reported **9:48.45** wall time and 7,460,860 KiB (approximately **7.1 GiB**)
  peak RSS across **full conversion**, native weft generation and both fresh
  TF parent/module reloads combined. Do not attribute the entire peak to
  the standalone streaming projection.

### Real full-source coverage and interpretation

The historical counts below are the **pre-crosswalk, numerical-address baseline**.
The edition-specific Zechariah correction described further below adds a fifth,
explicit `versification_candidate` status; do not interpret the old counts as
the current post-crosswalk distribution. The full pinned acceptance must
recompute every status from the same source bytes, preserving the total slot
count and distinct native Greek verse target invariants.

The source evidence audit distinguishes **1,574 OT candidate records**,
**615 NT records**, and **439 undetermined records** out of 2,628 physical
sources. Biblical verse markers alone never imply LXX scope. The bilateral
module instead gives each Coptic word exactly one queryable status:

| Native Coptic word `coptic_lxx_ref_status` | Word slots |
| --- | ---: |
| `reference_candidate` | 1,072,234 |
| `unclassified_corpus` | 1,309,117 |
| `unresolved` | 12,951 |
| `ambiguous` | 52 |
| **Total** | **2,394,354** |

The Greek module attaches shared reference identifiers to **21,120 distinct
LXX verse nodes**. Equal reference addresses are a *lookup hypothesis*, **not
textual equivalence**, and not a Greek↔Coptic word alignment. An unclassified
word may belong to an NT or undetermined source or to a source requiring a
separate editorial decision; it must not be silently remapped to Greek OT.
Unresolved and ambiguous evidence remains available through the Coptic
`coptic_lxx_ref_reason` and `coptic_lxx_ref_evidence` native scalar
features, as well as the original source's `source_record_id`.

These outputs and counts refer to the pinned
`CopticScriptorium/corpora` snapshot and `CenterBLC/LXX` 1935 v1.0.1,
not to all published Coptic biblical witnesses or a new critical edition.

## Edition-qualified Zechariah numbering candidates — #97

The source-byte-locked v2 policy `bohairic-zach-lxx1935-v2` addresses
a concrete Greek/Coptic versification mismatch. It is **not** a global Zechariah
chapter shift, nor a certified bilingual/word alignment.

| Exact source edition / original verse | Pinned Rahlfs Greek candidate |
| --- | --- |
| Bohairic `ot.zach.bohairic_ed` 1:18–21 | LXX Zech 2:1–4 |
| Bohairic `ot.zach.bohairic_ed` 2:1–6 | LXX Zech 2:5–10 |
| Bohairic `ot.zach.bohairic_ed` 2:7–13 | LXX Zech 2:11–17 |

The positive candidate rules apply only to `bohairic.ot` Zechariah chapter
1 and 2 with their exact 2 physical source-record IDs, upstream Git commit
and **per-record TT SHA-256**. A mismatched source-byte identity is not
silently accepted as a same-number reference. Sahidic `ot.zech.coptot`
and unrelated works/chapters are never shifted.

**Historical v1 crosswalk census (before v2's seven-verse extension).** The real pinned full-corpus
audit (CI run `38122380197`, job `114419601027`, exact Coptic/LXX
upstream Git revisions) reports **21,117 distinct Greek verse-address IDs**
and preserves all **2,394,354 Coptic word slots**. This is three fewer
Greek IDs than the historical 21,120-address number-only baseline because
the unreviewed tail loses unjustified Greek reference IDs. Native Coptic
word statuses are: ordinary `reference_candidate` 1,071,829,
`versification_candidate` 344, `unresolved` 12,807,
`ambiguous` 257, `unclassified_corpus` 1,309,117. These statuses
measure reproducible edition-qualified *reference candidates*, not a
translation alignment. Full native TF reload acceptance is a separate CI
gate.

**Fail-closed remainder:** Because Bohairic Zechariah chapter 2 has
source-specific numbering, **verses 2:14 onward remain `ambiguous`**
until individually audited; they must not silently map to existing
identically numbered Rahlfs verses. Such words retain original Coptic
verse markers and a native mapping reason, but no Greek reference ID.
The v2 addition reviews 7 consecutive pairs individually, rather than
assuming that any unexamined chapter or edition obeys an arithmetic offset.

The source's `verse_n`, `vid_n`, `verse_vid`, original CTS, and
`source_record_id` stay unchanged. Only the derived native cross-reference
`coptic_lxx_ref_id` targets the Greek verse numbering, and the Coptic native
`coptic_lxx_ref_status` explicitly says **`versification_candidate`**.
The associated scalar `coptic_lxx_ref_evidence` / `coptic_lxx_ref_reason`
carry the versioned rule and its caution.

**Evidence limits:** pinned real CI found 4/4 source Brenton English
lexical motifs consistent with the 1:18–21 → 2:1–4 correspondence and 6/6
for 2:1–6 → 2:5–10, versus 0/6 matches for the competing same-number
Bohairic chapter-2 addresses. Issue #111's real pinned CI subsequently
confirmed Bohairic 2:7–13 ↔ Greek 2:11–17 as seven distinct source-byte-
qualified *numbering candidates*: all 14/14 curated source-English and
Greek lexical motifs were present at shifted targets (2/2 per verse), while
the same-number Greek controls scored 0/14. This is an annotation-aided
reference-numbering hypothesis, not source-language translation proof. Real parent-Coptic/Greece tests reload two
native weft-only TF modules on their own warps. Because the English source
annotations themselves cite Brenton 1851 and Sahidic translations may be
missing, this evidence justifies a **reviewable edition-qualified reference
candidate**, not independent Coptic/Greek text or word equivalence.

For example, in the derived Coptic overlay, the source words belonging to
Bohairic Zechariah 2:1 keep source `verse_n="1"` but carry the Greek
address `CenterBLC/LXX:1935:Zech:2:5` with
`coptic_lxx_ref_status="versification_candidate"`. Any researcher can
therefore retrieve the original reference alongside the proposed Greek
reference without losing source provenance or inventing cross-warp node IDs.

Real byte-pinned regression:
`tests/live_issue97_crosswalk.py` and
`.github/workflows/issue97-crosswalk.yml`.
Further full-book textual/versification review remains open in issues #70,
#75, #92 and #97.

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

## Full-source streaming modules (issue #82)

For large corpora, prefer `materialize_lxx_reference_modules_streaming`
over the earlier pilot `materialize_lxx_reference_modules`. It accepts a
one-pass source-document iterator (including ZIP TT members) and emits native
Coptic and LXX weft-only features. Its intermediate disk-backed index is
temporary, not a serialized research sidecar.

**Important source authenticity requirement:** the supplied Coptic parent
Text-Fabric API **must load** `source_sha256` alongside
`source_record_id` and `source_word_ordinal`. Before any overlay is
published, the streaming mapper compares every input document's exact
TT source SHA-256 with that of the corresponding parent `document` node.
A matching record name, token count, or stated Git commit is insufficient.

```python
from tf.fabric import Fabric

coptic_api = Fabric(locations=[str(coptic_tf)], silent="deep").load(
    "source_record_id source_word_ordinal source_sha256", silent="deep"
)
assert coptic_api
```

The real full-source CI workflow `.github/workflows/issue82-full-streamed-lxx.yml`
checks both immutable Git commits, Greek mapping-critical feature hashes,
the Coptic parent's native warp fingerprint, all source records/slots, and
reloads both weft overlays. The process is intentionally resource-intensive
because constructing the complete Coptic parent TF remains memory-heavy;
the streaming change eliminates the additional all-word Python index and
per-feature dictionaries, not the parent conversion cost.

## Known limitations and next gates

Do **not** infer Greek/Coptic word identity from an equal verse address;
Coptic OT books may follow different verse divisions from Rahlfs LXX.
Greek `subverse` membership is a separate boundary layer. The **three-book
pilot** is retained as an introductory example, not a limit on the now
completed full source/address-candidate inventory. The current curated
multi-work CTS/book classification is still conservative: unresolved and
unclassified sources, alternate Greek editions (e.g., Daniel/Tobit), and
ambiguously displaced chapters require independent research. Issue #75
owns an **edition- and witness-qualified 1:N/N:1 versification crosswalk**
with primary evidence and explicit mapping statuses. That next step is
different from a book/chapter/verse equality lookup; independently evaluated
translated word alignment belongs after it.

See [research issue #70](../research/issue-70/RESEARCH_PLAN.md) and
[issue #73 plan](../research/issue-73/RESEARCH_PLAN.md) for those gates.
