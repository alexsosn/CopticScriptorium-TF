# Issue #205 — three consecutive adjacent Psalm source2 false IDs

## Research summary (pinned sources, 2026-11-15)
- Merged #203/#204 guarded **only original Bohairic source verse1** of Psalms 3, 17, 51; 100 source words. It did **not** justify a global verse shift. Curated chapter-level first-two-verse original lexical controls in #201/#202 support source1 ≠ same-number Greek title verse.
- Independent published Coptic Scriptorium chapter reading suggests **source verse2** also mismatches identically numbered LXX: Ps3 source2 `ⲟⲩⲟⲛ ⲟⲩ ⲙⲏϣ ϫⲱ` 'many say', Greek Ps3:3 `πολλοὶ λέγουσιν`; Ps17 source2 `ⲡ ϭⲟⲓⲥ ⲡⲉ ⲡⲁ ⲧⲁϫⲣⲟ` 'the Lord is my strength', Greek Ps17:3 `κύριος στερέωμά μου`; Ps51 source2 `ⲡⲉⲕ ⲗⲁⲥ ⲁϥ ⲥⲟϭⲛⲓ` 'your tongue devised', Greek Ps51:4 `ἀδικίαν ἐλογίσατο ἡ γλῶσσά σου`. Greek verse2 is a heading (Ps51), or preceding text (Ps3/17). Exact source-language word forms and Greek source word features **must be verified on the pinned real corpora** before making this a mapping decision.
- Pinned Coptic `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5` `bohairic.ot/bohairic.ot_TT.zip`; Coptic source sha256s: 3 `cbeb4996b0cd142e888bcd630eaac6123af05d7084d49b614066fa9799b5b9d6`, 17 `0fc5384f9baa44f0d4a180539b84b9cf06f5a3be5176360fdf7b27c9451e3af3`, 51 `fd179fe092f1adc0feb4bf4b9c0ae38a001175c18e745db014a8ca6bb7231d64`; exact Greek TF `CenterBLC/LXX@f32a98eddf7eb239aa73ab863d70381e416d5076`.

## Original source-boundary correction after first failed real CI

The first attempted `source2` lexical anchors above were extracted from
**chapter-view line breaks, not original TT verse markers**, and the real
exact-parent test rejected all three on 2026-11-15. This is a failed
research hypothesis, not upstream data corruption.

Exact original TT `Word.verse_n == "2"` observed through [run
43698201981](https://github.com/alexsosn/CopticScriptorium-TF/actions/runs/43698201981):
- Ps3 source2 starts `ⲛⲑⲟⲕ ⲇⲉ` ('you, however') — Greek **3:4** starts
  `σὺ δέ`, not Greek3:3; the former 'many say' is in source1 and Greek3:3.
- Ps17 source2 starts `ⲡⲁ ⲣⲉϥϯ ⲉϩⲣⲏⲓ` ('my protector') — **within Greek17:3**
  (Greek `ὑπερασπιστής`), while source1 has Greek17:3's earlier 'my
  strength'; Greek 17:3 is split across Coptic1 and Coptic2.
- Ps51 source2 starts `ⲙ ⲫ ⲣⲏϯ` ('like ...') — **within Greek51:4**
  (`ὡσεὶ ξυρὸν`), while source1 has Greek51:4's first clause; again
  Greek verse4 is split across Coptic1 and Coptic2.

We will remove temporary short text debugging from CI after the new source2
anchors pass, retain metadata-only artifact, and will NOT assign positive
whole-verse Greek references. The old candidate ID `Greek Ps chapter:2`
is demonstrably false for all three groups; the positive Greek subverse/word
span still requires further source-language adjudication.

## Plan + RED-first gates
1. Unit RED first: for 3 protected physical original Bohairic sources verse2, the resolver must return `ambiguous`, no `shared_id/lxx_node`, retain `source_verse_n="2"`; the already protected verse1 stays blocked; source3 remains **unchanged candidate** (not verified translation), and unrelated Psalm1/149/151 stay unchanged. Forged source TT SHA, CTS/edition/Git revision must fail closed; no reliance on filename only.
2. Source-level acceptance: load authentic Coptic TT ZIP, 3 original SHA and each source2 normalized word group; compare independently curated Coptic short *semantic anchor* sequences and first real Greek native TF words from alternative Ps3:3, Ps17:3, Ps51:4, and demonstrate mismatch with same-number Greek verse2 (by contextual word controls). Log **only** source group count/word count, source/Gk native numeric addresses, Boolean anchored evidence; no text content or licensed corpus distribution.
3. Implementation: extend existing `lxx_psalm_guard.py` to guard verse1+2 for these three exact original physical documents (one versioned rule v2); preserve public legacy function alias if necessary but prefer transparently named `blocked_same_number_psalm_body`. No unexamined chapter-wide shifting and no pretending that an entire Coptic source verse aligns with an entire Greek verse.
4. Run real focused source/LXX CI + 2,628-document full OT coverage + bidirectional native TF module reload regression; pinned source SHA + Greek feature blobs; assert exactly three additional status groups, sum of actual source2 words, prior 100 source1 words intact, other candidate groups unaffected.
5. Independent logically separated adversarial code/data review checks Greek *verse3* and *verse4* prefix lexical evidence, forged pins, false Greek number-to-Greek number inference, possible source3 shared Greek verse subspans, check docs and no sidecars.
6. Merge only after exact-head all relevant CI GREEN. Keep #75/#108/#201 open.

## Scope control
No new Greek positive mapping in this PR, no manual word alignment, no global Psalm numbering arithmetic, no text redistribution.
