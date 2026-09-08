## Issue / scope

Closes #

## Research

- Evidence/source revision:
- Relevant `research.md` / ADR / prior-project findings:
- Source shapes measured rather than assumed:

## Plan / contract

- Acceptance criteria implemented:
- Explicitly out of scope:
- Source semantics or TF invariants affected:

## TDD evidence

- RED test(s) added before implementation:
- Expected failure observed:
- If RED-first is not applicable, explain why:

## Verification on exact PR head

Head SHA:

- [ ] focused tests
- [ ] full relevant test suite
- [ ] real Text-Fabric save/reload where serialization is affected
- [ ] graph/source invariants
- [ ] corpus-wide parity/performance gates where affected
- [ ] no unexplained skipped/excluded source records

Commands/results:

## Provenance / data fidelity

- Upstream revision/hash impact:
- New exclusions/allowlist entries: none / explain
- Generated-data licensing impact:
- Known limitations updated if required:

## Developer review

Potential failure modes checked by the implementer:

## Logically independent adversarial review

Reviewer must re-read the issue/specification and exact-head diff without relying on the developer-review rationale.

Reviewed head SHA:

- [ ] source loss / silent filtering
- [ ] unstable identity/addressing
- [ ] misleading `oslots` / text formats
- [ ] duplicate/overlap semantics
- [ ] tests independent enough to catch converter corruption
- [ ] corpus-scale complexity
- [ ] provenance/licensing/release claims
- [ ] acceptance criteria satisfied

Findings / disposition:

A code-changing commit after this review requires adversarial review again for the new head.
