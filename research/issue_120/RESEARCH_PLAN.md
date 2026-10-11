# Issue #120 — full-corpus NT native weft acceptance

## Research evidence
- PR #106 validated native Coptic TF: 2,394,354 word slots, 2,628 physical documents, 134 .tf features, 7.15 GiB peak RSS. Reuse research/issue-16/full_converter_smoke.py instead of reimplementing converter.
- PR #106 verified every one of 2,747 original SBL annotations against the full native corpus.
- PR #115 independently resolved 2,301 edition-qualified candidates, 437 ambiguous, 9 unresolved; 904 unique Greek verse addresses.
- PR #119 established additive Coptic-owned weft-only modules and real TF round-trip: 129 SBL nodes to 44 Greek verse nodes, parent fingerprints and atomic no-clobber.

## Plan and required gates
1. RED-first tests define strict source-to-module count invariants and independent bilateral TF native reload, rejecting extra or missing feature nodes, invalid statuses, word-slot leakage, nonverse targets and incorrect Greek counts.
2. Reuse existing full converter smoke and full SBL source-to-native recheck. From all 2,628 pinned TT directory/ZIP records, independently scan original SBL attributes and parse exactly 48 annotated documents. Preserve treebank duplicate physical witnesses separately. Reject dirty source checkout and wrong Git revision.
3. In an isolated projection process load full pinned Coptic native TF and pinned read-only Greek NT TF. Run project_nt_modules for all 48 documents. Enforce exact 2,747 statuses, 2,301 Coptic candidate nodes, 904 Greek target verses and all 437+9 noncandidates. The German/Greek corpora are never modified.
4. In a distinct verification process validate cryptographic parent feature hashes, reload Coptic+weft and Greek+weft in native Text-Fabric, enumerate all sparse values, compare bilateral address-count multisets, reject mapping onto Coptic word slots and Greek nonverse nodes. Enforce report contains counts/hashes only, never source text.
5. Scope heavy CI only to dedicated issue120 branch or explicit manual dispatch. Record time/RSS for full converter, projection and verification as isolated processes. Upload only source-free results, not a derived Coptic/Greek corpus or weft data.
6. Post a logically independent skeptical review grounded in exact-head full-corpus evidence; only merge with passing tests, no counterfeit links and exact head SHA.

## Scope limits
Historical Greek source attestation supports verse-address candidates only, not word- or text-level equivalence. PR #117 investigates malformed SBL annotations; this gate preserves ambiguity rather than inventing data. The sblgnt repo remains an unchanged read-only parent.
