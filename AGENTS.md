# Agent instructions

All behavioral work in this repository is issue-driven and follows this gate sequence:

1. **Research** — inspect upstream data, relevant prior projects, and current repository state. Persist material findings in the issue and/or `research.md`/focused research docs.
2. **Plan** — define the source contract, graph/behavioral contract, acceptance criteria, failure modes, and test strategy before implementation.
3. **RED-first TDD** — for behavior that can be tested, add a failing test that demonstrates the required behavior or regression before implementing it. Record the RED evidence when practical.
4. **Implementation** — make the smallest change that satisfies the reviewed plan. Do not broaden corpus semantics opportunistically.
5. **Verification** — run focused tests, the complete relevant suite, graph invariants, and any corpus-wide parity gates against the exact PR head.
6. **Independent adversarial review** — review the issue/specification and exact-head diff from a logically independent context. Re-derive likely failure modes; do not merely validate the implementer's rationale.
7. **Finalize** — merge/close only after required checks and independent review pass for the current head. Any code-changing commit after review invalidates that review for finalization.

## Autonomous loop

When no unblocked feature ticket remains, continue with performance, stability, ergonomics, documentation, validation, release engineering, and edge cases. Research may open new issues when evidence warrants them.

Do not leave duplicate or orphaned implementation PRs/branches. Before taking work, reconcile current issues and PRs. One ticket should have at most one canonical active implementation PR. Superseded work must be closed or explicitly handed off.

Parallel claim/lease machinery is intentionally deferred to issue #5; until it exists, agents must use visible issue/PR state conservatively and avoid parallel implementation of the same ticket.

## Source fidelity rules

- Pin and record the upstream Coptic Scriptorium revision used for any reproducible conversion.
- Preserve stable source-relative paths and source hashes in provenance.
- Never silently skip malformed, empty, unsupported, duplicate, or license-restricted records. Classify and report them.
- Treat upstream annotation quality (`automatic`, `checked`, `gold`) as data, not as permission to overwrite one analysis with another.
- Distinguish identical duplicates, alternate analyses of the same document, and parallel witnesses. Do not deduplicate before the identity policy is reviewed.
- Do not infer a semantic value from layout/markup residue unless research establishes that interpretation.
- A successful parse/write/reload is not a losslessness proof. Corpus-wide semantic parity must eventually be checked by an independent reread of source material rather than by replaying the converter's own intermediate representation.

## Text-Fabric invariants inherited from prior converters

- Decide the semantic slot type explicitly; do not choose it because it is easiest to serialize.
- Independently positioned textual zero-span entities that must exist in the TF sequence use explicit surface-less synthetic slots when required. Do not borrow a neighbouring real slot or fabricate visible content.
- Metadata/provenance abstractions may use documented technical anchors if TF serialization requires them, but node-specific text formats must prevent those anchors from rendering as semantic text.
- Ancestors reuse descendant anchors instead of multiplying synthetic slots.
- Every non-slot `otype` must occupy a TF-safe contiguous node-id range at serialization/finalization time.
- Literal upstream identifiers remain available even when TF navigation requires a deterministic technical disambiguator.
- Distinguish semantic/source slots, synthetic slots, and total TF slots in reports and tests.

## Coptic Scriptorium parser constraints already observed

Do not treat `*.tt` as XML or as a line-oriented token format. The sampled TreeTagger SGML contains overlapping markup: a line span can close while a `norm` token remains open, the next line can open, and only then does the token close. Structural layout spans and linguistic spans therefore do not form one properly nested tree.

The parser design must preserve intersecting annotation layers explicitly. A strict XML parser or a single ordinary stack/tree is insufficient unless a separately researched normalization step first converts the SGML to an equivalent lossless representation and proves parity. Any such normalization needs tests showing that token text, layout boundaries, and source offsets survive unchanged.

Preserve the relationships among `orig_group`, `norm_group`, `orig`, and `norm` even when layout markup crosses them.

Upstream-local XML-like IDs such as `u1` and dependency heads such as `#u3` are document-local source identifiers; never use them directly as globally unique TF node IDs.

## Review standard

An independent reviewer should actively look for:

- silent source loss or undocumented filtering;
- graph objects that render misleading text through `oslots`;
- unstable/non-deterministic IDs or section addresses;
- duplicate data accidentally counted as independent evidence;
- metadata/annotation conflicts silently resolved by format precedence;
- tests that only reproduce the implementation rather than independently checking source semantics;
- allowlists/baselines that make a green gate look like zero known defects;
- corpus-scale complexity hidden by tiny synthetic fixtures;
- release/provenance claims not bound to an immutable upstream revision and generated artifact.
