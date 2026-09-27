# Issue #39 research and plan

## Research

Generated Text-Fabric metadata carries `upstreamCommit` globally, so this field is part
of reproducibility/provenance rather than a free-form note. The direct converter does
not validate it today. In contrast, the Agora adapter already accepts only full
40/64-hex Git commit hashes and converts an absent user-local revision to the explicit
`unversioned-local` sentinel.

Abbreviated Git hashes are repository-state-dependent and symbolic names such as
`main` are mutable. Storing either as the corpus's source commit makes later
reproduction ambiguous.

## Plan

1. RED: prove invalid symbolic and abbreviated revisions fail before
   `parse_source_tree()`; prove full SHA-1, full SHA-256 and `unversioned-local`
   pass the provenance gate.
2. Put the validation in the converter API, so CLI and Agora cannot diverge.
3. Reuse the same rule from the Agora adapter instead of maintaining a second regex.
4. Replace short synthetic revisions in converter tests with a full immutable fixture
   hash.
5. Document exact accepted provenance forms.
6. Run exact-head CI and perform independent adversarial review.

## Non-goals

No network lookup is performed to prove that a syntactically valid hash exists in a
remote repository. This gate guarantees immutable identifier form, not repository
membership.
