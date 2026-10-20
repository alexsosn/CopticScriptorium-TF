# Issue #178 — README source-schema inventory and measured footprint

## Original evidence (source-locked, not estimated)
- Actual current main at 251a151739586b0b129e0ed6066c6464cd0a8c9c after source conservation #173.
- Source code copticscriptorium_tf/model.py declares 83 native non-slot original TT wrapper kinds, in ten tuple declarations and the 3-key intervention dictionary. They coexist with 18 core source tag names; source tag category is not synonymous with a separate non-slot TF node.
- Immutable upstream CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5: 2,628 physical TT records / 2,394,354 word slots.
- Real #173 head full native workflow https://github.com/alexsosn/CopticScriptorium-TF/actions/runs/38258054937 (job 114841142280): 143 TF files, 669,347,470 bytes, process peak 7,847.0 MiB.
- Distinct full CoNLL-U workflow https://github.com/alexsosn/CopticScriptorium-TF/actions/runs/38258055163 (job 114841790478): 174 TF files, 794,868,039 bytes, peak 8,758.7 MiB; 2,361 supplemented records / 2,104,966 words. Workloads not identical; do not infer per-feature savings or per-word cost.
- Historical README 130 TF files / 618,769,322 bytes / 7,157.1 MiB has become a misleading present-tense metric. Its non-slot type enumeration excludes source events, and its #66 follow-up is already merged.

## Research → plan → TDD gates
1. Keep output schema/source logic unchanged; this is researcher-facing discoverability and measured-workload accuracy.
2. RED first: test using Python AST over *actual model.py* (not duplicated type allowlist) to extract every named wrapper type including intervention keys. Assert every one is documented as a backticked native type in the README; assert core native types and strictly labeled current full-source metrics. On baseline main, test fails because README lacks the annotation family section and uses early resource figures.
3. GREEN: revise only README's inventory, resource data, troubleshooting and stale follow-ups. Explain original source wrappers do not imply English/Coptic lexical alignment, nor that a source tag's own attribute implies a new independent word slot. Reference the complete researcher guide for detailed source semantics and the documented provenance restrictions.
4. On exact PR head: run focused #178 tests, repository tests and applicable integration jobs. Skeptically review current source code list and independently read actual CI resource logs. Do not merge merely because tests repeat README constants.
5. No full-source build is needed for *documentation-only* changes: reuse immutable head logs, avoid another 9 GiB, ~15-minute job with identical converter bytes. Keep #177 open pending actual independent researcher action smoke.
