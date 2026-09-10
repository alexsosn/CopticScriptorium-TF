# Identity, overlap, and addressing policy

Status: proposed ADR for issue #2, derived from the corpus-wide audit at pinned upstream `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`.

This ADR defines identity and non-destructive overlap semantics for later Text-Fabric graph design. It does not assign TF node IDs or section structures; those remain issue #3.

## Decision

Keep every physical TT source record addressable. Do not deduplicate the stored corpus from CTS equality, treebank membership, `redundant=yes`, filename similarity, or a quality rank.

Expose two independent identity levels:

1. **Release-scoped source record identity** — the literal dataset plus record path, bound in provenance to the immutable upstream commit and raw source hash. This identifies one physical source copy in one release. It is unique case-insensitively in the pinned corpus. A source path is not promised to survive upstream reorganizations across releases.
2. **Scholarly identity** — the literal upstream `document_cts_urn` when valid. It can identify multiple physical records. It is never synthesized from filename, title, neighbouring records, or a documented overlap relation.

The corpus also exposes relations among source records and scholarly identities. Those relations are data, not instructions to delete one side.

## Corpus-wide identity measurements

The pinned TT corpus contains:

- **2,628 physical source records**;
- **2,520 valid scholarly CTS identities**;
- **2,412 CTS identities with one source record**;
- **108 CTS identities with two source records**;
- no CTS identity with more than two source records;
- **0 missing**, **0 malformed**, and **0 conflicting** `document_cts_urn` values after source-native duplicate-attribute handling.

All 108 duplicated scholarly identities were classified from raw bytes, original text, normalized text, and linguistic-analysis fingerprints:

| Class | Groups | Meaning |
| --- | ---: | --- |
| `byte_identical` | 91 | The two TT byte streams are identical. |
| `core_identical_source_variant` | 1 | Raw source differs, but original text, normalized text, and linguistic analysis agree. |
| `alternate_analysis` | 15 | Text identity agrees while the linguistic-analysis fingerprint differs. |
| `textual_divergence` | 1 | Original or normalized text differs. |

The classification is deliberately hierarchical: textual divergence outranks analysis divergence, which outranks a source-only/enrichment variant, which outranks byte identity.

The upstream README calls the `coptic-treebank` copies “identical”, but this cannot be used as a generic deduplication rule. On the pinned release, `coptic-treebank` participates in 86 duplicate-CTS groups: 69 byte-identical, 15 alternate analyses, one core-identical source variant, and one textual divergence. `bohairic-treebank` participates in 22 groups, all byte-identical on this release. Treebank membership is therefore provenance/topology, not an equivalence proof.

## Documented book ↔ aggregate overlap

The biblical book-vs-aggregate overlap documented upstream is a separate relation family because the paired records do **not** share literal CTS identities.

The audit explicitly maps the finite upstream-documented families rather than inferring relations from similar filenames or CTS suffixes:

- 16 `sahidica.mark` ↔ `sahidica.nt` Mark chapter pairs;
- 16 `sahidica.1corinthians` ↔ `sahidica.nt` 1 Corinthians chapter pairs;
- 4 `sahidic.ruth` ↔ `sahidic.ot` Ruth chapter pairs.

All **36/36** documented counterparts are present and have different scholarly IDs. Their measured relationship is:

- **19 `alternate_analysis`** pairs;
- **17 `textual_divergence`** pairs;
- 0 byte-identical/core-identical pairs.

By family, Mark is 11 alternate-analysis / 5 textual-divergence, 1 Corinthians is 8 / 8, and Ruth is 0 / 4. These pairs must never be collapsed by a generic “same biblical chapter” rule.

## Redundancy and witness relations

`redundant=yes` is independent of both CTS duplication and the book↔aggregate relation.

The pinned corpus contains:

- **18 records marked `redundant=yes`**;
- one of those 18 has no `witness` value;
- **111 records with a `witness` value** in total, so witness metadata is not restricted to redundant records;
- 28 witness values are a pure CTS URN;
- 83 are free-text source values and remain preserved literally;
- five of those free-text values contain embedded CTS URNs;
- **35 CTS targets** are extractable from 33 witness relations;
- **35/35 targets resolve** to a known scholarly identity on the pinned release; unresolved-target count is 0.

