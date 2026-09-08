# Plan: Coptic Scriptorium → Text-Fabric

## Goal

Build a reproducible, loss-aware Text-Fabric converter that preserves Coptic Scriptorium's linguistic annotations, document structure, layout, translations, metadata, quality signals, overlap relationships, licensing, and provenance without inventing source semantics.

The plan is deliberately staged. Decisions marked **research gate** are not implementation choices yet.

## Phase 0 — repository/process bootstrap

- [ ] Persist agent workflow, research baseline, known-risk register, and PR review contract.
- [ ] Establish issue-driven work and independent review expectations.
- [ ] Add a parallel-agent claim protocol only after #5 determines the simplest reliable form.

## Phase 1 — source contract (**research gate: #1**)

Research first, then review:

- corpus/release inventory;
- field-by-field comparison of `*.tt`, CoNLL-U, TEI, PAULA, relANNIS, and `meta.json`;
- malformed/empty/exception census;
- annotation-quality inventory;
- upstream revision pinning and source hashing;
- license/distribution inventory.

Exit criteria:

- every candidate TF feature has a documented authoritative upstream representation;
- disagreements between representations are measured;
- source discovery is deterministic and reproducible;
- valid exceptions and fatal failures are explicitly classified.

## Phase 2 — identity and overlap policy (**research/design gate: #2**)

Define and independently review:

- stable scholarly document identity;
- release-scoped source-record identity;
- corpus membership;
- identical-copy relation;
- alternate-analysis relation;
- parallel-witness/redundancy relation;
- deterministic TF address disambiguation;
- user-facing filtering/preference semantics.

Exit criteria include corpus-wide uniqueness/collision measurements and machine-testable invariants.

## Phase 3 — TF schema (**research/design gate: #3**)

Choose only after phases 1–2 provide evidence:

- slot type;
- section/navigation policy across biblical and non-biblical corpora;
- nodes/edges for `orig_group`, `norm_group`, `orig`, `norm`;
- source and normalized text formats;
- UD dependency representation;
- entity and identity representation;
- sentence/layout/translation structures;
- metadata and quality features;
- zero-span and technical-anchor policy;
- deterministic node finalization/serialization order.

Required ADRs: slot semantics, section/address policy, zero-span/anchor policy, and identity/dedup policy.

## Phase 4 — parser and normalized intermediate source model

Create implementation ticket(s) only after reviewed phases 1–3.

RED-first tests must cover at least:

- metadata extraction;
- token/morpheme/bound-group nesting;
- layout boundary inside a normalized token;
- source-local dependency ID resolution;
- dependency root and missing/optional heads;
- entity span/head handling;
- translations;
- missing optional fields;
- malformed source behavior;
- deterministic source order and provenance.

The parser must preserve source semantics without assigning TF node IDs yet.

## Phase 5 — deterministic TF graph construction

RED-first tests for:

- contiguous semantic slot stream;
- every required non-slot object and edge;
- stable source-derived features;
- deterministic node assignment;
- TF-safe contiguous ranges per non-slot `otype`;
- zero-span behavior;
- no misleading `T.text()` rendering from technical anchors;
- exact source identifiers plus technical disambiguation where required;
- graph invariants before serialization.

## Phase 6 — Text-Fabric writer and real-TF integration

Tests must use the actual supported Text-Fabric version and verify:

- save/reload;
- warp and section indexes;
- formats and `T.text()` for each important node type;
- dependency/entity traversal;
- feature metadata/value types;
- deterministic artifact generation.

A mocked writer is insufficient as the final gate.

## Phase 7 — independent semantic parity audit

Build an audit path that rereads upstream material independently of the converter's normalized intermediate model.

At minimum compare:

- source files/hashes and conversion/exclusion ledger;
- document metadata and quality flags;
- structure and segmentation counts/content;
- original and normalized text reconstruction;
- lemmas/POS;
- dependency arcs/relations;
- entities/identities;
- layout boundaries;
- translations;
- overlap/redundancy classes;
- license/provenance records.

Deliberately corrupt generated data in tests and prove the audit detects it.

A green audit with non-zero allowlisted loss must say `regression-valid` or equivalent, not `lossless`/`research-ready`.

## Phase 8 — pinned full-corpus CI, scale, and release certification

- fetch/check out an immutable upstream release/tag/commit;
- run full conversion;
- run parity audit;
- load generated TF with real Text-Fabric;
- run representative research queries;
- enforce runtime/memory budgets;
- emit machine-readable census, structure, overlap, license, and provenance reports;
- cryptographically bind release certification to the generated artifact and upstream revision;
- keep published TF release directories immutable.

## Phase 9 — research ergonomics and documentation

After the corpus model is stable, add high-level helpers/examples for common tasks such as:

- querying normalized vs original forms;
- morphology/lemma/POS searches;
- dependency traversal;
- entity/identity lookup;
- retrieving translations;
- excluding or selecting redundant/alternate records;
- selecting annotation quality levels;
- citation/navigation for different corpus families.

Document source semantics and known limitations, not only API syntax.

## Ticket lifecycle

Each new implementation ticket must contain:

1. evidence/research references;
2. reviewed plan/contract;
3. explicit acceptance criteria;
4. RED test cases or an explanation why RED-first testing is inapplicable;
5. focused and full verification commands;
6. corpus-scale gate impact where relevant;
7. independent adversarial review bound to exact PR head.

When a full-corpus run reveals a valid unseen source shape, add a failing minimal fixture before implementing support. Do not weaken validation simply to make the corpus pass.
