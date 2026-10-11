# Issue #65 — repair stale release-facing status documents

## Research (2026-10-11; exact production evidence)

- `KNOWN-ISSUES.md` still says **no production converter exists**, TT authority, word slot/section model, identity policy and resource budgets are unsettled. False: `README.md`, `research.md`, merged #13–#16/#26 and many successful exact-head CI real full conversion/reload runs show a deterministic TT → native TF converter with one `word` slot per TT norm, document-only section hierarchy, explicit documented overlap/same scholarly edges and bounded measured memory.
- README itself is stale at the `### Automatic upstream acquisition: outstanding limitation` block and release-facing issue list: canonical Agora registry was updated by **merged Agora #213** at `2e8618b1f1af35b66b932d144abfe33dd191cc9a`; complete automatic remote sparse TT acquisition → sandboxed full native TF → Context-Fabric import/search/cleanup passed exact-head **Agora #215** run `38063116201`, code merged at `d5c95562363348007c5ef9264abe38622ec66ac2`. Coptic #17 and Agora #205 have since CLOSED. Host still does NOT *automatically chain* the user-triggered Context-Fabric import; that remains explicit, even though end-to-end acceptance passed.
- `CopticScriptorium-TF` now has *source-local* native `verse_n/vid_n/verse_vid`, actual CenterBLC/LXX pinned 1935 native reference-candidate modules, and a full 2,628-source corpus audit. This is **NOT** Coptic ↔ Greek verified translated passage/word alignment; #70/#75/#92 are still open. Existing baseline 21,120 Greek verse IDs (before active #100 Bohairic Zechariah candidate crosswalk); avoid hardcoding rapidly-changing status numbers in status text.
- `copticscriptorium_tf.conllu` provides source parsing but converter still doesn't materialize optional CoNLL-U enhancements; #66 and stale unmergeable PR #67 track it. Corpus licenses are heterogeneous, code is MIT, generated TF distribution is NOT generically authorized. Local `--upstream-commit` form validation is not an independent verification of local source bytes; remote Git acquisition verifies its actual checkout.
- Existing stale PR #65 body and patch still describe unmerged Agora #198 and claim no installed materializer; its branch conflicts with main. Prefer replacing with current-state documented status and tests, not merging its obsolete text.
- Verify all claims against current main and live GitHub PR statuses before review.

## Research→plan→RED tests→documentation→CI→independent review

1. RED static tests against real `KNOWN-ISSUES.md` and actual `README.md`: require declared operational converter, tested registered remote full corpus, pin and link to exact acceptance evidence, explicit manual Context-Fabric import, CoNLL-U limitation, Coptic/LXX candidate-not-equivalence warning and licensing. Forbid obsolete sentences, obsolete outstanding #17 blocker and "still incomplete" registration claim. Assert no unverified claims that Agora automatically imports on every materialization.
2. Replace false pre-implementation register with compact curated **verified / limitation / blocked** sections, preserving differentiations (source code license vs generated data; candidate references vs textual alignment; direct TT vs optional CoNLL-U).
3. Correct only stale README Agora-source subsection and release-follow-up list. Preserve proven user command, registry pin, source trust and real documentation of explicit MCP calls. Avoid implying no network/sandbox limitations.
4. Exact-head `research-tests` and applicable docs workflows GREEN; inspect real test log. Independent skeptical review focused on exact statuses/links and no corpus redistribution.
5. Old PR #65 is superseded and should be **closed without merge** once its unique claims are incorporated into new reviewed docs. Close #65 issue on successful replacement PR only.

## Acceptance
- [ ] Red tests demonstrated on old docs, green on revised docs
- [ ] No false outstanding Agora #17/#205 claims
- [ ] No unsupported textual-alignment/license claims
- [ ] Verified explicit Context-Fabric import workflow
- [ ] Exact-head CI and independent adversarial review
