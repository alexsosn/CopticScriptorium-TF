# Issue #97 — edition- and source-byte-locked Zechariah candidate crosswalk v1

## Research complete (real primary-source gates)
- Pinned Coptic `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5` and pinned CATSS-compatible `CenterBLC/LXX@f32a98eddf7eb239aa73ab863d70381e416d5076`.
- Merged #96 exact source/Greek CI found 26 Zechariah records: **Sahidic** `ot.zech.coptot` chapter1 ends at 1:17, chapter2 begins at 2:1; **Bohairic** `ot.zach.bohairic_ed` chapter1 extends through 1:21, chapter2 begins at 2:1. Greek Rahlfs 1935 Zech1:18..21 nodes absent; Greek Zech2:1..10 nodes present.
- Merged #99, independent reviewed real data CI job `114416677748`: Bohairic 1:18..21 versus Greek 2:1..4 = **4/4** full Brenton English lexical-motif support; Bohairic 2:1..6 versus Greek 2:5..10 = **6/6**; *competing identically-numbered Bohairic 2:1..6 vs Greek 2:1..6* had **0/6** motif support. 17 Bohairic Zech observations, English verse-local tags available; 5 Sahidic, none with unambiguous verse-local English. Public-domain Brenton chapter2 has both the four-horns and measuring-line passages and conventionally numbers the latter 2:1 while Rahlfs parent numbers it 2:5. This justifies **provisional, source-edition-specific reference-number crosswalk**; source English Brenton is NOT independent Coptic/Greek lexical proof.
- Exact source TT SHA-256 from #96 CI: Bohairic chapter 1 `c52322c9e69a68cefe39827c18417a37d291ecbd919f8440adc0c340cf7867bd`, chapter 2 `6521b293392498f22cddd432bfe2bc0a89ef4a244010040a5b8c3d45a5382028`. These lock the source data beyond moving source paths.
- Existing production resolver initially projects same-number `reference_candidate` LXX targets; its genuine Greek parent weft modules and direct pilot include **only** that status. A new `versification_candidate` status must be explicitly accepted everywhere a valid candidate ID is projected. Do not introduce a hidden migration that mislabels moved source references as exact-number matches.

## Research → RED TDD → implement → real full review
1. RED unit tests define exactly two immutable, **10-verse batch rules** (`Boh ot.zach.bohairic_ed` + *exact source SHA*, corpus/dataset, Git commit, CTS/chapter and physical source ID): source Zech1:18..21 → LXX2:1..4 and source Zech2:1..6 → LXX2:5..10. Require source-local CTS/verse markers remain original.
2. Negative controls: Sahidic `ot.zech.coptot`, other works/chapters/verses, old/future upstream SHA/commit, mutable source paths, wrong edition and missing LXX targets. A mismatched *targeted* Bohairic SHA must **fail closed** (ambiguous), never fall back to false-positive same-number candidate.
3. Implement versioned `BOHAIRIC_ZECH_CROSSWALK_VERSION` and single pure remap policy. Source validation occurs before the target `T.nodeFromSection` lookup; only target nodes actually present get stable shared IDs. Mark them `versification_candidate`, not `verified_translation`. Store rule ID in native Coptic `coptic_lxx_ref_evidence` / `coptic_lxx_ref_reason`, existing raw `verse_n/vid_n/verse_vid` remain unchanged.
4. Update both batch and streaming native LXX module projectors to explicitly accept candidate status and preserve it on the Coptic warp. Other sources remain exactly unchanged. Validate no edge linking unrelated warp node integers. Reuse existing real full source/Greek fingerprint gates.
5. Real pinned source CI: process exact two Bohairic source TT chapter records, check all **10** shifted Greek nodes, 0 same-number false candidates, source byte digests, negative Sahidic doc, source word/witness identity, and both TF modules reload onto same pinned parent. No corpus upload/sidecars.
6. Logically independent adversarial final review on exact CI head, comparing actual chapter continuity, language/edition evidence, internal source word and Greek node IDs; never elevate Brenton-English source annotation to independent philological certification.
7. Do not close parent #70/#75/#92 until full corpus-wide validation.

## Acceptance and limitations
- Versioned, explicit 10-verse source-reference **candidate** crosswalk, source-byte-qualified.
- All other positions unchanged; unresolved/missing references visible, duplicate witnesses not discarded.
- Native bilateral TF features, real pinned CI and independent skeptical review.
- A confirmed Coptic→Greek translated-word alignment remains a different scholarly task.
