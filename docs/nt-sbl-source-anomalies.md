# SBL NT reference anomaly inventory — complete source accounting

**Scope:** CopticScriptorium-TF issue [#117](https://github.com/alexsosn/CopticScriptorium-TF/issues/117). This is research into source annotations **without modifying any verse-address candidate or native TF weft**. The independent Greek NT TF corpus is a pinned, read-only parent; all alignment and diagnostics are owned by the Coptic repository.

## Real pinned evidence

Input Coptic TT: `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`. Greek verse-address lookup: `alexsosn/sblgnt@4dd0207bda66133fdfa9740ff0aae7de61228700`, 7,927 native verse nodes. Scan encompasses 2,628 physical directory/ZIP records, of which 48 contain 2,747 `sbl_greek` or `sbl_apparatus` annotations (1,652 + 1,095).

The original pinned source-to-Greek candidate classification remains **2,301 `reference_candidate`**, **437 `ambiguous`**, **9 `unresolved`**. Each original physical source annotation has a unique record, kind and ordinal and is represented in the full audit. All noncandidates are now included, not just the previous 24 diagnostic examples.

| Noncandidate reason category | Occurrences |
| --- | ---: |
| Missing/malformed NT source reference evidence | 366 |
| Conflicting source book/chapter/verse evidence | 67 |
| Mixed or missing Coptic word-level verse markers | 4 |
| No completely enclosed Coptic word span | 8 |
| Greek parent verse unavailable | 1 |
| **Total** | **446** |

**15 physical source records** contain one or more noncandidates. Source-free structured evidence in the GitHub CI artifact identifies each occurrence by physical record ID, annotation kind, original ordinal, fixed reason code, and categorical type of original source marker; each per-record status distribution is included.

## Raw annotation-shape verification

An independent regular-expression scanner of exact pinned TT opening attributes, which does not use the Coptic parser or Greek resolver, established these facts:

- Canonical `sahidica.mark/.../Mark_01.tt`: 45 verse groups, 45 `sbl_greek`, 36 `sbl_apparatus`, **no `verse_vid` tags**. Of 45 `vid_n` attributes, 41 have a CTS-verse-URN shape, 1 has an editorial reference shape, and 3 have neither shape. Ten `sbl_greek` values look like `41N chapter:verse` identifiers rather than Greek passage values.
- `coptic-treebank/.../Mark_01.tt`: the **same** counted source-annotation shapes, but its precise upstream Git blob hash differs from the canonical Mark 1 source: `a0da65bf1e656aa3b798fc4f50cebeb7f2ceb198` versus `16947eede50e5bdc03a1394c9b4d4b697da63072`. It is a *distinct physical witness*, **not** proven byte-identical.
- `sahidica.1corinthians/.../1Cor_01.tt`: 31 `verse_n`, 31 `verse_vid` and 31 `vid_n` tags; 30 `vid_n` values look like CTS verse URNs, one does not.

These classifications are lexical **shapes**, not editorial corrections. In particular, the Coptic resolver returns `None` both for absent and nonuniform word-markers. The diagnostic records `indeterminate` rather than `missing` when it cannot distinguish these causes. Even a source `vid_n` with the expected CTS syntax is not necessarily an authentic Greek/Coptic word alignment.

## Interpretation and next gates

A missing `verse_vid` field does **not automatically** invalidate a source verse if other **independent, matching** references could support it; however a Mark 1 source with possibly shifted attribute types must not be repaired by blindly relabeling Greek strings or editorial tags. The source evidence must be reviewed **by affected verse/annotation class**, with TDD examples for any proposed normalization. Retain both physical source identities.

The existing native Coptic/GNT TF modules and their 2,301 candidate, 437 ambiguous, 9 unresolved distribution are unchanged. If future repairs alter these, first test on pinned Mark/1Cor source and exact Greek node sections, then **rerun the full 2,394,354-word native TF plus bilateral module acceptance gate** from #120 with independently reviewed results. Don't redistribute Coptic/Greek source text or generated combined corpora without applicable rights review.

Implementation: `copticscriptorium_tf.nt_source_diagnostics.NonCandidateInventory`; raw scanner `research/issue_117/source_shape_probe.py`; complete pinned CI `tests/live_issue113_all_source_audit.py`. The checked report may be used to prioritize a subsequent source-limited repair ticket, but does not itself certify any new alignment.
