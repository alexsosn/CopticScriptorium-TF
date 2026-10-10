# Issue #75 — complete pinned Coptic OT/LXX coverage inventory (research stage)

## Findings and prior concrete evidence

- Full original `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5` corpus: **2,628** direct + ZIP physical TT records across 565 sparse Git blobs; #69 actual CI reported 2,571 records carrying `verse_n`, 73,844 `verse_n` tags, 29 positioned mid-word verse events, zero unmatched event boundary shapes.
- **Those are not all Coptic OT passages.** Source families `sahidica.nt`, `bohairic.nt`, etc. coexist with `sahidic.ot`, `bohairic.ot`, `sahidic.ruth`, `sahidic.jonah`, `bohairic-jonah`, `bohairic-habakkuk`, and others. A numerical biblical marker without corpus or book evidence must not trigger Greek OT alignment.
- #72 independently reviewed, merged verified source-label-to-real `CenterBLC/LXX@f32a98eddf7eb239aa73ab863d70381e416d5076` verse address candidates. #74 independently reviewed, merged dual native TF module prototype, 3 genuine source documents, 2,104 word slots, 54 candidate reference addresses. These are not scholarly translation correspondences or whole-OT coverage.
- CATSS-TF already pins this CenterBLC/LXX 1935 parent, 57 Greek books / 30,371 verse nodes. Full Coptic OT source book normalization and divergent reference-system conventions are **not yet researched/certified**.

## Research → RED → implementation → test gates (this PR)

1. RED-first unit tests define a conservative, auditable **source metadata evidence classifier**: `ot_candidate`, `nt_candidate`, `conflicting`, `undetermined`. CTS work namespace, source family, literal `meta book/chapter`, and title are evidence; none are a forged LXX equivalence. Do not assume `verse_n` implies OT. Require conflict detection and no automatic classification for unknown corpora.
2. Stream the *entire exact pinned* upstream direct/ZIP TT source under sparse Git, extract **metadata and counts only**, and aggregate by source family: physical records, OT/NT candidates, conflicts, missing chapter/book, verse-marker records/occurrences, distinct literal book labels/CTS work parts, bounded example source IDs. Do not write the original corpora or reconstructed text into repository or artifacts.
3. Fail CI on unexpected 565-blob / 2,628-record inventory size; produce machine-readable deterministic JSON and a small summary in GitHub Actions, with immutable SHA. Do not fail merely because unknown/conflicting classifications exist—those are precisely the audit findings and require separate reviewed choices.
4. Independent code/data adversarial review exact head: ZIP member path parsing, CTS namespace false positives, NT bleed-through, duplicate source records, metadata quoting, bounded output and deterministic ordering, resource usage, derived licensing. No full-corpus alignment claim from this inventory.

## Next implementation steps (follow-up PRs, not automated assumptions)
- Use actual inventory to expand curated Coptic OT family/book rules in batches, real verses vs LXX, and explicit source-edition versification exceptions; test dozens of representative positive and counterexamples.
- Account for all 29 positioned mid-word reference events without whole-word misassignment. For differing versification and Greek subverses create reviewed one-to-many/many-to-one mappings.
- Build *complete* dual native TF modules from verified crosswalk with qualified shared IDs, candidate/uncertain status and witness provenance; independent review and full real-data CI.

## Initial acceptance
- [x] Research source coverage and existing pilot limitations
- [ ] RED unit tests of metadata classifier
- [ ] Immutable full real-source JSON classification matrix
- [ ] CI checks + independently reviewed exact head
- [ ] A second-step, justified book/versification plan based on actual coverage counts
