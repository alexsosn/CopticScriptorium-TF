# Plan: Coptic Scriptorium → Text-Fabric

## Product goal

Deliver a usable local Coptic Scriptorium → Text-Fabric materializer that preserves the source semantics measured in issues #1–#3, loads cleanly in Text-Fabric/Context-Fabric, and can be invoked by Agora from either a pinned upstream checkout or a user-local source tree.

The current product does **not** require publishing prebuilt TF data, solving aggregate redistribution licensing, maintaining historical generated corpora, or building release-certification machinery.

## Completed research gates

### Source authority — #1 complete

The canonical production inputs and conflict rules are established:

- TT is the source-native document/annotation authority;
- structurally valid CoNLL-U supplies explicitly allowed supplementary UD/construction information;
- `meta.json` is normalization/reference evidence, not an overwrite source;
- PAULA/relANNIS and TEI remain validation/provenance evidence unless later implementation exposes a measured missing requirement;
- malformed/empty/source-exception cases are ledgered;
- provenance is bound to an immutable upstream revision.

### Identity and overlap — #2 complete

The default product is one logical union corpus preserving every physical source record. Scholarly CTS identity, source-record identity, overlap classes, witnesses, redundancy, and source-preference semantics remain separate and queryable. No silent deduplication is permitted.

### TF graph schema — #3 finalization gate

PR #12 contains the measured graph contract. Before production implementation begins in earnest:

1. complete logically independent adversarial review of the exact PR head;
2. fix any review findings;
3. rerun the exact-head pinned-corpus gate;
4. merge #12 and close #3.

No additional broad corpus research is required before implementation. New research is triggered only by a failing fixture, an unseen source shape, or a concrete product requirement not covered by the reviewed contracts.

## Implementation path

### Phase 1 — parser and normalized source model

Implement a deterministic parser/intermediate representation without assigning TF node IDs.

RED-first coverage must include metadata, grouping/segmentation, dependencies, entities, translations, token-internal layout crossings, zero-token textual loci, malformed/optional fields, archive-packaged inputs, deterministic ordering, and source provenance.

Exit criteria:

- supported source records parse into one explicit normalized model;
- invalid/unsupported records fail or ledger exactly as specified by #1;
- source semantics can be reconstructed without TF-specific behavior;
- focused and full parser tests pass.

### Phase 2 — deterministic graph construction

Transform the normalized source model into the reviewed #3 graph contract.

RED-first coverage must include semantic word slots, synthetic zero-span slots, document/sentence/group/layout/entity/translation nodes, dependency/entity-head edges, overlap/witness relations, deterministic node ordering, and TF-safe contiguous non-slot ranges.

Exit criteria:

- graph invariants are validated before serialization;
- every physical source record remains distinct;
- no technical anchor or synthetic slot fabricates visible Coptic text;
- normalized and diplomatic representations remain independently recoverable.

### Phase 3 — Text-Fabric writer and local load

Serialize the graph using the supported real Text-Fabric version.

Tests must verify:

- `otype.tf`/`oslots.tf` and required semantic features;
- save/reload with real TF;
- document section lookup;
- named normalized, diplomatic/layout and translation text formats;
- dependency/entity traversal;
- deterministic output for identical input;
- clean Context-Fabric/cfabric-mcp discovery/load path.

A mocked writer is not a final acceptance gate.

### Phase 4 — independent source parity and full-corpus validation

Keep the existing independent-audit principle, but scope it to product correctness rather than release certification.

At minimum verify against the pinned upstream source:

- document/source identity and provenance;
- segmentation and reconstructed normalized/original text;
- metadata/quality/license evidence;
- lemma/POS and dependency information;
- entities/identities;
- layout boundaries including token-internal crossings;
- translations and zero-span translation loci;
- overlap/redundancy/witness relations.

The audit must reread upstream evidence independently of the converter's intermediate representation. Deliberate-corruption tests should prove important regressions are detected.

Exit criteria:

- complete pinned-source materialization succeeds;
- real TF reload succeeds;
- representative research queries return the expected structures;
- runtime, peak memory and output size are measured and reasonable for local use;
- known source defects appear in the conversion report rather than being silently normalized away.

### Phase 5 — Agora materializer integration

Implement the smallest Agora-facing contract required for installation/use:

- pinned Git acquisition from `CopticScriptorium/corpora`;
- user-local source-directory input;
- network-independent conversion after acquisition;
- deterministic local output layout;
- `conversion-report.json` with source revision, source-record provenance, exceptions and license evidence;
- Agora manifest/schema validation;
- local TF discovery/load through the intended Context-Fabric/cfabric-mcp path.

Selective corpus materialization is deferred unless full-corpus measurements show a real disk/memory problem. If added later, it must reuse the same identity/schema model and may not introduce silent deduplication.

### Phase 6 — user documentation and research ergonomics

Before calling the materializer usable, document:

- installation/materialization from Agora and directly from the CLI/module;
- expected disk/time/memory footprint;
- corpus/dataset filtering in the union corpus;
- normalized vs diplomatic/original text;
- morphology/lemma/POS queries;
- dependency traversal;
- entities/identities;
- translations;
- overlap/redundancy/preference semantics;
- provenance, licenses and known source defects.

Prefer a small number of working end-to-end examples over a large tutorial framework.

## Explicitly deferred / not required for the first usable release

- publication of prebuilt TF corpora;
- aggregate mixed-license solving/relicensing;
- cryptographic release certification;
- immutable archives of historical generated TF versions;
- a custom parallel-agent claim registry;
- CI optimization work that does not unblock product implementation;
- selective/sub-corpus materialization without measured local-resource need;
- production TEI/PAULA/relANNIS parsers without measured missing semantics.

## Ticket lifecycle

Every implementation ticket follows:

research evidence/contract → focused plan → RED tests → implementation → focused tests → relevant full-corpus gate → logically independent exact-head adversarial review.

Do not rerun broad exploratory research for already settled questions. When implementation discovers a genuinely unseen valid source shape, first add a minimal failing fixture and record the measured source evidence; then extend the contract narrowly.
