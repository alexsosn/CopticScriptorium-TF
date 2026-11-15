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

## Optional external STEPBible TVTMS numbering diagnostic (#194)

The crosswalk audit can *optionally* compare source-reference candidates against
the STEPBible/Tyndale House **TVTMS** English→Greek numbering table. Its derived
[Metaxia JSON](https://github.com/metaxiamultimedia/scriptures-js-source-stepbible-versification)
is **CC BY 4.0** data, not vendored into this MIT package. Original TVTMS by
STEP Bible / Tyndale House Cambridge:
https://github.com/STEPBible/STEPBible-Data
([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)).
The derived dataset reorders/normalizes source references and is restricted to
39 books; it omits the Latin/variant Greek columns. Its own validation report
records `English->LXX: groundTruthAvailable=false`, `anchorChecked=0`,
and 119 normalization conflicts across directions. **Never use it as proof
of a Coptic reading or translate its numbering to Coptic automatically.**

The exact accepted derived dataset is
`metaxiamultimedia/scriptures-js-source-stepbible-versification@f426b7253623731ce788c8ce7abcd1d8f95c1f70`,
file `data/stepbible-versification/mapping.json`, Git blob
`fe3cd19cdef252e7537bb739b8cf4117dcabe927`. The original TVTMS
source pin is `STEPBible/STEPBible-Data@86ab0b75e195d3269c081201f2ff66afa10d5a30`.
The loader rejects any other normalized JSON bytes before parsing. An independent
GitHub Actions checkout of the original STEPBible file at the pinned commit
found Git blob `4fdcb4fd761ba8a680a3f0cc95ad65f591e18d4b` and raw-file
SHA-256 `63058e0f20201af4bdaa7d830da5be8f493455d947c5f147d84840b33db9ddf8`.
**The derived project's `SOURCE.json` instead claims `934350a6…` for that
same upstream commit.** This discrepancy means the derived transformation
chain is not independently reproducible as currently documented. The
report records both digests and a `provenance_warning`; neither the
17 Zechariah numbering agreements nor broader hypotheses prove textual
correspondence.

Run the existing complete pinned Coptic TT ↔ LXX audit with this extra input:

```bash
python tests/live_issue80_full_lxx_coverage.py \
  /path/to/pinned-coptic /path/to/CenterBLC-LXX/tf/1935 \
  /tmp/coptic-coverage-tvtms-report.json \
  /path/to/pinned-metaxia/data/stepbible-versification/mapping.json
```

This adds an **aggregate-only** `external_tvtms_diagnostic` section:
`reviewed_agree`/`reviewed_disagree` only for the exact existing
byte-locked *Bohairic Zechariah* numbering candidate policy (17 rules);
`source_scheme_unverified` where the external English scheme makes a
different suggestion but Coptic numbering provenance is insufficient;
`external_non_1to1` for missing/partial targets;
`no_explicit_exception` for absent entries in the *exceptions-only*
TVTMS mapping (which emphatically does **not** prove identity); and
`unclassifiable` for invalid/unknown/unsupported source references
(including alternate Greek edition selection). This is a read-only
diagnostic; native Coptic TF/LXX TF parent modules and original source
references are **unchanged**. No Greek/Coptic word alignment is inferred.

The real negative control is **Sahidic Jonah 2:1**: an English Jonah 2:1
would map to Greek 2:2 in TVTMS, but this Coptic edition already uses
Greek-style verse numbering. Assigning the English offset would corrupt
existing references. Psalms superscriptions and `verse_n=0` are likewise
not automatically converted. Issue [#194](https://github.com/alexsosn/CopticScriptorium-TF/issues/194)
tracks the aggregate external coverage audit and remaining primary-text review.

## Bohairic Psalm verse-zero source spans — #199

A reproducible *actual upstream* audit of `CopticScriptorium/corpora`
`bohairic.ot/bohairic.ot_TT.zip` at
`3ac067f1709a0012daf39ea8da2fac79980176a5` finds **151/151
nonempty** source-`verse_n="0"` spans, totaling **1,313 original Coptic
word slots** in the Bohairic Psalm 1–151 documents. All zero markers
are the first verse marker before any `norm`, and all are followed by
literal `verse_n="1"`; there are **no zero-word placeholders**.
Their 151 counterpart Greek first-verse `Ps chapter:1` nodes exist
in the exact pinned CenterBLC/LXX parent (each has one native subverse).
This is *Greek reference existence*, not certified textual alignment.

Source controls: Psalm 1 zero span has **1 word**, Psalm 17 has **59**,
Psalm 151 has **11**. The Coptic Scriptorium Bohairic Psalm 17
[chapter view](https://data.copticscriptorium.org/texts/bohairicot/19_psalmi_17/)
shows words corresponding to the superscription including David and
Saul; the published [LXX Ps 17:1–2](https://www.biblindex.org/en/bible/septuaginta/ps-17%3A1)
places the superscription in Greek verse 1, with "and he said"
at Greek verse 2. Thus **Coptic zero spans cannot be mapped by a
single global 0→Greek 1 rule**, and Coptic verse 1 must not be assumed
to be equivalent to Greek verse 1 in chapters with numbered headings.
Psalm 1's one-word zero span is another negative control.

Read-only classifier `copticscriptorium_tf.psalm_zero_boundary.inspect_psalm_zero`
returns original source zero/next-marker positions and counts,
Greek next verse **existence only**, physical source SHA-256 and
chapter/edition provenance. It **does not modify** original
Coptic `verse_n`, native TF graph, or bilateral weft references.
Run a real exact-source acceptance using:

```bash
python tests/live_issue199_psalm_zero.py \
  /path/to/pinned-coptic /path/to/CenterBLC-LXX/tf/1935 \
  /tmp/issue199-psalm-zero-report.json
```

Only aggregate source metadata is saved; no licensed Coptic/Greek text
is redistributed. The exact-source real CI for this audit and follow-up
primary-text cross-boundary/many-to-one mapping work are tracked by
[#199](https://github.com/alexsosn/CopticScriptorium-TF/issues/199)
and the open parent [#75](https://github.com/alexsosn/CopticScriptorium-TF/issues/75).

## Six source-byte-locked Bohairic Psalm0 / Greek1–2 lexical anchors — #201

The read-only `copticscriptorium_tf.psalm_boundary_crosscheck` compares
**six original, SHA-256-locked physical TT Bohairic Psalm witnesses**
(`bohairic.ot:19_Psalmi_001,003,017,051,149,151`) to the exact
`CenterBLC/LXX:1935` Greek Psalm `verse 1` and `verse 2` *native word
nodes*. All 12 Greek verse sections were loaded from
`CenterBLC/LXX@f32a98eddf7eb239aa73ab863d70381e416d5076`, with
parent feature blobs verified. No English↔Greek TVTMS offset was assumed.

| Psalm | Original Coptic verse-0 word slots | Verified source-language / Greek lexical *anchor* | Hypothesis; NOT a certified translation |
| --- | ---: | --- | --- |
| 1 | 1 | Original source 0 is literal `...`; Greek 1 begins `Μακάριος` | Source editorial placeholder, not a matching word |
| 3 | 16 | David + Absalom named in source 0 and Greek 1 | Heading may fall in Greek 3:1 |
| 17 | 59 | Source 0 ends with 'and he said' (`ⲟⲩⲟϩ ⲡⲉϫⲁϥ`); Greek 17:2 **begins** `καὶ εἶπεν` | Crosses Greek 17:1–2, so Coptic 0 cannot be mapped to a single complete Greek verse |
| 51 | 42 | Source 0 names Doeg and Abimelech; corresponding names in Greek 51:2, while Greek 51:1 opens heading with David | Heading may cover two Greek verse addresses (51:1–2) |
| 149 | 1 | Source 0 `ⲁⲗⲗⲏⲗⲟⲩⲓⲁ` is Greek 149:1 opening `Ἀλληλούϊα` | Inside one Greek verse, not Greek verse 0 or complete Greek verse 1 |
| 151 | 11 | Original/source first-two-verse word nodes checked; no shared trusted anchor established | Needs primary collation; unusual Psalm 151 editorial tradition |

Use the exact-source Coptic OT `bohairic.ot_TT.zip` at
`CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`
and original LXX `tf/1935` parent at the pinned commit:

```bash
python tests/live_issue201_psalm_boundary.py \
  /path/to/pinned-coptic /path/to/CenterBLC-LXX/tf/1935 \
  /tmp/issue201-six-boundaries.json
```

The script rejects any of the six changed TT content hashes, non-original
document CTS work/edition or parent Greek TF feature blobs, absent/misordered
native verse/word nodes, and altered curated positional lexical motifs.
The result contains **only metadata** (source IDs/SHA, word counts, Boolean
motif attestations, cautious status) and is safe to inspect; neither Coptic
nor Greek text is redistributed. Independent Rahlfs displays corroborate
the title boundaries:
[Ps 3](https://www.die-bibel.de/bibel/LXX/PSA.3),
[Ps 17](https://www.die-bibel.de/bibel/LXX/PSA.17),
[Ps 51](https://www.die-bibel.de/bibel/LXX/PSA.51),
[Ps 149](https://www.die-bibel.de/bibel/LXX/PSA.149).
See [#201](https://github.com/alexsosn/CopticScriptorium-TF/issues/201)
for exact SHA-256 controls.

**No TF mapping has been changed.** Existing numeric verse candidates for
these chapters remain hypotheses and may be **incorrect**, especially
`bohairic.ot` Psalm17 source verse 1 → Greek17:1, as the Greek 17:1 text
is an earlier superscription while Coptic verse 1 begins after 'and he said'.
A future mapping must preserve the source 0/1 split, identify Greek word
positions and allow 1:N/N:1 relations in native Text-Fabric rather than
representing a cross-verse span as a one-verse `coptic_lxx_ref_id`. The
remaining Bohairic/Sahidic Psalm editions and #75/#108 are open.

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
