# Issue #78 — reviewed, batch CTS work aliases for Coptic→LXX reference candidates

## Actual research, not guessed identity
Real pinned full-source report in PR #77 (job 114256875157) counted 1,574 OT candidate physical TT records in 77 source-family×work profiles. The large archives `sahidic.ot` and `bohairic.ot` contain 46 and 24 different raw CTS works respectively. Across families, raw work spellings include `ot.Jonah`/`ot.jonah`, `ot.zach`/`ot.zech`, `ot.pss` (Psalms), `ot.eccl` (Ecclesiastes), and `ot.song` (Song). Example pinned OT ZIP filenames `bohairic.ot_TT.zip!01_Genesis_01.tt`, `!19_Psalmi_001.tt` confirm the archive is not a single book. Corpus families with OT CTS data include `coptic-treebank` and `bohairic-treebank`; their physical witness identity must be preserved, not deduplicated.

Parent book codes are versioned by `CATSS-TF/src/catss_tf/lxx_schema.py` for pinned `CenterBLC/LXX@f32a98eddf7eb239aa73ab863d70381e416d5076` (`Gen`, `Ps`, `Qoh`, `Cant`, `Zech`, etc.). Distinct Greek versions must not be collapsed: `TobBA/TobS`, `Dan/DanTh`, `Sus/SusTh`, `Bel/BelTh`; do NOT choose from CTS `ot.tob`, `ot.dan`, etc. alone. Reference matching is only `reference_candidate` and **not certified Coptic/Greek passage equivalence**; LXX/OT chapter and verse numbering may differ.

## Gates
1. RED tests for multiwork `sahidic.ot` source with `urn:cts:copticLit:ot.gen.ed:1`, Bohairic `ot.pss`, aliases `zach`/`zech` and `Jonah`, undetermined editions, NT contamination, partial/mismatched CTS and `verse_vid`.
2. Implement the curated immutable work alias map and eight **observed** source family gates; require exact document CTS work when using a multiwork source family, and strict per-verse `vid_n` consistency with work/chapter/verse. Known single-book families with no document CTS remain compatible with the already tested three-book pilot; contradictory CTSlit must produce `ambiguous`.
3. Keep ambiguous target editions and unknown CTS work explicitly unclassified; never derive Greek book from path substrings. Existing Coptic TF word slots and source metadata remain untouched.
4. Validate real pinned source direct and ZIP subsets and against an actual pinned Greek TF parent; report observed address-candidate counts and unresolved/ambiguous statuses; cover multiple works per one ZIP. Independent skeptical code/data review before merge.
5. Follow-up #75 full crosswalk/versification exception review and expanded dual modules. Do NOT close #70 from source-ID normalization or candidate address matches alone.
