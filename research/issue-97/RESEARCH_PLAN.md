# #97 — Edition-specific Zechariah boundary crosswalk: independent sequence audit

## Prior actual evidence (2026-10-11)
- Immutable upstream Coptic `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`; Greek `CenterBLC/LXX@f32a98eddf7eb239aa73ab863d70381e416d5076` (validated by CATSS LXX feature Git hashes).
- Merged #96, CI run 38098829623 / job 114350301131: 26 exact CTS OT Zechariah source records; **Bohairic** `ot.zach.bohairic_ed` 1:18–21 lacks same-number LXX 1:18–21; target `Zech 2:1–4` exists. Sahidic `ot.zech.coptot` starts chapter 2 at 2:1 with the corresponding four-horns narrative in the Greek target; 2:1–2 Bohairic *also* independently match address 2:1–2. The presence of both contiguous Bohairic groups warns that global numerical shifts, and even same-number candidates, may be wrong.
- The #96 evidence reports **only 3 Coptic head words** and 4 Greek head words, which do not establish passage equivalence; generic formulae (e.g. "and I") appear multiple times. The #97 issue proposes tentative Bohairic 1:18..21 → Greek 2:1..4 and Bohairic 2:1..6 → Greek 2:5..10. **Do not encode either as verified** without reading verses and translations from exact upstream source and contrasting independent Sahidic witness.

## RED → plan → real source audit → independent review gates

1. RED-first tests require exact edition-specific CTS (`ot.zach.bohairic_ed` vs `ot.zech.coptot`) and contiguous full verse groups, reject misleading first-word coincidence. Guard normalization/scoring including empty translation and unaligned/overlapping translation spans. All comparisons deterministic and bounded.
2. Parse only the exact 2 Coptic OT ZIPs; extract full **local in-memory** normalized Coptic tokens per verse and associated English translation annotation, without printing or distributing complete texts. Record word/translation lengths, translation source labels, abbreviated evidence, and **pairwise normalized token sequence/overlap scores** for Bohairic 1:18..21 / 2:1..6 against (a) Sahidic 2:1..10 English and (b) neighboring Bohairic passages as a duplication negative control. Beware English translations may derive from distinct sources and may be missing/misaligned.
3. Independently verify actual Greek `Zech 2:1..10` native verse nodes and *Greek word counts*; verify parent Git feature blobs. Do **not** use Greek first-four-token similarity as textual equivalence.
4. Report expected two mapping hypotheses with scores and explicit unknowns, plus competing same-number hypotheses. Fail only on source/parent integrity and missing data, not on unproven scholarly claims. CI printed material bounded; no source/artifact upload.
5. Independently critically review actual run and determine whether evidence supports a narrowly reviewed versioned crosswalk. If inconclusive, publish findings and leave unresolved/competing hypotheses; do not fabricate verse alignment.
6. Only if defensible, add edition-qualified crosswalk as next **separate** RED-tested change; include negative Sahidic/unrelated editions and native TF module reload. Never assume 1:N or 1:1 without source evidence.

Parent issue #70/#75/#92, #95/#96. No semantic sidecars, no source corpus redistribution.