Embedded target extraction does not rewrite the literal witness string. Free-text witness metadata remains `free_text`; extracted CTS targets are a parallel machine-readable relation layer. If a future release contains an unresolved target, it must remain in an explicit unresolved-target ledger.

## Fingerprints are evidence, not public identity

The research audit computes deterministic fingerprints for:

- raw TT bytes;
- ordered normalized-token sequence;
- ordered original/diplomatic segment sequence;
- linguistic analysis (`norm`, lemma, fine POS, dependency relation, dependency head resolved to document token position);
- selected orthogonal enrichment counts.

These hashes classify relationships inside a pinned release. They are not public identifiers and must not replace literal source provenance or CTS identity.

A changed fingerprint in a later source release means the relation must be remeasured. It is not evidence that an old address should be silently redirected to a new record.

## User-facing views

Storage/default materialization policy is **preserve all**. Views are non-destructive filters over that storage.

### `all`

Return all physical source records. This is the default and the only view that is semantically neutral.

### `nonredundant`

Exclude only records with literal upstream `redundant=yes` from the view. The records remain stored and directly addressable. This filter does not remove treebank duplicates or book↔aggregate overlaps unless those records independently carry `redundant=yes`.

### `source-preferred`

This view may select the non-convenience source copy only when all of the following are true:

- two records share one scholarly CTS identity;
- the pair is `byte_identical` or `core_identical_source_variant`;
- exactly one copy belongs to a known convenience treebank dataset and one does not.

On the pinned corpus, **92/108 duplicate groups are eligible** and 16 are ineligible because they contain alternate analysis or textual divergence. Ineligible groups must return/preserve both candidates rather than inventing a winner.

### `best-parsing`

No automatic winner is evidence-backed on this release. Among all 108 duplicated CTS groups:

- **0 have a unique highest parsing-quality candidate**;
- **108 are ties**;
- 104 are `gold`/`gold` ties and four are `automatic`/`automatic` ties;
- 0 groups lack parsing-quality metadata.

A deterministic source-record ID can order tied candidates for stable output, but that ordering is not a scholarly preference and must not be exposed as “best”. If a future release produces a unique explicit quality winner, the view may report it only when every candidate in that scholarly-identity group has a recognized parsing-quality value. If all candidates lack recognized quality the status is `missing_quality`; if known and unknown quality values are mixed the status is `incomplete_quality`. Both statuses return no winner and preserve all candidates.

## Addressing invariants for issue #3

Issue #3 may choose TF section/navigation structure, but it must preserve these identity invariants:

- every physical source record keeps its release-scoped source identity and immutable source provenance;
- literal `document_cts_urn` remains separately available as scholarly identity;
- a CTS identity is not assumed to identify exactly one physical record;
- documented book↔aggregate relations do not synthesize CTS equivalence;
- treebank membership never implies semantic equivalence without the measured fingerprint class;
- `redundant=yes` and witness relations remain independently queryable;
- literal witness text and extracted CTS targets remain separately recoverable;
- no preference/filter view mutates stored records or redirects one source identity onto another;
- case-insensitive source-address collisions fail closed rather than receiving silent suffixes.

## Release behavior

A generated release must record the upstream commit used to derive source identities and relationship classifications. Re-running against a newer upstream revision recomputes all fingerprints, duplicate classes, documented-overlap pairs, witness resolutions, and preference eligibility.

The public source-record identity is release-scoped by design. Stable cross-release scholarly linkage is supplied by literal CTS identity where upstream provides it; the converter must not pretend source paths are permanent identifiers.

## Consequences for implementation planning

Issue #3 can now design a union TF corpus without choosing one record per CTS identity. The graph should preserve all source copies and expose scholarly identity plus explicit overlap/witness relations as features/edges or metadata suitable for querying.

Implementation tickets should test the four duplicate classes separately. In particular, optimization must never replace “same CTS” with “same node” or use treebank membership as a destructive deduplication shortcut.
