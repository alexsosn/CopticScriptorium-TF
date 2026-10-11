# Issue #117: complete source-free ambiguity anatomy

## Research, pinned public source
- The independent full TT→Greek NT census in #115/#122 observed 2,301 verified address candidates, 437 ambiguous and 9 unresolved SBL annotations. These statuses must not change during this research ticket.
- Exact pinned Coptic source `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`; exact read-only Greek NT TF parent `alexsosn/sblgnt@4dd0207bda66133fdfa9740ff0aae7de61228700`.
- Directly checked physical `sahidica.mark/sahidica.mark_TT/Mark_01.tt` (and independent `coptic-treebank` copy). Mark1 has 45 `verse_n`, **zero `verse_vid`**, 45 `vid_n` of which **41 begin CTS URN, one is editor-like and three other**, and 45 `sbl_greek` literals, **10 shaped as editor references (`41N n:n`)**. This is evidence of multiple source markup regimes plus apparent column shift; not justification to blindly infer targets.
- Directly checked `sahidica.1corinthians/sahidica.1corinthians_TT/1Cor_01.tt`: 31 `verse_vid` with 30 CTS-shaped `vid_n` and one other. The field anomalies are not limited to Mark.
- Canonical Mark1 and treebank Mark1 have **distinct upstream Git blob hashes** (`16947eede50e5bdc03a1394c9b4d4b697da63072` vs `a0da65bf1e656aa3b798fc4f50cebeb7f2ceb198`) despite identical observed raw annotation-tag-shape totals. Treat them as distinct physical witnesses; do not assume source bytes or readings are identical. No Greek or Coptic lexical source text will be copied.

## Research→plan→RED→implement→test→adversarial review
1. Write fail-first test corpus of synthetic Coptic SBL references for raw malformed/missing CTS, missing/malformed editor label, fake Greek literal that looks like `41N 1:5`, no whole-word span and mixed source markers. Fail closed on unknown reason/status or duplicate physical occurrence.
2. Implement a **read-only**, bounded vocabulary diagnostic collector for every unresolved/ambiguous annotation: exact physical source ID, original kind/ordinal, fixed reason_code, structural label shape codes and tag-presence flags; report no source Greek/apparatus or Coptic lexical values. Include complete noncandidate inventory and reason, shape, physical corpus + record counts (not a 24-example cap).
3. Hook collector into existing **pinned all-record source audit** job, while independently retaining its strict one-to-one 2,747 annotation conservation and actual Greek reverse node validation. Require diagnosis totals **437 ambiguous + 9 unresolved** and parity with existing audit counts. Provide machine-readable source-free JSON artifact.
4. Investigate distribution on all 48 annotated physical TT records (2,628 full scanned), compare sample anomalies with independently viewed pinned Mark1/1Cor1 and treebank copies. Distinguish source defects from overly strict resolver evidence policies, but do not change candidate classification until separate TDD proof is possible.
5. Independent adversarial PR review grounded in real source and exact CI evidence, including leakage/duplicate/count drift cases. No Coptic alignment files, code or results go to read-only sblgnt.

## Next gate
Use real anomaly strata to choose a *small, corroborated* verse-reference rule in a later PR. Any change to the 2,301/437/9 baseline requires the complete #120 native TF+weft release gate rerun, not merely pilot success.
