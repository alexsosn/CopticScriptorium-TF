# Issue #2 — document identity, overlap, redundancy, and release-stable addressing

Pinned upstream repository: `CopticScriptorium/corpora`

Pinned upstream commit: `3ac067f1709a0012daf39ea8da2fac79980176a5`

Repository base for this cycle: `b69eef8edde66d74a9ff56656d6702127a5362f8`

## Goal

Define measured identity levels and overlap classes before Text-Fabric section addresses, node IDs, or any deduplication/preference policy are implemented.

## Upstream evidence already established

The pinned upstream README distinguishes three situations:

1. `coptic-treebank` repeats gold treebanked documents also present in source corpora and describes those copies as identical;
2. manually annotated biblical book corpora such as `sahidica.mark`, `sahidica.1corinthians`, and `sahidic.ruth` overlap the aggregate Sahidic NT/OT corpora and may differ in analysis;
3. parallel witnesses can be marked `redundant="yes"`; they need not be text-identical and are primarily a quantitative filtering concern.

Issue #1 measured 2,628 TT source records but only 2,390 `meta.json` scholarly identities: 2,152 identities have one TT copy and 238 have two TT copies. Physical source-copy identity and scholarly identity are therefore observably different.

A direct pinned-source check of the README's `XH204-216` example refines the upstream prose. The `shenoute-fox` and `coptic-treebank` TT records share the same literal `document_cts_urn`, title, normalized linguistic beginning, and core analysis, but their raw TT blobs differ: the treebank copy adds Arabic translation metadata and `<arabic ...>` markup. Raw byte equality is therefore too strong for semantic duplicate classification, while CTS equality alone is too weak.

## Identity levels to measure

The audit must keep these levels separate:

### 1. Physical source record

A release-scoped source copy identified by:

- pinned upstream repository;
- pinned upstream commit;
- stable source-relative path;
- raw source SHA-256;
- literal dataset/corpus path components.

No other identity level may erase this one.

### 2. Scholarly identity

The literal upstream `document_cts_urn` when present. Missing values, duplicate values, malformed values, and any inconsistent metadata remain explicit ledger entries. No CTS URN is synthesized from a title, filename, or neighboring record.

### 3. Text identity

Two deterministic projections are measured independently:

- normalized token sequence (`norm` attributes, entity-unescaped);
- original/diplomatic segment sequence (`orig` attributes, entity-unescaped).

This separates text-equivalence from raw serialization and orthogonal enrichment.

### 4. Linguistic-analysis identity

A deterministic per-token projection containing normalized form, lemma, fine POS, dependency relation, and dependency head resolved from TT-local IDs to document token positions. This deliberately excludes document metadata, translations, layout, and entity enrichment.

### 5. Orthogonal enrichment

Presence/count fingerprints for layers that can differ without changing the core linguistic analysis, including translations, Arabic translation markup, entities/identities, and layout boundaries. Metadata field/value differences are reported separately rather than folded into analysis identity.

## Same-scholarly-identity classification

For every group sharing one literal `document_cts_urn`, classify each pair/group from measured fingerprints:

- `byte_identical`: raw TT SHA-256 equal;
- `core_identical_source_variant`: raw bytes differ but normalized text, original text, and linguistic-analysis fingerprints agree;
- `alternate_analysis`: normalized text agrees but linguistic-analysis fingerprint differs;
- `textual_divergence`: normalized text fingerprint differs;
- `insufficient_identity`: required source identity evidence is missing or malformed; never force the record into another class.

Classification precedence is textual divergence > alternate analysis > core-identical source variant > byte-identical.

## Redundancy and witness relations

`redundant="yes"` is an independent source relation, not a duplicate class. The audit must list every redundant source record and preserve literal `witness` metadata where present. If a witness value is CTS-like, target resolution is measured but an unresolved target is reported rather than invented.

Parallel-witness filtering must never delete the source record from the generated dataset. It is a view/query policy.

## Release-scoped addressing contract to evaluate

The design will keep two public identifiers:

- `source_record_id`: deterministic from the literal release-scoped source path; human-readable path components stay available even if TF later needs a technical disambiguator;
- `scholarly_id`: literal `document_cts_urn` where available.

A source path is not claimed to be stable across upstream reorganizations. A scholarly CTS identity is not claimed to be a unique physical record. Published release provenance binds both to the immutable upstream commit.

Actual TF section/address structure remains issue #3; issue #2 only establishes the identity data that issue #3 may safely consume.

## Preference/filter policy to evaluate

Default behavior: preserve all source records.

Potential explicit views, to be accepted only if corpus measurements support them:

- `all`: every physical source record;
- `nonredundant`: exclude records explicitly marked `redundant=yes` from the view only;
- `source-preferred`: for core-identical `coptic-treebank`/source duplicates, prefer the non-convenience source copy while retaining the treebank copy addressable;
- `best-parsing`: within one scholarly identity, rank explicit `parsing` quality (`gold > checked > automatic`) and use a deterministic source-record tie-breaker. This must never compare unrelated scholarly identities or overwrite alternate analyses.

No preference view becomes destructive storage/deduplication.

## Corpus-wide research questions

The audit must answer:

1. How many TT records lack `document_cts_urn`?
2. How many scholarly identities have 1, 2, or more physical copies?
3. How many duplicate-CTS groups are byte-identical, core-identical source variants, alternate analyses, or textually divergent?
4. Which corpora participate in each class?
5. Do the documented treebank/source examples form one consistent class corpus-wide?
6. Do biblical book-vs-aggregate overlaps share CTS identities, and if so, what divergence class do they exhibit?
7. How many records are `redundant=yes`, what witness metadata is present, and how often does it resolve to a known scholarly identity?
8. Are literal source-record addresses unique case-sensitively and case-insensitively?
9. Does a deterministic quality preference ever face unresolved ties or missing quality metadata?

## TDD plan for research tooling

RED-first tests will cover at minimum:

1. same CTS + identical bytes;
2. same CTS + identical core analysis but extra enrichment/metadata;
3. same CTS + same normalized text but different POS/dependency analysis;
4. same CTS + different normalized text;
5. missing CTS remains ungrouped and ledgered;
6. `redundant=yes` + witness relation is preserved independently;
7. unresolved witness targets are surfaced;
8. source-record address collisions fail closed;
9. deterministic report ordering;
10. invalid UTF-8 fails closed rather than replacement-decoding.

The corpus-wide workflow will run the resulting identity audit against the exact pinned upstream commit and upload a machine-readable artifact.

## Deliverables

- deterministic `identity_audit.py` research tool;
- RED-first unit/regression tests;
- generated corpus-wide identity/overlap artifact in CI;
- `IDENTITY_POLICY.md` ADR with measured class counts and explicit preserve/filter/preference semantics;
- update to `research.md`;
- logically independent adversarial review on the exact final PR head.

## Gates

1. Research evidence and measurement plan committed.
2. Draft PR opened as the single canonical #2 work item.
3. RED tests prove missing behavior.
4. Smallest research-tool implementation makes tests GREEN.
5. Exact-head unit suite and pinned corpus audit GREEN.
6. ADR/policy written from generated evidence, not assumptions.
7. Independent adversarial review re-derives the contract from issue #2, upstream README, raw examples, diff, and generated artifact.
8. Merge only if no code-changing commit occurs after the final review.
